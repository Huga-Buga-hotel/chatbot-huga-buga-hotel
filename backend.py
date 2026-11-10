"""Cliente HTTP do backend Java do Huga Buga Hotel (só rotas públicas de consulta).

As respostas são devolvidas como texto JSON compacto para o modelo ler.
Erros nunca derrubam o chatbot: viram uma mensagem que o modelo repassa ao hóspede.
"""

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()  # antes de ler as variáveis (este módulo é importado antes do chatbot.py)

# Inclui o prefixo da API: as rotas abaixo ("/cavernas"...) são relativas a ele
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080/api/v1")
TIMEOUT_SEGUNDOS = float(os.getenv("BACKEND_TIMEOUT", "10"))
MAX_CARACTERES = 6000  # evita mandar respostas gigantes para o modelo

_cliente = httpx.Client(base_url=BACKEND_URL, timeout=TIMEOUT_SEGUNDOS)


def _limpar_parametros(parametros: dict) -> dict:
    """Remove parâmetros vazios e transforma listas em "a,b,c"."""
    limpos = {}
    for chave, valor in parametros.items():
        if valor is None or valor == "" or valor == []:
            continue
        if isinstance(valor, (list, tuple)):
            valor = ",".join(str(item) for item in valor)
        if isinstance(valor, bool):
            valor = str(valor).lower()
        limpos[chave] = valor
    return limpos


def consultar(rota: str, parametros: dict | None = None) -> str:
    """Faz um GET no backend e devolve o corpo (ou uma mensagem de erro amigável)."""
    try:
        resposta = _cliente.get(rota, params=_limpar_parametros(parametros or {}))
    except httpx.HTTPError as erro:
        print(f"Backend indisponível ({rota}): {erro}")
        return "ERRO: o sistema de reservas está indisponível no momento."

    if resposta.status_code == 404:
        return "ERRO: não encontrado."
    if resposta.status_code in (400, 422):
        return f"ERRO: parâmetros inválidos. Detalhe do sistema: {resposta.text[:500]}"
    if resposta.status_code >= 400:
        print(f"Backend respondeu {resposta.status_code} em {rota}: {resposta.text[:300]}")
        return "ERRO: o sistema de reservas não conseguiu responder agora."

    try:
        texto = json.dumps(resposta.json(), ensure_ascii=False, separators=(",", ":"))
    except ValueError:
        texto = resposta.text
    if len(texto) > MAX_CARACTERES:
        texto = texto[:MAX_CARACTERES] + "... (resposta cortada)"
    return texto
