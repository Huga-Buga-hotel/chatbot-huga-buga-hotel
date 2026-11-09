import ferramentas
import rag


def test_trechos_levam_o_titulo_da_secao():
    trechos = rag.dividir_em_trechos(rag.ARQUIVO_BASE.read_text(encoding="utf-8"))
    assert len(trechos) > 10
    assert all(trecho.startswith("## ") for trecho in trechos)
    pet = next(trecho for trecho in trechos if "Pet friendly" in trecho)
    assert pet.startswith("## Lazer e serviços")


def test_tool_sem_resultado_relevante(monkeypatch):
    monkeypatch.setattr(rag, "buscar", lambda pergunta: [])
    assert "Nenhuma informação" in ferramentas.buscar_informacoes_hotel.invoke({"pergunta": "copa de 2002"})


def test_tool_junta_trechos(monkeypatch):
    monkeypatch.setattr(rag, "buscar", lambda pergunta: ["## Horários\n- Check-in: 13h", "## Políticas\n- Silêncio"])
    resposta = ferramentas.buscar_informacoes_hotel.invoke({"pergunta": "check-in"})
    assert "Check-in: 13h" in resposta and "Silêncio" in resposta
