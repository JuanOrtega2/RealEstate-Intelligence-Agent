from unittest.mock import MagicMock, patch

from src.core.nvidia_client import NvidiaClient


def test_nvidia_client_init():
    """
    Test that NvidiaClient initializes correctly with settings.
    """
    with patch("src.core.nvidia_client.settings") as mock_settings:
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.INVOKE_URL = "https://test.api.com"

        client = NvidiaClient()
        assert client.api_key == "test-key"
        assert client.invoke_url == "https://test.api.com"


@patch("src.core.nvidia_client.requests.post")
def test_chat_completion_non_streaming(mock_post):
    """
    Test non-streaming chat completion using requests.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
    mock_post.return_value = mock_response

    client = NvidiaClient()
    messages = [{"role": "user", "content": "hello"}]

    response = client.chat_completion(messages, stream=False)

    assert response == {"choices": [{"message": {"content": "hello"}}]}
    mock_post.assert_called_once()

    # Check headers (Authorization should include Bearer)
    args, kwargs = mock_post.call_args
    assert "Authorization" in kwargs["headers"]
    assert "Bearer" in kwargs["headers"]["Authorization"]
