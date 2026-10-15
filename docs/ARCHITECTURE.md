# Arquitetura

O serviço é uma API FastAPI em camadas que copia os bancos Postgres `core` e `auth` para os schemas Bronze de um Lakehouse Databricks. Ele não inicia carga sozinho: não há cron, a sincronização é sempre disparada por uma chamada autenticada (ou pelo `workflow_dispatch` do GitHub Actions).

## Camadas

```text
app/
  main.py            cria o app (create_app), registra as rotas e o gerenciador de tarefas
  config.py          lê e valida as variáveis de ambiente (load_config)
  auth.py            token de serviço (Authorization: Bearer, comparado a SYNC_API_TOKEN)
  models.py          modelos de resposta (resumo, tarefa, andamento)
  errors.py          erros de configuração, de execução e de tarefa em andamento
  routes/            health.py (GET /health) e sync.py (POST /sync, GET /sync/{id})
  services/
    sync_service.py  sincronização: sync_table, sync_source, synchronize
    jobs.py          tarefas em segundo plano, uma por vez, com histórico limitado
  infra/
    postgres.py      PostgresSource: tabelas, colunas e leitura em lotes (cursor no servidor)
    databricks.py    conexão com o SQL Warehouse
    typemap.py       tipos do Postgres para o Databricks e conversão de valores
api.py               atalho de compatibilidade: reexporta `app` (o start do Render usa `api:app`)
synchronizer.py      atalho de compatibilidade: `synchronize()` e `main()` (o `sync.yml` roda `python synchronizer.py`)
tests/               pytest com bancos simulados (sem rede)
```

## Fluxo

```text
cliente com Bearer token
        |
        | POST /sync   (202 com o id da tarefa; ?wait=true espera o fim)
        v
   routes/sync.py --> services/jobs.py (uma tarefa por vez, 409 se já houver)
                              |
                              v
                    services/sync_service.py
                      /                  \
         infra/postgres.py           infra/databricks.py
         core e auth (lotes)         bronze_core e bronze_auth
        ^
        | GET /sync/{id}   andamento por tabela e resumo final
```

`synchronize` consulta as tabelas públicas dos bancos, cria os schemas Bronze quando necessário, recria cada tabela de destino e insere os registros em lotes (`SYNC_BATCH_SIZE`, padrão 500) lidos com cursor no servidor, sem carregar a tabela inteira na memória. Falhas por tabela são acumuladas e a carga continua pelas outras tabelas e pela outra origem. Uma falha durante a substituição pode deixar a tabela afetada parcial, porque a operação usa `CREATE OR REPLACE TABLE` antes de inserir os dados.

## Tarefas em segundo plano

`POST /sync` valida a configuração (503 se faltar variável), registra a tarefa e responde `202` com `status_url`. Só uma tarefa roda por vez; uma segunda chamada recebe `409`. O histórico guarda as últimas 20 tarefas em memória (somem quando o processo reinicia). Em instância gratuita do Render, o serviço dorme sem tráfego de entrada: acompanhe a tarefa chamando `GET /sync/{id}` até terminar. `?wait=true` mantém o comportamento antigo (a requisição só termina no fim, com `200` ou `500` e o resumo).

## Configuração e execução

- `Inter/.env` contém os segredos locais e fica fora do repositório. `SYNC_API_TOKEN` protege a API; as demais variáveis configuram Postgres, catálogo, schemas e SQL Warehouse; `SYNC_BATCH_SIZE` ajusta o lote.
- O Makefile cria `.venv`, instala `requirements.txt` e `requirements-dev.txt`, e inicia o Uvicorn (`app.main:app`) em `0.0.0.0:8000`. No Render o start continua `uvicorn api:app`.
- O workflow `sync.yml` mantém somente o gatilho manual e usa GitHub Secrets.
- Qualquer cliente com o Bearer token pode iniciar uma carga que substitui dados no Bronze e consome recursos do Databricks.
