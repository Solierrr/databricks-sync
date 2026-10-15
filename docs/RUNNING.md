# Executando localmente

O serviço disponibiliza uma API FastAPI para iniciar manualmente a sincronização completa dos bancos `core` e `auth` para a camada Bronze do Databricks. O servidor não dispara sincronizações automaticamente.

## Requisitos

- Python 3.12 ou superior
- GNU Make
- Acesso de rede aos Postgres e ao SQL Warehouse Databricks
- Credenciais em `Inter/.env`, um nível acima deste repositório

Copie as variáveis de [`.env.example`](../.env.example) para o `.env` local e preencha os acessos aos dois bancos, Databricks e um `SYNC_API_TOKEN` forte. Não coloque credenciais reais em arquivos versionados.

## Iniciar

Na pasta `databricks-sync`, instale as dependências e inicie a API:

```sh
make install
make dev
```

O servidor escuta em `0.0.0.0:8000`. A documentação interativa OpenAPI fica em `http://localhost:8000/docs` e `GET /health` responde sem token (serve para acordar o serviço no Render gratuito).

## Executar uma sincronização

Na interface `/docs`, selecione **Authorize**, informe o Bearer token definido por `SYNC_API_TOKEN` e:

1. Execute `POST /sync`. A resposta é `202` com o `id` da tarefa; se já houver uma em andamento, `409`; se faltar variável de ambiente, `503`.
2. Chame `GET /sync/{id}` até o `status` deixar de ser `running`. O andamento mostra tabelas e linhas sincronizadas; ao final, `result` traz o resumo e, se alguma tabela falhou, os erros por tabela.

`POST /sync?wait=true` mantém o comportamento antigo: a requisição só termina quando a sincronização acabar, com `200` e o resumo, ou `500` com as tabelas que falharam. Como cada tabela é recriada com `CREATE OR REPLACE TABLE`, uma falha durante a carga pode deixar aquela tabela parcialmente preenchida; confira os detalhes antes de repetir.

O workflow [`sync.yml`](../.github/workflows/sync.yml) também pode ser iniciado manualmente em GitHub Actions como alternativa (`python synchronizer.py`). Ele não tem execução agendada.

## Testes

```sh
make test   # pytest com bancos simulados
make lint   # ruff
```
