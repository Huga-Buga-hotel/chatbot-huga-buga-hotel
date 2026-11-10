from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

import app
import chatbot
import rag


class ModeloFalso(GenericFakeChatModel):
    """Modelo de mentira: devolve as mensagens programadas, em ordem."""

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def cliente(monkeypatch):
    chatbot.conversas.clear()
    return TestClient(app.app)


def usar_modelo_falso(monkeypatch, *mensagens):
    modelo = ModeloFalso(messages=iter(mensagens))
    monkeypatch.setattr(chatbot, "agente", create_agent(model=modelo, tools=chatbot.ferramentas.TODAS))


def test_agente_chama_tool_e_responde(cliente, monkeypatch):
    monkeypatch.setattr(rag, "buscar", lambda pergunta: ["## Horários\n- Check-in: a partir das 13h"])
    usar_modelo_falso(
        monkeypatch,
        AIMessage(
            content="", tool_calls=[{"name": "buscar_informacoes_hotel", "args": {"pergunta": "check-in"}, "id": "1"}]
        ),
        AIMessage(content="Check-in starts at 1 PM!"),
    )
    resposta = cliente.post("/chat", json={"mensagem": "What time is check-in?", "id_sessao": "s1"})
    assert resposta.status_code == 200
    assert resposta.json() == {"resposta": "Check-in starts at 1 PM!"}
    # o histórico guarda só a pergunta e a resposta final
    assert [m["role"] for m in chatbot.conversas["s1"]] == ["user", "assistant"]


def test_chat_audio(cliente, monkeypatch):
    groq_falso = MagicMock()
    groq_falso.audio.transcriptions.create.return_value = SimpleNamespace(text=" ¿Aceptan mascotas? ")
    monkeypatch.setattr(chatbot, "cliente_groq", groq_falso)
    usar_modelo_falso(monkeypatch, AIMessage(content="¡Sí!"))

    resposta = cliente.post(
        "/chat/audio",
        files={"audio": ("msg.m4a", b"audio", "audio/mp4")},
        data={"id_sessao": "s2", "idioma": "es"},
    )
    assert resposta.json() == {"transcricao": "¿Aceptan mascotas?", "resposta": "¡Sí!"}
    assert groq_falso.audio.transcriptions.create.call_args.kwargs["language"] == "es"


@pytest.mark.parametrize(
    ("nome", "conteudo", "status"),
    [("msg.txt", b"x", 415), ("msg.m4a", b"", 400)],
)
def test_chat_audio_invalido(cliente, nome, conteudo, status):
    assert cliente.post("/chat/audio", files={"audio": (nome, conteudo)}).status_code == status


def test_erro_no_modelo_vira_502(cliente, monkeypatch):
    agente = MagicMock()
    agente.invoke.side_effect = RuntimeError("groq fora do ar")
    monkeypatch.setattr(chatbot, "agente", agente)
    assert cliente.post("/chat", json={"mensagem": "oi"}).status_code == 502
    assert "padrao" not in chatbot.conversas or chatbot.conversas["padrao"] == []


def test_prompt_tem_a_data_de_hoje():
    prompt = chatbot.montar_prompt_sistema(date(2026, 11, 13))
    assert "2026-11-13 (sexta)" in prompt


def test_health(cliente):
    assert cliente.get("/health").json() == {"status": "ok"}


def test_com_token_configurado_so_o_backend_conversa(cliente, monkeypatch):
    monkeypatch.setenv("CHATBOT_TOKEN", "segredo")
    usar_modelo_falso(monkeypatch, AIMessage(content="Oi!"))
    corpo = {"mensagem": "oi", "id_sessao": "s3"}

    assert cliente.post("/chat", json=corpo).status_code == 401
    assert cliente.post("/chat", json=corpo, headers={"X-Chatbot-Token": "errado"}).status_code == 401
    assert cliente.delete("/chat/s3").status_code == 401
    assert cliente.post("/chat", json=corpo, headers={"X-Chatbot-Token": "segredo"}).json() == {"resposta": "Oi!"}
    # o health check continua aberto (Docker/monitoramento)
    assert cliente.get("/health").status_code == 200


def test_audio_sem_fala_vira_422(cliente, monkeypatch):
    groq_falso = MagicMock()
    groq_falso.audio.transcriptions.create.return_value = SimpleNamespace(text=" . ")
    monkeypatch.setattr(chatbot, "cliente_groq", groq_falso)
    assert cliente.post("/chat/audio", files={"audio": ("msg.m4a", b"audio")}).status_code == 422
