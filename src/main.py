# ruff: noqa: E402
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import asyncio
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
from src.core.security import security_guard

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent for technical and financial real estate analysis.",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    """
    Initialize resources and warm up connections.
    We do it without blocking the main thread to avoid Gateway Timeouts.
    """
    # 1. Warm up Tools Cache (fast, usually local/memory)
    try:
        await get_tools_schema()
    except Exception as e:
        print(f"⚠️ Tools cache warm-up failed: {e}")

    # 2. Warm up NVIDIA Connection in background
    # This allows the app to start accepting requests immediately
    asyncio.create_task(background_warmup())


async def background_warmup():
    """Perform connection warming in the background."""
    try:
        messages = [{"role": "user", "content": "hi"}]
        # Dummy request to pre-establish SSL/TLS
        nvidia_client.chat_completion(messages, stream=False, max_tokens=1)
        print("✅ NVIDIA connection warmed up in background.")
    except Exception as e:
        print(f"⚠️ Background warm-up failed: {e}")


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
    print(f"📩 Incoming chat request with {len(request.messages)} messages.")
    try:
        # 1. Security Check (Scan latest message with context)
        latest_user_msg = ""
        context = []
        if request.messages:
            if request.messages[-1]["role"] == "user":
                latest_user_msg = request.messages[-1]["content"]
                context = request.messages[:-1]  # All messages except the last one

        is_safe, reason = await security_guard.check_input_safety(
            latest_user_msg, context
        )
        if not is_safe:
            return {"error": f"Security Alert: {reason}"}

        # 2. Prepare conversation history
        # We wrap the user input in XML tags to separate data from instructions
        system_prompt = prompt_manager.get_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}]
        for msg in request.messages:
            if msg["role"] == "user":
                msg["content"] = f"<user_input>\n{msg['content']}\n</user_input>"
            full_messages.append(msg)

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
                    # Show human text as it arrives (Filtering tool leakage)
                    if "content" in delta and delta["content"]:
                        content = delta["content"]
                        # Safety: If the LLM starts writing JSON or tool names, skip it
                        if '{"name":' in content or "analyze_investment_roi" in content:
                            continue
                        yield content

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

                        # Extract text content from MCP result for the LLM
                        result_content = ""
                        if hasattr(result, "content"):
                            result_content = "\n".join(
                                [c.text for c in result.content if hasattr(c, "text")]
                            )
                        else:
                            result_content = str(result)

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
                                "content": result_content,
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
    import os

    # Render and other platforms provide the PORT as an env var
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=settings.DEBUG)  # noqa: S104
