<p align="center">
  <img src="../assets/readme/banners/databricks.png" alt="Databricks" width="100%">
</p>

# Visão de produto

O serviço transporta dados para a análise e publica indicadores calculados por outro componente. Ele atende à operação de dados, sem tela própria para o usuário final.

## Capacidades

- Copiar todas as tabelas públicas de negócio para uma camada de entrada analítica.
- Iniciar a cópia em segundo plano e consultar o progresso.
- Esperar uma cópia e receber o resultado final.
- Publicar um conjunto revisado de indicadores para consulta analítica.
- Informar tabelas e linhas copiadas e identificar falhas por tabela.

## Regras

A carga atual de entrada usa somente o banco de negócio. O banco de autenticação deixou de participar, ao contrário do levantamento anterior.

A cópia inicial substitui cada tabela de destino e pode terminar com algumas tabelas copiadas e outras com erro. A publicação dos indicadores é diferente. Ela prepara o conjunto e troca os dados em uma única transação no banco de destino, preservando o estado anterior se essa transação falhar.

O serviço não calcula indicadores e exige que o pipeline anterior tenha terminado com o resultado no contrato revisado. O contrato de referência é o do produtor, e o exportador ainda usa nomes diferentes.

Uma execução ocupa a instância até terminar, e o histórico é temporário, por isso não comprova a atualidade de todos os indicadores depois de um reinício. Depois de uma falha, a carga é repetida por inteiro.
