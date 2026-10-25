# Arquitetura

`POST /sync` lê somente as views do schema `export` (papel `ro_databricks`), nunca
`public`. O CoreDB envia todas as views do schema para `<catálogo>.bronze_core`; o
AuthDB envia só `auth_user`, `federated_identity` e `federated_provider_link` para
`<catálogo>.bronze_auth`, e a carga falha se alguma delas não existir. O catálogo
(`analytics`, ou `analyticsqa` em QA) vem de `DATABRICKS_CATALOG`.
As pipelines Silver e Gold ficam no `databricks-stocker`.

```text
CoreDB export -> databricks-sync /sync -> <catálogo>.bronze_core
AuthDB export -> databricks-sync /sync -> <catálogo>.bronze_auth
                                -> Silver -> Gold (databricks-stocker)
                                            -> Databricks Job task
                                            -> databricks-sync /sync/gold
                                            -> analyticsdb.gold
```

O job de Databricks executa Silver, depois Gold e, após sucesso das duas,
chama `POST /sync/gold`. O endpoint usa a mesma verificação de Bearer token e
a mesma trava local que o Bronze. O manifesto fixa as views que podem ser
exportadas. O destino PostgreSQL usa uma transação para substituir as tabelas
de KPI e Row Level Security para isolar os consumidores.

Veja [GOLD.md](GOLD.md) para o contrato, a preparação do banco e as limitações.
