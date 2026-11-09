FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home bugao
WORKDIR /app

# PyTorch só-CPU: imagem ~1,5 GB menor que a versão com CUDA
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=bugao *.py hotel_info.md ./
USER bugao

# Baixa o modelo de embeddings no build: o container sobe sem depender do HuggingFace
RUN python -c "import rag; rag.carregar_embeddings()"
ENV HF_HUB_OFFLINE=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 1 worker só: o histórico das conversas fica em memória
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
