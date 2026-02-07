# LLM Council

![llmcouncil](images/header2.jpeg)

> **Fork of the original [karpathy/llm-council](https://github.com/karpathy/llm-council)** project with improvements and additional features.

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses OpenRouter to send your query to multiple LLMs, it then asks them to review and rank each other's work, and finally a Chairman LLM produces the final response.

## Modifications in this fork

Compared to the original repository (which only included premium models), this fork adds:

| Original | This fork |
|----------|-----------|
| Single council type (Premium) | **Three types**: 💎 Premium, 💰 Economic, 🆓 Free |
| Fixed model selection | **Per-message council type selection** |
| — | **Automatic fallback**: free models switch to paid if they fail |
| — | **PDF export** with selectable text (pdfmake) |
| — | **Reasoning tokens**: extraction and handling for DeepSeek R1 models |
| — | **Context summarization**: automatic summarization for token limits |
| — | **Remote access**: Tailscale support, configurable CORS |
| — | **Windows**: instructions for PowerShell and CMD |

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

For a detailed record of changes in this fork, see [CHANGELOG.md](CHANGELOG.md).

## Setup

### 1. Configure API Key

Copy the example environment file and add your OpenRouter API key:

**Linux/Mac:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Windows (CMD):**
```cmd
copy .env.example .env
```

Then edit `.env` and add your API key:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Make sure to purchase the credits you need, or sign up for automatic top up.

### 2. Configure Models (Optional)

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

# Premium Chairman model - synthesizes final response
CHAIRMAN_MODEL_PREMIUM = "google/gemini-3-pro-preview"

# Economic Council
COUNCIL_MODELS_ECONOMIC = [
    "qwen/qwen3-235b-a22b-thinking-2507",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-r1-0528-qwen3-8b",
    "nousresearch/hermes-4-70b",
]

# Economic Chairman model - synthesizes final response
CHAIRMAN_MODEL_ECONOMIC = "deepseek/deepseek-v3.1-terminus"

# Free Council
COUNCIL_MODELS_FREE = [
    "mistralai/mistral-small-24b-instruct-2501:free",
    "google/gemini-2.5-flash:free",
    "z-ai/glm-4.5-air:free",
    "deepseek/deepseek-r1-distill-qwen-32b",
]

# Free Chairman model - synthesizes final response
CHAIRMAN_MODEL_FREE = "deepseek/deepseek-r1-distill-llama-70b:free"
```

You can select the council type when sending a message. The selected council type is displayed in each assistant response and in the conversation list.

## Running the Application

**Option 1: Use Docker Compose (Recommended)**

Works on Windows, macOS, and Linux. No need to install dependencies manually - Docker handles everything during the build process.

**Prerequisites:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

```bash
docker compose up -d --build
```

Then open http://localhost:5174 in your browser (backend on port 8001, frontend on port 5174).

**Port Configuration:**
- **Backend**: Port 8001
- **Frontend**: Port 5174 (mapped from container port 5173)

If you have port conflicts, you can modify the ports in `docker-compose.yml`. See the [Port Configuration](#port-configuration) section below for details.

**Option 2: Use the start script**

First, install dependencies:

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

Then run the start script:
```bash
./start.sh
```

**Option 3: Run manually**

First, install dependencies (same as Option 2):

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

Then run each service separately:

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
- **PDF Export**: Export complete conversations to PDF with selectable text
  - Includes all user messages and assistant responses
  - Stage 1: All individual model responses (without reasoning tokens)
  - Stage 2: Complete peer evaluations, extracted rankings, and aggregate rankings table
  - Stage 3: Final Chairman response
  - Click the "Export PDF" button at the end of any conversation

## Port Configuration

### Checking for Port Conflicts

Before running the application, you can check if ports 8001 and 5174 are already in use:

**Using the provided scripts:**

**Linux/Mac:**
```bash
./check-ports.sh
```

**Windows (PowerShell):**
```powershell
.\check-ports.ps1
```

**Manual check:**

**Linux/Mac:**
```bash
# Check port 8001 (backend)
lsof -i :8001
# or
netstat -an | grep 8001

# Check port 5174 (frontend)
lsof -i :5174
# or
netstat -an | grep 5174
```

**Windows (PowerShell):**
```powershell
# Check port 8001 (backend)
netstat -ano | findstr :8001

# Check port 5174 (frontend)
netstat -ano | findstr :5174
```

**Windows (CMD):**
```cmd
netstat -ano | findstr :8001
netstat -ano | findstr :5174
```

### Changing Ports

If you need to change the ports due to conflicts, edit `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "YOUR_BACKEND_PORT:8001"  # Change YOUR_BACKEND_PORT to your desired port
  frontend:
    ports:
      - "YOUR_FRONTEND_PORT:5173"  # Change YOUR_FRONTEND_PORT to your desired port
```

You'll also need to update the frontend API configuration in `frontend/src/api.js` if you change the backend port:

```javascript
const getApiBase = () => {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  return `${protocol}//${hostname}:YOUR_BACKEND_PORT`;  // Update this port
};
```

After making changes, rebuild and restart:
```bash
docker compose down
docker compose up -d --build
```

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API
- **Frontend:** React + Vite, react-markdown for rendering
- **PDF Generation:** pdfmake for generating PDFs with selectable text
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript
- **Containerization:** Docker Compose for easy deployment
