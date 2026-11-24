import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_worker import (
    clean_markdown_artifacts,
    resolve_report_output,
    resolve_sensitive_input,
    sanitize_pii,
    write_docx_report,
    write_txt_report,
)
from qwen_worker import redact_secrets, scan_dangerous_code, validate_python_ast


def test_path_traversal_blocked_on_input():
    with pytest.raises(PermissionError):
        resolve_sensitive_input("../qwen_worker.py")


def test_path_traversal_blocked_on_output():
    target = resolve_report_output("../../malicious_report", "txt")
    assert target.parent.name == "reports"
    assert target.name == "malicious_report.txt"


def test_sanitize_pii_dominican_patterns():
    raw = (
        "Empleado: Juan Perez, cedula 001-1234567-8, "
        "tel 809-555-0192, correo jperez@banco.do, cuenta 987654321012"
    )
    sanitized = sanitize_pii(raw)
    assert "001-1234567-8" not in sanitized
    assert "809-555-0192" not in sanitized
    assert "jperez@banco.do" not in sanitized
    assert "987654321012" not in sanitized
    assert "[CEDULA_REDACTED]" in sanitized
    assert "[PHONE_REDACTED]" in sanitized
    assert "[EMAIL_REDACTED]" in sanitized


def test_redact_secrets_before_ollama():
    env_text = (
        "OPENAI_API_KEY=sk-proj-1234567890abcdefghijklmnop\n"
        "GOOGLE_KEY=AIzaSyDummyKeyValue12345678901234567890\n"
        "DB_PASSWORD=SuperSecretPass2026!\n"
    )
    redacted = redact_secrets(env_text)
    assert "sk-proj-" not in redacted
    assert "AIzaSy" not in redacted
    assert "SuperSecretPass2026!" not in redacted


def test_validate_python_ast_and_dangerous_code():
    good_code = "```python\ndef suma(a: int, b: int) -> int:\n    return a + b\n```"
    bad_code = "```python\ndef rota(:\n    pass\n```"
    dangerous = "import os\nos.system('rm -rf /')"

    assert validate_python_ast(good_code)[0] is True
    assert validate_python_ast(bad_code)[0] is False
    assert len(scan_dangerous_code(dangerous)) >= 2


def test_clean_markdown_and_report_writers(tmp_path: Path):
    md_text = "## Resumen\n**Total:** `RD$50,000`"
    clean = clean_markdown_artifacts(md_text)
    assert "#" not in clean
    assert "**" not in clean
    assert "`" not in clean

    docx_file = tmp_path / "test.docx"
    txt_file = tmp_path / "test.txt"
    write_docx_report(docx_file, "nomina.csv", "Auditar", clean)
    write_txt_report(txt_file, "nomina.csv", "Auditar", clean)

    assert docx_file.exists() and docx_file.stat().st_size > 0
    assert txt_file.exists() and "RD$50,000" in txt_file.read_text(encoding="utf-8")
