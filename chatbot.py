"""Lógica do chatbot do Huga Buga Hotel usando a API do Groq."""

import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODELO = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_MENSAGENS_HISTORICO = 20  # limita o histórico enviado ao modelo

INFO_HOTEL = (Path(__file__).parent / "hotel_info.md").read_text(encoding="utf-8")

PROMPT_SISTEMA = f"""Você é o Bugão, assistente virtual do Huga Buga Hotel.

Regras:
- Responda sempre em português do Brasil, de forma simpática, clara e curta.
- Use apenas as informações do hotel abaixo. Se não souber a resposta, diga que
  não tem essa informação e indique o contato da recepção.
- Não invente preços, horários ou serviços.
- Você não faz reservas: oriente o hóspede a reservar pelo site, app, telefone ou WhatsApp.
- Se a pergunta não tiver relação com o hotel ou com hospedagem/turismo, diga
  educadamente que só pode ajudar com assuntos do Huga Buga Hotel.

Informações do hotel:
{INFO_HOTEL}
"""

cliente = Groq()  # lê a chave da variável de ambiente GROQ_API_KEY

# Histórico de cada conversa, guardado em memória: {id_sessao: [mensagens]}
conversas: dict[str, list[dict]] = {}


def responder(mensagem: str, id_sessao: str = "padrao") -> str:
    """Envia a mensagem do usuário ao modelo e devolve a resposta do bot."""
    historico = conversas.setdefault(id_sessao, [])
    nova_mensagem = {"role": "user", "content": mensagem}

    resposta = cliente.chat.completions.create(
        model=MODELO,
        messages=[{"role": "system", "content": PROMPT_SISTEMA}]
        + historico[-MAX_MENSAGENS_HISTORICO:]
        + [nova_mensagem],
        temperature=0.5,
    )
    texto = resposta.choices[0].message.content

    # Só salva no histórico se a chamada deu certo
    historico.extend([nova_mensagem, {"role": "assistant", "content": texto}])
    return texto


def limpar_conversa(id_sessao: str) -> None:
    """Apaga o histórico de uma conversa."""
    conversas.pop(id_sessao, None)


if __name__ == "__main__":
    # Modo terminal, para testar o bot sem a API
    print("Bugão - Huga Buga Hotel (digite 'sair' para encerrar)\n")
    while True:
        pergunta = input("Você: ").strip()
        if pergunta.lower() in ("sair", "exit", "quit"):
            break
        if pergunta:
            print(f"Bugão: {responder(pergunta)}\n")
