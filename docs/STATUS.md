<p align="center">
  <img src="../assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

# Situação

Levantamento da main `c3c1c251`, em 2026-10-30.

- Bronze copia somente CoreDB. O risco específico de copiar authdb inteiro do checklist não representa esta implementação (2026-10-30).
- Há API, consulta de jobs, health, readiness, OpenAPI e exportação de 19 indicadores Gold (2026-10-30).
- O manifesto exige `workspace.gold_core` e nomes `kpi_fornecedor_*`, enquanto o produtor usa o schema `gold`, nomes `kpi_supplier_*` e job no catálogo `analytics`, contrato que é a referência. A adaptação do manifesto está pendente (2026-10-30).
- O token fixo Bearer ainda difere do padrão de `X-Service-Key` por chamador, e a adoção desse padrão está pendente (2026-10-30).
- A Bronze substitui as tabelas individualmente, sem snapshot único nem rollback global, e seleciona todas as tabelas públicas, sem lista revisada nem filtro de campos. Depois de uma falha, a carga é repetida por inteiro (2026-10-30).
- Jobs e trava da API são locais ao processo. Reinício perde histórico e execução em thread daemon pode ser interrompida (2026-10-30).
- Gold usa uma transação PostgreSQL e staging, mas não uma transação única entre as fontes Databricks. Não atualizar as fontes durante a exportação (2026-10-30).
- A RLS forçada depende da função e dos principais provisionados no banco de analytics, e a prontidão não verifica o contrato completo de autorização (2026-10-30).
