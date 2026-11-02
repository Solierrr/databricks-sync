<p align="center">
  <img src="../assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

# Carga Bronze

A operação inicia cópia das tabelas públicas de negócio e acompanha o resultado.

```mermaid
flowchart TD
  A[Conferir Bearer e configuração] --> B{Job ocupado?}
  B -->|Sim| C[409]
  B -->|Não| D[Descobrir tabelas públicas]
  D --> E[Substituir tabela de destino]
  E --> F[Inserir lotes]
  F -->|Sucesso| G[Somar progresso]
  F -->|Falha| H[Registrar erro e continuar]
  G --> I{Há outra tabela?}
  H --> I
  I -->|Sim| E
  I -->|Não| J[Resumo concluído ou falho]
```

## Falhas e limites

Uma falha numa tabela não desfaz os destinos já gravados, e no modo assíncrono a resposta 202 apenas aceita o job, enquanto um reinício pode interromper a thread e perder o histórico.

Fonte em [implementação](https://github.com/Solierrr/databricks-sync/blob/main/app/services/sync_service.py). O contexto está em [cópia analítica](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/ANALYTICS_SYNC.md).
