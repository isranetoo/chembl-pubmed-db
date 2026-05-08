# Integração do frontend no repositório `chembl-pubmed-db`

O frontend agora vive diretamente em `frontend/`, sem a pasta aninhada `frontend/frontend/`.

## Localização

```txt
chembl-pubmed-db/
  api.py
  dashboard.py
  docker-compose.yml
  requirements.txt
  frontend/
    package.json
    src/
```

## Sequência de uso

### 1. Banco

O repositório já usa `docker-compose.yml` com PostgreSQL e pgAdmin:

```bash
docker compose up -d
```

### 2. API

Suba a API local na porta `8000`:

```bash
uvicorn api:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

## O que esse frontend consome

- `GET /stats`
- `GET /compounds`
- `GET /compounds/{chembl_id}`
- `GET /compounds/{chembl_id}/admet`
- `GET /compounds/{chembl_id}/indications`
- `GET /compounds/{chembl_id}/mechanisms`
- `GET /compounds/{chembl_id}/bioactivities`
- `GET /compounds/{chembl_id}/articles`
- `GET /articles`
- `GET /targets`
- `GET /search`

## Próximos ajustes sugeridos

1. Mover `DB_CONFIG` de `api.py` e `dashboard.py` para variáveis de ambiente.
2. Padronizar o naming visual entre repo, API e dashboard.
3. Adicionar um endpoint de health mais detalhado, se quiser mostrar status no frontend.
