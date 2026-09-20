import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from app.schemas import ChatCompletionRequest, HealthResponse
from app.router import route_query
from app.proxy import stream_upstream_response, send_upstream_request
from app.middleware import StructuredLoggingMiddleware

app = FastAPI(
    title="Nexus-Route Gateway",
    version="0.1.0",
    description="High-performance semantic AI gateway with dynamic task routing."
)

app.add_middleware(StructuredLoggingMiddleware)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

@app.post("/classify")
async def classify_prompt(payload: dict):
    prompt = payload.get("prompt", "")
    return route_query(prompt)

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    user_prompt = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_prompt = msg.content
            break

    routing_result = route_query(user_prompt)
    target_tier = routing_result["target_tier"]
    payload = request.model_dump(exclude_none=True)

    base_headers = {
        "X-Gateway-Initial-Tier": target_tier,
        "X-Gateway-Score": str(routing_result["similarity_score"]),
        "X-Gateway-Latency-MS": str(routing_result["latency_ms"])
    }

    if request.stream:
        return StreamingResponse(
            stream_upstream_response(target_tier, payload),
            media_type="text/event-stream",
            headers=base_headers
        )

    response, resolved_tier = await send_upstream_request(target_tier, payload)
    response.headers.update(base_headers)
    response.headers["X-Gateway-Resolved-Tier"] = resolved_tier
    return response
