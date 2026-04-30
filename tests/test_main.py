from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_read_root():
    """
    Test the root endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]


@patch("src.main.nvidia_client")
@patch("src.main.prompt_manager")
def test_chat_endpoint(mock_prompt, mock_nvidia, client=client):
    """
    Test the /chat endpoint by mocking the agent logic.
    """
    mock_prompt.get_system_prompt.return_value = "System prompt"
    mock_nvidia.chat_completion.return_value = {
        "choices": [{"message": {"content": "Mocked response"}}]
    }

    response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 200
    assert "Mocked response" in response.json()["choices"][0]["message"]["content"]
    mock_prompt.get_system_prompt.assert_called_once()
    mock_nvidia.chat_completion.assert_called_once()


def test_health_check():
    """
    Test the health check endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
