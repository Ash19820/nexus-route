from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "auto"
    messages: List[ChatMessage] = Field(..., min_length=1)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None

class HealthResponse(BaseModel):
    status: Literal["healthy"]
    timestamp: float
