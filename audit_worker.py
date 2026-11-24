import csv
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

BASE_DIR = Path(__file__).resolve().parent
SENSITIVE_DIR = (BASE_DIR / "sensitive_data").resolve()
REPORTS_DIR = (BASE_DIR / "reports").resolve()

LLM_API_URL = os.getenv("LLM_API_URL", "http://127.0.0.1:11434/v1/chat/completions")
AUDIT_MODEL = os.getenv("OLLAMA_AUDIT_MODEL", "qwen2.5-coder:3b")


def ensure_isolated_dirs() -> None:
    """Garantiza que las carpetas aisladas existan."""
    SENSITIVE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def resolve_sensitive_input(filename: str) -> Path:
    """Valida que el archivo de entrada viva estrictamente dentro de ./sensitive_data/."""
    ensure_isolated_dirs()
    candidate = (SENSITIVE_DIR / filename).resolve()
    if not candidate.is_relative_to(SENSITIVE_DIR) or candidate == SENSITIVE_DIR:
        raise PermissionError(
            f"Acceso denegado: '{filename}' sale del perímetro aislado ./sensitive_data/."
        )
    if not candidate.is_file():
        raise FileNotFoundError(
            f"Archivo no encontrado en ./sensitive_data/: '{filename}'."
        )
    return candidate


def resolve_report_output(report_name: str, fmt: Literal["docx", "txt"]) -> Path:
    """Valida que el reporte de salida se escriba estrictamente dentro de ./reports/."""
    ensure_isolated_dirs()
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(report_name).stem).strip("_")
    if not safe_stem:
        safe_stem = f"auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    target = (REPORTS_DIR / f"{safe_stem}.{fmt}").resolve()
    if not target.is_relative_to(REPORTS_DIR):
        raise PermissionError("Acceso denegado: ruta de salida fuera de ./reports/.")
    return target


def read_sensitive_content(file_path: Path, max_chars: int = 24000) -> str:
    """Lee CSV, JSON, TXT o DOCX desde ./sensitive_data/ en texto estructurado."""
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        raw = file_path.read_text(encoding="utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(raw))
        rows = [" | ".join(row) for row in reader if any(cell.strip() for cell in row)]
        content = "\n".join(rows)
    elif suffix == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
        content = json.dumps(data, ensure_ascii=False, indent=2)
    elif suffix == ".docx":
        doc = Document(str(file_path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                paragraphs.append(" | ".join(cell.text.strip() for cell in row.cells))
        content = "\n".join(paragraphs)
    else:
        content = file_path.read_text(encoding="utf-8", errors="replace")

    if len(content) > max_chars:
        return content[:max_chars] + "\n...[CONTENIDO TRUNCADO POR LIMITE DE CONTEXTO]..."
    return content


def clean_markdown_artifacts(text: str) -> str:
    """Limpia sintaxis Markdown cruda para reportes ejecutivos dirigidos a usuarios no técnicos."""
    cleaned = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    return cleaned.strip()


def sanitize_pii(text: str) -> str:
    """
    Barrera determinística en Python antes de devolver cualquier texto a la nube.
    Bloquea cédulas dominicanas, teléfonos, correos, cuentas largas y nombres etiquetados.
    """
    text = re.sub(r"\b\d{3}-?\d{7}-?\d{1}\b", "[CEDULA_REDACTED]", text)
    text = re.sub(
        r"(?:\+?1[-.\s]?)?\(?(?:809|829|849)\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[PHONE_REDACTED]",
        text,
    )
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL_REDACTED]",
        text,
    )
    text = re.sub(r"\b\d{9,18}\b", "[ACCOUNT_OR_ID_REDACTED]", text)
    text = re.sub(
        r"(?i)(nombre|empleado|titular|cliente|c[eé]dula|tel[eé]fono|correo)\s*:\s*[^\n,;]+",
        r"\1: [PII_REDACTED]",
        text,
    )
    return text


def write_docx_report(
    output_path: Path,
    source_filename: str,
    audit_instruction: str,
    full_local_report: str,
) -> None:
    """Genera un documento Word (.docx) limpio y formal en ./reports/."""
    doc = Document()

    title = doc.add_heading("Reporte de Auditoría Local Confidencial", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT

    meta = doc.add_paragraph()
    meta_run = meta.add_run(
        f"Archivo auditado: {source_filename}\n"
        f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Motor de procesamiento: {AUDIT_MODEL} (100% Local / Air-Gapped)\n"
        f"Objetivo de auditoría: {audit_instruction}"
    )
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor(80, 90, 105)

    doc.add_heading("Resultados y Hallazgos Detallados", level=1)

    clean_body = clean_markdown_artifacts(full_local_report)
    for block in clean_body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.endswith(":") and len(block) < 90:
            doc.add_heading(block[:-1], level=2)
        else:
            p = doc.add_paragraph(block)
            p.paragraph_format.space_after = Pt(6)

    doc.save(str(output_path))


def write_txt_report(
    output_path: Path,
    source_filename: str,
    audit_instruction: str,
    full_local_report: str,
) -> None:
    """Genera un reporte .txt plano y legible sin Markdown crudo en ./reports/."""
    clean_body = clean_markdown_artifacts(full_local_report)
    header = (
        "============================================================\n"
        "REPORTE DE AUDITORIA LOCAL CONFIDENCIAL (AIR-GAPPED)\n"
        "============================================================\n"
        f"Archivo auditado : {source_filename}\n"
        f"Fecha            : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Modelo local     : {AUDIT_MODEL}\n"
        f"Instruccion      : {audit_instruction}\n"
        "============================================================\n\n"
    )
    output_path.write_text(header + clean_body + "\n", encoding="utf-8")


async def run_airgapped_audit(
    filename: str,
    audit_instruction: str,
    report_name: str = "",
    output_format: Literal["docx", "txt"] = "docx",
) -> str:
    """
    Ejecuta la auditoría 100% en local usando salida JSON estructurada:
    1. Lee el archivo exclusivamente desde ./sensitive_data/.
    2. Genera reporte detallado con PII en ./reports/ (.docx o .txt).
    3. Devuelve únicamente métricas agregadas sanitizadas con Regex.
    """
    fmt: Literal["docx", "txt"] = "txt" if str(output_format).lower() == "txt" else "docx"
    input_path = resolve_sensitive_input(filename)
    output_path = resolve_report_output(report_name or f"audit_{input_path.stem}", fmt)
    sensitive_text = read_sensitive_content(input_path)

    system_prompt = (
        "Eres un auditor de datos financieros operando en modo air-gapped. "
        "Responde ÚNICAMENTE con un objeto JSON válido con exactamente estas dos claves de tipo string:\n"
        '1. "reporte_local": texto detallado en español claro (sin Markdown #, ** o `), '
        "incluyendo nombres completos, cédulas, montos y hallazgos específicos para gerencia.\n"
        '2. "resumen_nube": únicamente métricas agregadas, totales, promedios y conteos. '
        "PROHIBIDO incluir nombres propios, cédulas, teléfonos, correos o cuentas individuales en resumen_nube."
    )

    user_prompt = (
        f"Instrucción de auditoría: {audit_instruction}\n\n"
        f"Datos del archivo ({input_path.name}):\n{sensitive_text}"
    )

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            LLM_API_URL,
            json={
                "model": AUDIT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": 2600,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        cleaned_json_text = (
            data["choices"][0]["message"]["content"]
            if "choices" in data
            else data.get("response", "")
        ).strip()

    try:
        parsed = json.loads(cleaned_json_text)
        local_section = str(parsed.get("reporte_local", "")).strip() or cleaned_json_text
        raw_cloud = parsed.get("resumen_nube", "")
        if isinstance(raw_cloud, dict):
            cloud_section = "\n".join(f"- {k}: {v}" for k, v in raw_cloud.items())
        elif isinstance(raw_cloud, list):
            cloud_section = "\n".join(f"- {item}" for item in raw_cloud)
        else:
            cloud_section = str(raw_cloud).strip()
        if not cloud_section:
            cloud_section = "Auditoría completada localmente. Consulta el reporte en ./reports/."
    except json.JSONDecodeError:
        local_section = cleaned_json_text
        cloud_section = (
            "Auditoría completada localmente. Salida no estructurada retenida en local por seguridad; "
            "consulta el reporte generado en ./reports/."
        )

    if fmt == "docx":
        write_docx_report(output_path, input_path.name, audit_instruction, local_section)
    else:
        write_txt_report(output_path, input_path.name, audit_instruction, local_section)

    safe_cloud_summary = sanitize_pii(clean_markdown_artifacts(cloud_section))

    return (
        f"Auditoría local completada (0 bytes de PII enviados a la nube).\n"
        f"Reporte detallado guardado localmente en: reports/{output_path.name}\n\n"
        f"Resumen agregado sanitizado:\n{safe_cloud_summary}"
    )

