# Antigravity Qwen Worker (MCP + Skill)

Arquitectura jerÃ¡rquica **Arquitecto (Cloud) -> Worker (Local)** para **Google Antigravity**. Permite que modelos en la nube (Gemini / Claude) deleguen bloques pesados de cÃ³digo repetitivo, esquemas, CRUDs y pruebas unitarias a un modelo local corriendo en **Ollama** (`qwen3:4b`, `qwen2.5-coder`, etc.) mediante **MCP (Model Context Protocol)**, ahorrando cuota semanal y acelerando la generaciÃ³n de boilerplate.

## Requisitos previos
- Python 3.10 o superior
- [Ollama](https://ollama.com/) instalado y ejecutÃ¡ndose (`ollama serve`)
- Un modelo descargado en Ollama (por defecto `qwen3:4b`): `ollama pull qwen3:4b`

## InstalaciÃ³n rÃ¡pida

### 1. Clonar el repositorio y crear el entorno virtual
    git clone [https://github.com/FelizLopezDev/Qwen_worker_mcp.git](https://github.com/FelizLopezDev/Qwen_worker_mcp.git)
    cd Qwen_worker_mcp
    python -m venv .venv

Activa el entorno e instala las dependencias:
- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
- **macOS / Linux:** `source .venv/bin/activate && pip install -r requirements.txt`

### 2. Instalar el Skill global en Antigravity
Copia la carpeta del skill a tu directorio global de Antigravity:
- **Windows (PowerShell):**
      New-Item -ItemType Directory -Force -Path "$HOME\.gemini\antigravity\skills\delegate-qwen"
      Copy-Item ".\skills\delegate-qwen\SKILL.md" -Destination "$HOME\.gemini\antigravity\skills\delegate-qwen\SKILL.md"

- **macOS / Linux:**
      mkdir -p ~/.gemini/antigravity/skills/delegate-qwen
      cp ./skills/delegate-qwen/SKILL.md ~/.gemini/antigravity/skills/delegate-qwen/SKILL.md

### 3. Registrar el servidor MCP en `mcp_config.json`
AÃ±ade `local-qwen-worker` a tu archivo `~/.gemini/antigravity/mcp_config.json` (ajusta la ruta absoluta segÃºn tu sistema):

    {
      "mcpServers": {
        "local-qwen-worker": {
          "command": "RUTA_ABSOLUTA/Qwen_worker_mcp/.venv/Scripts/python.exe",
          "args": [
            "RUTA_ABSOLUTA/Qwen_worker_mcp/qwen_worker.py"
          ],
          "env": {
            "OLLAMA_MODEL": "qwen3:4b",
            "OLLAMA_URL": "http://localhost:11434/api/generate"
          }
        }
      }
    }

*(En macOS/Linux cambia `.venv/Scripts/python.exe` por `.venv/bin/python`).*

## CÃ³mo funciona la delegaciÃ³n
El skill incluye un **umbral de rentabilidad**:
- **Bloques > 30 lÃ­neas:** El modelo Cloud delega esquemas Pydantic/SQL, endpoints CRUD completos o suites de tests (`pytest`/`Jest`) a `delegar_a_qwen` y luego audita sintaxis, tipos y seguridad.
- **Micro-tareas (< 25 lÃ­neas):** El modelo Cloud las resuelve directamente para evitar latencia innecesaria.

