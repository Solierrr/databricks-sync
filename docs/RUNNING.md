# Configuração local

Configure `.env` no diretório pai do repositório a partir de `.env.example`.
Preserve o `SYNC_API_TOKEN` existente. `POST /sync` usa credenciais de CoreDB
(`DB_CORE_*`), AuthDB (`DB_AUTH_*`), ambas do papel `ro_databricks`, e
Databricks; `POST /sync/gold` usa credenciais do SQL Warehouse, do AnalyticsDB e
o mesmo Bearer token.

O comando `make run` inicia a API FastAPI. A documentação OpenAPI fica em
`/docs`. Não execute os endpoints apenas para validar esta alteração: cada
chamada inicia uma sincronização real.

Para a exportação Gold, crie o banco com
`make create TARGET=analytics ENVIRONMENT=prod` no `database-console` e aplique
`make schema TARGET=analytics ENVIRONMENT=prod`. Cadastre as identidades de
exportação e leitura em `gold.principal_access` e provisione o row
filter do Databricks conforme [GOLD.md](GOLD.md). Configure o job Silver → Gold
→ exportação do `databricks-stocker` com a URL da API e o token em segredos do
Databricks. O job não é instalado automaticamente pelo repositório.

As tabelas Gold exportadas e a política de tipos estão em
`gold_export_manifest.json` e `gold_synchronizer.py`. O serviço falha diante
de uma view ausente ou mudança de schema, sem substituir parcialmente o
AnalyticsDB.
