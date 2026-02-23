# Railway Environment Variables Setup

## 📌 IMPORTANTES: O que copicar e o que NÃO copiar

### ❌ NÃO COPIE (são locais):
- `OLLAMA_BASE_URL` — seu ollama local, Railway não tem
- `INGESTION_PROVIDER=open_source` — em Railway use `gemini`
- `EMBEDDING_PROVIDER=open_source` — em Railway use `gemini`
- `QDRANT_HOST=qdrant` — Docker local, Railway será diferente
- `UPLOAD_DIR` / `IMAGES_DIR` — caminhos Docker, adaptar ao Railway
- `.env` não vai acompanhar (gitignored) — precisa configurar via Railway UI

### ✅ COPIE PARA RAILWAY:

#### Backend Essenciais:

| Variável | Seu Valor | Descrição |
|----------|-----------|-----------|
| `GEMINI_API_KEY` | `AIzaSyDljC04sFQY2IVTnYBV6NPLfyagm9fC4Bw` | Chave Google Gemini (manter) |
| `SECRET_KEY` | `Andreja2024SuperSecretKeyChangeThisInProduction_xK9mP2zQr8` | JWT secret (trocar em prod!) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token expiration (8h) |
| `ADMIN_EMAIL` | `admin@andreja.com` | Default admin |
| `ADMIN_PASSWORD` | `admin123` | Default admin (trocar depois!) |
| `EMBEDDING_VECTOR_SIZE` | `768` | Vector dimension |
| `INGESTION_PAGE_DELAY_SECONDS` | `0` | Sem delay |
| `OLLAMA_TIMEOUT_SECONDS` | `180` | Timeout (Railway não usa Ollama mesmo) |

#### Backend — Railways específicas:

| Variável | Valor no Railway | Descrição |
|----------|------------------|-----------|
| `INGESTION_PROVIDER` | `gemini` | ⚠️ Mude de `open_source` para `gemini` |
| `EMBEDDING_PROVIDER` | `gemini` | ⚠️ Mude de `open_source` para `gemini` |
| `QDRANT_HOST` | `[Qdrant Service name no Railway]` | Ex: `qdrant` ou IP service |
| `QDRANT_PORT` | `6333` | Porta padrão |
| `DATABASE_URL` | `sqlite:////app/data/andreja.db` | Persiste em volume ou mude para PostgreSQL |
| `UPLOAD_DIR` | `/app/data/uploads` | Dentro do container |
| `IMAGES_DIR` | `/app/data/images` | Dentro do container |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | (Não usado em Railway, mas deixe preenchido) |
| `OLLAMA_MODEL` | `qwen2.5vl:7b` | (Não usado em Railway) |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | (Não usado em Railway) |

#### Frontend (build-time):

| Variável | Seu Valor | Descrição |
|----------|-----------|-----------|
| `RAG_SERVER_URL` | Para Railway: `https://seu-backend.railway.app` | URL do backend (sem trailing slash) |
| `RAG_API_KEY` | (opcional, deixe vazio) | Não usado atualmente |
| `RAG_ADMIN_KEY` | (opcional, deixe vazio) | Não usado atualmente |
| `MP_PUBLIC_KEY` / `MERCADO_PAGO_PUBLIC_KEY` | (opcional) | Se usar Mercado Pago |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | (opcional) | Se usar Supabase |

---

## 🚀 PASSO A PASSO:

### 1. **Criar serviços no Railway**
   - Backend (FastAPI + Python)
   - Frontend (Node.js + Vite)
   - Qdrant (Vector database)
   - (Opcional) PostgreSQL se não usar SQLite

### 2. **Backend: variables**
   Copiar todas da tabela **Backend Essenciais** + **Railways específicas**.
   
   ⚠️ **IMPORTANTE**: Mude `INGESTION_PROVIDER` e `EMBEDDING_PROVIDER` de `open_source` → `gemini`

### 3. **Frontend: variables**
   - `RAG_SERVER_URL=https://seu-backend.railway.app` (substitua pelo seu domínio)
   - Opcionais: `RAG_API_KEY`, `RAG_ADMIN_KEY`, `MP_PUBLIC_KEY`
   
   Rebuild/redeploy frontend com `npm run build`

### 4. **Qdrant: variables**
   Configure conforme Railway requer (host, porta, chave API se houver)

### 5. **Conectar Railway ao GitHub**
   - Railway já lê `docker-compose.yml` / `Dockerfile`
   - Cada commit em `main` faz rebuild automático

---

## ⚠️ ALERTAS:

1. **`INGESTION_PROVIDER` e `EMBEDDING_PROVIDER`**  
   No local é `open_source` (Ollama), no Railway deve ser `gemini` (vai chamar API Google).

2. **`UPLOAD_DIR` / `IMAGES_DIR`**  
   Em Railway precisam ser em volume persistente ou bancos externos.

3. **`QDRANT_HOST`**  
   Mude de `localhost` para o hostname do serviço Qdrant no Railway.

4. **Secrets**  
   `GEMINI_API_KEY` e `SECRET_KEY` — marque como "sensitive" no Railway.

---

## 📝 Resumo Rápido:

**Copie direto:** `GEMINI_API_KEY`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`  
**Adapte:** `INGESTION_PROVIDER` → `gemini`, `EMBEDDING_PROVIDER` → `gemini`, `QDRANT_HOST` → service name  
**Frontend:** Configure `RAG_SERVER_URL` com domínio do backend no Railway

---

## ✅ CENÁRIO MAIS SIMPLES (SEU CASO AGORA): Frontend no Railway + Backend na VPS

Se você for subir **somente o frontend** no Railway e manter backend/Qdrant na VPS, configure no serviço de frontend:

- `RAG_SERVER_URL=https://SEU_BACKEND_PUBLICO` (URL pública da API na VPS)
- `BACKEND_URL=https://SEU_BACKEND_PUBLICO` (para proxy Nginx em `/api`, `/auth`, `/chat`, `/admin`)

Exemplo:

- `RAG_SERVER_URL=https://api.uxcodedev.com.br`
- `BACKEND_URL=https://api.uxcodedev.com.br`

Nesse cenário, **não precisa configurar `QDRANT_HOST` no Railway frontend**.
