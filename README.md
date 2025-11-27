# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses OpenRouter to send your query to multiple LLMs, it then asks them to review and rank each other's work, and finally a Chairman LLM produces the final response.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for project management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Make sure to purchase the credits you need, or sign up for automatic top up.

### 3. Configure Models (Optional)

The application supports three types of councils:

- **Premium**: High-performance models (GPT-5.1, Gemini 3 Pro, Claude Opus 4.5, Grok 4)
- **Economic**: Cost-effective models with good performance (DeepSeek V3.1, Qwen3, Llama 3.3, etc.)
- **Free**: Free models with automatic fallback to paid versions if unavailable

Edit `backend/config.py` to customize the council models for each type:

```python
# Premium Council
COUNCIL_MODELS_PREMIUM = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "x-ai/grok-4",
]

# Economic Council
COUNCIL_MODELS_ECONOMIC = [
    "qwen/qwen3-235b-a22b-thinking-2507",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-r1-0528-qwen3-8b",
    "nousresearch/hermes-4-70b",
]

# Free Council
COUNCIL_MODELS_FREE = [
    "mistralai/mistral-small-24b-instruct-2501:free",
    "google/gemini-2.5-flash:free",
    "z-ai/glm-4.5-air:free",
    "deepseek/deepseek-r1-distill-qwen-32b",
]
```

You can select the council type when sending a message. The selected council type is displayed in each assistant response and in the conversation list.

## Running the Application

**Option 1: Use Docker Compose (Recommended)**
```bash
docker compose up -d --build
```

Then open http://localhost:5174 in your browser (backend on port 8001, frontend on port 5174).

**Option 2: Use the start script**
```bash
./start.sh
```

**Option 3: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Usage

1. **Create a Conversation**: Click "+ New Conversation" in the sidebar
2. **Select Council Type**: Choose Premium, Economic, or Free using the selector above the message input
3. **Ask a Question**: Type your question and send it
4. **View Results**: 
   - Stage 1 shows individual responses from each model
   - Stage 2 shows peer rankings and evaluations
   - Stage 3 shows the final synthesized answer
   - Each response displays the council type used (💎 Premium, 💰 Economic, 🆓 Free)

## Features

- **Three Council Types**: Choose between Premium, Economic, or Free models when sending messages
- **Council Type Display**: Each response shows which council type was used (💎 Premium, 💰 Economic, 🆓 Free)
- **Automatic Fallback**: Free models automatically fallback to paid versions if unavailable
- **Reasoning Token Handling**: Properly handles reasoning tokens from models like DeepSeek R1
- **Context Management**: Automatically summarizes large contexts for models with token limits (32k for free, 128k for economic)
- **Transparency**: View original reasoning tokens while saving tokens in internal stages
- **Per-Message Council Selection**: Choose different council types for different messages in the same conversation

## Technical Details

### Council Type Selection
- Council type is selected per message, not per conversation
- You can use different council types for different messages in the same conversation
- The council type used is displayed in each assistant response
- Conversations show the council type in the sidebar list

### Model Configuration
- **Premium Models**: High-performance models for best quality
- **Economic Models**: Cost-effective alternatives with good performance
- **Free Models**: Free tier models with automatic fallback to paid versions on failure

### Advanced Features
- **Reasoning Token Extraction**: Automatically extracts final content from reasoning models (DeepSeek R1) while preserving original for transparency
- **Context Summarization**: For free models with 32k token limits, Stage 2 results are automatically summarized before passing to the Chairman
- **Error Handling**: Failed models are excluded from results, and free models automatically try paid fallback versions

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript
- **Containerization:** Docker Compose for easy deployment
