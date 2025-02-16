# ollama-proxy (Ollama Proxy to LM Studio)

## Overview
This FastAPI-based proxy allows applications designed for **Ollama** to communicate seamlessly with **LM Studio**. It intercepts Ollama-style API requests and transforms them into **OpenAI-compatible** requests for LM Studio.

This was designed specifically for the [Goose AI agent](https://github.com/block/goose), but can be adapted to work with other applications.

### Key Features:
- **Ollama-Compatible API**: Your app can send requests as if it were talking to Ollama.
- **Automatic Translation**: Converts requests to LM Studio format.
- **Streaming Support**: Handles both normal and streaming responses.
- **Non-Blocking Execution**: Uses FastAPI and `httpx` for efficient async handling.

  
### Demo

https://github.com/user-attachments/assets/74ebdcd0-f36b-4fa3-88c7-11cc8dabaafa



## Installation

1. **Clone the Repository (If Applicable)**
   ```bash
   git clone https://github.com/Embedded-Nature/ollama-proxy.git
   cd ollama-proxy
   ```

2. **Set Up a Virtual Environment (Optional but Recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install fastapi uvicorn httpx
   ```

## Usage

### Running the Proxy Server
Start the FastAPI server with:
```bash
uvicorn ollama_proxy:app --host 0.0.0.0 --port 11434 --reload
```
This makes the proxy **listen on port 11434**, which is the default for Ollama.

### Sending Requests
Your application can now send requests to `http://localhost:11434/api/generate`, and they will be **converted to work with LM Studio**.

#### Example API Call
```bash
curl -X POST "http://localhost:11434/api/generate" \
     -H "Content-Type: application/json" \
     -d '{"model": "mistral", "prompt": "Tell me a story.", "stream": true}'
```

#### Expected Response (Streaming Enabled)
```
Once upon a time...
The brave knight ventured...
```

## Configuration
- **Modify the LM Studio API URL** in `ollama_proxy.py` if needed:
  ```python
  LM_STUDIO_API = "http://localhost:1234/v1/completions"
  ```
- **Adjust Timeout** in the script (`120s` default) if needed.
- **Supports Temperature & Max Tokens** adjustments in the API call.

## Troubleshooting
### 1. LM Studio Doesn't Respond
- Make sure LM Studio is **running** and accepting requests on `http://localhost:1234/v1/completions`.
- Test LM Studio separately:
  ```bash
  curl -X POST "http://localhost:1234/v1/completions" -H "Content-Type: application/json" -d '{"prompt": "Hello"}'
  ```

### 2. Proxy Not Running
- Ensure `uvicorn` is installed:
  ```bash
  pip install uvicorn
  ```
- Check if the port is **already in use**:
  ```bash
  netstat -an | grep 11434
  ```
  If another process is using the port, restart your machine or change the port in `uvicorn`.

### 3. Request Timeout Issues
- Increase timeout in `ollama_proxy.py`:
  ```python
  async with httpx.AsyncClient(timeout=300) as client:
  ```
- Ensure LM Studio is **not overloaded** with too many requests.

## Next Steps
- **Deploy**: Run the proxy as a system service or Docker container.
- **Enhancements**: Add API key authentication or logging.

---
🚀 **Now, your app can use LM Studio while thinking it's talking to Ollama!**

