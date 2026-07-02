# Qwen3.6-27B Telegram Bot via llama.cpp

> **Work in Progress** — this project is actively being built out. Features and documentation may be incomplete or subject to change.

Run the Qwen3.6-27B language model locally using llama.cpp in a Docker container and expose it via a Telegram bot. Users send messages to a Telegram bot, which forwards them to the llama.cpp inference server and returns the model's response. Messages can optionally be routed through LangChain or LangGraph instead of the raw HTTP call — see [Message Modes](#message-modes).

---

## Architecture

```
Telegram User
     │
     ▼
telegram-bot (Python, Docker)
     │  HTTP POST /v1/chat/completions
     ▼
llama-server (llama.cpp, Docker + CUDA)
     │
     ▼
Qwen3.6-27B-Q4_K_M.gguf (GPU memory)
```

Two services in `docker-compose.yml`:

- **llama-server** — llama.cpp's built-in HTTP server. Loads the model once into GPU memory and serves all requests. Exposes an OpenAI-compatible REST API.
- **telegram-bot** — Lightweight Python bot that bridges Telegram messages to the llama-server API.

---

## Target Hardware

- **GPU**: NVIDIA RTX A4000 Ada (20 GB VRAM)
- **RAM**: 32 GB system RAM
- **OS**: Windows 10 with WSL2

---

## Model Preparation

### Option A — Download a pre-quantized GGUF

Search Hugging Face for `Qwen3.6-27B GGUF` from known quantizers (e.g. `bartowski`, `unsloth`).

```powershell
hf download <repo-name> <filename>-Q4_K_M.gguf --local-dir .\models\
```

### Option B — Convert from HF weights

```bash
git clone https://github.com/ggml-org/llama.cpp.git
pip install -r llama.cpp/requirements.txt
hf download Qwen/Qwen3.6-27B --local-dir ./Qwen3.6-27B/
python llama.cpp/convert_hf_to_gguf.py ./Qwen3.6-27B/ \
  --outfile ./models/Qwen3.6-27B-F16.gguf --outtype f16
```

Then quantize to Q4_K_M:

```powershell
docker run --rm --gpus all `
  -v "${PWD}\models:/models" `
  ghcr.io/ggml-org/llama.cpp:full-cuda --quantize `
  /models/Qwen3.6-27B-F16.gguf `
  /models/Qwen3.6-27B-Q4_K_M.gguf `
  Q4_K_M
```

---

## Quick Start

### Prerequisites

- WSL2 enabled (`wsl --install`, then restart)
- NVIDIA driver ≥ 470.76
- Docker Desktop (WSL2 backend, NVIDIA Container Toolkit included)
- Hugging Face CLI (`hf`) for model download

### 1. Configure environment

```powershell
Copy-Item .env.example .env
notepad .env   # paste your TELEGRAM_BOT_TOKEN
```

### 2. Place the model

Put `Qwen3.6-27B-Q4_K_M.gguf` in `./models/`.

### 3. Find your Telegram user ID (first time only)

The bot restricts access to a single authorised user via `TELEGRAM_USER_ID`. To find your ID:

1. In `telegram-bot/bot.py`, uncomment the `retrieve_user_id` function and its handler (lines 40–42 and 47), and comment out the `handle_message` handler on line 48.
2. Build and start the bot: `docker-compose up --build`
3. Send any message to your bot on Telegram.
4. Check the logs — your user ID will be printed: `docker-compose logs telegram-bot`
5. Copy the ID into `TELEGRAM_USER_ID` in your `.env` file.
6. Undo the changes to `bot.py` (re-comment `retrieve_user_id`, uncomment `handle_message`) and restart: `docker-compose up --build`

### 4. Build and run

```powershell
docker-compose up --build
```

First build takes 10–20 minutes (compiles llama.cpp with CUDA). Once you see:

```
llama server listening at http://0.0.0.0:8080
```

Send any message to your Telegram bot and it will respond.

---

## Message Modes

Prefix a message to route it through a different code path:

| Prefix | Mode | Behavior |
|---|---|---|
| *(none)* | raw | Direct HTTP call to `llama-server`. Stateless, single-turn. Default behavior. |
| `//chain <text>` | LangChain | A LangChain LCEL chain against the same `llama-server` endpoint. Stateless, single-turn. |
| `//graph <text>` | LangGraph | A LangGraph agent with per-chat conversation memory (in-process, cleared on restart) — the only mode that remembers earlier turns in the same chat. |

---

## Monitoring

```powershell
docker-compose logs -f              # all services
docker-compose logs -f llama-server
docker-compose logs -f telegram-bot
nvidia-smi                          # GPU utilisation
curl.exe http://localhost:8080/health
docker-compose down                 # stop everything
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| GPU not detected in Docker | Enable WSL2 backend in Docker Desktop; update NVIDIA driver |
| OOM / killed | Reduce `--ctx-size` to 8192 or `--n-gpu-layers` to 40 |
| Model file not found | Verify `dir models\` and that `MODEL_FILE` in `.env` matches |
| Bot sends no reply | Check `TELEGRAM_BOT_TOKEN`; check llama-server health endpoint |
| CUDA build fails | Match the `nvidia/cuda` image tag to your driver's CUDA version (`nvidia-smi`) |
| Slow responses despite GPU | Check `nvidia-smi` during inference; increase `--n-gpu-layers` |

---

## Roadmap / Checklist

- [x] Download LLM Model
- [x] Create Docker container
- [x] Run LLM Model in Docker container with llama server
- [x] Set up Telegram bot
- [x] Add langchain and langgraph capabilities
- [ ] Add tools and nodes for langchain and langgraph
- [ ] Add Obsidian MCP capabilities — connect the bot to an Obsidian vault via MCP so it can read and write notes, search knowledge base entries, and surface relevant context in responses
- [ ] Build custom MCP client and server — implement a personal MCP client/server from scratch and progressively add tools (e.g. web search, file I/O, calendar, shell commands) to extend what the bot can do

---

## Project Structure

```
project-root/
├── README.md
├── CLAUDE.md
├── docker-compose.yml
├── .env                    # secrets — never commit
├── .env.example
├── models/                 # GGUF files — gitignored
│   └── Qwen3.6-27B-Q4_K_M.gguf
├── llama-server/
│   └── Dockerfile
└── telegram-bot/
    ├── Dockerfile
    ├── bot.py
    └── requirements.txt
```
