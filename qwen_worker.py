import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from mcp.server.mcpserver import MCPServer

from audit_worker import ensure_isolated_dirs, run_airgapped_audit

mcp = MCPServer("local-qwen-worker")

BASE_DIR = Path(__file__).resolve().parent
METRICS_FILE = BASE_DIR / "savings_metrics.json"

OLLAMA_GENERATE_URL = os.getenv("OLLAMA_GENERATE_URL", "http://127.0.0.1:11434/api/generate")
DEFAULT_CODE_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")

CLOUD_USD_PER_1K_TOKENS = 0.01075

SECRET_PATTERNS = [
    (r"\bsk-[A-Za-z0-9_-]{20,}\b", "[OPENAI_OR_API_KEY_REDACTED]"),
    (r"\bAIza[0-9A-Za-z_-]{30,}\b", "[GOOGLE_API_KEY_REDACTED]"),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "[GITHUB_TOKEN_REDACTED]"),
    (r"\bAKIA[0-9A-Z]{16}\b", "[AWS_ACCESS_KEY_REDACTED]"),
    (r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[JWT_REDACTED]"),
    (
        r"(?im)^([A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PWD|CREDENTIAL)[A-Z0-9_]*)\s*=\s*['\"]?[^\s'\"]+['\"]?",
        r"\1=[SECRET_REDACTED]",
    ),
]

DANGEROUS_CODE_PATTERNS = [
    (r"\brm\s+-rf\s+[/~*]", "Comando destructivo 'rm -rf' detectado"),
    (r"\bshutil\.rmtree\s*\(", "Eliminación recursiva 'shutil.rmtree' detectada"),
    (r"Remove-Item\s+.*-Recurse.*-Force", "Comando destructivo 'Remove-Item -Recurse -Force' detectado"),
    (r"\bos\.system\s*\(", "Ejecución directa de shell 'os.system' detectada"),
    (r"\beval\s*\(", "Uso inseguro de 'eval()' detectado"),
]


def redact_secrets(text: str) -> str:
    """Enmascara credenciales y variables sensibles antes de procesar contexto."""
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


def scan_dangerous_code(code: str) -> list[str]:
    """Detecta patrones peligrosos o destructivos en el código devuelto por el modelo."""
    findings = []
    for pattern, message in DANGEROUS_CODE_PATTERNS:
        if re.search(pattern, code, flags=re.IGNORECASE):
            findings.append(message)
    return findings


def validate_python_ast(output: str) -> tuple[bool, str]:
    """
    Extrae bloques ```python ... ``` (o código puro) y valida su sintaxis con ast.parse.
    Retorna (es_valido, detalle).
    """
    blocks = re.findall(r"```python\s*(.*?)```", output, flags=re.DOTALL | re.IGNORECASE)
    candidate = "\n\n".join(blocks).strip() if blocks else output.strip()

    if not re.search(r"^\s*(?:def|async\s+def|class|import|from)\s+", candidate, flags=re.MULTILINE):
        return True, "Texto/código no-Python (AST omitido)"

    try:
        ast.parse(candidate)
        return True, "AST válido (0 errores de sintaxis)"
    except SyntaxError as exc:
        return False, f"SyntaxError en línea {exc.lineno}: {exc.msg}"


def record_telemetry(prompt_tokens: int, completion_tokens: int, ast_passed: bool) -> None:
    """Persiste métricas acumuladas de ahorro y calidad en savings_metrics.json."""
    data = {
        "delegations": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "ast_checked": 0,
        "ast_passed": 0,
        "estimated_usd_saved": 0.0,
        "model": DEFAULT_CODE_MODEL,
        "last_updated": "",
    }
    if METRICS_FILE.exists():
        try:
            data.update(json.loads(METRICS_FILE.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass

    total_new = prompt_tokens + completion_tokens
    data["delegations"] += 1
    data["prompt_tokens"] += prompt_tokens
    data["completion_tokens"] += completion_tokens
    data["total_tokens"] += total_new
    data["ast_checked"] += 1
    if ast_passed:
        data["ast_passed"] += 1
    data["estimated_usd_saved"] = round(
        (data["total_tokens"] / 1000.0) * CLOUD_USD_PER_1K_TOKENS, 4
    )
    data["model"] = DEFAULT_CODE_MODEL
    data["last_updated"] = datetime.now().isoformat(timespec="seconds")

    METRICS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@mcp.tool()
async def delegar_a_qwen(instruccion: str, contexto_codigo: str = "") -> str:
    """
    Delega tareas repetitivas, boilerplate, pruebas unitarias,
    docstrings o refactorizaciones mecánicas al modelo local Qwen,
    aplicando sanitización de secretos, verificación AST y telemetría.
    """
    safe_instruction = redact_secrets(instruccion)
    safe_context = redact_secrets(contexto_codigo)

    prompt_completo = (
        f"{safe_instruction}\n\nCódigo/Contexto:\n{safe_context}"
        if safe_context
        else safe_instruction
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": DEFAULT_CODE_MODEL,
                "prompt": prompt_completo,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2600,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()

    raw_output = payload.get("response", "")
    prompt_tokens = int(payload.get("prompt_eval_count") or len(prompt_completo) // 4)
    completion_tokens = int(payload.get("eval_count") or len(raw_output) // 4)

    ast_ok, ast_note = validate_python_ast(raw_output)
    danger_alerts = scan_dangerous_code(raw_output)
    record_telemetry(prompt_tokens, completion_tokens, ast_ok)

    warnings = []
    if not ast_ok:
        warnings.append(f"[AST_WARNING] {ast_note}")
    if danger_alerts:
        warnings.append(f"[SECURITY_GUARDRAIL] {'; '.join(danger_alerts)}")

    if warnings:
        header = "\n".join(warnings) + "\n\n"
        return header + raw_output
    return raw_output


@mcp.tool()
async def audit_sensitive_file(
    filename: str,
    audit_instruction: str,
    report_name: str = "",
    output_format: Literal["docx", "txt"] = "docx",
) -> str:
    """
    Audita archivos confidenciales (nóminas, PII, registros financieros) 100% en local.
    Lee exclusivamente desde ./sensitive_data/, escribe el reporte detallado con nombres/PII
    en ./reports/ (.docx o .txt) y devuelve a la nube únicamente métricas agregadas sanitizadas.
    """
    result_msg, p_tokens, c_tokens = await run_airgapped_audit(
        filename=filename,
        audit_instruction=audit_instruction,
        report_name=report_name,
        output_format=output_format,
        return_usage=True,
    )
    record_telemetry(prompt_tokens=p_tokens, completion_tokens=c_tokens, ast_passed=True)
    return result_msg


@mcp.tool()
def get_token_savings() -> str:
    """Devuelve el reporte acumulado de tokens locales, ahorro USD y tasa de éxito AST."""
    if not METRICS_FILE.exists():
        return "Aún no hay delegaciones registradas en savings_metrics.json."
    data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    checked = max(1, int(data.get("ast_checked", 1)))
    passed = int(data.get("ast_passed", 0))
    pass_rate = round((passed / checked) * 100.0, 1)
    return (
        f"Modelo activo: {data.get('model')}\n"
        f"Delegaciones completadas: {data.get('delegations')}\n"
        f"Tokens procesados localmente: {data.get('total_tokens'):,}\n"
        f"First-Pass AST Acceptance Rate: {pass_rate}% ({passed}/{checked})\n"
        f"Ahorro estimado en API Cloud: ${data.get('estimated_usd_saved'):.4f} USD"
    )


if __name__ == "__main__":
    ensure_isolated_dirs()
    mcp.run()
