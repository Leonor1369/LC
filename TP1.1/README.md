# TP1.1 - Horário Escolar

Este projeto consiste em desenvolver um gerador de horário escolar em Marimo, respeitando as restrições do enunciado e validando o resultado com dados reais em CSV.

## Checklist para terminar o trabalho

### Estrutura e execução em Marimo
- [x] Criar/editar o notebook principal em Marimo para o problema de horário escolar
- [ ] Garantir que o projeto corre corretamente em Marimo e não apenas como script Python normal
- [ ] Confirmar que os ficheiros CSV são lidos a partir da pasta `dados/` e `dados_v2/`
- [ ] Organizar o código em células Marimo com lógica separada por responsabilidade
- [x] Incluir uma forma simples de executar o notebook localmente

### Leitura e modelação dos dados
- [x] Ler `turmas.csv`, `disciplinas.csv`, `salas.csv` e `disponibilidade_excecoes.csv`
- [ ] Validar que os dados estão no formato correto
- [x] Representar turmas, disciplinas, professores, salas e indisponibilidades em listas/dicionários
- [ ] Tratar corretamente disciplinas com `duplo_periodo=sim`
- [ ] Tratar corretamente disciplinas com `sala_especial`

### Geração do horário
- [ ] Implementar a geração de um horário inicial válido
- [ ] Garantir que uma turma não tem duas aulas ao mesmo tempo
- [ ] Garantir que cada disciplina cumpre a carga semanal correta
- [ ] Garantir que não há mais do que uma aula da mesma disciplina por dia, por turma, salvo duplos
- [ ] Garantir que disciplinas de duplo período só aparecem em blocos consecutivos
- [ ] Garantir que um professor não dá duas aulas em simultâneo
- [ ] Garantir que um professor só ministra aulas quando está disponível
- [ ] Garantir que cada aula usa uma sala válida
- [ ] Garantir que o número de aulas por tipo de sala não excede a capacidade disponível

### Optimização
- [ ] Definir uma função objetivo para minimizar buracos no horário dos professores
- [ ] Ajustar a solução para melhorar a qualidade do horário, mesmo que não seja ótima
- [ ] Documentar as decisões de modelação e otimização no notebook

### Construção incremental
- [ ] Gerar um horário válido `H0` com os dados iniciais
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
- [ ] Produzir o relatório/visualização no notebook Marimo
- [ ] Mostrar o horário final de forma clara (tabelas, texto ou UI)
- [ ] Documentar o processo de geração e as decisões tomadas
- [ ] Verificar que o notebook pode ser aberto e executado em Marimo sem erros
- [ ] Preparar a versão final para entrega

## Como correr em Marimo

A partir da pasta do projeto:

```bash
cd TP1.1
marimo run horario_escolar_enunciado.py
```

O notebook existente chama-se `horario_escolar_enunciado.py`. Quando criares o ficheiro final `horario_escolar.py`, podes trocar o nome no comando.

## Observações

- O código deve ler os dados dos ficheiros CSV e não usar dicionários ou listas fixas no próprio notebook.
- A solução deve funcionar para alterações ligeiras de recursos, como as que aparecem em `dados_v2/`.
- O tempo de execução e o número de mudanças entre `H0` e `H1` devem ser apresentados como parte da análise.

## Estado atual

Ainda falta realizar a implementação completa do problema e validar o fluxo em Marimo.
