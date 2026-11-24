# Local Qwen Worker MCP (`local-qwen-worker`)

Servidor **Model Context Protocol (MCP)** para arquitectura híbrida **Cloud + Local** mediante **Ollama**. Permite que agentes de IA en la nube (Antigravity, Claude Desktop, Cursor) deleguen tareas mecánicas de código y auditen archivos confidenciales **100% en local**, reduciendo costos de API y garantizando que **0 bytes de información sensible (PII)** salgan de la máquina.

---

## Arquitectura del Sistema

* **Orquestador Cloud (Gemini / Claude):** Planificación, arquitectura y razonamiento complejo; recibe únicamente resúmenes agregados sanitizados.
* **Servidor MCP Local (`qwen_worker.py` + `audit_worker.py`):** Expone las herramientas por `stdio`, aplica filtros de seguridad, valida sintaxis AST y gestiona carpetas aisladas.
* **Motor Local (`Ollama` — `qwen2.5-coder:3b`):** Ejecuta generación de código y auditorías completamente offline en la máquina anfitriona.

---

## Herramientas MCP Expuestas

### 1. `audit_sensitive_file` (Auditoría Local *Air-Gapped*)
Procesa nóminas, registros financieros o documentos con datos personales sin exponer el contenido crudo a la nube:
* **Perímetro aislado (`Path.is_relative_to`):** Lee exclusivamente archivos `.csv`, `.json`, `.txt` y `.docx` dentro de `./sensitive_data/`, bloqueando intentos de *path traversal*.
* **Precálculo aritmético determinístico:** En archivos `.csv`, Python calcula previamente conteos, sumas, promedios, mínimos y máximos exactos de columnas numéricas antes de invocar al modelo local, eliminando errores aritméticos en modelos ligeros (3B).
* **Reportes ejecutivos locales:** Guarda el informe detallado (con nombres, cédulas y hallazgos completos) en `./reports/` en formato **Word (`.docx`)** o **texto plano (`.txt`)**, limpiando artefactos de Markdown crudo.
* **Doble barrera de privacidad:** El LLM estructura la salida en JSON separando `reporte_local` de `resumen_nube`, y Python aplica limpieza determinística con expresiones regulares (`sanitize_pii`) para redactar cédulas, teléfonos, correos y cuentas antes de responder al cliente MCP.

### 2. `delegar_a_qwen` (Enrutamiento de Código y Tareas Mecánicas)
Descarga generación de funciones, scripts, pruebas unitarias y transformaciones repetitivas hacia Ollama:
* **Sanitización previa:** Bloquea o enmascara llaves de API (`sk-`, `AIza`, `ghp_`, `AKIA`, JWTs) y comandos destructivos (`rm -rf`) antes de ejecutar.
* **Validación sintáctica automática:** Verifica el código Python generado mediante `ast.parse()` para medir la tasa de éxito en el primer intento (*First-Pass AST Acceptance Rate*).

### 3. `get_token_savings` (Telemetría de Ahorro y Calidad)
Consulta `savings_metrics.json` y reporta de forma acumulada:
* Total de delegaciones y auditorías procesadas localmente.
* Volumen de tokens ejecutados offline.
* Tasa de éxito de validación sintáctica (`AST`).
* Ahorro estimado en dólares frente a tarifas estándar de APIs Cloud.

---

## Estructura del Proyecto

```text
Qwen_worker_mcp/
├── qwen_worker.py          # Servidor FastMCP, filtros de seguridad y telemetría
├── audit_worker.py         # Motor air-gapped, precálculo CSV, sanitización PII y reportes .docx/.txt
├── requirements.txt        # Dependencias (mcp, httpx, python-docx)
├── sensitive_data/         # Carpeta aislada de entrada (ignorada por Git)
├── reports/                # Carpeta aislada de reportes generados (ignorada por Git)
└── README.md