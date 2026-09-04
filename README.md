# Finalidade do repositório

O `databricks-sync` é um script Python de sincronização batch que replica os bancos Postgres operacionais da organização (o domínio `core` e o domínio `auth`) para a camada bronze de um Lakehouse Databricks. A cada execução, ele introspecta o `information_schema` de cada Postgres de origem, recria as tabelas de destino no Databricks com `CREATE OR REPLACE TABLE` traduzindo os tipos de coluna do Postgres para SQL do Databricks, e insere os dados lidos via `psycopg2` em lotes de 500 linhas com `executemany`. Não há API, servidor ou processo de longa duração aqui: é um job que roda do início ao fim e termina, disparado periodicamente por um workflow do GitHub Actions (`.github/workflows/sync.yml`), a cada 4 horas via `cron` ou manualmente via `workflow_dispatch`.

<p>

[![License](https://img.shields.io/github/license/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/pulls)
[![GitHub Contributors](https://img.shields.io/github/contributors/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/graphs/contributors)
[![Release](https://img.shields.io/github/v/release/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/releases)

</p>

<div align="center">

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,postgresql,githubactions,github" height="48" alt="Sincronização de Dados">
  </a>
</p>

<p>

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)](https://www.databricks.com/)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)

</p>

</div>

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md), fluxo de sincronização e árvore do repositório.
- [RUNNING.md](./RUNNING.md), como rodar o script localmente.
- **Deployment**, este repositório **não segue** o fluxo padrão de deploy via `Dockerfile` + Docker Hub + ArgoCD/GKE descrito no [Deployment global](https://github.com/Solierrr/.github/blob/main/DEPLOYMENT.md) da organização — não existe `Dockerfile` aqui. A "publicação" é o próprio agendamento do workflow [`sync.yml`](./.github/workflows/sync.yml), que roda o script direto no runner do GitHub Actions a cada 4 horas (`cron: "0 */4 * * *"`) ou sob demanda via `workflow_dispatch`, sem etapa de build de imagem ou sincronização de cluster.

## Contribuindo

- [.github/CONTRIBUTING.md](./.github/CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [.github/CODEOWNERS](./.github/CODEOWNERS), donos responsáveis por aprovar mudanças em cada caminho do repositório.
- `CODE_OF_CONDUCT.md` e `SECURITY.md`, {a confirmar, não encontrados neste repositório no momento da escrita}.
