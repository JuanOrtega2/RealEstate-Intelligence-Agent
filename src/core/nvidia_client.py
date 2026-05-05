import json
from typing import Any, Dict, Generator, List, Optional

import requests

from src.core.config import settings


class NvidiaClient:
    """
    Client for interacting with NVIDIA NIM API.
    """

    def __init__(self):
        """
        Initializes the client with configuration settings and a persistent session.
        """
        self.api_key = settings.NVIDIA_API_KEY
        self.invoke_url = settings.INVOKE_URL
        self.session = requests.Session()

    def chat_completion(
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
        Sends a chat completion request to NVIDIA NIM using a persistent session.
        Supports tools (function calling) and custom timeouts.
        """
        auth_header = (
            self.api_key
            if self.api_key.startswith("Bearer ")
            else f"Bearer {self.api_key}"
        )

        headers = {
            "Authorization": auth_header,
            "Accept": "text/event-stream" if stream else "application/json",
        }

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

        import time

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            response = self.session.post(
                self.invoke_url,
                headers=headers,
                json=payload,
                stream=stream,
                timeout=timeout,
            )

            if response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2**attempt))
                    continue

            response.raise_for_status()
            break

        if stream:
            return self._stream_response(response)
        else:
            return response.json()

    def _stream_response(
        self, response: requests.Response
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generates structured chunks from a streaming response.
        """
        for line in response.iter_lines(decode_unicode=True):
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


nvidia_client = NvidiaClient()
