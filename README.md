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
   Java em `BACKEND_URL`. Sem o backend, o bot continua respondendo pela base de conhecimento.
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

## Arquitetura recomendada (mobile + backend Java na AWS)

```
App mobile (Kotlin/Java) ──HTTPS──▶ Backend Java (Spring Boot, AWS) ──rede interna──▶ API do chatbot (Python, AWS) ──▶ Groq
                                            ▲                                                │
                                            └──────── tools: GET /cavernas, /restaurante... ─┘
```

- **O app não chama o chatbot direto.** Ele fala só com o backend Java, que autentica o usuário,
  usa o id do usuário como `id_sessao` e repassa a requisição. Assim a API do chatbot não fica
  exposta na internet e a chave do Groq nunca vai para o app.
- **Deploy do chatbot na AWS:** rode em container (ECS Fargate ou App Runner) ou numa EC2.
  Libere a porta só para o backend (security group) e guarde a `GROQ_API_KEY` em variável de
  ambiente ou no Secrets Manager.
- **Histórico em memória:** funciona com **uma** instância. Se o chatbot rodar com várias
  instâncias, o histórico precisa ir para um armazenamento compartilhado (Redis/ElastiCache ou DynamoDB).

### Backend Java (Spring Boot) — repassando texto e áudio

```java
@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final RestClient chatbot = RestClient.create("http://chatbot-interno:8000");

    record PerguntaChat(String mensagem, String id_sessao) {}
    record RespostaChat(String resposta) {}
    record RespostaChatAudio(String transcricao, String resposta) {}

    @PostMapping
    public RespostaChat texto(@RequestBody Map<String, String> body, Principal usuario) {
        return chatbot.post().uri("/chat")
                .contentType(MediaType.APPLICATION_JSON)
                .body(new PerguntaChat(body.get("mensagem"), usuario.getName()))
                .retrieve().body(RespostaChat.class);
    }

    @PostMapping(value = "/audio", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public RespostaChatAudio audio(@RequestPart("audio") MultipartFile audio,
                                   @RequestParam(required = false) String idioma,
                                   Principal usuario) {
        MultiValueMap<String, Object> form = new LinkedMultiValueMap<>();
        form.add("audio", audio.getResource()); // mantém o nome original do arquivo (ex.: .m4a)
        form.add("id_sessao", usuario.getName());
        if (idioma != null) form.add("idioma", idioma);

        return chatbot.post().uri("/chat/audio")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(form)
                .retrieve().body(RespostaChatAudio.class);
    }
}
```

Lembre de aumentar o limite de upload do Spring (o padrão é 1 MB):

```properties
spring.servlet.multipart.max-file-size=25MB
spring.servlet.multipart.max-request-size=25MB
```

### App Android (Kotlin) — gravando e enviando o áudio

Permissão no `AndroidManifest.xml`: `<uses-permission android:name="android.permission.RECORD_AUDIO" />`
(pedir também em tempo de execução).

```kotlin
// Gravação em .m4a (AAC), 16 kHz mono: arquivo pequeno e ideal para o Whisper
val arquivo = File(context.cacheDir, "mensagem.m4a")
val gravador = MediaRecorder(context).apply {   // API 31+; antes disso use MediaRecorder()
    setAudioSource(MediaRecorder.AudioSource.MIC)
    setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
    setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
    setAudioSamplingRate(16_000)
    setAudioChannels(1)
    setOutputFile(arquivo.absolutePath)
    prepare()
    start()
}
// ... quando o usuário soltar o botão:
gravador.stop(); gravador.release()

// Envio para o backend Java (OkHttp)
val corpo = MultipartBody.Builder().setType(MultipartBody.FORM)
    .addFormDataPart("audio", arquivo.name, arquivo.asRequestBody("audio/mp4".toMediaType()))
    .addFormDataPart("idioma", Locale.getDefault().language) // opcional: "pt", "en", "es"
    .build()

val requisicao = Request.Builder()
    .url("https://api.hugabuga.com.br/api/chat/audio")
    .header("Authorization", "Bearer $token")
    .post(corpo)
    .build()
// resposta: {"transcricao": "...", "resposta": "..."}
```

Para o bot também **falar** a resposta, o mais simples é usar o `TextToSpeech` nativo do
Android no próprio app (gratuito e funciona em vários idiomas).

## Limitações

- O histórico das conversas fica em memória: é perdido quando a API reinicia.
- O bot só consulta: reservas, pagamentos e cancelamentos são feitos no app/site.
- A API sobe em alguns segundos a mais por causa do modelo de embeddings, e a imagem Docker
  fica com ~1,5 GB (PyTorch + modelo).
- O Groq cobra no mínimo 10 segundos por áudio transcrito, mesmo que o áudio seja mais curto.
