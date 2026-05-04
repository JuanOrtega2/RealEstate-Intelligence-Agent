from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_read_root():
    """Verifica que la interfaz de usuario se sirve correctamente."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@patch("src.main.security_guard.check_input_safety")
def test_chat_security_block(mock_safety):
    """Verifica que el Security Guard bloquea ataques."""
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
    """Verifica que una consulta válida devuelve una respuesta simulada (Mock)."""
    mock_safety.return_value = (True, "Safe")

    # Simulamos un generador de respuesta para el stream
    def mock_stream(*args, **kwargs):
        yield {"content": "Respuesta", "role": "assistant"}
        yield {"content": " simulada", "role": "assistant"}

    mock_chat.return_value = mock_stream()

    payload = {"messages": [{"role": "user", "content": "Hola"}]}
    # Usamos stream=True en la petición si el endpoint lo requiere
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    # Al ser un StreamingResponse, el contenido viene en response.text o iterando
    assert "Respuesta simulada" in response.text
