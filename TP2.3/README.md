# Exercício 3

Considere o problema descrito no documento +Lógica Computacional: Multiplicação de Inteiros https://www.dropbox.com/scl/fi/zozzuriwaw7db9abpewyh/Logica-Computacional-Multiplicacao-de-Inteiros.paper?rlkey=j92tgvb8emq3ybb0aiv8jz33q&dl=0. Nesse documento usa-se um “Control Flow Automaton” como  modelo do programa imperativo que calcula a multiplicação de  inteiros positivos representados por vetores de bits.


1. Construir um SFOTS, usando BitVec’s de tamanho $$n$$ , que descreva o comportamento deste autómato; para isso identifique e codifique em `Z3` , as variáveis do modelo, o estado inicial , a relação de transição e o estado de erro.
2. Usando $$k$$-indução verifique nesse SFOTS se $$\;$$a propriedade $$\;(x*y + z = a*b)\;$$ $$\;$$é um invariante do seu comportamento.
3. Usando $$k$$-indução no SFOTS acima e adicionando ao estado inicial  a condição  $$\,$$ $$\,(a < 2^{n/2})\land(b < 2^{n/2})\,$$, verifique a segurança do programa; nomeadamente  prove que, com tal estado inicial, o estado de erro nunca é acessível.
4. Codifique a propriedade de animação que exprime que o programa termina quaisquer que sejam os valores iniciais de $$\,a\,$$ e $$\,b\,$$ e prove que ela se verifica no SFOTS  que construiu.

https://share.google/aimode/80OTdhEEscQJAbLsy


Puma melhor interpretaçao do enunciado foi usado o claude no seguinte chat: https://claude.ai/share/c4fb403c-1ec4-4e9b-a545-3804fbf2d7da

para a file tree: https://claude.ai/share/8f2ac999-7b1b-4f50-8779-9317812be298

## Referência rápida: operadores pySMT usados no notebook

O notebook usa pySMT para construir fórmulas com vetores de bits e o solver
Z3 para as resolver. Um `BitVec` tem largura fixa: operações aritméticas
mantêm essa largura e, por isso, podem sofrer overflow (aritmética módulo
`2^n`). O vetor não é, por si só, assinado ou sem sinal; isso depende da
operação de comparação ou da extensão usada.

| Operador | O que faz neste exercício |
| --- | --- |
| `Symbol(nome, BVType(n))` | Declara uma variável simbólica com `n` bits. |
| `BV(valor, n)` | Cria uma constante BitVec com largura `n`. |
| `BVULT(a, b)` | Compara `a < b` como números **sem sinal**. |
| `BVSGE(a, b)` | Compara `a >= b` como números **com sinal**. |
| `BVExtract(x, alto, baixo)` | Extrai de `x` os bits dos índices `alto` a `baixo`, inclusive. |
| `BVZExt(x, k)` | Aumenta a largura de `x` em `k` bits, acrescentando zeros à esquerda. |
| `BVSExt(x, k)` | Aumenta a largura de `x` em `k` bits, repetindo o bit de sinal à esquerda. |
| `BVAdd(a, b)`, `BVSub(a, b)`, `BVMul(a, b)` | Soma, subtrai e multiplica vetores de bits; o resultado mantém a largura dos operandos. |
| `BVLShl(x, k)`, `BVLShr(x, k)` | Deslocam os bits à esquerda ou à direita; o deslocamento à direita preenche com zeros. |
| `BVAnd(a, b)` | Aplica AND bit a bit aos vetores de bits. |
| `And(...)`, `Or(...)`, `Not(c)`, `Equals(a, b)` | Constroem conjunções, disjunções, negações e igualdade lógica para as fórmulas do solver. |

## Lista de tarefas do enunciado

Estado com base no notebook Marimo. É possível escolher `n = 8` ou `n = 16`;
as provas por k-indução do invariante e da segurança são executadas apenas
para `n <= 8`, e a validação exaustiva está fixa em `n = 8`.

- [x] Modelar o SFOTS: variáveis, estado inicial, transições e estado de erro.
- [x] Usar `k`-indução para verificar `x*y + z = a*b`, tanto com aritmética de `n` bits como numa versão alargada a `2n` bits.
- [x] Restringir os valores iniciais a `a, b < 2^(n/2)` e verificar que o estado `ERROR` não é alcançado.
- [x] Codificar a verificação de terminação: o notebook prova a descida de uma variante, ausência de bloqueio e procura por BMC caminhos que não chegam a `STOP` nem a `ERROR` em `4n` passos.
- [x] Completar o notebook Marimo com a explicação do modelo SFOTS, transições, overflow, propriedades, `k`-indução, segurança e terminação.
- [x] Permitir selecionar `n = 8` ou `n = 16` no notebook e adaptar o modelo ao valor escolhido; para `n = 16`, as provas por k-indução do invariante e da segurança são omitidas por custo computacional.
- [x] Criar e executar testes para validar o modelo e os resultados do solver, incluindo diferentes valores de `n`.
- [x] Executar o notebook e confirmar que os resultados apresentados pelo solver correspondem ao esperado antes de entregar.
