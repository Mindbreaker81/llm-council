MODELOS ECONOMICO

Rol	Modelo Recomendado	Justificación Técnica	Costo Est. (Entrada/Salida)
Presidente (Chairman)	DeepSeek V3.1 terminus	deepseek/deepseek-v3.1-terminus
Miembro 1	Qwen3 qwen/qwen3-235b-a22b-thinking-2507
Miembro 2	Llama 3.3 70B Instruct meta-llama/llama-3.3-70b-instruct
Miembro 3	DeepSeek R1 deepseek/deepseek-r1-0528-qwen3-8b
Miembro 4	Hermes 4 70B nousresearch/hermes-4-70b

MODELOS FREE
Presidente	DeepSeek R1 Distill Llama 70B (Free) deepseek/deepseek-r1-distill-llama-70b:free
Miembro 1 Mistral Small 3.1 24B (Free) mistralai/mistral-small-24b-instruct-2501:free
Miembro 2 Grok 4.1 Fast (Free) xai/grok-4-fast:free
Miembro 3 GLM-4.5 Air (Free) z-ai/glm-4.5-air:free
Miembro 4 DeepSeek R1 Distill Qwen 32B deepseek/deepseek-r1-distill-qwen-32b

####################
Detalles de Implementación Técnica e Integración
Al integrar estos modelos en el código de llm-council, se requieren ajustes técnicos específicos para manejar las peculiaridades de los nuevos modelos.

6.1. Manejo de Tokens de Razonamiento (DeepSeek R1)
Modelos como DeepSeek R1 emiten un bloque <think>.

Problema: El modelo "Presidente" en la Etapa 3 podría confundirse si recibe tokens de pensamiento crudos de un miembro, interpretándolos como parte de la respuesta final.

Solución: El middleware debe analizar la salida. Para la "Vista del Usuario", el proceso de pensamiento es valioso (transparencia). Para la etapa de "Revisión por Pares", se recomienda eliminar los tokens de pensamiento para ahorrar espacio en la ventana de contexto, pasando solo la respuesta final a los otros modelos para su calificación. Alternativamente, si el contexto lo permite, incluir el pensamiento permite una revisión más profunda de la lógica y no solo del resultado.

6.2. Gestión de la Ventana de Contexto
Gemini 3.0 Pro tiene una ventana de contexto de millones de tokens. Los reemplazos (Qwen, Llama) típicamente tienen un tope de 128k, y algunos modelos gratuitos pueden tener límites de 32k.

Implicación: Si el usuario pega un libro entero, 128k podría ser ajustado para la etapa de agregación, donde se suman todas las revisiones.

Mitigación: Implementar una arquitectura de "Paso de Resumen". En lugar de alimentar el texto crudo completo de las 4 vueltas anteriores al Presidente, use Mistral Small para resumir las "Revisiones por Pares" en un "Boletín de Calificaciones" conciso que luego se alimenta al Presidente. Esto crea un Consejo jerárquico que ahorra tokens y mantiene la coherencia.

6.3. Configuración de la API
En el archivo .env o de configuración de llm-council, el usuario deberá mapear los IDs de modelo correctamente para OpenRouter.

Antiguo: google/gemini-3.0-pro

Nuevo: deepseek/deepseek-chat (para V3), qwen/qwen-2.5-72b-instruct, meta-llama/llama-3.3-70b-instruct.

Es vital verificar la disponibilidad de los modelos "gratuitos" (:free), ya que pueden estar sujetos a congestión. Se recomienda implementar una lógica de respaldo (fallback) en el código: si el modelo gratuito falla, cambiar automáticamente a la versión pagada de bajo costo (por ejemplo, de mistral-small:free a mistral-small pagado).