---
name: delegate-qwen
description: Delega generación de bloques medianos o grandes de código repetitivo (>30 líneas: múltiples esquemas Pydantic, endpoints CRUD completos, suites de pruebas unitarias, docstrings masivos o refactorizaciones mecánicas) al modelo local Qwen mediante la herramienta MCP `delegar_a_qwen`. NO lo uses para micro-fragmentos de menos de 25 líneas ni para arquitectura o seguridad.
---

# Protocolo de Delegación: Arquitecto (Cloud) → Worker (Qwen Local)

Actúas como el **Arquitecto Principal**. Tu responsabilidad es el diseño del sistema, la lógica de negocio compleja, la seguridad y la integración final. Para optimizar cuota y velocidad, debes delegar bloques sustanciales de trabajo mecánico al modelo local en Ollama mediante la herramienta MCP `delegar_a_qwen`.

## Umbral de rentabilidad (Regla de oro)
- **NO delegues micro-tareas (<25-30 líneas):** Si solo necesitas un arreglo corto, una interfaz simple o una función de pocas líneas, escríbelo tú directamente; el costo de ida y vuelta de la herramienta MCP supera el ahorro.
- **SÍ delega bloques pesados (>30 líneas):** Agrupa varias tareas mecánicas en una sola llamada a `delegar_a_qwen` (por ejemplo: todos los modelos de una entidad + sus pruebas unitarias en una misma instrucción).

## Cuándo delegar obligatoriamente (en bloques)
1. **Boilerplate y estructuras:** Esquemas completos de base de datos, múltiples modelos Pydantic, interfaces/tipos de TypeScript, endpoints CRUD estándar.
2. **Testing:** Suites completas de pruebas unitarias (pytest, Jest), mocks y fixtures extensos.
3. **Documentación y formato:** Docstrings de módulos enteros, README detallados o conversión de archivos JSON/YAML grandes.

## Cuándo NO delegar (Hazlo tú)
- Diseño de arquitectura, estructura de carpetas o elección de patrones.
- Debugging complejo o errores de estado/concurrencia.
- Código crítico de seguridad (autenticación, manejo de tokens, permisos, sanitización de inputs).

## Reglas de ejecución
1. **Contexto acotado:** Nunca envíes archivos enteros a Qwen. Envía únicamente las firmas, interfaces necesarias y especificaciones exactas.
2. **Prompts deterministas:** Redacta la `instruccion` con tipos de datos, nombres exactos y librerías requeridas.
3. **Auditoría obligatoria:** Revisa la sintaxis, casos borde e imports de la respuesta de Qwen antes de escribirla en el archivo final.
