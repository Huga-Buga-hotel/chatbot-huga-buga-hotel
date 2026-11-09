"""Tools do agente (aula 05): o modelo decide sozinho quando chamar cada uma.

Todas são de CONSULTA. Ações que mudam dados (reservar, pagar, cancelar,
alterar datas, agendar) ficam no app/site, onde o hóspede está logado.
Datas sempre no formato AAAA-MM-DD.
"""

from langchain_core.tools import tool

import rag
from backend import consultar


@tool
def buscar_informacoes_hotel(pergunta: str) -> str:
    """Busca na base de conhecimento do hotel: horários de check-in/check-out,
    políticas (pets, cancelamento, silêncio, fumo, documentos), formas de
    pagamento, lazer, serviços, endereço e contatos. Escreva a pergunta em
    português, mesmo que o hóspede tenha escrito em outro idioma."""
    trechos = rag.buscar(pergunta)
    if not trechos:
        return "Nenhuma informação sobre isso na base do hotel."
    return "\n\n---\n\n".join(trechos)


@tool
def buscar_cavernas(
    check_in: str | None = None,
    check_out: str | None = None,
    adultos: int | None = None,
    idades_criancas: list[int] | None = None,
    categoria: str | None = None,
    preco_min: float | None = None,
    preco_max: float | None = None,
    comodidades: list[str] | None = None,
    acessivel: bool | None = None,
    ordem: str | None = None,
) -> str:
    """Busca as cavernas (acomodações/quartos) do hotel, com disponibilidade e
    preço quando check_in e check_out são informados. `ordem` pode ser
    "nota", "menor_preco" ou "maior_preco". Para filtrar por comodidades, use
    os nomes de listar_comodidades."""
    return consultar(
        "/cavernas",
        {
            "checkIn": check_in,
            "checkOut": check_out,
            "adultos": adultos,
            "idadesCriancas": idades_criancas,
            "categoria": categoria,
            "precoMin": preco_min,
            "precoMax": preco_max,
            "comodidades": comodidades,
            "acessivel": acessivel,
            "ordem": ordem,
            "page": 0,
            "size": 5,
        },
    )


@tool
def detalhar_caverna(slug: str) -> str:
    """Detalhes de uma caverna (descrição, capacidade, comodidades), pelo slug
    retornado em buscar_cavernas."""
    return consultar(f"/cavernas/{slug}")


@tool
def cotar_estadia(
    caverna_id: int,
    check_in: str,
    check_out: str,
    adultos: int,
    idades_criancas: list[int] | None = None,
) -> str:
    """Calcula o valor exato de uma estadia numa caverna (use o id retornado
    em buscar_cavernas). Use sempre esta tool para falar de valor total."""
    return consultar(
        f"/cavernas/{caverna_id}/cotacao",
        {
            "checkIn": check_in,
            "checkOut": check_out,
            "adultos": adultos,
            "idadesCriancas": idades_criancas,
        },
    )


@tool
def avaliacoes_caverna(caverna_id: int) -> str:
    """Avaliações (relatos) de hóspedes sobre uma caverna."""
    return consultar(f"/cavernas/{caverna_id}/relatos", {"page": 0, "size": 5})


@tool
def listar_comodidades() -> str:
    """Lista as comodidades que podem ser usadas como filtro em buscar_cavernas."""
    return consultar("/comodidades")


@tool
def listar_extras() -> str:
    """Catálogo de extras que podem ser adicionados a uma reserva (ex.: transfer, decoração)."""
    return consultar("/extras")


@tool
def listar_atividades(categoria: str | None = None) -> str:
    """Catálogo de atividades do hotel (trilhas, recreação etc.), com filtro opcional de categoria."""
    return consultar("/atividades", {"categoria": categoria})


@tool
def horarios_atividade(atividade_id: int, de: str | None = None, ate: str | None = None) -> str:
    """Sessões (horários) e vagas de uma atividade entre as datas `de` e `ate`."""
    return consultar(f"/atividades/{atividade_id}/sessoes", {"de": de, "ate": ate})


@tool
def info_restaurante() -> str:
    """Restaurante O Banquete: turnos, se está aberto agora e desconto para hóspedes."""
    return consultar("/restaurante")


@tool
def cardapio_restaurante(categoria: str | None = None) -> str:
    """Cardápio do restaurante O Banquete, com filtro opcional de categoria."""
    return consultar("/restaurante/cardapio", {"categoria": categoria})


@tool
def horarios_restaurante(data: str, pessoas: int) -> str:
    """Horários do restaurante numa data para N pessoas (LIVRE ou LOTADO)."""
    return consultar("/restaurante/horarios", {"data": data, "pessoas": pessoas})


@tool
def consultar_reserva(codigo: str, email: str) -> str:
    """Consulta o status de uma reserva. Precisa do código da reserva E do
    e-mail usado nela: peça os dois ao hóspede, nunca invente."""
    return consultar("/reservas/buscar", {"codigo": codigo, "email": email})


TODAS = [
    buscar_informacoes_hotel,
    buscar_cavernas,
    detalhar_caverna,
    cotar_estadia,
    avaliacoes_caverna,
    listar_comodidades,
    listar_extras,
    listar_atividades,
    horarios_atividade,
    info_restaurante,
    cardapio_restaurante,
    horarios_restaurante,
    consultar_reserva,
]
