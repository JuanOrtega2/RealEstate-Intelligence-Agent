import json
from typing import Any, Dict, List, Optional

import httpx
import requests

from src.core.config import settings


class NvidiaClient:
    """
    Client for interacting with NVIDIA NIM API.
    Uses a persistent AsyncClient for maximum performance and low latency.
    """

    def __init__(self):
        """
        Initializes the client with configuration settings.
        """
        self.api_key = settings.NVIDIA_API_KEY
        self.invoke_url = settings.INVOKE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
            if not self.api_key.startswith("Bearer ")
            else self.api_key,
            "Accept": "text/event-stream",
        }
        # Persistent client to reuse connections (Connection Pooling)
        # This significantly reduces latency per request.
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_async_client(self, timeout: int) -> httpx.AsyncClient:
        """Lazy initialization of the persistent async client."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                headers=self.headers,
            )
        return self._async_client

    async def achat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = settings.DEFAULT_MODEL,
        stream: bool = True,
        temperature: float = 0.8,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: int = 120,
    ) -> Any:
        """
        Async version of chat completion.
        Optimized for low-latency streaming.
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        if stream:
            return self._astream_generator(payload, timeout)
        else:
            client = self._get_async_client(timeout)
            response = await client.post(
                self.invoke_url,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def _astream_generator(self, payload: dict, timeout: int):
        """
        Asynchronous generator for non-blocking streaming with persistent client.
        """
        client = self._get_async_client(timeout)
        try:
            async with client.stream(
                "POST",
                self.invoke_url,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(
                        f"NVIDIA API {response.status_code}: {error_text.decode()}"
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[len("data: ") :]
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if delta:
                                yield delta
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            # Handle connection errors gracefully
            print(f"📡 Connection Error in Stream: {e}")
            yield {"content": f"\n\n⚠️ Error de conexión: {str(e)}"}

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = settings.DEFAULT_MODEL,
        stream: bool = False,
        temperature: float = 0.8,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: int = 120,
    ) -> Any:
        """
        Synchronous version for scripts and evaluation runners.
        Uses requests for simplicity in CLI environments.
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        with requests.Session() as session:
            response = session.post(
                self.invoke_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}"
                    if not self.api_key.startswith("Bearer ")
                    else self.api_key,
                    "Accept": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

    async def close(self):
        """Cleanly close the persistent client."""
        if self._async_client:
            await self._async_client.aclose()


nvidia_client = NvidiaClient()
