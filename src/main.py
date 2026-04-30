# ruff: noqa: E402
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.core.config import settings
from src.core.nvidia_client import nvidia_client
from src.core.prompt_manager import prompt_manager

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent for technical and financial real estate analysis.",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    """
    Schema for a chat request.
    """

    message: str


@app.get("/", tags=["UI"])
async def root():
    """
    Serves the isolated Chat UI from the static folder.
    """
    return FileResponse("src/static/index.html")


@app.post("/chat", tags=["Agent"])
async def chat(request: ChatRequest):
    """
    Send a message to the Real Estate Intelligence Agent with streaming.
    """
    try:
        system_prompt = prompt_manager.get_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message},
        ]

        # Enable streaming at the client level
        def stream_generator():
            try:
                for chunk in nvidia_client.chat_completion(messages, stream=True):
                    if chunk:
                        yield chunk
            except Exception as e:
                yield f" [Error: {str(e)}]"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except Exception as e:
        return {"error": "Internal Server Error", "details": str(e)}


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring service status.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", host="127.0.0.1", port=settings.PORT, reload=settings.DEBUG
    )
