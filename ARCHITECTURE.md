# Arquitetura do Repositório

A arquitetura deste repositório é a de um script batch único (`synchronizer.py`), sem framework de aplicação, sem camada de API e sem servidor persistente. Toda a lógica vive em um único arquivo Python, estruturado em funções pequenas e sequenciais: leitura de metadados do Postgres, tradução de tipos, recriação da tabela de destino no Databricks e inserção dos dados em lotes. O fluxo é orientado por duas fontes de configuração: variáveis de ambiente (carregadas de um `.env` na raiz do monorepo pai via `python-dotenv`) e uma lista estática `SOURCES` no topo do arquivo, que define quais bancos Postgres são sincronizados e para qual schema da camada bronze cada um vai.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,postgresql,databricks" height="48" alt="Arquitetura — Sincronização Batch">
  </a>
</p>

- **Script batch único**, não há `main.py`/aplicação de longa duração; `synchronizer.py` conecta, sincroniza e encerra em uma única execução, disparada pelo workflow agendado do GitHub Actions.
- **Dois domínios Postgres, dois schemas Databricks**, a lista `SOURCES` mapeia cada prefixo de variável de ambiente (`DB_CORE`, `DB_AUTH`) para seu schema de destino na camada bronze (`bronze_core`, `bronze_auth`), isolando os dados de cada domínio de origem.
- **Full load com `CREATE OR REPLACE TABLE`**, a cada execução a tabela de destino no Databricks é recriada do zero a partir do schema atual do Postgres (via `information_schema.columns`) e todas as linhas são reinseridas — não há sincronização incremental, CDC ou merge/upsert.
- **Tradução de tipos Postgres → Databricks SQL**, o dicionário `PG_TO_SQL_TYPE` mapeia os tipos do `information_schema` do Postgres (incluindo `numeric`/`decimal` com precisão e escala) para os tipos equivalentes do Databricks SQL, com fallback para `STRING` em tipos não mapeados (`ARRAY`, `USER-DEFINED`, `json`/`jsonb`, `uuid`, `bytea`).
- **Inserção em lote via `executemany`**, as linhas lidas do Postgres passam por `_to_dbx_value` (serializando UUID, dict/list como JSON e bytes como hex) antes de serem inseridas no Databricks em lotes fixos de 500 linhas.
- **Execução agendada, não containerizada**, não há `Dockerfile` neste repositório; a execução acontece diretamente em um runner `ubuntu-latest` do GitHub Actions, que instala as dependências do `requirements.txt` e roda `python synchronizer.py` com as credenciais injetadas via GitHub Secrets.

```Tree do Repositório
├── .github/
│   ├── CODEOWNERS
│   ├── CONTRIBUTING.md
│   ├── pull_request_template.md
│   └── workflows/
│       └── sync.yml
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── ARCHITECTURE.md
├── RUNNING.md
├── requirements.txt
└── synchronizer.py
```
