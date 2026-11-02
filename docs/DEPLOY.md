<p align="center">
  <img src="../assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

# Execução e ambiente

O repositório mantém execução local e um workflow manual Bronze. Não há Dockerfile, manifesto de hospedagem ou workflow que publique este servidor na main analisada.

| Contexto | Endereço ou disparo | Evidência |
|---|---|---|
| Local | `http://localhost:8000` | Makefile |
| Ambiente declarado ALIVE | `https://databricks.solarianetwork.site` | Workflow de ambiente e OpenAPI |
| Carga manual no CI | `workflow_dispatch` | Workflow `sync.yml` |
| Exportação posterior ao pipeline | `POST /sync/gold` | Notebook do produtor |

O README de origem ainda afirma execução somente local, mas o serviço está hospedado no endereço consultado pelo workflow.

O workflow manual usa Python 3.14, instala dependências e executa `synchronizer.py` com secrets de PostgreSQL e Databricks. Não tem cron. O notebook consumidor envia Bearer e espera até 1800 segundos pela exportação. Não existe garantia de continuidade do job em memória após parada ou hibernação.

O fluxo comum está em [cópia analítica](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/ANALYTICS_SYNC.md). A configuração atual difere do texto antigo desse fluxo quanto ao banco de autenticação.

Fontes em [workflow de carga](https://github.com/Solierrr/databricks-sync/blob/main/.github/workflows/sync.yml), [ambiente](https://github.com/Solierrr/databricks-sync/blob/main/.github/workflows/environment-status.yml) e [bootstrap da API](https://github.com/Solierrr/databricks-sync/blob/main/app/main.py).
