# Exportação Gold → AnalyticsDB

`POST /sync/gold` lê somente as 19 views materializadas listadas em
`gold_export_manifest.json`, no catálogo `workspace.gold_core` do
`databricks-stocker`. Ele não calcula KPIs e não lê entidades do AnalyticsDB
para produzir Gold. As 11 views anteriores e as 8 novas views de fornecedor
são copiadas para tabelas homônimas em `analyticsdb.analytics_gold`.

## Ordem de execução

O job versionado em `databricks-stocker/exports/medallion_export_job.json`
encadeia a pipeline Silver, a pipeline Gold e, apenas se ambas terminarem com
sucesso, o notebook que chama o endpoint. O arquivo usa os IDs e o caminho de
workspace registrados nos artefatos de recuperação do projeto; confirme-os ao
instalar o job. O endpoint continua acionável manualmente por quem possui o
Bearer token, portanto a ordem operacional depende do job e da proteção do
token. Nenhum job foi instalado ou executado por esta alteração.

## Destino e contrato

Antes da primeira exportação, aplique `database-console/db/analytics/schema.sql`
em `analyticsdb` por meio do fluxo de criação de schema desse repositório.
O exportador confere todas as views e tipos no Databricks antes de escrever no
PostgreSQL. Cria cada tabela de destino a partir das colunas publicadas pela
respectiva view; em cargas posteriores, exige as mesmas colunas, ordem e tipos.
Uma divergência interrompe a carga para que uma migração explícita seja feita.
Tipos Gold não reconhecidos também interrompem a exportação.

Os dados são lidos em lotes e preparados em tabelas temporárias PostgreSQL.
As 19 substituições ocorrem numa única transação, com trava transacional para
impedir duas cargas simultâneas. Uma falha cancela todas as substituições e
preserva o estado anterior do AnalyticsDB. Reexecutar a exportação substitui
os dados da mesma forma, sem duplicar linhas. A leitura de views distintas no
Databricks não oferece uma transação única de snapshot: não atualize a Gold
durante a exportação.

## Isolamento

As views de fornecedor criadas em `databricks-stocker` recebem row filter do
Unity Catalog antes de serem disponibilizadas. O SQL de provisionamento fica
em `databricks-stocker/security/supplier_access.sql`; a tabela de acesso começa
vazia e precisa receber vínculos validados para a identidade do pipeline, a
identidade exportadora e os fornecedores.

No AnalyticsDB, cada tabela exportada recebe PostgreSQL Row Level Security
forçado. `analytics_gold.principal_access` mapeia o login real (`session_user`)
a ADMIN, EXPORTER, SUPPLIER, REQUESTER ou PROFESSIONAL. Identidades sem vínculo
ativo e escopos com mais de uma entidade distinta não leem dados. O usuário
que criou a função de autorização pode exportar; se o exportador for outro
login, registre-o explicitamente como EXPORTER. A aplicação deve usar logins
distintos por principal: um login compartilhado torna o isolamento por usuário
impossível. Não conceda a leitores acesso de escrita, propriedade das tabelas,
`BYPASSRLS` ou acesso direto aos arquivos do Databricks.

`ANALYTICS_READER_ROLE` é opcional. Se definido, o exportador concede à role
somente USAGE no schema, EXECUTE na função e SELECT nas tabelas KPI. A política
de linha ainda é aplicada. A role deve existir previamente; o exportador não
cria nem vincula logins a ela.

## Fontes e limitações observadas estaticamente

- A Gold existente contém indicadores administrativos, de fornecedor,
  demandante e profissional. O manifesto espelha essas views, sem criar
  métricas adicionais no serviço de sincronização.
- A Silver deste checkout não contém pedidos/itens/pagamentos. Por isso as
  métricas condicionais de pedido do documento do fornecedor ainda não têm
  fonte Gold e não entram no manifesto.
- A Silver consulta `offer.commercial_status`, mas o `db/core/schema.sql`
  versionado em `database-console` não contém essa coluna. É preciso alinhar
  o schema operacional e a Silver antes de atualizar a pipeline Gold.
- `proposals` na Silver usa `fk_supplier`, também ausente no `proposal` do
  schema CoreDB versionado. Os novos KPIs de fornecedor derivam o fornecedor
  por `proposal_item → offer`, conforme a especificação.
- O preço negociado do item é multiplicado pela quantidade sem reaplicar
  desconto. Valor nulo segue nulo; o aceite temporal usa a criação da
  proposta como aproximação.

Nenhum endpoint, pipeline ou banco foi acionado durante esta alteração.
