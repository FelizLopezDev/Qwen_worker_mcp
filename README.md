# Qwen_worker_mcp

Arquitectura jerárquica **Arquitecto (Cloud) -> Worker (Local)** compatible con **Claude Code**, **Cursor**, **OpenCode** y **Google Antigravity**.

Permite que modelos frontera en la nube (Claude, Gemini, GPT) deleguen bloques pesados de código repetitivo, esquemas, endpoints CRUD y suites de pruebas unitarias a un modelo local corriendo en **Ollama** (`qwen3:4b`, `qwen2.5-coder`, etc.) mediante **MCP (Model Context Protocol)**, ahorrando cuota semanal y acelerando la generación de boilerplate.

## Requisitos previos
- Python 3.10 o superior
- [Ollama](https://ollama.com/) instalado y ejecutándose (`ollama serve`)
- Un modelo descargado en Ollama (por defecto `qwen3:4b`):
  ```bash
  ollama pull qwen3:4b
  ```

## Instalación rápida

### 1. Clonar el repositorio y crear el entorno virtual
```bash
git clone [https://github.com/FelizLopezDev/Qwen_worker_mcp.git](https://github.com/FelizLopezDev/Qwen_worker_mcp.git)
cd Qwen_worker_mcp
python -m venv .venv
```

Activa el entorno e instala las dependencias:
- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

### 2. Instalar el Skill (`SKILL.md`) en tu agente
Copia `skills/delegate-qwen/SKILL.md` al directorio de skills o reglas de tu cliente:
- **Claude Code:** `~/.claude/skills/delegate-qwen/SKILL.md`
- **Google Antigravity:** `~/.gemini/antigravity/skills/delegate-qwen/SKILL.md`
- **Cursor:** Copia el contenido en `.cursor/rules/delegate-qwen.mdc` (o en tus User Rules).
- **OpenCode:** Añádelo en tu directorio global de skills/instrucciones.

### 3. Registrar el servidor MCP
Añade `local-qwen-worker` a la configuración MCP de tu herramienta (`~/.gemini/antigravity/mcp_config.json`, `~/.cursor/mcp.json` o `.mcp.json` en Claude Code):

```json
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
```
*(En macOS/Linux cambia `.venv/Scripts/python.exe` por `.venv/bin/python`).*

## Cómo funciona la delegación
El skill incluye un **umbral de rentabilidad**:
- **Bloques > 30 líneas:** El modelo Cloud delega esquemas Pydantic/SQL, endpoints CRUD completos o suites de tests (`pytest`/`Jest`) a `delegar_a_qwen` y luego audita sintaxis, tipos y seguridad.
- **Micro-tareas (< 25 líneas):** El modelo Cloud las resuelve directamente para evitar latencia innecesaria.
