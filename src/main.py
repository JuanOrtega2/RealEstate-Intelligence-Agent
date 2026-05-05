# ruff: noqa: E402
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Dict, List

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize resources and warm up connections.
    """
    try:
        await get_tools_schema()
    except Exception as e:
        print(f"⚠️ Tools cache warm-up failed: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent for technical and financial real estate analysis.",
    version="0.1.0",
    lifespan=lifespan,
)

# Global cache for proactive summarization (Memory Store)
SUMMARY_CACHE = {}


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]


@app.get("/", tags=["UI"])
async def root():
    return FileResponse("src/static/index.html")


@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Security check (Layer 0 - Heuristics)
        # Latency Optimization: use_ai_agent=False by default to avoid double LLM calls.
        is_safe, reason = await security_guard.check_input_safety(
            request.messages[-1]["content"] if request.messages else "",
            use_ai_agent=False,
        )

        if not is_safe:
            error_type = reason.lower()
            if "length" in error_type:
                msg = "📏 El mensaje es demasiado extenso. ¿Podrías resumirlo?"
            else:
                msg = (
                    "🛡️ Por seguridad, no puedo procesar este mensaje. "
                    "Hablemos de los números del inmueble."
                )

            async def error_generator():
                yield msg

            return StreamingResponse(error_generator(), media_type="text/plain")

        # 2. Identify Conversation (for caching)
        conv_key = "default"
        if request.messages:
            conv_key = str(hash(request.messages[0]["content"]))

        # 3. Prepare conversation history
        system_prompt = prompt_manager.get_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}]

        cached_summary = SUMMARY_CACHE.get(conv_key)
        if cached_summary and len(request.messages) > 6:
            recent_messages = request.messages[-4:]
            full_messages.append(
                {
                    "role": "system",
                    "content": f"[MEMORIA PRE-CALCULADA]: {cached_summary}",
                }
            )
            for msg in recent_messages:
                full_messages.append(msg)
        else:
            for msg in request.messages:
                full_messages.append(msg)

        async def stream_generator():
            full_assistant_content = ""
            try:
                available_tools = await get_tools_schema()
                response_gen = nvidia_client.chat_completion(
                    full_messages, tools=available_tools, stream=True
                )

                tool_calls = []
                for delta in response_gen:
                    if "content" in delta and delta["content"]:
                        content = delta["content"]
                        if '{"name":' in content or "analyze_investment_roi" in content:
                            continue
                        full_assistant_content += content
                        yield content

                    if "tool_calls" in delta:
                        for tc in delta["tool_calls"]:
                            index = tc["index"]
                            if len(tool_calls) <= index:
                                tool_calls.append(
                                    {"id": tc["id"], "name": "", "arguments": ""}
                                )
                            if "function" in tc:
                                fn = tc["function"]
                                if "name" in fn:
                                    tool_calls[index]["name"] += fn["name"]
                                if "arguments" in fn:
                                    tool_calls[index]["arguments"] += fn["arguments"]

                if tool_calls:
                    for call in tool_calls:
                        args = (
                            json.loads(call["arguments"]) if call["arguments"] else {}
                        )

                        # UI Feedback
                        tool_name = call["name"]
                        if tool_name == "read_property_link":
                            yield (
                                "\n\n_🔗 Consultando la fuente del inmueble y "
                                "extrayendo datos..._\n\n"
                            )
                        elif tool_name == "search_market_data":
                            yield (
                                "\n\n_📊 Analizando registros de mercado y "
                                "cruzando datos de la zona..._\n\n"
                            )
                        elif tool_name == "analyze_investment_roi":
                            yield (
                                "\n\n_⚙️ Ejecutando modelo financiero y "
                                "calculando métricas de rentabilidad..._\n\n"
                            )

                        result = await call_mcp_tool(call["name"], args)

                        result_content = ""
                        if hasattr(result, "content"):
                            result_content = "\n".join(
                                [c.text for c in result.content if hasattr(c, "text")]
                            )
                        else:
                            result_content = str(result)

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

                    for final_delta in nvidia_client.chat_completion(
                        full_messages, stream=True
                    ):
                        if "content" in final_delta and final_delta["content"]:
                            full_assistant_content += final_delta["content"]
                            yield final_delta["content"]

                # Update summary for NEXT turn (summarize every 3 turns)
                if len(request.messages) >= 4 and (len(request.messages) % 3 == 0):
                    background_tasks.add_task(
                        update_conversation_summary,
                        conv_key,
                        request.messages
                        + [{"role": "assistant", "content": full_assistant_content}],
                    )

            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg:
                    yield (
                        "\n\n⚠️ **Aviso de Tráfico:** El cerebro de la IA está "
                        "saturado en este momento. Por favor, espera 30 segundos "
                        "y vuelve a intentar tu última consulta. ¡Gracias por tu "
                        "paciencia!"
                    )
                else:
                    yield f"\n\n🛠️ **Error técnico:** {str(e)}"

        return StreamingResponse(stream_generator(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def update_conversation_summary(conv_key: str, messages: list):
    try:
        summary_prompt = (
            "Resume los datos técnicos (precio, ubicación, m2, rentabilidad, acuerdos) "
            "de esta conversación en máximo 3 líneas."
        )
        context = "\n".join(
            [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages]
        )
        summary_response = await asyncio.to_thread(
            nvidia_client.chat_completion,
            [{"role": "user", "content": f"{summary_prompt}\n{context}"}],
            stream=False,
            max_tokens=150,
            temperature=0.0,
        )
        SUMMARY_CACHE[conv_key] = summary_response["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Background summary failed: {e}")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("src.main:app", host="127.0.0.1", port=port, reload=settings.DEBUG)
