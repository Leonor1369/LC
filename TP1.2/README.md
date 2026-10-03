# TP1.2 - Sudoku Genérico como CSP

Este trabalho implementa um resolvedor de Sudoku genérico como problema de satisfação de restrições (CSP), apresentado num notebook Marimo. O tamanho da grelha é parametrizado por `n`: a dimensão é `n² × n²` e os valores possíveis são `1` a `n²`.

## Checklist

### Base Marimo e modelo
- [x] Criar um notebook Marimo de trabalho separado do ficheiro do enunciado
- [x] Permitir escolher `n` no notebook (`n=2` ou `n=3`)
- [x] Criar a classe genérica `box` para grupos de células com valores distintos
- [x] Validar coordenadas e valores adicionados a um `box`
- [x] Converter um grupo para uma matriz `n² × n²`, com zero fora das células fixas
- [x] Criar `cube` para representar blocos `n × n`
- [x] Criar `path` para sequências horizontais e verticais em qualquer direção
- [x] Gerar aleatoriamente células e valores das pistas
- [x] Construir linhas, colunas, blocos e pistas usando a abstração comum
- [x] Criar um modelo CP-SAT com uma variável por célula e domínio `1..n²`
- [x] Permitir adicionar um número arbitrário de grupos ao modelo
- [x] Restringir os valores de cada grupo a serem todos diferentes
- [x] Fixar no modelo as células fornecidas como pistas
- [x] Devolver uma grelha resolvida ou `None` quando o modelo for inviável
- [x] Mostrar a solução no notebook e destacar as pistas

### Testes e validação
- [x] Incluir uma função que verifica dimensões, domínio, grupos e pistas da solução
- [x] Verificar automaticamente que `box.add` rejeita coordenadas inválidas
- [x] Verificar automaticamente que `box.add` rejeita valores fora de `1..n²`
- [x] Testar linhas, colunas e blocos com uma solução conhecida
- [x] Testar o fluxo completo com `n=2`
- [x] Testar o fluxo completo com `n=3`
- [x] Testar o comportamento de um conjunto de pistas sem solução
- [x] Confirmar que o notebook corre em Marimo com OR-Tools no ambiente ativo

### Relatório e entrega
- [x] Explicar no notebook a escolha de CP-SAT e a modelação do CSP
- [ ] Registar resultados dos testes para `n=2` e `n=3` em texto mais claro
- [ ] Documentar limitações ou tempo de execução observado
- [ ] Rever o notebook completo e preparar a versão final para entrega

## Estado atual do ficheiro `sudoku.py`

O ficheiro [TP1.2/sudoku.py](TP1.2/sudoku.py) já implementa a maior parte do enunciado e está muito próximo do que é exigido.

### Já está implementado
- [x] Notebook separado do enunciado, em Marimo
- [x] Suporte paramétrico para `n` com slider no notebook
- [x] Classe `box` genérica com validação de coordenadas e valores
- [x] Conversão do grupo para matriz com zeros fora das células fixas
- [x] Classes `cube` e `path` para blocos e linhas/colunas
- [x] Geração aleatória de pistas
- [x] Modelo CP-SAT com variável por célula e domínio `1..n²`
- [x] Adição de grupos arbitrários ao modelo (`box`, `cube`, `path`, etc.)
- [x] Restrição "todos diferentes" para cada grupo
- [x] Fixação dos valores das pistas no modelo
- [x] Resolução do puzzle e retorno de `None` quando não há solução
- [x] Visualização da grelha e destaque das pistas
- [x] Validação automática da grelha resolvida
- [x] Testes para `n=2` e `n=3`
- [x] Verificação de rejeição de coordenadas e valores inválidos
- [x] Verificação do comportamento de `path` em ambos os sentidos

### O que ainda falta para fechar totalmente o enunciado
- [ ] Documentar de forma mais explícita o caso de puzzle sem solução, com um exemplo concreto e não apenas com tentativa aleatória repetida
- [ ] Registar os resultados observados para `n=2` e `n=3` em texto mais claro no notebook/README
- [ ] Confirmar execução completa em Marimo no ambiente de entrega e verificar que não há erros de runtime
- [ ] Validar manualmente um caso de instância impossível, para garantir que a mensagem final e a estratégia de re-tentativa estão corretamente explicadas
- [ ] Revisar o relatório final e preparar a entrega definitiva

### Conclusão
O projeto está funcional e segue muito bem a lógica do enunciado, mas ainda faltam alguns pontos de apresentação e validação final para ficar completamente pronto para entrega.

## Como executar

A partir da pasta `TP1.2`, com o ambiente Python que contém Marimo e OR-Tools ativo:

```bash
marimo edit sudoku.py
```

Para correr sem editar:

```bash
marimo run sudoku.py
```

O notebook gera pistas aleatórias. Algumas combinações podem não ter solução; nesse caso apresenta uma mensagem e pode ser executado novamente para gerar outras pistas.
