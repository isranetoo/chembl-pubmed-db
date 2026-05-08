# Frontend web — `chembl-pubmed-db`

Este frontend foi adaptado para entrar diretamente na raiz do repositório como pasta `frontend/`.

## Estrutura final esperada

```txt
chembl-pubmed-db/
  api.py
  dashboard.py
  docker-compose.yml
  requirements.txt
  populate.py
  refresh.py
  validate_db.py
  frontend/
    package.json
    vite.config.js
    tailwind.config.js
    src/
```

## Stack

- React + Vite
- Tailwind CSS
- React Router
- TanStack Query

## Páginas prontas

- `/` Dashboard inicial com métricas de `/stats`
- `/compounds` Explorer de compostos usando `/compounds`
- `/compounds/:chemblId` Detalhe do composto
- `/articles` Exploração de artigos
- `/targets` Exploração de targets
- `/search` Busca global usando `/search`

## Como subir junto com o projeto atual

Primeiro suba o banco com o `docker-compose.yml` do repositório:

```bash
docker compose up -d
```

Depois rode a API Python:

```bash
uvicorn api:app --reload --port 8000
```

Em outro terminal, rode o frontend:

```bash
cd frontend
npm install
npm run dev
```

## Variável de ambiente

Crie `frontend/.env` baseado em `frontend/.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Observações sobre o backend atual

- A API já está pronta para esse frontend porque expõe `/stats`, `/compounds`, `/articles`, `/targets` e `/search`.
- O `CORSMiddleware` em `api.py` já permite origem aberta, então o Vite roda sem bloqueio local.
- As credenciais do banco ainda estão hardcoded em `api.py` e `dashboard.py`, então o próximo passo recomendável é mover isso para `.env`.

## Melhorias já incluídas nessa adaptação

- pasta `frontend/` pronta para entrar na raiz do repo
- branding alinhado ao nome do repositório
- paginação visual em compostos, artigos e targets
- layout lateral consistente com a API já existente
