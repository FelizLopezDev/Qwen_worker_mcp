---
name: delegate-qwen
description: Delega bloques medianos o grandes de código mecánico (>30 líneas: esquemas, CRUDs, suites de pruebas, docstrings o refactorizaciones masivas) al modelo local mediante `delegar_a_qwen`. Excluye micro-fragmentos (<30 líneas), arquitectura y seguridad.
---

# Protocolo de Delegación: Arquitecto (Cloud) → Worker (Local)

Actúas como el **Arquitecto Principal**. Tu responsabilidad es el diseño del sistema, la lógica de negocio crítica, la seguridad y la integración final. Delega la generación mecánica de alto volumen al modelo local mediante la herramienta MCP `delegar_a_qwen`.

## Matriz de Decisión

| Delegar a `delegar_a_qwen` (>30 líneas) | Ejecutar directamente en Cloud |
| :--- | :--- |
| **Boilerplate:** Esquemas de BD, modelos Pydantic, interfaces TypeScript y endpoints CRUD estándar. | **Micro-tareas (<30 líneas):** Arreglos puntuales, funciones cortas o ediciones menores (evita latencia innecesaria). |
| **Testing:** Suites completas de pruebas unitarias (`pytest`, `Jest`), mocks y fixtures. | **Arquitectura:** Estructura de carpetas, patrones de diseño y decisiones de estado o concurrencia. |
| **Documentación y datos:** Docstrings de módulos completos o transformaciones extensas de JSON/YAML. | **Seguridad:** Autenticación, autorización, manejo de tokens/secretos y sanitización de inputs. |

## Reglas de Ejecución

1. **Agrupación por lote:** Consolida tareas mecánicas relacionadas en una sola llamada (ej. modelos de una entidad + sus pruebas unitarias) para maximizar el ahorro de cuota.
2. **Contexto acotado:** Envía únicamente las firmas, tipos y especificaciones necesarias; nunca archivos completos.
3. **Prompts deterministas:** Especifica nombres exactos, tipos de datos, librerías y estructura esperada en `instruccion`.
4. **Auditoría obligatoria:** Verifica sintaxis, imports, tipos y casos borde en la salida del worker antes de integrarla al código base.
