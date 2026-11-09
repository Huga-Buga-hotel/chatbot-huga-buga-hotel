"""Lógica do chatbot do Huga Buga Hotel: agente LangChain + Groq com tools e RAG."""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from langchain.agents import create_agent
from langchain_groq import ChatGroq

import ferramentas

load_dotenv()

MODELO = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MODELO_TRANSCRICAO = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
MAX_MENSAGENS_HISTORICO = 20  # limita o histórico enviado ao modelo

DIAS_DA_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

PROMPT_SISTEMA = """Você é o Bugão, assistente virtual do Huga Buga Hotel.
Hoje é {hoje} ({dia_semana}).

Idioma:
- Responda SEMPRE no mesmo idioma da última mensagem do hóspede (ex.: português,
  inglês, espanhol), traduzindo as informações do hotel. Mantenha valores em
  reais (R$), horários e contatos. Se não der para identificar o idioma,
  responda em português do Brasil.

Como responder:
- Seja simpático, claro e curto.
- Use as ferramentas para buscar informações. Nunca invente preços, horários,
  disponibilidade ou serviços.
- Dúvidas gerais e políticas do hotel: use buscar_informacoes_hotel.
- Acomodações (cavernas), disponibilidade, preços, atividades, restaurante e
  reservas: use as ferramentas do sistema. Esses dados são os oficiais e têm
  prioridade sobre a base de conhecimento.
- Valor total de estadia: use cotar_estadia. Se faltar dado (datas, número de
  adultos, idades das crianças), pergunte ao hóspede antes.
- Converta datas citadas pelo hóspede ("sexta que vem", "next weekend") para
  AAAA-MM-DD a partir da data de hoje.
- Se uma ferramenta devolver ERRO ou nada relevante, diga que não tem essa
  informação agora e indique a recepção: (11) 99999-9999 (telefone/WhatsApp).
- Você só consulta. Reservar, pagar, cancelar, alterar datas, fazer check-in
  online ou agendar atividades/mesa é feito pelo hóspede no app ou site do
  Huga Buga: explique o caminho.
- Se a pergunta não tiver relação com o hotel ou com hospedagem/turismo, diga
  educadamente que só pode ajudar com assuntos do Huga Buga Hotel.
- Algumas mensagens são transcrições automáticas de áudio e podem ter pequenos
  erros de reconhecimento: interprete a intenção do hóspede. Se a mensagem
  estiver incompreensível, peça para ele repetir.
"""

llm = ChatGroq(model=MODELO, temperature=0.5, max_retries=2)
agente = create_agent(model=llm, tools=ferramentas.TODAS)

cliente_groq = Groq()  # usado na transcrição de áudio (lê GROQ_API_KEY)

# Histórico de cada conversa, guardado em memória: {id_sessao: [mensagens]}
# Guarda só as perguntas e respostas finais (as chamadas de tools não entram).
conversas: dict[str, list[dict]] = {}


def montar_prompt_sistema(hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    return PROMPT_SISTEMA.format(hoje=hoje.isoformat(), dia_semana=DIAS_DA_SEMANA[hoje.weekday()])


def responder(mensagem: str, id_sessao: str = "padrao") -> str:
    """Envia a mensagem do usuário ao agente e devolve a resposta do bot."""
    historico = conversas.setdefault(id_sessao, [])
    nova_mensagem = {"role": "user", "content": mensagem}

    resultado = agente.invoke(
        {
            "messages": [{"role": "system", "content": montar_prompt_sistema()}]
            + historico[-MAX_MENSAGENS_HISTORICO:]
            + [nova_mensagem]
        }
    )
    texto = resultado["messages"][-1].content

    # Só salva no histórico se a chamada deu certo
    historico.extend([nova_mensagem, {"role": "assistant", "content": texto}])
    return texto


def transcrever(audio: bytes, nome_arquivo: str, idioma: str | None = None) -> str:
    """Transcreve uma mensagem de voz com o Whisper (Groq) e devolve o texto.

    O Whisper detecta o idioma sozinho; `idioma` (código ISO-639-1, ex.: "pt",
    "en", "es") é opcional e só serve para melhorar a precisão.
    """
    opcionais = {"language": idioma} if idioma else {}
    transcricao = cliente_groq.audio.transcriptions.create(
        file=(nome_arquivo, audio),
        model=MODELO_TRANSCRICAO,
        temperature=0,
        **opcionais,
    )
    return transcricao.text.strip()


def limpar_conversa(id_sessao: str) -> None:
    """Apaga o histórico de uma conversa."""
    conversas.pop(id_sessao, None)


if __name__ == "__main__":
    # Modo terminal, para testar o bot sem a API.
    # Digite o caminho de um arquivo de áudio (ex.: audio.m4a) para testar a transcrição.
    print("Bugão - Huga Buga Hotel (digite 'sair' para encerrar)\n")
    while True:
        pergunta = input("Você: ").strip()
        if pergunta.lower() in ("sair", "exit", "quit"):
            break
        caminho = Path(pergunta)
        if caminho.suffix.lower() in (".mp3", ".m4a", ".ogg", ".wav", ".webm", ".flac") and caminho.is_file():
            pergunta = transcrever(caminho.read_bytes(), caminho.name)
            print(f"(transcrição) {pergunta}")
        if pergunta:
            print(f"Bugão: {responder(pergunta)}\n")
