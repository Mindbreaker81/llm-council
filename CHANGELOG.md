# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

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

