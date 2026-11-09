import httpx
import pytest

import backend
import ferramentas


@pytest.fixture
def backend_falso(monkeypatch):
    """Substitui o backend Java por respostas fixas e guarda as requisições feitas."""
    requisicoes = []

    def responder(requisicao: httpx.Request) -> httpx.Response:
        requisicoes.append(requisicao)
        if requisicao.url.path == "/cavernas/nao-existe":
            return httpx.Response(404)
        if requisicao.url.path == "/restaurante":
            return httpx.Response(500, text="erro interno")
        return httpx.Response(200, json={"ok": True, "caminho": requisicao.url.path})

    cliente = httpx.Client(transport=httpx.MockTransport(responder), base_url="http://backend")
    monkeypatch.setattr(backend, "_cliente", cliente)
    return requisicoes


def test_buscar_cavernas_monta_parametros(backend_falso):
    resposta = ferramentas.buscar_cavernas.invoke(
        {
            "check_in": "2026-12-20",
            "check_out": "2026-12-23",
            "adultos": 2,
            "idades_criancas": [5, 8],
            "acessivel": True,
        }
    )
    assert '"ok":true' in resposta
    parametros = backend_falso[0].url.params
    assert backend_falso[0].url.path == "/cavernas"
    assert parametros["checkIn"] == "2026-12-20"
    assert parametros["idadesCriancas"] == "5,8"
    assert parametros["acessivel"] == "true"
    assert "categoria" not in parametros  # parâmetros vazios não são enviados


def test_cotar_estadia_usa_id_na_rota(backend_falso):
    ferramentas.cotar_estadia.invoke(
        {"caverna_id": 7, "check_in": "2026-12-20", "check_out": "2026-12-22", "adultos": 2}
    )
    assert backend_falso[0].url.path == "/cavernas/7/cotacao"


def test_consultar_reserva(backend_falso):
    ferramentas.consultar_reserva.invoke({"codigo": "HB123", "email": "a@b.com"})
    assert backend_falso[0].url.path == "/reservas/buscar"
    assert backend_falso[0].url.params["codigo"] == "HB123"


def test_erros_viram_mensagem(backend_falso):
    assert ferramentas.detalhar_caverna.invoke({"slug": "nao-existe"}) == "ERRO: não encontrado."
    assert ferramentas.info_restaurante.invoke({}).startswith("ERRO")


def test_backend_fora_do_ar(monkeypatch):
    def cair(requisicao):
        raise httpx.ConnectError("sem conexão")

    monkeypatch.setattr(backend, "_cliente", httpx.Client(transport=httpx.MockTransport(cair), base_url="http://x"))
    assert "indisponível" in ferramentas.listar_extras.invoke({})
