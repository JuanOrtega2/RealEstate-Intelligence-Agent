from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_read_root():
    """Verify that the UI (HTML) is served correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@patch("src.main.security_guard.check_input_safety")
def test_chat_security_block(mock_safety):
    """Verify that the Security Guard blocks known attacks."""
    # Simulate guard detecting an attack
    mock_safety.return_value = (False, "Technical meta-command detected")

    payload = {"messages": [{"role": "user", "content": "attack"}]}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert "Security Alert" in data["error"]


@patch("src.main.nvidia_client.chat_completion")
@patch("src.main.security_guard.check_input_safety")
def test_chat_valid_response(mock_safety, mock_chat):
    """Verify that a valid query returns a mocked response."""
    # Configure mocks
    mock_safety.return_value = (True, "Safe")

    # Simulate a stream generator for the response
    def mock_stream(*args, **kwargs):
        yield {"content": "Mocked", "role": "assistant"}
        yield {"content": " response", "role": "assistant"}

    mock_chat.return_value = mock_stream()

    payload = {"messages": [{"role": "user", "content": "Hello"}]}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    # Since it's a StreamingResponse, check text content
    assert "Mocked response" in response.text
