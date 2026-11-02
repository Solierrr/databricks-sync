<p align="center">
  <img src="./assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

<p align="center">
  <img src="./assets/readme/stacks/python.png" width="100" hspace="8" alt="Python" title="Python">
  <img src="./assets/readme/stacks/fastapi.png" width="100" hspace="8" alt="FastAPI" title="FastAPI">
  <img src="./assets/readme/stacks/postgresql.png" width="100" hspace="8" alt="PostgreSQL" title="PostgreSQL">
</p>

# Transporte dos dados analíticos

[![License](https://img.shields.io/github/license/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/commits)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/databricks-sync)](https://github.com/Solierrr/databricks-sync/releases)

Este serviço copia dados de negócio para análise e devolve indicadores já calculados ao banco usado para consulta analítica. Ele atende à operação que prepara as cargas e acompanha seu resultado. A cópia não acompanha cada alteração em tempo real. Quem inicia uma execução recebe um identificador para acompanhar ou espera o resumo, com o resultado por tabela e as falhas encontradas.

FastAPI oferece os comandos de carga e consulta. PostgreSQL é a origem dos dados de negócio e o destino dos indicadores, enquanto Databricks recebe a cópia inicial e fornece os resultados calculados pelo pipeline analítico. As chamadas exigem um token de serviço. O histórico de execuções fica na memória da instância e se perde quando o processo reinicia.

## Aprofunde-se no Projeto!

- [OVERVIEW.md](./docs/OVERVIEW.md), finalidade e regras das cargas.
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md), componentes, concorrência e integrações.
- [RUNNING.md](./docs/RUNNING.md), configuração e testes locais.
- [API.md](./docs/API.md), autenticação, contrato e exemplos.
- [DEPLOY.md](./docs/DEPLOY.md), execução manual e ambiente declarado.
- [STATUS.md](./docs/STATUS.md), diferenças e limites verificados.
- [Fluxos](./flows/), carga Bronze e exportação Gold.
- [Dados](./database/), contratos de escrita no Databricks e no PostgreSQL.
- [PENDENCIAS.md](./PENDENCIAS.md), confirmações do responsável.

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/.github/CONTRIBUTING.md), convenções de contribuição.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), reporte de vulnerabilidade.
