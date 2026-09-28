# TP1.1 - Horário Escolar

Este projeto consiste em desenvolver um gerador de horário escolar em Marimo, respeitando as restrições do enunciado e validando o resultado com dados reais em CSV.

## Checklist para terminar o trabalho

### Estrutura e execução em Marimo
- [x] Criar/editar o notebook principal em Marimo para o problema de horário escolar
- [ ] Garantir que o projeto corre corretamente em Marimo e não apenas como script Python normal
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
- [ ] Definir uma função objetivo para minimizar buracos no horário dos professores
- [ ] Ajustar a solução para melhorar a qualidade do horário, mesmo que não seja ótima
- [ ] Documentar as decisões de modelação e otimização no notebook

### Construção incremental
- [x] Implementar a geração de `H0` com os dados iniciais (`dados/`)
- [ ] Gerar um novo horário válido `H1` com os dados alterados em `dados_v2/`
- [ ] Implementar uma abordagem incremental, reutilizando informação de `H0`
- [ ] Garantir que `H1` respeita as mesmas restrições do problema
- [ ] Minimizar o número de aulas alteradas entre `H0` e `H1`
- [ ] Medir e comparar tempo de execução entre solução do zero e solução incremental
- [ ] Mostrar evidência de que a abordagem incremental é melhor ou mais estável

### Validação e testes
- [ ] Criar validação automática das restrições R1 a R8
- [ ] Testar pelo menos um caso de cada restrição
- [ ] Verificar o comportamento com dados diferentes do conjunto fornecido
- [ ] Confirmar que não existem valores hardcoded no código

### Apresentação e entrega
- [x] Produzir a visualização do horário no notebook Marimo
- [x] Mostrar o horário por turma e por professor em tabelas semanais
- [ ] Documentar o processo de geração e as decisões tomadas
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
- Para usar os dados alternativos, alterar `PASTA_DADOS = "dados"` para `PASTA_DADOS = "dados_v2"` na célula de carregamento.
- O notebook regista o tempo de execução de H0, mas ainda não compara H0 e H1.

## Estado atual

O notebook lê e valida os CSVs da pasta indicada em `PASTA_DADOS`, constrói o modelo
CP-SAT com as restrições R1–R7, resolve H0, atribui salas concretas e apresenta o horário
por turma e por professor. A implementação está no notebook, mas a execução completa
continua por confirmar no ambiente Marimo devido ao erro de importação de OR-Tools/Pandas
com bloqueio de DLL reportado anteriormente.

Ainda faltam a validação automática e independente das restrições R1–R8, testes para cada
restrição e com dados alternativos, a otimização O1 (buracos dos professores), a construção
incremental R9 (gerar e comparar H0/H1), documentar essa avaliação e preparar a entrega.
