import httpx
from typing import AsyncGenerator, Dict, Any, Tuple
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from app.config import settings

def get_tier_config(tier: str) -> Dict[str, str]:
    if tier == "REASONING_TIER":
        return {
            "url": settings.REASONING_TIER_URL,
            "key": settings.REASONING_TIER_KEY,
            "model": settings.REASONING_TIER_MODEL,
            "fallback": "FAST_TIER"
        }
    return {
        "url": settings.FAST_TIER_URL,
        "key": settings.FAST_TIER_KEY,
        "model": settings.FAST_TIER_MODEL,
        "fallback": "REASONING_TIER"
    }

async def send_upstream_request(tier: str, payload: Dict[str, Any]) -> Tuple[JSONResponse, str]:
    current_tier = tier
    for attempt in range(2):
        config = get_tier_config(current_tier)
        if not config["key"]:
            current_tier = config["fallback"]
            continue

        payload["model"] = config["model"]
        payload["stream"] = False
        headers = {
            "Authorization": f"Bearer {config['key']}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(config["url"], headers=headers, json=payload)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                    current_tier = config["fallback"]
                    continue
                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)
                return JSONResponse(content=resp.json()), current_tier
            except (httpx.ConnectError, httpx.TimeoutException):
                if attempt == 0:
                    current_tier = config["fallback"]
                    continue
                raise HTTPException(status_code=504, detail="Upstream gateway timeout on both tiers")

    raise HTTPException(status_code=500, detail="All configured tiers failed")

async def stream_upstream_response(tier: str, payload: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
    current_tier = tier
    client = httpx.AsyncClient(timeout=60.0)

    try:
        for attempt in range(2):
            config = get_tier_config(current_tier)
            if not config["key"]:
                current_tier = config["fallback"]
                continue

            payload["model"] = config["model"]
            payload["stream"] = True
            headers = {
                "Authorization": f"Bearer {config['key']}",
                "Content-Type": "application/json"
            }

            req = client.build_request("POST", config["url"], headers=headers, json=payload)
            upstream_resp = await client.send(req, stream=True)

            # If rate-limited or upstream server error before streaming begins, swap tier
            if upstream_resp.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                await upstream_resp.aclose()
                current_tier = config["fallback"]
                continue

            if upstream_resp.status_code != 200:
                error_bytes = await upstream_resp.aread()
                await upstream_resp.aclose()
                yield f"data: {{\"upstream_error\": {error_bytes.decode()}}}\n\n".encode("utf-8")
                yield b"data: [DONE]\n\n"
                return

            # Once bytes start streaming, we cannot fail over mid-stream
            async for chunk in upstream_resp.aiter_bytes():
                yield chunk
            await upstream_resp.aclose()
            return
    except Exception as e:
        yield f"data: {{\"gateway_error\": \"{str(e)}\"}}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"
    finally:
        await client.aclose()
