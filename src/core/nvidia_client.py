import json
from typing import Any, Dict, Generator, List

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
        temperature: float = 1.0,
        top_p: float = 0.9,
        max_tokens: int = 2048,
    ) -> Any:
        """
        Sends a chat completion request to NVIDIA NIM using a persistent session.

        Args:
            messages: List of message dictionaries.
            model: The model to use.
            stream: Whether to stream the response.
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens to generate.

        Returns:
            A generator for streaming content or the full JSON response.
        """
        # Handle case where key might already include 'Bearer ' prefix
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
            "chat_template_kwargs": {"enable_thinking": True},
        }

        response = self.session.post(
            self.invoke_url,
            headers=headers,
            json=payload,
            stream=stream,
            timeout=60,  # Increased timeout for complex prompts
        )

        response.raise_for_status()

        if stream:
            return self._stream_response(response)
        else:
            return response.json()

    def _stream_response(
        self, response: requests.Response
    ) -> Generator[str, None, None]:
        """
        Generates content chunks from a streaming response.
        """
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[len("data: ") :]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        content = data["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


nvidia_client = NvidiaClient()
