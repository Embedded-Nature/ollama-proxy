import re
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import httpx
from fastapi.responses import StreamingResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

# LM Studio OpenAI-compatible API
LM_STUDIO_API = "http://localhost:1234/v1/completions"

# Model name mapping (only for OpenAI-style requests)
MODEL_MAP = {
    "qwen2.5": "qwen2.5-coder-32b-instruct-mlx",
}

class ChatRequest(BaseModel):
    model: str
    messages: list
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 512
    tools: list = None

class OllamaRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 512

async def stream_chat_response(request_data):
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            async with client.stream("POST", LM_STUDIO_API, json=request_data) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_text():
                    yield chunk  # Send data as it arrives

        except httpx.HTTPStatusError as e:
            yield f"ERROR: LM Studio returned {e.response.status_code}: {e.response.text}"
        except httpx.TimeoutException:
            yield "ERROR: LM Studio request timed out"
        except httpx.RequestError as e:
            yield f"ERROR: Request failed: {str(e)}"

def clean_lm_response(text):
    """
    Cleans LM Studio responses by removing unwanted system markers like '<|im_start|>Assistant###'.
    """
    text = text.strip()  # Remove leading/trailing spaces

    # Remove system markers like '<|im_start|>Assistant###'
    text = re.sub(r'<\|im_start\|>Assistant###\s*', '', text, flags=re.IGNORECASE)

    # Remove any leading "ASSISTANT###" or other unintended prefixes
    text = re.sub(r'^(ASSISTANT###|ASSISTANT:|<|im_start|>)+\s*', '', text, flags=re.IGNORECASE)

    return text

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log incoming requests.
    """
    body = await request.body()
    logging.info(f"📡 Incoming Request: {request.method} {request.url} | Payload: {body.decode('utf-8')}")
    
    response = await call_next(request)
    
    logging.info(f"📡 Response: {response.status_code} for {request.method} {request.url}")
    return response

def convert_messages_to_prompt(messages):
    """
    Converts OpenAI-style chat messages into a single prompt string for LM Studio.
    """
    prompt = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, list):
            content = "\n".join([item["text"] for item in content if isinstance(item, dict) and "text" in item])

        prompt += f"{role.upper()}: {content}\n"
    
    return prompt.strip()

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    Converts OpenAI-style chat completion requests into LM Studio-compatible requests.
    """
    logging.info("🟢 Processing request for /v1/chat/completions")

    # Convert model name ONLY for OpenAI requests
    model_name = MODEL_MAP.get(request.model, request.model)
    if model_name != request.model:
        logging.info(f"🔄 Converting model name: {request.model} → {model_name}")

    # Convert `messages` to a single `prompt`
    prompt = convert_messages_to_prompt(request.messages)

    # Build LM Studio payload
    lm_studio_payload = {
        "model": model_name,
        "prompt": prompt,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "stream": request.stream,
    }

    if request.stream:
        return StreamingResponse(stream_chat_response(lm_studio_payload), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(LM_STUDIO_API, json=lm_studio_payload)
            response.raise_for_status()
            lm_response = response.json()  # Get LM Studio response
        except httpx.HTTPStatusError as e:
            logging.error(f"❌ LM Studio error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"LM Studio error: {e.response.text}")
        except httpx.TimeoutException:
            logging.error("❌ LM Studio request timed out")
            raise HTTPException(status_code=504, detail="LM Studio request timed out")
        except httpx.RequestError as e:
            logging.error(f"❌ Request error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

    # ✅ Convert response format to OpenAI-compatible
    openai_response = {
        "id": lm_response["id"],
        "object": "chat.completion",
        "created": lm_response["created"],
        "model": model_name,
        "choices": [
            {
                "index": choice["index"],
                "message": {
                    "role": "assistant",
                    "content": clean_lm_response(choice["text"])
                },
                "finish_reason": choice["finish_reason"]
            }
            for choice in lm_response["choices"]
        ],
        "usage": lm_response["usage"]
    }

    logging.info("✅ Successfully processed /v1/chat/completions request")
    return openai_response

@app.post("/api/generate")
async def generate_ollama(request: OllamaRequest):
    """
    Intercepts Ollama-style requests and transforms them into LM Studio (OpenAI-compatible) requests.
    """
    logging.info("🟢 Processing request for /api/generate")

    # DO NOT convert model names for Ollama requests!
    model_name = request.model  # Keep the exact model name

    # Build LM Studio payload
    lm_studio_payload = {
        "model": model_name,
        "prompt": request.prompt,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "stream": request.stream
    }

    if request.stream:
        return StreamingResponse(stream_chat_response(lm_studio_payload), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(LM_STUDIO_API, json=lm_studio_payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logging.error(f"❌ LM Studio error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"LM Studio error: {e.response.text}")
        except httpx.TimeoutException:
            logging.error("❌ LM Studio request timed out")
            raise HTTPException(status_code=504, detail="LM Studio request timed out")
        except httpx.RequestError as e:
            logging.error(f"❌ Request error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

    logging.info("✅ Successfully processed /api/generate request")
    
    # Transform LM Studio response into Ollama-compatible format
    lm_response = response.json()
    ollama_response = {
        "model": model_name,
        "created_at": lm_response.get("created", ""),
        "response": lm_response.get("choices", [{}])[0].get("text", ""),
        "done": True
    }

    return ollama_response

@app.get("/")
async def root():
    logging.info("🟢 Root endpoint accessed")
    return {"message": "Ollama Proxy to LM Studio is running"}