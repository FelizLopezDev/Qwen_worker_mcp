import os
import httpx
from mcp.server.mcpserver import MCPServer

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120.0"))

mcp = MCPServer("local-qwen-worker")

@mcp.tool()
async def delegar_a_qwen(instruccion: str, contexto_codigo: str = "") -> str:
    """
    Delega la generación de bloques medianos o grandes de código repetitivo,
    boilerplate, pruebas unitarias, docstrings o refactorizaciones mecánicas
    al modelo local en Ollama.
    """
    prompt_completo = (
        f"{instruccion}\n\nCódigo/Contexto:\n{contexto_codigo}"
        if contexto_codigo
        else instruccion
    )

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt_completo,
                "stream": False,
                "options": {
                    "temperature": 0.1
                },
            },
        )
        response.raise_for_status()
        return response.json().get("response", "")

if __name__ == "__main__":
    mcp.run()
