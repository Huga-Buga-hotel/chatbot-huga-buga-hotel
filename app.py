"""API REST do chatbot, para ser consumida pelos apps web e mobile (Java)."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chatbot import limpar_conversa, responder

app = FastAPI(title="Chatbot Huga Buga Hotel")

# Libera chamadas vindas do navegador (app web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PerguntaChat(BaseModel):
    mensagem: str = Field(min_length=1, max_length=1000)
    id_sessao: str = "padrao"


class RespostaChat(BaseModel):
    resposta: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=RespostaChat)
def chat(pergunta: PerguntaChat):
    try:
        return RespostaChat(resposta=responder(pergunta.mensagem, pergunta.id_sessao))
    except Exception as erro:
        print(f"Erro ao chamar o Groq: {erro}")
        raise HTTPException(status_code=502, detail="Não foi possível obter resposta do chatbot.")


@app.delete("/chat/{id_sessao}")
def encerrar_conversa(id_sessao: str):
    limpar_conversa(id_sessao)
    return {"status": "conversa encerrada"}
