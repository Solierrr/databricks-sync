<p align="center">
  <img src="../assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

# API de sincronização

O contrato está em [openapi.yaml](https://github.com/Solierrr/databricks-sync/blob/main/openapi.yaml). `/docs` e `/openapi.json` são expostos enquanto `DOCS_ENABLED` não for falso.

## Autenticação

As chamadas usam Bearer com o token fixo `SYNC_API_TOKEN`, e o esquema chamado `bearerAuth` no contrato não representa o JWT de uma pessoa. O health e o readiness são públicos, e a troca do token fixo pela `X-Service-Key` de cada chamador, padrão definido para chamadas entre serviços, está pendente.

## Operações

| Operação | Resultado |
|---|---|
| `POST /sync` | 202 com id e endereço de consulta |
| `POST /sync?wait=true` | Aguarda Bronze, 200 com resumo ou 500 com `result` |
| `GET /sync/{job_id}` | Estado, progresso, resultado ou erro do job |
| `POST /sync/gold` | Aguarda exportação Gold e devolve resumo |
| `GET /health` | Processo e versão |
| `GET /ready` | 200 UP ou 503 DOWN |

## Exemplo

O comando inicia uma carga que substitui tabelas no destino. Usar somente no ambiente autorizado.

```bash
curl --request POST http://localhost:8000/sync   --header "Authorization: Bearer $SYNC_API_TOKEN"
```

Consultar `status_url` devolvida pela API com o mesmo cabeçalho até `completed` ou `failed`. Não tratar 202 como carga concluída. O histórico pode desaparecer no reinício ou por limite de 20 jobs.

## Erros

Um token inválido responde 401, um job ocupado responde 409, uma configuração ausente responde 503 e uma execução com erro responde 500, incluindo `result` quando há resumo, enquanto um job inexistente responde 404. O formato é `application/problem+json`, conforme os [erros HTTP](https://github.com/Solierrr/docs-warehouse/blob/main/docs/standards/ERRORS.md), e o `GET` de um job que falhou continua respondendo com o seu estado, sem se transformar em 500.

As fontes são [rotas](https://github.com/Solierrr/databricks-sync/blob/main/app/routes/sync.py) e [autenticação](https://github.com/Solierrr/databricks-sync/blob/main/app/auth.py).
