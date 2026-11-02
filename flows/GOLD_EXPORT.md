<p align="center">
  <img src="../assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

# Exportação Gold

O produtor solicita publicação após concluir os indicadores, desde que nomes e contratos estejam alinhados.

```mermaid
sequenceDiagram
  participant P as Produtor analítico
  participant A as API de carga
  participant D as Databricks
  participant G as AnalyticsDB
  P->>A: HTTP POST com Bearer de serviço
  A->>D: SQL descrever as 19 fontes
  alt Contrato inválido
    A-->>P: Erro sem publicar
  else Contrato válido
    A->>G: Abrir transação e trava
    A->>D: Ler fontes em lotes
    A->>G: Staging, RLS e substituição
    alt Falha na publicação
      A->>G: Rollback do conjunto
      A-->>P: 500 com resultado
    else Sucesso
      A->>G: Commit
      A-->>P: 200 com resumo
    end
  end
```

## Falhas e limites

O exportador ainda não segue o contrato do produtor, que é a referência, por isso não basta executar o job. A transação preserva o destino PostgreSQL quando há falha, mas não congela a Gold de origem durante a exportação.

Fonte em [implementação](https://github.com/Solierrr/databricks-sync/blob/main/gold_synchronizer.py). O contexto está em [cópia analítica](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/ANALYTICS_SYNC.md).
