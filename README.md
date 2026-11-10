# Chatbot Huga Buga Hotel

O **Bugão** responde dúvidas sobre o hotel e consulta o sistema de reservas (cavernas,
disponibilidade, cotação, atividades, restaurante, status de reserva). É exposto como uma
**API REST**, integrada ao backend Java (AWS) e ao app mobile (Java/Kotlin).

- Aceita mensagens de **texto** e de **voz** (o áudio é transcrito com o Whisper do Groq).
- Responde no **mesmo idioma** do hóspede (português, inglês, espanhol e outros).
- É um **agente com tools** (aula 05) que usa **RAG com fallback por score** (aulas 07 e 08).

## Como o bot funciona

```
pergunta ─▶ agente (LangChain + Groq) ─┬─▶ buscar_informacoes_hotel ─▶ RAG: Chroma + embeddings do hotel_info.md
                                       └─▶ tools do sistema ──────────▶ backend Java (GET /cavernas, /restaurante...)
```

| Arquivo          | O que faz                                                                        |
| ---------------- | -------------------------------------------------------------------------------- |
| `app.py`         | API REST (FastAPI): `/chat`, `/chat/audio`, `/health`                            |
| `chatbot.py`     | agente (`create_agent`), prompt do sistema, histórico e transcrição de áudio      |
| `ferramentas.py` | as tools que o agente pode chamar                                                 |
| `rag.py`         | banco vetorial (Chroma) com o `hotel_info.md`, busca com score mínimo             |
| `backend.py`     | cliente HTTP do backend Java (só GETs públicos; erros viram mensagem amigável)   |
| `hotel_info.md`  | base de conhecimento: políticas, horários, serviços, contatos                     |

**RAG:** o `hotel_info.md` é dividido em trechos (um item por trecho, com o título da seção) e
indexado em memória quando a API sobe, usando o modelo multilíngue
`paraphrase-multilingual-MiniLM-L12-v2` (pergunta em inglês/espanhol encontra o texto em
português). Só entram no contexto trechos com score ≥ `RAG_SCORE_MINIMO` (0,35). Se nada passar,
a tool responde "nenhuma informação" e o bot indica a recepção (fallback). Teste a busca com:
`python rag.py "Do you accept pets?"`.

**Tools do sistema** (todas só de consulta):

| Tool                     | Rota do backend                    |
| ------------------------ | ---------------------------------- |
| `buscar_cavernas`        | `GET /cavernas` (filtros, disponibilidade) |
| `detalhar_caverna`       | `GET /cavernas/{slug}`             |
| `cotar_estadia`          | `GET /cavernas/{id}/cotacao`       |
| `avaliacoes_caverna`     | `GET /cavernas/{id}/relatos`       |
| `listar_comodidades`     | `GET /comodidades`                 |
| `listar_extras`          | `GET /extras`                      |
| `listar_atividades`      | `GET /atividades`                  |
| `horarios_atividade`     | `GET /atividades/{id}/sessoes`     |
| `info_restaurante`       | `GET /restaurante`                 |
| `cardapio_restaurante`   | `GET /restaurante/cardapio`        |
| `horarios_restaurante`   | `GET /restaurante/horarios`        |
| `consultar_reserva`      | `GET /reservas/buscar?codigo=&email=` |

O bot **não** reserva, paga, cancela, altera datas nem agenda: essas ações exigem o usuário
logado e ficam no app/site. O bot explica o caminho.

## Como rodar

1. Crie uma chave de API em https://console.groq.com/keys
2. Instale as dependências:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate # no Windows: .venv\Scripts\activate
   pip install torch --index-url https://download.pytorch.org/whl/cpu   # PyTorch só-CPU (menor)
   pip install -r requirements-dev.txt
   ```
3. Copie `.env.example` para `.env`, coloque sua chave em `GROQ_API_KEY` e o endereço do backend
   Java em `BACKEND_URL` (com `/api/v1`). Sem o backend, o bot continua respondendo pela base de conhecimento.
4. Escolha como testar:
   - **Terminal:** `python chatbot.py` (digite uma pergunta, ou o caminho de um arquivo
     de áudio, ex.: `pergunta.m4a`, para testar a transcrição)
   - **API:** `uvicorn app:app --reload --host 0.0.0.0 --port 8000`
     e abra o localhost:porta/docs para testar pelo navegador (dá para enviar áudio por lá).
   - **Docker:** `docker build -t chatbot-huga-buga . && docker run --env-file .env -p 8000:8000 chatbot-huga-buga`
5. Antes de abrir um PR, rode `ruff check . && ruff format --check . && pytest` (é o que o CI roda).

## Endpoints da API

### `POST /chat` — mensagem de texto

```json
// requisição
{ "mensagem": "What time is check-in?", "id_sessao": "usuario-123" }

// resposta
{ "resposta": "Check-in starts at 1 PM! 😊" }
```

- `id_sessao` identifica a conversa, para o bot lembrar das mensagens anteriores.
  Cada usuário deve usar um id diferente (ex.: o id do usuário logado ou um UUID).
- Em caso de erro com o Groq, a API devolve status `502`.

### `POST /chat/audio` — mensagem de voz

Requisição `multipart/form-data`:

| Campo       | Obrigatório | Descrição                                                                 |
| ----------- | ----------- | ------------------------------------------------------------------------- |
| `audio`     | sim         | arquivo `m4a`, `mp3`, `ogg`, `wav`, `webm`, `flac`, `mp4`, `mpeg`, `mpga` (até 25 MB) |
| `id_sessao` | não         | mesmo id usado no `/chat` (texto e voz compartilham o histórico)          |
| `idioma`    | não         | dica de idioma ISO-639-1 (`pt`, `en`, `es`). Sem ela, o idioma é detectado sozinho |

```bash
curl -X POST http://localhost:8000/chat/audio \
  -F "audio=@pergunta.m4a" -F "id_sessao=usuario-123"
```

```json
// resposta
{ "transcricao": "¿Aceptan mascotas?", "resposta": "¡Sí! Aceptamos mascotas pequeñas (hasta 10 kg)..." }
```

- `transcricao` pode ser mostrada no app como a "bolha" da mensagem do usuário.
- Erros: `415` formato não suportado, `400` arquivo vazio, `413` maior que 25 MB,
  `422` áudio sem fala reconhecível, `502` falha no Groq.

### `DELETE /chat/{id_sessao}`

Apaga o histórico daquela conversa (ex.: quando o usuário fecha o chat).

### `GET /health`

Retorna `{"status": "ok"}` para verificar se a API está no ar.

## Voz e idioma

1. O app grava o áudio e envia o arquivo.
2. A API manda o áudio para o **Whisper** (`whisper-large-v3-turbo`, no Groq), que detecta o
   idioma e devolve o texto transcrito no idioma original.
3. O texto entra no mesmo fluxo do `/chat`. O prompt do sistema manda o modelo responder
   **no idioma da última mensagem** do hóspede, traduzindo as informações do `hotel_info.md`.

Não é preciso manter uma base de conhecimento por idioma: a base fica em português e o modelo traduz.

## Integração (backend Java + app Android, na AWS)

```
App Android / Site ──HTTPS──▶ Backend Java  /api/v1/chat ──rede interna + X-Chatbot-Token──▶ esta API ──▶ Groq
                                     ▲                                                           │
                                     └──────────── tools: GET /api/v1/cavernas, /restaurante... ─┘
```

- **O app não chama o chatbot direto.** Ele usa `POST /api/v1/chat`, `POST /api/v1/chat/audio` e
  `DELETE /api/v1/chat/{idSessao}` do backend (`ChatController` / `ChatbotService` no repositório
  Backend-Huga-Buga), que repassa para cá. A chave do Groq nunca vai para o app.
- **`id_sessao`:** quem monta é o backend (`usuario-<uuid>-<conversa>` ou `anonimo-<conversa>`), a partir de
  um UUID que o app gera por conversa. Assim ninguém consegue escrever na conversa de outra pessoa.
- **`CHATBOT_TOKEN`:** com ele definido, `/chat*` exige o header `X-Chatbot-Token` (o backend envia o mesmo
  valor). O `/health` continua aberto. Sem ele (desenvolvimento), a API fica aberta.
- **`BACKEND_URL`** inclui o prefixo: `http://localhost:8080/api/v1` (no Docker de produção: `http://api:8080/api/v1`).
- **Deploy:** o `deploy/aws/docker-compose.yml` do backend sobe API + este chatbot + Caddy (HTTPS) numa EC2,
  com banco no RDS e fotos no S3. Os dois repositórios ficam lado a lado na EC2. Passo a passo em
  `Backend-Huga-Buga/deploy/aws/README.md`.
- **Histórico em memória:** funciona com **uma** instância (como no compose). Para várias, o histórico
  precisa ir para um armazenamento compartilhado (Redis/ElastiCache ou DynamoDB).
- **App Android:** a tela do chat (`ChatbotActivity`) envia texto e voz (m4a/AAC 16 kHz mono, até 2 min) e
  apaga a conversa ao fechar.

## Limitações

- O histórico das conversas fica em memória: é perdido quando a API reinicia.
- O bot só consulta: reservas, pagamentos e cancelamentos são feitos no app/site.
- A API sobe em alguns segundos a mais por causa do modelo de embeddings, e a imagem Docker
  fica com ~1,5 GB (PyTorch + modelo).
- O Groq cobra no mínimo 10 segundos por áudio transcrito, mesmo que o áudio seja mais curto.
