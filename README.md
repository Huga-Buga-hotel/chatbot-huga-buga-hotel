# Chatbot Huga Buga Hotel

Responde dúvidas sobre o hotel (quartos, preços, horários, lazer, políticas etc.) e é exposto
como uma **API REST**, para ser integrado aos aplicativos web e mobile feitos em Java.

## Como rodar

1. Crie uma chave de API em https://console.groq.com/keys
2. Instale as dependências:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate # no Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copie `.env.example` para `.env` e coloque sua chave em `GROQ_API_KEY`.
4. Escolha como testar:
   - **Terminal:** `python chatbot.py`
   - **API:** `uvicorn app:app --reload --host 0.0.0.0 --port 8000`
     e abra o localhost:porta/docs para testar pelo navegador.

## Endpoints da API

### `POST /chat`

Envia uma mensagem e recebe a resposta do bot.

```json
// requisição
{ "mensagem": "Qual o horário do check-in?", "id_sessao": "usuario-123" }

// resposta
{ "resposta": "O check-in é a partir das 14h! 😊" }
```

- `id_sessao` identifica a conversa, para o bot lembrar das mensagens anteriores.
  Cada usuário/aba do app deve usar um id diferente (ex.: um UUID).
- Em caso de erro com o Groq, a API devolve status `502`.

### `DELETE /chat/{id_sessao}`

Apaga o histórico daquela conversa (ex.: quando o usuário fecha o chat).

### `GET /health`

Retorna `{"status": "ok"}` para verificar se a API está no ar.

## Integração com Java (exemplo)

```java
HttpClient client = HttpClient.newHttpClient();

String json = """
    {"mensagem": "Vocês aceitam pets?", "id_sessao": "usuario-123"}
    """;

HttpRequest request = HttpRequest.newBuilder()
        .uri(URI.create("http://localhost:8000/chat"))
        .header("Content-Type", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(json))
        .build();

HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.body()); // {"resposta": "..."}
```

Observações:

- O CORS já está liberado, então o front-end web também pode chamar a API direto pelo navegador.

## Limitações

- O histórico das conversas fica em memória: é perdido quando a API reinicia.
- O bot não faz reservas de verdade, só orienta o usuário.
