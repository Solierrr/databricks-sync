# Configuração local

Configure `.env` no diretório pai do repositório a partir de `.env.example`.
Preserve o `SYNC_API_TOKEN` existente. `POST /sync` usa credenciais de CoreDB
e Databricks; `POST /sync/gold` usa credenciais do SQL Warehouse, do
AnalyticsDB e o mesmo Bearer token.

O comando `make run` inicia a API FastAPI. A documentação OpenAPI fica em
`/docs`. Não execute os endpoints apenas para validar esta alteração: cada
chamada inicia uma sincronização real.

Para a exportação Gold, crie o banco com
`make create TARGET=analytics ENVIRONMENT=prod` no `database-console` e aplique
`make schema TARGET=analytics ENVIRONMENT=prod`. Cadastre as identidades de
exportação e leitura em `analytics_gold.principal_access` e provisione o row
filter do Databricks conforme [GOLD.md](GOLD.md). Configure o job Silver → Gold
→ exportação do `databricks-stocker` com a URL da API e o token em segredos do
Databricks. O job não é instalado automaticamente pelo repositório.

As tabelas Gold exportadas e a política de tipos estão em
`gold_export_manifest.json` e `gold_synchronizer.py`. O serviço falha diante
de uma view ausente ou mudança de schema, sem substituir parcialmente o
AnalyticsDB.

## Contrato, erros e saúde

O Swagger fica em `/docs` e o contrato em `/openapi.json`; `DOCS_ENABLED=false`
desliga os dois. O contrato versionado (`openapi.yaml`) é gerado por
`make openapi` e conferido no CI pelo lint de OpenAPI da organização: depois de
mudar uma rota, rode o comando e versione o resultado. A versão vem de
`version.txt`, atualizado pelo release-please junto com o `openapi.yaml`.

Todo erro responde `application/problem+json` no contrato de erro da
organização (`errorCode`, `detail`, `instance`, `timestamp`). Uma sincronização
com `wait=true` que termina com erros responde 500 `INTERNAL_ERROR` com o resumo
no campo `result`.

`GET /health` responde se o processo está vivo, sem tocar nos bancos.
`GET /ready` confere o CoreDB, o AnalyticsDB (quando `DB_ANALYTICS_HOST` está
definido) e o workspace do Databricks, com timeout de 2 segundos cada, e
responde 503 quando algum está fora. A checagem do Databricks usa a API REST do
workspace e não liga o SQL Warehouse.

`CORS_ALLOWED_ORIGINS` (separada por vírgula) libera as origens que abrem o
contrato pelo navegador, como o `web-sandbox`.
