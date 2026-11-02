<p align="center">
  <img src="../assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

# Execução local

São necessários o Python 3.14, conforme o workflow de sincronização, além do pip, do make e de um shell, e o guia comum está em [Python](https://github.com/Solierrr/docs-warehouse/blob/main/readme/running/PYTHON.md). Esta main não tem Dockerfile.

## Preparar

Executar no checkout do serviço.

```bash
make doctor
make vault
make install
make dev
```

O `make vault` lê as pastas `/database` e `/databricks`, e a API carrega o `.env` sem substituir as variáveis já presentes no processo, iniciando na porta 8000. As credenciais devem ser obtidas pelo processo autorizado, sem que nenhum valor apareça em exemplos.

| Variável | Papel |
|---|---|
| `SYNC_API_TOKEN` | Token Bearer dos endpoints de sincronização |
| `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN`, `DATABRICKS_CATALOG` | Workspace e conexão SQL |
| `DB_CORE_HOST`, `DB_CORE_PORT`, `DB_CORE_USER`, `DB_CORE_PASS`, `DB_CORE_NAME` | Origem Bronze |
| `DATABRICKS_SCHEMA_CORE`, `SYNC_BATCH_SIZE` | Schema de destino e lote Bronze |
| `DB_ANALYTICS_HOST`, `DB_ANALYTICS_PORT`, `DB_ANALYTICS_USER`, `DB_ANALYTICS_PASS`, `DB_ANALYTICS_NAME` | Destino Gold |
| `DATABRICKS_SCHEMA_GOLD`, `GOLD_BATCH_SIZE` | Fonte e lote Gold |
| `ANALYTICS_READER_ROLE` | Role leitora já existente, opcional |
| `DOCS_ENABLED`, `CORS_ALLOWED_ORIGINS` | Documentação e origens do navegador |

O lote Bronze padrão é 500 e deve ser positivo, a Gold admite lotes de 1 a 10000 e o catálogo e o schema Gold precisam coincidir com o manifesto, e não apenas apontar para um objeto existente.

## Verificar

```bash
make test
make lint
make build
make openapi
```

Os alvos executam o pytest, o Ruff, o compileall e a exportação do contrato, mas o `make format` não tem comando configurado. Quando habilitado, o Swagger local fica em `http://localhost:8000/docs`.

O `python synchronizer.py` inicia uma carga Bronze real, e o `python gold_synchronizer.py` inicia uma exportação Gold real com a configuração do ambiente, por isso esses comandos alteram os destinos e não servem como verificações sem efeito.

O diagnóstico deve separar configuração ausente, token inválido, job ocupado e resultado parcial. Prontidão não substitui revisão do manifesto, da função de autorização e dos privilégios. Fontes em [Makefile](https://github.com/Solierrr/databricks-sync/blob/main/Makefile), [configuração](https://github.com/Solierrr/databricks-sync/blob/main/app/config.py) e [CLI](https://github.com/Solierrr/databricks-sync/blob/main/app/cli.py).
