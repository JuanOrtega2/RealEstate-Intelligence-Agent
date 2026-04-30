import os

import requests
from dotenv import load_dotenv

load_dotenv()


def test_nvidia_connection():
    api_key = os.getenv("NVIDIA_API_KEY")
    invoke_url = os.getenv(
        "INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions"
    )
    model = os.getenv("DEFAULT_MODEL", "meta/llama-3.1-70b-instruct")

    print("--- Testing Connection to NVIDIA NIM ---")
    print(f"URL: {invoke_url}")
    print(f"Model: {model}")

    # Clean API key
    if api_key.startswith("Bearer "):
        auth_header = api_key
    else:
        auth_header = f"Bearer {api_key}"

    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello world in one word."}],
        "max_tokens": 10,
        "temperature": 1.0,
        "top_p": 1.0,
        "stream": False,
    }

    try:
        print("Sending request (timeout 60s)...")
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("Success!")
            print(f"Response: {response.json()['choices'][0]['message']['content']}")
        else:
            print(f"Error Body: {response.text}")

    except Exception as e:
        print(f"Connection Failed: {str(e)}")


if __name__ == "__main__":
    test_nvidia_connection()
