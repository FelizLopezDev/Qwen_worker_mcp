# Qwen Worker MCP (local-qwen-worker)

Servidor **Model Context Protocol (MCP)** hibrido que conecta orquestadores en la nube con modelos locales en **Ollama** (qwen2.5-coder:3b) para delegacion de codigo y **Auditoria Local Aislada (Air-Gapped Audit)** con cero exfiltracion de PII.

## Seguridad y Gobernanza
- **Air-Gapped Audit (audit_worker.py):** lectura aislada en ./sensitive_data/, reportes ejecutivos en ./reports/ (.docx/.txt) y sanitizacion Regex deterministica de PII antes de retornar metricas agregadas a la nube.
- **Hardening (qwen_worker.py):** redaccion de secretos salientes, validacion sintactica ast.parse, guardrail de comandos destructivos y telemetria en savings_metrics.json.

## Benchmarks (Operacion Fundir el Modelo)
| Metrica | Resultado |
|---|---|
| Modelo local | qwen2.5-coder:3b |
| Delegaciones | 88 |
| Tokens locales | 200,946 |
| Ahorro Cloud | .1606 USD |
| Codigo generado | 68 archivos / 11,580 lineas |
| Tests Vitest | 71/71 pasando (1.14 s) |
