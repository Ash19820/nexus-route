# Nexus-Route

A low-latency, containerized semantic AI gateway built with FastAPI and FastEmbed. It classifies incoming prompts via local ONNX embeddings to dynamically route traffic between fast and reasoning model tiers.

## Architecture

- **Semantic Routing:** FastEmbed (`BAAI/bge-small-en-v1.5`) running locally via ONNX Runtime.
- **Threshold Routing:** Classifies complexity against a semantic similarity threshold (`0.62`):
  - **Fast Tier:** Low-latency completions via Groq.
  - **Reasoning Tier:** Complex/analytical tasks via Google Gemini.
- **Streaming:** Zero-buffering Server-Sent Events (SSE) pass-through.
- **Containerization:** Multi-stage container build with baked-in model weights for instant cold starts.

## Prerequisites

- Podman or Docker
- GNU Make

## Quickstart

1. **Clone and Configure:**
   ```bash
   git clone [https://github.com/Ash19820/nexus-route.git](https://github.com/Ash19820/nexus-route.git)
   cd nexus-route
   cp .env.example .env
   # Edit .env with your API keys
