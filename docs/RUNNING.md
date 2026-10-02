# Executando localmente

O serviço disponibiliza uma API FastAPI para iniciar manualmente a sincronização completa dos bancos `core` e `auth` para a camada Bronze do Databricks. O servidor não dispara sincronizações automaticamente.

## Requisitos

- Python 3.12 ou superior
- GNU Make
- Acesso de rede aos Postgres e ao SQL Warehouse Databricks
- Credenciais em `Inter/.env`, um nível acima deste repositório

Copie as variáveis de [`.env.example`](./.env.example) para o `.env` local e preencha os acessos aos dois bancos, Databricks e um `SYNC_API_TOKEN` forte. Não coloque credenciais reais em arquivos versionados.

## Iniciar

Na pasta `databricks-sync`, instale as dependências e inicie a API:

```sh
make setup
make run
```

O servidor escuta em `0.0.0.0:8000` para permitir chamadas pela rede local. A documentação interativa OpenAPI fica em `http://localhost:8000/docs`.

## Executar uma sincronização

Na interface `/docs`, abra `POST /sync`, selecione **Authorize**, informe o Bearer token definido por `SYNC_API_TOKEN` e execute a chamada. A requisição só termina quando a sincronização acabar. Se outra execução estiver em andamento, a API responde `409`.

Uma resposta bem-sucedida resume as tabelas e linhas processadas. Se alguma tabela falhar, as demais continuam e a API retorna `500` com as tabelas que falharam. Como o sincronizador recria cada tabela com `CREATE OR REPLACE TABLE`, uma falha durante a carga pode deixar aquela tabela parcialmente preenchida; confira os detalhes da resposta antes de repetir.

O workflow [`sync.yml`](./.github/workflows/sync.yml) também pode ser iniciado manualmente em GitHub Actions como alternativa. Ele não tem execução agendada.
