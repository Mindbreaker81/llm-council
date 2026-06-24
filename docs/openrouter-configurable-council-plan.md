# Plan de mejora: consejo configurable con catalogo de OpenRouter

Fecha de investigacion: 2026-06-24

## Resumen ejecutivo

Si es posible seleccionar modelos dinamicamente sin romper el consejo actual.
OpenRouter expone un catalogo de modelos por API con identificador, nombre, precios,
modalidades, parametros soportados y limites de contexto. La app puede usar ese
catalogo para construir un cuarto tipo de consejo, `custom`, manteniendo intactos
los presets actuales: `premium`, `economic` y `free`.

La recomendacion es no reemplazar de golpe la configuracion actual de
`backend/config.py`. Primero conviene convertirla en presets estables y anadir una
capa de catalogo/validacion para selecciones personalizadas. Asi el flujo de tres
fases sigue igual: Stage 1 consulta a N modelos, Stage 2 esos modelos evaluan las
respuestas anonimizadas, y Stage 3 un chairman sintetiza.

## Lo que permite OpenRouter

Fuentes oficiales:

- Models API: https://openrouter.ai/docs/guides/overview/models
- Models API filtrada por usuario/key: https://openrouter.ai/docs/api/api-reference/models/list-models-user
- Free Models Router: https://openrouter.ai/openrouter/free

Endpoints relevantes:

- `GET https://openrouter.ai/api/v1/models`
- `GET https://openrouter.ai/api/v1/models/user`
- `GET https://openrouter.ai/api/v1/model/{author}/{slug}`

Campos utiles del catalogo:

- `id`: slug que se manda en `model`, por ejemplo `google/gemini-2.5-flash`.
- `name`: nombre visible para la UI.
- `pricing.prompt`, `pricing.completion`, `pricing.request`: coste por token o request.
- `architecture.input_modalities` y `architecture.output_modalities`: texto, imagen, audio, etc.
- `top_provider.context_length`: ventana de contexto.
- `top_provider.max_completion_tokens`: limite de salida.
- `supported_parameters`: soporte para `tools`, `structured_outputs`, `reasoning`, `temperature`, etc.
- `per_request_limits`: restricciones especificas, si existen.

Consulta real realizada con la key local:

- `GET /api/v1/models?output_modalities=text` devolvio 339 modelos de texto.
- `GET /api/v1/models/user` tambien devolvio 339 modelos para esta key.
- Filtrando modelos con `prompt == 0`, `completion == 0` y `request == 0`, aparecieron 26 candidatos gratuitos con salida de texto.

Nota: `openrouter/free` existe como router automatico gratuito. Es util como opcion
rapida, pero para un consejo conviene preferir modelos concretos, porque si todos
los puestos usan el mismo router se pierde diversidad controlada y reproducibilidad.

## Como detectar modelos gratis

Regla practica (OpenRouter devuelve los precios como strings, por ejemplo
`"0.0000001"`, asi que hay que parsear a float, no comparar contra `"0"`):

```text
float(pricing.prompt or 0) <= 0
float(pricing.completion or 0) <= 0
float(pricing.request or 0) <= 0
```

Ademas, muchos gratuitos llevan sufijo `:free`, pero no debe ser la unica regla.
En la consulta aparecieron modelos gratuitos sin sufijo obvio y routers como
`openrouter/free`.

Ejemplos de modelos gratuitos detectados en la consulta:

- `cohere/north-mini-code:free`
- `nvidia/nemotron-3-ultra-550b-a55b:free`
- `openrouter/owl-alpha`
- `poolside/laguna-m.1:free`
- `google/gemma-4-31b-it:free`
- `nvidia/nemotron-3-super-120b-a12b:free`
- `openai/gpt-oss-120b:free`
- `qwen/qwen3-coder:free`
- `meta-llama/llama-3.3-70b-instruct:free`
- `openrouter/free`

La lista debe refrescarse desde la API, no hardcodearse, porque cambia con el
tiempo.

## Diseno propuesto

### 1. Mantener presets actuales

Conservar:

- `premium`
- `economic`
- `free`

Estos presets deberian seguir funcionando aunque OpenRouter este caido o cambie el
catalogo. La configuracion local sigue siendo el fallback estable.

### 2. Anadir tipo `custom`

Nuevo payload sugerido para enviar mensaje:

```json
{
  "content": "Pregunta del usuario",
  "council_type": "custom",
  "custom_council": {
    "models": [
      "anthropic/claude-sonnet-4.6",
      "google/gemini-2.5-flash",
      "deepseek/deepseek-v4-flash"
    ],
    "chairman_model": "google/gemini-2.5-flash"
  }
}
```

Reglas minimas:

- `models`: entre 2 y 8 modelos. Recomendado: 3 o 4.
- `chairman_model`: obligatorio para `custom`, o por defecto el primer modelo seleccionado.
- Todos los modelos deben existir en el catalogo o pasar un lookup individual.
- Todos deben soportar entrada `text` y salida `text`.
- Excluir embeddings, imagen pura, audio puro y modelos sin salida textual.
- Avisar si el contexto de algun modelo es pequeno para Stage 2/3.

### 3. Backend de catalogo

Crear modulo nuevo:

```text
backend/model_catalog.py
```

Responsabilidades:

- Consultar `GET /api/v1/models/user` con la key local.
- Cachear respuesta en memoria con TTL, por ejemplo 15 minutos.
- Exponer funciones:
  - `list_models(filters)`
  - `get_model(model_id)`
  - `is_free_model(model)`
  - `estimate_model_cost(model, input_tokens, output_tokens)`
  - `validate_custom_council(models, chairman_model)`

Endpoints nuevos:

```text
GET /api/models
GET /api/models/{author}/{slug}
POST /api/councils/validate
```

Filtros de `GET /api/models`:

- `free_only=true`
- `text_only=true`
- `supports=tools,structured_outputs,reasoning`
- `min_context=32000`
- `sort=pricing-low-to-high|context-high-to-low|most-popular`
- `q=gemini`

Notas de integracion:

- El endpoint publico `GET /api/v1/models` no requiere auth y es el fallback
  seguro; usar `GET /api/v1/models/user` solo si se confirma que existe para la key.
- `POST /api/councils/validate` es solo ayuda para la UI. La validacion de
  `custom_council` debe repetirse SIEMPRE en servidor al enviar el mensaje;
  nunca confiar en lo que manda el cliente.
- `run_full_council` y `get_council_config` hoy solo aceptan `council_type`.
  Para `custom` hay que extenderlos con modelos/chairman dinamicos validados,
  por ejemplo `get_council_config(council_type, custom_council=None)` que
  devuelva la config explicita cuando `council_type == "custom"`.
- Los modelos custom no tienen entrada en `MODEL_FALLBACK_MAP`, asi que si uno
  falla no hay red de seguridad: documentar el fallo por modelo en Stage 1 y
  continuar con los que respondan, en vez de abortar todo el consejo.

### 4. UI de seleccion

Anadir una cuarta opcion junto a Premium/Economic/Free:

- `Custom`

La UI deberia tener:

- Buscador de modelos.
- Filtros: gratis, baratos, populares, contexto grande, razonamiento, tools.
- Tabla/lista con nombre, slug, precio por 1M input/output, contexto y badges.
- Selector multiple para miembros del consejo.
- Selector separado para chairman.
- Estimacion aproximada de coste antes de enviar.

Importante: no cargar 339 modelos en componentes pesados sin virtualizacion si la
lista crece. Para esta escala, una tabla filtrada simple aun vale.

### 5. Persistencia

Guardar en cada mensaje assistant:

```json
{
  "role": "assistant",
  "council_type": "custom",
  "custom_council": {
    "models": ["..."],
    "chairman_model": "..."
  },
  "stage1": [],
  "stage2": [],
  "stage3": {}
}
```

Guardar tambien un snapshot opcional de metadatos de modelo usados en ese momento:

```json
{
  "model_metadata": {
    "google/gemini-2.5-flash": {
      "name": "Google: Gemini 2.5 Flash",
      "pricing": {"prompt": "...", "completion": "..."},
      "context_length": 1048576
    }
  }
}
```

Esto evita que una conversacion antigua cambie visualmente si OpenRouter cambia
precios o nombres despues.

## Cambios necesarios para no romper el consejo

Antes o durante `custom`, corregir estos puntos:

1. Tipar la respuesta del endpoint no-streaming con un response_model Pydantic
   (hoy devuelve un dict suelto). `council_type` ya viaja en `metadata`, el
   problema es la falta de tipado, no la ausencia del campo.
2. Pasar `council_type` a `stage3_synthesize_final` tambien en la ruta streaming
   (hoy se omite en `main.py`, rompe la deteccion de limite de contexto `free`).
3. Arreglar el parser SSE del frontend: mantener un buffer entre chunks para
   eventos partidos y usar `decoder.decode(value, {stream: true})` para no
   romper caracteres UTF-8 multibyte a caballo entre lecturas.
4. Sustituir prints de debug por logging con niveles.
5. Validar `OPENROUTER_API_KEY` al arrancar o devolver error claro.
6. Hacer persistencia atomica o migrar a SQLite antes de permitir operaciones mas complejas.
7. Centralizar la validacion de `council_type` (hoy la lista `valid_types` esta
   duplicada en `send_message` y `send_message_stream`) para no olvidar `custom`
   en uno de los dos sitios.

## Riesgos y mitigaciones

Riesgo: modelos gratis cambian o desaparecen.
Mitigacion: cache corto, validacion al enviar, fallback claro y presets estables.

Riesgo: el usuario elige modelos incompatibles.
Mitigacion: validar modalidades text->text y bloquear modelos de embeddings/audio/imagen pura.

Riesgo: coste inesperado en consejos personalizados.
Mitigacion: mostrar precio por 1M tokens, estimacion previa y etiqueta de coste.
Tener en cuenta que con N modelos el flujo hace ~2N+1 llamadas (Stage 1: N,
Stage 2: N, Stage 3: 1), asi que el coste crece con N. Anadir un tope de precio
opcional (guardrail) y/o un feature flag para evitar abuso si la app es publica.

Riesgo: un modelo custom falla y no tiene fallback definido.
Mitigacion: registrar el fallo por modelo, seguir con los que respondan y avisar
en UI; no abortar todo el consejo por un solo modelo caido.

Riesgo: el chairman elegido tiene contexto pequeno y no cabe Stage 1 + Stage 2.
Mitigacion: el contexto del chairman es el limite real de Stage 3; validar su
`context_length`, resumir Stage 2 (ya existe `summarize_stage2_results`) y avisar.

Riesgo: Stage 2/3 supera contexto en modelos pequenos.
Mitigacion: usar `top_provider.context_length`, avisar en UI y resumir antes.

Riesgo: `openrouter/free` usado varias veces produce respuestas poco reproducibles.
Mitigacion: permitirlo, pero marcarlo como router dinamico y recomendar modelos concretos.

## Fases recomendadas

### Fase 1: saneamiento

- Corregir `council_type` en response models.
- Corregir `council_type` en streaming Stage 3.
- Arreglar parser SSE.
- Validar key y limpiar logs.
- Anadir pruebas unitarias para ranking parser, validacion de consejo y SSE parser.

### Fase 2: catalogo backend

- Crear `backend/model_catalog.py`.
- Implementar cache TTL.
- Implementar endpoints `GET /api/models` y `POST /api/councils/validate`.
- Normalizar precios a USD por 1M tokens para UI.
- Detectar gratis por pricing, no solo por sufijo `:free`.

### Fase 3: consejo custom backend

- Extender `SendMessageRequest` con `custom_council`.
- Anadir `COUNCIL_TYPE_CUSTOM = "custom"`.
- Cambiar `get_council_config` para aceptar config dinamica validada.
- Guardar `custom_council` y metadata snapshot en mensajes.

### Fase 4: UI

- Anadir selector `Custom`.
- Crear buscador/lista de modelos.
- Mostrar precios, contexto, capacidades y badge gratis.
- Validar seleccion antes de enviar.
- Mostrar estimacion de coste y advertencias.

### Fase 5: persistencia robusta

- Opcion minima: locks por conversacion y escritura atomica JSON.
- Opcion recomendable: SQLite con tablas `conversations`, `messages`,
  `model_snapshots` y `custom_councils`.

## Decision recomendada

Implementar `custom` como extension incremental, no como reemplazo de los presets.
La API de OpenRouter da suficiente informacion para seleccionar modelos, estimar
costes y detectar gratuitos. El mayor trabajo no es la consulta al catalogo, sino
la validacion, la UI y la persistencia para que las conversaciones sigan siendo
reproducibles.
