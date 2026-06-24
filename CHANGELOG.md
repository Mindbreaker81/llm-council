# Changelog

All notable changes to this project will be documented in this file.

## [2.4.0] - 2026-06-24

### Added
- **Custom council type**: Users can choose 2-8 OpenRouter text models and an Orchestrator per message.
- **OpenRouter catalog API**: Added backend endpoints to list, inspect, and validate models for custom councils.
- **Council preset visibility**: Added an API/UI view of active preset models and Orchestrator for Premium, Economic, and Free councils.
- **Model metadata**: Custom council messages store the selected models, Orchestrator, and model metadata snapshot.
- **Backend tests**: Added unit coverage for model catalog filtering, free model detection, custom validation, and council config resolution.
- **Frontend tests**: Added a dependency-free Node test for chunked Server-Sent Events parsing and a Vitest/Testing Library render test for custom council responses.
- **PDF metadata coverage**: Added a frontend test that verifies exported PDF content includes provenance, full model IDs, Orchestrator, and OpenRouter snapshot metadata.

### Improved
- **Streaming robustness**: SSE parsing now buffers partial chunks and handles UTF-8 split across reads.
- **Storage safety**: Conversation JSON writes are atomic and protected by per-conversation locks.
- **Validation**: Council type validation is centralized and custom councils are validated server-side before sending.
- **Logging**: Replaced verbose debug prints with Python logging.
- **Bundle size**: PDF export now loads dynamically, keeping the main frontend bundle smaller.
- **Dependency audit**: Updated frontend dependencies and overrides so `npm audit` reports zero known vulnerabilities.
- **Custom council guidance**: Documented that the active Orchestrator is the final synthesizer for Stage 3.
- **Council UX**: Added creation feedback, input focus, run summaries, clearer stage progress, and Orchestrator wording in Custom mode.
- **PDF export traceability**: PDFs now include export provenance, conversation metadata, full model IDs, peer reviewers, Orchestrator, and Custom council OpenRouter pricing/context snapshots.

### Fixed
- **Council metadata**: Conversation response models now preserve `council_type`.
- **Free context handling**: Streaming Stage 3 now passes the selected `council_type` to context-limit logic.
- **Frontend lockfile**: Regenerated `package-lock.json` so frontend dependencies match `package.json`.
- **New conversation feedback**: Newly created conversations are selected and rendered immediately in the UI.

## [2.3.0] - 2026-02-07

### Changed
- **Language unification**: All user-facing text in the web app is now in English
  - **ChatInterface.jsx**: Alerts, button labels, council type labels (Economic), tooltips translated to English
  - **pdfExport.js**: All PDF content (headers, section titles, table headers, footer), error messages, comments, and date formatting (`es-ES` → `en-US`) translated to English

### Files Modified
- `frontend/src/components/ChatInterface.jsx`: User-facing strings (alerts, Export PDF button, Council Type label, Economic label)
- `frontend/src/utils/pdfExport.js`: PDF content, comments, error messages, locale

## [2.2.0] - 2025-11-27

### Añadido
- **Exportación a PDF con texto seleccionable**: Nueva funcionalidad para exportar conversaciones completas a PDF
  - Botón "Exportar PDF" al final de cada conversación
  - Incluye todos los mensajes del usuario y respuestas del asistente
  - Stage 1: Todas las respuestas individuales de cada modelo (sin reasoning tokens)
  - Stage 2: Todas las evaluaciones completas, rankings extraídos y tabla de rankings agregados
  - Stage 3: Respuesta final del Chairman
  - Formato legible con colores diferenciados por stage
  - **PDFs generados con texto seleccionable y buscable** (no como imágenes)
  - Nombre de archivo automático: `llm-council-[titulo]-[fecha].pdf`

### Mejorado
- **Generación de PDF**: Migrado de html2canvas/jsPDF a pdfmake para generar PDFs con texto real en lugar de imágenes
  - Texto completamente seleccionable y buscable
  - Archivos más pequeños
  - Mejor calidad de renderizado
  - Sin problemas de gráficos partidos o mezcla de colores

### Dependencias
- **pdfmake** (v0.2.11): Librería para generar PDFs con texto seleccionable
- **marked** (v14.1.0): Conversión de Markdown a texto plano para el PDF

### Eliminado
- **html2pdf.js** (v0.10.2): Reemplazado por pdfmake
- **html2canvas** (v1.4.1): Ya no necesario
- **jspdf** (v2.5.2): Ya no necesario

### Archivos Nuevos
- `frontend/src/utils/pdfExport.js`: Utilidad para generar PDFs de conversaciones con pdfmake

### Archivos Modificados
- `frontend/package.json`: Actualizadas dependencias (pdfmake reemplaza html2pdf.js, html2canvas, jspdf)
- `frontend/src/components/ChatInterface.jsx`: Agregado botón de exportar PDF al final de la conversación y lógica de exportación
- `frontend/src/components/ChatInterface.css`: Estilos para el botón de exportar PDF

## [2.1.0] - 2025-11-27

### Añadido
- **Archivo `.env.example`**: Plantilla de configuración para facilitar el setup
- **Soporte para Tailscale y acceso remoto**: Configuración CORS mejorada para permitir acceso desde IPs remotas y dominios Tailscale
- **Variables de entorno para CORS**: Soporte para `ALLOWED_ORIGINS` para agregar orígenes personalizados
- **Configuración Vite mejorada**: Configurado para aceptar conexiones desde cualquier IP (`host: '0.0.0.0'`)

### Mejorado
- **Documentación README**: 
  - Agregada información sobre modelos CHAIRMAN para cada tipo de consejo
  - Instrucciones para Windows (PowerShell y CMD)
  - Aclaración sobre dependencias con Docker (no necesarias)
  - Documentación sobre acceso remoto y Tailscale
- **Seguridad CORS**: Configuración más segura con orígenes específicos en lugar de `["*"]` (aunque mantiene localhost por defecto)
- **Dockerfile backend**: Limpiado para eliminar referencia a archivo eliminado

### Eliminado
- **CLAUDE.md**: Documentación técnica interna innecesaria para usuarios
- **frontend/README.md**: README genérico de Vite sin información relevante
- **modelos.md**: Archivo duplicado/innecesario

### Cambios Técnicos
- **backend/main.py**: 
  - CORS configurado con lista de orígenes permitidos (localhost, Tailscale)
  - Soporte para variable de entorno `ALLOWED_ORIGINS`
  - Comentarios de advertencia sobre seguridad en producción
- **frontend/vite.config.js**: 
  - Configurado `host: '0.0.0.0'` para aceptar conexiones externas
  - Puerto 5173 configurado explícitamente

## [2.0.0] - 2025-01-27

### Añadido

#### Sistema de Consejos Múltiples
- **Tres tipos de consejos**: Implementado sistema para elegir entre consejo Premium, Económico y Free
- **Selección por mensaje**: El usuario puede elegir el tipo de consejo al enviar cada mensaje
- **Indicador visual**: Cada respuesta muestra el tipo de consejo utilizado (💎 Premium, 💰 Económico, 🆓 Free)
- **Badge en conversaciones**: Las conversaciones en el sidebar muestran el tipo de consejo usado

#### Configuración de Modelos
- **Consejo Premium**: Modelos de alto rendimiento (GPT-5.1, Gemini 3 Pro, Claude Opus 4.5, Grok 4)
- **Consejo Económico**: Modelos económicos con buen rendimiento (DeepSeek V3.1, Qwen3, Llama 3.3, Hermes 4)
- **Consejo Free**: Modelos gratuitos con fallback automático (Mistral Small, Grok 4 Fast, GLM-4.5 Air, DeepSeek R1 Distill)

#### Mejoras Técnicas

##### Manejo de Reasoning Tokens
- Extracción automática de contenido final de modelos con reasoning tokens (DeepSeek R1)
- Preservación del contenido original con reasoning tokens para transparencia del usuario
- Eliminación de reasoning tokens en Stage 2 para ahorrar tokens en la ventana de contexto
- Función `extract_final_content()` para procesar tokens de razonamiento (`<think>`, `<reasoning>`, etc.)

##### Sistema de Fallback Automático
- Fallback automático de modelos gratuitos a versiones pagadas cuando fallan
- Mapeo configurable de modelos free a versiones pagadas en `MODEL_FALLBACK_MAP`
- Logging de intentos de fallback para debugging

##### Gestión de Contexto
- Detección automática de límites de contexto según tipo de consejo (32k para free, 128k para economic)
- Resumen automático de resultados de Stage 2 cuando el contexto excede límites
- Función `summarize_stage2_results()` que crea un "Boletín de Calificaciones" conciso
- Función `check_context_limits()` para verificar si se exceden los límites de tokens

#### Backend

##### Nuevos Archivos y Funciones
- `get_council_config()`: Obtiene configuración de modelos según tipo de consejo
- `estimate_token_count()`: Estima el número de tokens en un texto
- `check_context_limits()`: Verifica si el contexto excede límites
- `summarize_stage2_results()`: Resume resultados de Stage 2 para ahorrar tokens

##### Modificaciones en Archivos Existentes
- `backend/config.py`:
  - Agregadas constantes `COUNCIL_TYPE_PREMIUM`, `COUNCIL_TYPE_ECONOMIC`, `COUNCIL_TYPE_FREE`
  - Agregadas configuraciones `COUNCIL_MODELS_ECONOMIC`, `CHAIRMAN_MODEL_ECONOMIC`
  - Agregadas configuraciones `COUNCIL_MODELS_FREE`, `CHAIRMAN_MODEL_FREE`
  - Agregado `MODEL_FALLBACK_MAP` para mapeo de fallback

- `backend/council.py`:
  - Parametrizadas todas las funciones para aceptar `council_models` y `chairman_model`
  - `stage1_collect_responses()` ahora acepta `council_models` como parámetro
  - `stage2_collect_rankings()` ahora acepta `council_models` como parámetro
  - `stage3_synthesize_final()` ahora acepta `chairman_model` y `council_type` como parámetros
  - `run_full_council()` ahora acepta `council_type` como parámetro
  - Agregado soporte para resumen automático cuando el contexto es muy grande

- `backend/openrouter.py`:
  - Agregada función `extract_final_content()` para procesar reasoning tokens
  - Agregada función `get_fallback_model()` para obtener versión pagada de modelos free
  - `query_model()` ahora acepta `extract_final_content_flag` y `use_fallback`
  - `query_models_parallel()` ahora acepta `extract_final_content_flag` y `use_fallback`
  - Implementado fallback automático cuando modelos free fallan

- `backend/main.py`:
  - `CreateConversationRequest` ahora incluye `council_type` (default: "premium")
  - `SendMessageRequest` ahora incluye `council_type` (default: "premium")
  - Validación de tipos de consejo en los endpoints
  - Endpoints actualizados para usar `council_type` del request
  - Agregados logs de depuración para troubleshooting

- `backend/storage.py`:
  - `create_conversation()` ahora acepta `council_type` como parámetro
  - `add_assistant_message()` ahora acepta `council_type` como parámetro
  - `list_conversations()` ahora incluye `council_type` en los metadatos

#### Frontend

##### Modificaciones en Componentes
- `frontend/src/components/ChatInterface.jsx`:
  - Agregado selector de tipo de consejo (Premium/Económico/Free) visible al enviar mensajes
  - Agregado indicador visual del tipo de consejo usado en cada respuesta
  - Estado `councilType` sincronizado con la conversación

- `frontend/src/components/Sidebar.jsx`:
  - Removido selector de tipo de consejo (ahora solo está en ChatInterface)
  - Agregado badge que muestra el tipo de consejo usado en cada conversación
  - Removidas props `councilType` y `onCouncilTypeChange`

- `frontend/src/App.jsx`:
  - Removido estado `newConversationCouncilType`
  - `handleSendMessage()` ahora acepta `councilType` como parámetro
  - `handleNewConversation()` ahora usa "premium" como default
  - Actualizado para pasar `councilType` a `sendMessageStream`
  - Agregado `council_type` a los mensajes del asistente

- `frontend/src/api.js`:
  - `createConversation()` ahora acepta `councilType` como parámetro
  - `sendMessage()` ahora acepta `councilType` como parámetro
  - `sendMessageStream()` ahora acepta `councilType` como parámetro

##### Estilos CSS
- `frontend/src/components/ChatInterface.css`:
  - Agregados estilos para `.council-type-selector`
  - Agregados estilos para `.council-type-option`
  - Agregados estilos para `.council-type-indicator`
  - Ajustes responsive para móviles

- `frontend/src/components/Sidebar.css`:
  - Removidos estilos de `.council-type-selector-sidebar`
  - Agregados estilos para `.council-type-badge`
  - Ajustes en `.conversation-meta` para mostrar badge

### Corregido

- **Bug crítico en `query_models_parallel()`**: Corregido uso incorrecto de argumentos posicionales que causaba timeout de 0 segundos
- **Validación de tipos de consejo**: Agregada validación para asegurar que solo se acepten tipos válidos
- **Manejo de respuestas vacías**: Mejorado el manejo cuando Stage 1 devuelve 0 resultados
- **Persistencia de council_type**: Corregido para que el tipo de consejo se guarde correctamente en cada mensaje

### Mejorado

- **Logging y debugging**: Agregados logs detallados para facilitar troubleshooting
- **Manejo de errores**: Mejorado manejo de errores HTTP con mensajes más descriptivos
- **Documentación**: README.md actualizado con información sobre los tres tipos de consejos
- **UX**: Selector de tipo de consejo más accesible y visible solo cuando es necesario

### Cambios Técnicos

- **Arquitectura**: Sistema modular que permite fácil extensión a más tipos de consejos
- **Rendimiento**: Optimización de tokens mediante resumen automático cuando es necesario
- **Compatibilidad**: Mantenida compatibilidad hacia atrás con conversaciones existentes

### Cambios en esta versión

- **Corrección crítica**: Arreglado bug en `query_models_parallel()` que causaba timeout de 0 segundos debido a argumentos posicionales incorrectos
- **Mejoras en frontend**: Agregada validación robusta de datos y manejo de errores para prevenir pantallas en blanco
- **Actualización de modelos free**: Reemplazado `xai/grok-4-fast:free` (no disponible) por `google/gemini-2.5-flash:free`
- **UI mejorada**: Removido selector de tipo de consejo del sidebar, ahora solo visible al enviar mensajes
- **Indicadores visuales**: Badge de tipo de consejo en conversaciones y en cada respuesta del asistente

## [1.0.0] - Versión Original

Versión inicial del proyecto con soporte para un solo tipo de consejo (Premium).
