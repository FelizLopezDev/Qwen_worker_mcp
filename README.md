# Local Qwen Worker MCP (`local-qwen-worker`)

Servidor **Model Context Protocol (MCP)** para arquitectura híbrida **Cloud + Local** mediante **Ollama**. Permite que agentes de IA en la nube (Antigravity, Claude Desktop, Cursor) deleguen tareas mecánicas de código y auditen archivos confidenciales **100% en local**, reduciendo costos de API y garantizando que **0 bytes de información sensible (PII)** salgan de la máquina.

---

## Arquitectura del Sistema

- **Orquestador Cloud (Gemini / Claude):** Planificación, arquitectura y razonamiento complejo; recibe únicamente resúmenes agregados sanitizados.
- **Servidor MCP Local (`qwen_worker.py` + `audit_worker.py`):** Expone las herramientas por `stdio`, aplica filtros de seguridad, valida sintaxis AST y gestiona carpetas aisladas.
- **Motor Local (`Ollama`):** Ejecuta generación de código y auditorías completamente offline en la máquina anfitriona.

---

## Requisitos de Hardware y Modelos Recomendados

El servidor está optimizado para correr en laptops y estaciones de trabajo estándar sin necesidad de GPU dedicada de servidor, ajustando el modelo según la memoria RAM disponible:

| RAM del Equipo | Modelo Ollama Recomendado | Caso de Uso Ideal |
| :--- | :--- | :--- |
| **8 GB RAM** | `qwen2.5-coder:1.5b` o `qwen2.5-coder:3b` *(por defecto)* | Laptops ligeras; auditoría de CSV/TXT con precálculo determinístico y scripts rápidos. |
| **16 GB RAM** | `qwen2.5-coder:3b` o `qwen3:4b` | Balance óptimo entre velocidad y precisión en generación de código y reportes complejos. |
| **32 GB+ RAM** | `qwen2.5-coder:7b` o `qwen2.5-coder:14b` | Auditorías documentales extensas y refactorización avanzada sin latencia. |

> **Nota:** Para documentos tabulares (`.csv`), `audit_worker.py` precalcula sumas, promedios, mínimos y máximos de forma determinística en Python antes de invocar al modelo, garantizando precisión matemática exacta incluso en modelos ligeros de 1.5B–3B parámetros.

---

## Herramientas MCP Expuestas

### 1. `audit_sensitive_file` (Auditoría Local *Air-Gapped*)
Procesa nóminas, registros financieros o documentos con datos personales sin exponer el contenido crudo a la nube:
- **Perímetro aislado (`Path.is_relative_to`):** Lee exclusivamente archivos `.csv`, `.json`, `.txt` y `.docx` dentro de `./sensitive_data/`, bloqueando intentos de *path traversal*.
- **Precálculo aritmético determinístico:** En archivos `.csv`, Python calcula previamente conteos, sumas, promedios, mínimos y máximos exactos de columnas numéricas antes de pasar el contexto al modelo local.
- **Reportes ejecutivos locales:** Guarda el informe detallado (con nombres, cédulas y hallazgos completos) en `./reports/` en formato **Word (`.docx`)** o **texto plano (`.txt`)**, limpiando artefactos de Markdown crudo.
- **Doble barrera de privacidad:** El LLM estructura la salida en JSON separando `reporte_local` de `resumen_nube`, y Python aplica limpieza determinística con expresiones regulares (`sanitize_pii`) para redactar cédulas, teléfonos, correos y cuentas antes de responder al cliente MCP.

### 2. `delegar_a_qwen` (Enrutamiento de Código y Tareas Mecánicas)
Descarga generación de funciones, scripts, pruebas unitarias y transformaciones repetitivas hacia Ollama:
- **Sanitización previa:** Bloquea o enmascara llaves de API (`sk-`, `AIza`, `ghp_`, `AKIA`, JWTs) y comandos destructivos (`rm -rf`) antes de ejecutar.
- **Validación sintáctica automática:** Verifica el código Python generado mediante `ast.parse()` para medir la tasa de éxito en el primer intento (*First-Pass AST Acceptance Rate*).

### 3. `get_token_savings` (Telemetría de Ahorro y Calidad)
Consulta `savings_metrics.json` y reporta de forma acumulada:
- Total de delegaciones y auditorías procesadas localmente.
- Volumen de tokens ejecutados offline.
- Tasa de éxito de validación sintáctica (`AST`).
- Ahorro estimado en dólares frente a tarifas estándar de APIs Cloud.

---

## Instalación Paso a Paso

### 1. Requisitos previos
- **Python 3.10 o superior**
- **Ollama** instalado y en ejecución (`ollama serve`) con el modelo local descargado:
  ```bash
  ollama pull qwen2.5-coder:3b
  ```

### 2. Clonar el repositorio e instalar dependencias
```bash
git clone [https://github.com/FelizLopezDev/Qwen_worker_mcp.git](https://github.com/FelizLopezDev/Qwen_worker_mcp.git)
cd Qwen_worker_mcp
```

**En Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
```

**En macOS / Linux:**
```bash
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
```

### 3. Conectar a tu cliente MCP (Antigravity, Claude Desktop o Cursor)
Agrega esta configuración en tu archivo `mcp_config.json` apuntando al intérprete de tu entorno virtual y a `qwen_worker.py`:

```json
{
  "mcpServers": {
    "local-qwen-worker": {
      "command": "C:\\Ruta\\A\\Qwen_worker_mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Ruta\\A\\Qwen_worker_mcp\\qwen_worker.py"
      ],
      "env": {
        "OLLAMA_MODEL": "qwen2.5-coder:3b",
        "OLLAMA_AUDIT_MODEL": "qwen2.5-coder:3b"
      }
    }
  }
}
```

*(En macOS/Linux, reemplaza `command` por `/ruta/a/Qwen_worker_mcp/.venv/bin/python`.)*

### 4. Uso rápido
1. Coloca los archivos confidenciales (`.csv`, `.json`, `.txt` o `.docx`) dentro de `./sensitive_data/`.
2. Pídele a tu agente MCP: *"Audita el archivo en `sensitive_data/` y guarda el reporte detallado en Word"*.
3. Consulta el documento completo con PII en `./reports/` mientras el modelo en la nube recibe únicamente las métricas agregadas sanitizadas.

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
```

---

## Variables de Entorno Opcionales

| Variable | Valor por defecto | Descripción |
| :--- | :--- | :--- |
| `OLLAMA_MODEL` | `qwen2.5-coder:3b` | Modelo local usado por `delegar_a_qwen`. |
| `OLLAMA_AUDIT_MODEL` | `qwen2.5-coder:3b` | Modelo local usado por `audit_sensitive_file`. |
| `OLLAMA_GENERATE_URL` | Endpoint local de Ollama | Ruta de generación de texto (configurable para contenedores o puertos personalizados). |
| `LLM_API_URL` | Endpoint OpenAI-compatible local | Ruta para salidas JSON estructuradas en auditoría. |

[![M8ven Score](https://m8ven.ai/badge/mcp/felizlopezdev-qwen-worker-mcp-x2ma8u?v=2ee9b5ac05dafae38908d2aa6f0fe2a1)](https://m8ven.ai/mcp/felizlopezdev-qwen-worker-mcp-x2ma8u?s=readme)
