# TP1.1 - Horário Escolar

Este projeto consiste em desenvolver um gerador de horário escolar em Marimo, respeitando as restrições do enunciado e validando o resultado com dados reais em CSV.

## Checklist para terminar o trabalho

### Estrutura e execução em Marimo
- [x] Criar/editar o notebook principal em Marimo para o problema de horário escolar
- [ ] Confirmar a execução completa em Marimo no ambiente de entrega
- [x] Ler os CSVs a partir da pasta indicada em `PASTA_DADOS` (`dados/` ou `dados_v2/`)
- [x] Organizar o código em células Marimo com lógica separada por responsabilidade
- [x] Incluir uma forma simples de executar o notebook localmente

### Leitura e modelação dos dados
- [x] Ler `turmas.csv`, `disciplinas.csv`, `salas.csv` e `disponibilidade_excecoes.csv`
- [x] Validar que os dados estão no formato correto
- [x] Representar turmas, disciplinas, professores, salas e indisponibilidades em listas/dicionários
- [x] Tratar disciplinas com `duplo_periodo=sim` como sessões consecutivas de dois períodos
- [x] Restringir disciplinas com `sala_especial` à sala especial indicada

### Geração do horário
- [x] Implementar a geração de um horário inicial válido
- [x] Garantir que uma turma não tem duas aulas ao mesmo tempo
- [x] Garantir que cada disciplina cumpre a carga semanal correta
- [x] Garantir que não há mais do que uma aula da mesma disciplina por dia, por turma
- [x] Garantir que disciplinas de duplo período só aparecem em blocos consecutivos
- [x] Garantir que um professor não dá duas aulas em simultâneo
- [x] Garantir que um professor só ministra aulas quando está disponível
- [x] Garantir que cada aula usa uma sala válida
- [x] Garantir que o número de aulas por tipo de sala não excede a capacidade disponível

### Optimização
- [x] Definir uma função objetivo para minimizar buracos no horário dos professores
- [x] Limitar o tempo de resolução; aceitar solução viável mesmo que não seja ótima
- [x] Documentar no notebook a modelação e a função objetivo

### Construção incremental
- [x] Implementar a geração de `H0` com os dados iniciais (`dados/`)
- [x] Implementar a geração de `H1` com os dados de `dados_v2/`
- [x] Implementar uma abordagem incremental que usa `H0` como pistas e objetivo de estabilidade
- [x] Construir `H1` com as mesmas restrições R1–R7
- [x] Maximizar o número de sessões que mantêm turma, disciplina, dia e início de `H0`
- [x] Medir e mostrar tempos e sessões alteradas para solução do zero e incremental
- [ ] Executar e registar evidência de que o incremental é mais rápido ou mais estável

### Validação e testes
- [x] Criar validação automática e independente das restrições R1 a R8
- [ ] Testar automaticamente pelo menos um caso de cada restrição (atualmente há testes de R1, R2, R5 e R6)
- [ ] Verificar o comportamento com dados diferentes do conjunto fornecido
- [x] Ler os dados de entrada dos CSVs em vez de os codificar no modelo

### Apresentação e entrega
- [x] Produzir a visualização do horário no notebook Marimo
- [x] Mostrar o horário por turma e por professor em tabelas semanais
- [x] Documentar no notebook as decisões de modelação, restrições e objetivo
- [ ] Verificar que o notebook pode ser aberto e executado em Marimo sem erros
- [ ] Preparar a versão final para entrega

## Como correr em Marimo

A partir da pasta do projeto:

```bash
cd TP1.1
marimo run horario_escolar.py
```

O notebook principal chama-se `horario_escolar.py`.

## Observações

- O código deve ler os dados dos ficheiros CSV e não usar dicionários ou listas fixas no próprio notebook.
- A pasta é selecionada pela constante `PASTA_DADOS`: usar `"dados"` para H0 e `"dados_v2"` para H1; ainda não há seletor interativo.
- O notebook apresenta uma tabela de comparação H1 do zero versus incremental, com estado, tempo, alterações, buracos e erros.
- O fluxo está implementado no notebook, mas as métricas comparativas ainda precisam de ser executadas e registadas como evidência.

## Estado atual

O notebook inclui leitura e validação dos CSVs, modelo CP-SAT com R1–R7, objetivo O1,
geração de H0 e H1, atribuição de salas, validação independente R1–R8, apresentação dos
horários e comparação entre H1 do zero e incremental. Ainda faltam executar o fluxo completo
no ambiente final, completar testes deliberados para R3, R4, R7 e R8, testar um conjunto de
dados adicional, registar evidência dos resultados incrementais e preparar a entrega final.
