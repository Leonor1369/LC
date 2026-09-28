# TP1.2 - Sudoku Genérico como CSP

Este trabalho implementa um resolvedor de Sudoku genérico como problema de satisfação de restrições (CSP), apresentado num notebook Marimo. O tamanho da grelha é parametrizado por `n`: a dimensão é `n² × n²` e os valores possíveis são `1` a `n²`.

## Checklist

### Base Marimo e modelo
- [ ] Criar um notebook Marimo de trabalho separado do ficheiro do enunciado
- [ ] Permitir escolher `n` no notebook (`n=2` ou `n=3`)
- [ ] Criar a classe genérica `box` para grupos de células com valores distintos
- [ ] Validar coordenadas e valores adicionados a um `box`
- [ ] Converter um grupo para uma matriz `n² × n²`, com zero fora das células fixas
- [ ] Criar `cube` para representar blocos `n × n`
- [ ] Criar `path` para sequências horizontais e verticais em qualquer direção
- [ ] Gerar aleatoriamente células e valores das pistas
- [ ] Construir linhas, colunas, blocos e pistas usando a abstração comum
- [ ] Criar um modelo CP-SAT com uma variável por célula e domínio `1..n²`
- [ ] Permitir adicionar um número arbitrário de grupos ao modelo
- [ ] Restringir os valores de cada grupo a serem todos diferentes
- [ ] Fixar no modelo as células fornecidas como pistas
- [ ] Devolver uma grelha resolvida ou `None` quando o modelo for inviável
- [ ] Mostrar a solução no notebook e destacar as pistas

### Testes e validação
- [ ] Incluir uma função que verifica dimensões, domínio, grupos e pistas da solução
- [ ] Verificar automaticamente que `box.add` rejeita coordenadas inválidas
- [ ] Verificar automaticamente que `box.add` rejeita valores fora de `1..n²`
- [ ] Testar linhas, colunas e blocos com uma solução conhecida
- [ ] Testar o fluxo completo com `n=2`
- [ ] Testar o fluxo completo com `n=3`
- [ ] Testar o comportamento de um conjunto de pistas sem solução
- [ ] Confirmar que o notebook corre em Marimo com OR-Tools no ambiente ativo

### Relatório e entrega
- [ ] Explicar no notebook a escolha de CP-SAT e a modelação do CSP
- [ ] Registar resultados dos testes para `n=2` e `n=3`
- [ ] Documentar limitações ou tempo de execução observado
- [ ] Rever o notebook completo e preparar a versão final para entrega

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
