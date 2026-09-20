<div align="center">

# Nexus-Route

**Ultra-low latency, containerized semantic AI gateway with local ONNX inference.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-1.17+-005CED.svg?style=flat&logo=onnx&logoColor=white)](https://onnxruntime.ai)
[![Podman](https://img.shields.io/badge/Podman-Rootless-892CA0.svg?style=flat&logo=podman&logoColor=white)](https://podman.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

Nexus-Route sits between clients and upstream LLMs to eliminate the trade-off between latency and reasoning depth. It computes local vector embeddings in under 16 ms to dynamically bifurcate traffic: trivial queries route to ultra-fast inference (Groq), while complex or analytical queries escalate to frontier reasoning models (Gemini).

## Table of Contents

- [The Core Problem](#the-core-problem)
- [Architecture & Routing Pipeline](#architecture--routing-pipeline)
- [Algorithmic Routing Mechanics](#algorithmic-routing-mechanics)
- [Repository Structure](#repository-structure)
- [Telemetry & Performance Baseline](#telemetry--performance-baseline)
- [Configuration Reference](#configuration-reference)
- [Quickstart](#quickstart)
  - [Container Workflow (Recommended)](#1-container-workflow-recommended)
  - [Bare-Metal Local Development](#2-bare-metal-local-development)
- [API Reference](#api-reference)
  - [Chat Completions (`/v1/chat/completions`)](#post-v1chatcompletions)
  - [Semantic Classifier Probe (`/classify`)](#post-classify)
  - [Health Check (`/health`)](#get-health)
- [Failure Modes & Resilience](#failure-modes--resilience)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## The Core Problem

Frontier reasoning models are overkill for mundane tasks (formatting, boilerplate, simple lookups) and add excessive latency and cost. Conversely, smaller, fast models collapse when asked to perform deep logical induction or complex problem solving.

Nexus-Route enforces workload separation at the network edge:
1. **Zero External API Cost for Routing:** Embeddings run on-CPU locally via ONNX Runtime (`BAAI/bge-small-en-v1.5`).
2. **True OpenAI Protocol Compatibility:** Works as a drop-in replacement for OpenAI SDKs, LangChain, or LlamaIndex.
3. **Zero-Buffer SSE Streaming:** Chunked streaming tokens pass through instantly without proxy buffering.

---

## Architecture & Routing Pipeline

```mermaid
flowchart TD
    Client["Client Application<br/>(OpenAI SDK / HTTP)"] -->|POST /v1/chat/completions| GW["Nexus-Route Edge Gateway"]

    subgraph Internal ["Internal Routing Engine (app/router.py)"]
        GW --> Extract["Extract Last User Message"]
        Extract --> Embed["FastEmbed Inference<br/>(BAAI/bge-small-en-v1.5 ONNX)"]
        Embed --> Cosine["Calculate Cosine Similarity<br/>against Reasoning Centroid"]
        Cosine --> Threshold{"Similarity >= 0.62 ?"}
    end

    Threshold -->|No (< 0.62)| Fast["Fast Tier (Groq)<br/>Model: openai/gpt-oss-20b<br/>Target: &lt; 500ms TTFT"]
    Threshold -->|Yes (>= 0.62)| Reason["Reasoning Tier (Gemini)<br/>Model: gemini-3.6-flash<br/>Target: Deep Analysis & Synthesis"]

    Fast -->|Raw Token Stream| Client
    Reason -->|Raw Token Stream| Client
```

---

## Algorithmic Routing Mechanics

Nexus-Route compares incoming query vectors against pre-computed reasoning centroids. Instead of spinning up a heavyweight cross-encoder or making an external classification call, the routing decision is computed directly using normalized cosine similarity:

$$\text{Sim}(\mathbf{q}, \mathbf{c}) = \frac{\mathbf{q} \cdot \mathbf{c}}{\Vert{}\mathbf{q}\Vert{}_2 \Vert{}\mathbf{c}\Vert{}_2}$$

Where:
- $\mathbf{q}$ is the 384-dimensional dense vector representation of the user's latest prompt.
- $\mathbf{c}$ is the pre-calculated reasoning anchor centroid representing analytical, mathematical, and algorithmic intents.
- When $\text{Sim}(\mathbf{q}, \mathbf{c}) \ge 0.62$, the request is dispatched to the reasoning tier.

---

## Repository Structure

```text
nexus-route/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application, lifecycle, and route handlers
│   ├── router.py        # FastEmbed ONNX initialization and vector scoring
│   └── schemas.py       # OpenAI-compatible Pydantic request/response models
├── deploy/
│   └── nexus-gateway.container  # Systemd Quadlet deployment spec (optional)
├── .dockerignore
├── .env.example         # Sanitized configuration template
├── .gitignore
├── Dockerfile           # Multi-stage build with pre-cached ONNX weights
├── Makefile             # Zero-RAM local development management
├── README.md
└── requirements.txt     # Locked production dependencies
```

---

## Telemetry & Performance Baseline

Measured on an x86_64 host running rootless Podman:

| Metric | Target | Observed Value | Validation Method |
| :--- | :--- | :--- | :--- |
| **Router Overhead** | `< 25 ms` | `15.69 ms` | Tokenization + ONNX inference latency |
| **Memory Footprint** | `< 350 MB` | `~290 MB` | Resident Set Size (RSS) under load |
| **Proxy Chunk Delay** | `0 ms` | `< 1 ms` | SSE unbuffered chunk flush |
| **Cold Start Duration**| `< 2.0 s` | `1.18 s` | Local container boot (weights pre-baked) |

---

## Configuration Reference

Create a `.env` file from the provided template:

```bash
cp .env.example .env
```

| Variable | Type | Description |
| :--- | :--- | :--- |
| `FAST_TIER_URL` | String | OpenAI-compatible endpoint URL for fast/streaming completions |
| `FAST_TIER_KEY` | Secret | Bearer token / API key for the fast tier provider |
| `FAST_TIER_MODEL` | String | Target model identifier (e.g. `openai/gpt-oss-20b`) |
| `REASONING_TIER_URL`| String | Completions endpoint URL for the reasoning provider |
| `REASONING_TIER_KEY`| Secret | Bearer token / API key for the reasoning tier provider |
| `REASONING_TIER_MODEL`| String | Target reasoning model (e.g. `gemini-3.6-flash`) |
| `SIMILARITY_THRESHOLD`| Float | Cosine similarity cutoff (Default: `0.62`) |

---

## Quickstart

### 1. Container Workflow (Recommended)

Requires Podman or Docker and GNU Make. This runs the gateway in the foreground and immediately frees memory when stopped.

```bash
# Build the container image (bakes in model weights)
make build

# Run in foreground with automatic port binding and --rm cleanup
make run
```
*Press `Ctrl + C` at any time to kill the container and reclaim RAM.*

### 2. Bare-Metal Local Development

If you prefer running directly in a virtual environment without containers:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start uvicorn development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## API Reference

### `POST /v1/chat/completions`

OpenAI-compatible chat endpoint. Supports both standard blocking responses and SSE token streaming.

**Request:**
```bash
curl -N -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a concise engineering assistant."},
      {"role": "user", "content": "Write an awk one-liner to print the second column of a CSV."}
    ],
    "stream": true
  }'
```

---

### `POST /classify`

Probe the classifier directly to test routing decisions and latency without invoking upstream LLM APIs.

**Request:**
```bash
curl -s -X POST http://127.0.0.1:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Prove that the square root of 2 is irrational using contradiction."}'
```

**Response (`200 OK`):**
```json
{
  "tier": "REASONING_TIER",
  "similarity_score": 0.6939,
  "threshold": 0.62,
  "router_latency_ms": 15.69
}
```

---

### `GET /health`

Readiness and liveness probe for orchestrators and monitoring agents.

**Response (`200 OK`):**
```json
{
  "status": "healthy",
  "timestamp": 1789913802.401353
}
```

---

## Failure Modes & Resilience

- **Upstream Timeouts:** If a provider fails to emit the first byte within the configured timeout window, the gateway aborts the connection with a structured `504 Gateway Timeout`.
- **Model Disconnects:** Upstream HTTP errors (such as 429 Rate Limits) are intercepted and propagated as OpenAI-standard error structures rather than generic internal server crashes.
- **Model Weight Baking:** The `BAAI/bge-small-en-v1.5` ONNX model is pulled during `podman build` into `/root/.cache/fastembed/`. Containers never attempt to fetch weights from Hugging Face at runtime, preventing cold-start network failures.

---

## Troubleshooting

### Port `8000` is already in use
```bash
# Check what process is holding the port
lsof -i :8000
# Kill lingering containers
podman rm -f nexus-gateway
```

### Upstream 401 Unauthorized Errors
Ensure keys in `.env` contain no trailing spaces, newline artifacts, or shell-escaped quotes. Restart the container after modifying `.env`.

---

## Roadmap

- [ ] Add Prometheus `/metrics` endpoint (scrape counters for tier routing distribution and latency percentiles).
- [ ] Implement an automated similarity threshold calibration script across custom evaluation datasets.
- [ ] Add dynamic multi-centroid clustering (Code, Math, General, Creative).
- [ ] Automatic upstream fallback routing on HTTP 429 / Rate Limit responses.
