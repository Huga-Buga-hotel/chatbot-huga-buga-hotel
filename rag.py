"""RAG: busca trechos relevantes do hotel_info.md num banco vetorial (Chroma).

Baseado nas aulas 07 e 08: divide o documento em chunks, gera embeddings com
sentence-transformers e busca por similaridade com score. Só devolve trechos
com score acima do mínimo (se nada for relevante, o bot cai no "fallback" e
diz que não tem a informação).

O hotel_info.md é pequeno, então o banco é montado em memória quando a API
sobe: assim ele nunca fica desatualizado em relação ao arquivo.

Teste rápido no terminal:  python rag.py "Do you accept pets?"
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

ARQUIVO_BASE = Path(__file__).parent / "hotel_info.md"

# Modelo multilíngue: perguntas em inglês/espanhol encontram o texto em português.
# (o all-mpnet-base-v2 usado em aula só funciona bem em inglês)
MODELO_EMBEDDINGS = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
SCORE_MINIMO = float(os.getenv("RAG_SCORE_MINIMO", "0.35"))
QTD_TRECHOS = 3


def carregar_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=MODELO_EMBEDDINGS,
        encode_kwargs={"normalize_embeddings": True},
    )


def dividir_em_trechos(texto: str) -> list[str]:
    """Divide o markdown por seção (## Título) e quebra seções longas em
    pedaços menores. Cada chunk leva o título da seção, para não perder o contexto.
    Chunks pequenos e focados dão scores de similaridade mais claros."""
    secoes = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "secao")],
        strip_headers=True,
    ).split_text(texto)
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=120,
        chunk_overlap=0,
        separators=["\n\n", "\n- ", "\n"],
    )
    trechos = []
    for secao in secoes:
        titulo = secao.metadata.get("secao", "Huga Buga Hotel")
        for pedaco in divisor.split_text(secao.page_content):
            trechos.append(f"## {titulo}\n{pedaco.strip()}")
    return trechos


@lru_cache(maxsize=1)
def banco_vetorial() -> Chroma:
    """Cria o banco vetorial (uma vez só, na primeira busca)."""
    trechos = dividir_em_trechos(ARQUIVO_BASE.read_text(encoding="utf-8"))
    return Chroma.from_texts(
        texts=trechos,
        embedding=carregar_embeddings(),
        collection_name="hotel_info",
        collection_metadata={"hnsw:space": "cosine"},
    )


def buscar_com_scores(pergunta: str, k: int = QTD_TRECHOS) -> list[tuple[str, float]]:
    resultados = banco_vetorial().similarity_search_with_relevance_scores(pergunta, k=k)
    return [(documento.page_content, score) for documento, score in resultados]


def buscar(pergunta: str) -> list[str]:
    """Devolve só os trechos relevantes (score >= SCORE_MINIMO)."""
    return [texto for texto, score in buscar_com_scores(pergunta) if score >= SCORE_MINIMO]


if __name__ == "__main__":
    pergunta = " ".join(sys.argv[1:]) or input("Pergunta: ")
    for texto, score in buscar_com_scores(pergunta):
        marcador = "✔" if score >= SCORE_MINIMO else "✘"
        print(f"\n{marcador} Score: {score:.3f}\n{texto[:300]}")
