# Finalidade do repositório

O `databricks-sync` envia as views do schema `export` do CoreDB para `<catálogo>.bronze_core` e as views liberadas do AuthDB para `<catálogo>.bronze_auth` por `POST /sync` (catálogo `analytics`, ou `analyticsqa` em QA, definido em `DATABRICKS_CATALOG`) e exporta os KPIs já materializados em `workspace.gold_core` para o AnalyticsDB por `POST /sync/gold`. As pipelines Bronze → Silver → Gold pertencem ao `databricks-stocker`, cujo job chama a exportação após a conclusão bem-sucedida da Gold. Ambos os endpoints exigem o mesmo Bearer token.

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

- [ARCHITECTURE.md](./docs/ARCHITECTURE.md), fluxo de sincronização.
- [RUNNING.md](./docs/RUNNING.md), configuração da API local.
- [GOLD.md](./docs/GOLD.md), views exportadas, contrato do AnalyticsDB e isolamento por principal.
- **Deployment**, este repositório não publica um serviço hospedado: a API é iniciada localmente pelo Makefile. O workflow [`sync.yml`](./.github/workflows/sync.yml) mantém acionamento manual para Bronze; a exportação Gold é acionada pelo job do `databricks-stocker`.

## Contribuindo

- [.github/CONTRIBUTING.md](./.github/CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [.github/CODEOWNERS](./.github/CODEOWNERS), donos responsáveis por aprovar mudanças em cada caminho do repositório.
- `CODE_OF_CONDUCT.md` e `SECURITY.md`, {a confirmar, não encontrados neste repositório no momento da escrita}.
