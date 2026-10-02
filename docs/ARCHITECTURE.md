# Arquitetura

`api.py` oferece a API local FastAPI e o documento OpenAPI. `POST /sync` valida o Bearer token, impede execuções concorrentes no processo e aguarda a sincronização terminar. O serviço não inicia uma carga sozinho; não há cron.

`synchronizer.py` mantém a integração batch com Postgres e Databricks. Ele consulta as tabelas públicas dos bancos `core` e `auth`, cria os schemas Bronze quando necessário, recria cada tabela de destino e insere os registros em lotes de 500 linhas. `SOURCES` é montado a partir das variáveis de ambiente e direciona `core` para `bronze_core` e `auth` para `bronze_auth` por padrão.

Falhas por tabela são acumuladas e a carga continua pelas outras tabelas e pela outra origem. Ao final, qualquer falha faz `POST /sync` responder `500` com totais e detalhes. Uma falha durante a substituição pode deixar a tabela afetada parcial, pois a operação atual usa `CREATE OR REPLACE TABLE` antes de inserir os dados.

## Configuração e execução

- `Inter/.env` contém os segredos locais e fica fora do repositório. `SYNC_API_TOKEN` protege o endpoint; as demais variáveis configuram Postgres, catálogo, schemas e SQL Warehouse Databricks.
- O Makefile cria `.venv`, instala `requirements.txt` e inicia Uvicorn em `0.0.0.0:8000` para chamadas na rede local.
- O workflow de GitHub Actions mantém somente o gatilho manual `workflow_dispatch`. Ele usa GitHub Secrets e pode servir como alternativa manual.
- A API deve ser executada em uma máquina confiável da rede; qualquer cliente com o Bearer token pode iniciar uma carga que substitui dados no Bronze e consome recursos do Databricks.

## Fluxo

```text
cliente com Bearer token
        |
        | POST /sync
        v
   FastAPI / OpenAPI
        |
        v
   synchronizer.py
      /       \
 Postgres    Databricks SQL Warehouse
 core/auth   bronze_core/bronze_auth
```
