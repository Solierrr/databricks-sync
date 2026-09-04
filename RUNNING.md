# Rodando o Projeto Localmente

Este repositório é Python, mas não é uma API: não há `uvicorn`, `FastAPI` nem processo escutando porta. É um script batch único que roda, sincroniza os dados e encerra. O processo local é: clonar, criar um ambiente virtual, instalar as dependências do `requirements.txt` e executar `python synchronizer.py` diretamente. Antes de iniciar, verifique a seção de impedimentos abaixo — o script depende inteiramente de credenciais externas (dois bancos Postgres e um workspace Databricks) mesmo em ambiente local, e falha imediatamente com `KeyError` se alguma variável obrigatória não estiver definida.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,postgresql,databricks,github" height="48" alt="Rodando o Projeto — Python">
  </a>
</p>

## Possíveis Impedimentos

- **Python 3.12 instalado localmente**, a mesma versão usada no workflow do GitHub Actions (`.github/workflows/sync.yml`, `python-version: "3.12"`) — não há `Dockerfile` neste repositório, então rodar localmente depende diretamente da versão instalada na máquina.
- **Acesso aos dois bancos Postgres de origem**, o script conecta via `psycopg2` com `sslmode="require"` em `DB_CORE_*` e `DB_AUTH_*`; sem rede/VPN até esses hosts e sem um usuário Postgres válido com acesso ao schema `public`, a conexão falha antes de qualquer sincronização.
- **Acesso ao workspace Databricks**, o script conecta via SQL Warehouse (`databricks-sql-connector`) usando `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH` e `DATABRICKS_TOKEN`; o token precisa ter permissão de `CREATE SCHEMA`/`CREATE OR REPLACE TABLE` no catálogo definido em `DATABRICKS_CATALOG`.
- **Arquivo `.env` fora da raiz do repositório**, o script carrega variáveis com `load_dotenv` a partir de `Path(__file__).resolve().parent.parent / ".env"` — ou seja, o `.env` precisa estar **um nível acima** da pasta `databricks-sync` (no diretório pai), não dentro dela. {a confirmar: motivo dessa convenção — provavelmente um `.env` compartilhado entre repositórios irmãos no monorepo/workspace local}.
- **Secrets locais equivalentes aos do GitHub Actions**, em produção as credenciais (`DB_CORE_*`, `DB_AUTH_*`, `DATABRICKS_*`) vêm de GitHub Secrets injetados no workflow `sync.yml`; localmente elas precisam ser criadas manualmente no `.env` descrito acima.

## Instalação do Projeto

### Iniciando o repositório com o Github

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=github,vscode" height="48" alt="Frameworks">
  </a>
</p>

Clone o repositório e abra no VS Code.

```Comandos para clonar o repositório
git clone https://github.com/Solierrr/databricks-sync.git
cd ./databricks-sync
code . -r
```

### Instalando dependências necessárias para rodar o projeto localmente

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python" height="48" alt="Frameworks">
  </a>
</p>

Crie um ambiente virtual antes de instalar as dependências, para não poluir o Python global da máquina. Antes de rodar, copie o `.env.example` para um `.env` **no diretório pai** do repositório (veja o impedimento acima) e preencha as credenciais dos dois bancos Postgres (`DB_CORE_*`, `DB_AUTH_*`) e do Databricks (`DATABRICKS_*`).

```Comandos para instalação de dependências
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python synchronizer.py
```

Ao rodar com sucesso, o script imprime no console o progresso da sincronização tabela a tabela (`ok  <tabela>: <n> linhas`) para cada uma das fontes definidas em `SOURCES`, encerrando com `Sincronizacao concluida.`.
