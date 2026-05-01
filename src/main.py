# ruff: noqa: E402
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import json
from typing import Dict, List

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import src.core.tools  # noqa: F401
from src.core.config import settings
from src.core.mcp import (
    call_mcp_tool,
    get_tools_schema,
    mcp,  # noqa: F401
)
from src.core.nvidia_client import nvidia_client
from src.core.prompt_manager import prompt_manager

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent for technical and financial real estate analysis.",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]


@app.get("/", tags=["UI"])
async def root():
    return FileResponse("src/static/index.html")


@app.post("/chat", tags=["Agent"])
async def chat(request: ChatRequest):
    """
    Main entry point for the agent.
    """
    try:
        system_prompt = prompt_manager.get_system_prompt()
        full_messages = [
            {"role": "system", "content": system_prompt}
        ] + request.messages

        async def stream_generator():
            try:
                # Retrieve schemas dynamically from the MCP registry
                available_tools = await get_tools_schema()

                # First call to AI (with dynamic tools enabled)
                response_gen = nvidia_client.chat_completion(
                    full_messages,
                    stream=True,
                    tools=available_tools if available_tools else None,
                )

                tool_calls = []
                for delta in response_gen:
                    # Show human text as it arrives
                    if "content" in delta and delta["content"]:
                        yield delta["content"]

                    # Catch tool calls and assemble fragments
                    if "tool_calls" in delta:
                        for tc in delta["tool_calls"]:
                            index = tc["index"]
                            # Create entry for new tool calls
                            if len(tool_calls) <= index:
                                tool_calls.append(
                                    {"id": tc["id"], "name": "", "arguments": ""}
                                )

                            # Append name and arguments fragments
                            if "function" in tc:
                                fn = tc["function"]
                                if "name" in fn:
                                    tool_calls[index]["name"] += fn["name"]
                                if "arguments" in fn:
                                    tool_calls[index]["arguments"] += fn["arguments"]

                # 4. If tools were called, execute them and get final response
                if tool_calls:
                    for call in tool_calls:
                        # Parse the assembled JSON
                        args = json.loads(call["arguments"])

                        # Execute our Python function
                        result = await call_mcp_tool(call["name"], args)

                        # Update history with the tool call and the result
                        full_messages.append(
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": call["id"],
                                        "type": "function",
                                        "function": {
                                            "name": call["name"],
                                            "arguments": call["arguments"],
                                        },
                                    }
                                ],
                            }
                        )
                        full_messages.append(
                            {
                                "role": "tool",
                                "name": call["name"],
                                "tool_call_id": call["id"],
                                "content": json.dumps(result),
                            }
                        )

                    # 5. Second call to AI to interpret the results
                    for final_delta in nvidia_client.chat_completion(
                        full_messages, stream=True
                    ):
                        if "content" in final_delta and final_delta["content"]:
                            yield final_delta["content"]

            except Exception as e:
                yield f" [Error: {str(e)}]"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except Exception as e:
        return {"error": str(e)}


@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", host="127.0.0.1", port=settings.PORT, reload=settings.DEBUG
    )
