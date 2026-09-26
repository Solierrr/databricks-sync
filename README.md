# Finalidade do repositório

O `databricks-sync` replica os bancos Postgres operacionais `core` e `auth` para os schemas Bronze de um Lakehouse Databricks. A sincronização completa é iniciada manualmente por uma API FastAPI local (`POST /sync`) ou pelo `workflow_dispatch` do GitHub Actions; não existe mais execução agendada. A API exige Bearer token e retorna um resumo com tabelas processadas e falhas.

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
- [RUNNING.md](./RUNNING.md), como iniciar a API localmente e chamar o endpoint manual.
- **Deployment**, este repositório não publica um serviço hospedado: a API é iniciada localmente pelo Makefile. O workflow [`sync.yml`](./.github/workflows/sync.yml) mantém apenas um acionamento manual alternativo e não usa cron.

## Contribuindo

- [.github/CONTRIBUTING.md](./.github/CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [.github/CODEOWNERS](./.github/CODEOWNERS), donos responsáveis por aprovar mudanças em cada caminho do repositório.
- `CODE_OF_CONDUCT.md` e `SECURITY.md`, {a confirmar, não encontrados neste repositório no momento da escrita}.
