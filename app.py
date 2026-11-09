"""API REST do chatbot, para ser consumida pelos apps web e mobile (Java)."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import rag
from chatbot import limpar_conversa, responder, transcrever


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Carrega o modelo de embeddings e monta o banco vetorial ao subir a API,
    # para a primeira pergunta não ficar lenta.
    rag.banco_vetorial()
    yield


app = FastAPI(title="Chatbot Huga Buga Hotel", lifespan=ciclo_de_vida)

# Libera chamadas vindas do navegador (app web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Limites do Whisper no Groq (plano gratuito: até 25 MB por arquivo)
FORMATOS_AUDIO = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}
TAMANHO_MAX_AUDIO = 25 * 1024 * 1024


class PerguntaChat(BaseModel):
    mensagem: str = Field(min_length=1, max_length=1000)
    id_sessao: str = "padrao"


class RespostaChat(BaseModel):
    resposta: str


class RespostaChatAudio(BaseModel):
    transcricao: str
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
        raise HTTPException(status_code=502, detail="Não foi possível obter resposta do chatbot.") from erro


@app.post("/chat/audio", response_model=RespostaChatAudio)
def chat_audio(
    audio: Annotated[UploadFile, File(description="Mensagem de voz (m4a, mp3, ogg, wav, webm...)")],
    id_sessao: Annotated[str, Form()] = "padrao",
    idioma: Annotated[str | None, Form(description="Opcional: idioma ISO-639-1 (pt, en, es)")] = None,
):
    nome = audio.filename or "audio.m4a"
    if Path(nome).suffix.lower() not in FORMATOS_AUDIO:
        raise HTTPException(status_code=415, detail=f"Formato de áudio não suportado: {nome}")

    conteudo = audio.file.read(TAMANHO_MAX_AUDIO + 1)
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo de áudio vazio.")
    if len(conteudo) > TAMANHO_MAX_AUDIO:
        raise HTTPException(status_code=413, detail="Áudio maior que 25 MB.")

    try:
        texto = transcrever(conteudo, nome, idioma)
    except Exception as erro:
        print(f"Erro ao transcrever o áudio: {erro}")
        raise HTTPException(status_code=502, detail="Não foi possível transcrever o áudio.") from erro

    if not texto:
        raise HTTPException(status_code=422, detail="Não foi possível entender o áudio.")

    try:
        return RespostaChatAudio(transcricao=texto, resposta=responder(texto, id_sessao))
    except Exception as erro:
        print(f"Erro ao chamar o Groq: {erro}")
        raise HTTPException(status_code=502, detail="Não foi possível obter resposta do chatbot.") from erro


@app.delete("/chat/{id_sessao}")
def encerrar_conversa(id_sessao: str):
    limpar_conversa(id_sessao)
    return {"status": "conversa encerrada"}
