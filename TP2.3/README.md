# Exercício 3

Considere o problema descrito no documento +Lógica Computacional: Multiplicação de Inteiros https://www.dropbox.com/scl/fi/zozzuriwaw7db9abpewyh/Logica-Computacional-Multiplicacao-de-Inteiros.paper?rlkey=j92tgvb8emq3ybb0aiv8jz33q&dl=0. Nesse documento usa-se um “Control Flow Automaton” como  modelo do programa imperativo que calcula a multiplicação de  inteiros positivos representados por vetores de bits.


1. Construir um SFOTS, usando BitVec’s de tamanho $$n$$ , que descreva o comportamento deste autómato; para isso identifique e codifique em `Z3` , as variáveis do modelo, o estado inicial , a relação de transição e o estado de erro.
2. Usando $$k$$-indução verifique nesse SFOTS se $$\;$$a propriedade $$\;(x*y + z = a*b)\;$$ $$\;$$é um invariante do seu comportamento.
3. Usando $$k$$-indução no SFOTS acima e adicionando ao estado inicial  a condição  $$\,$$ $$\,(a < 2^{n/2})\land(b < 2^{n/2})\,$$, verifique a segurança do programa; nomeadamente  prove que, com tal estado inicial, o estado de erro nunca é acessível.
4. Codifique a propriedade de animação que exprime que o programa termina quaisquer que sejam os valores iniciais de $$\,a\,$$ e $$\,b\,$$ e prove que ela se verifica no SFOTS  que construiu.

https://share.google/aimode/80OTdhEEscQJAbLsy


Puma melhor interpretaçao do enunciado foi usado o claude no seguinte chat: https://claude.ai/share/c4fb403c-1ec4-4e9b-a545-3804fbf2d7da

para a file tree: https://claude.ai/share/8f2ac999-7b1b-4f50-8779-9317812be298

## Referência rápida: operadores Z3

Os operadores abaixo são usados em `ex3_py.py` para modelar o programa com
vetores de bits. Um `BitVec` tem largura fixa: operações aritméticas mantêm
essa largura e, por isso, podem sofrer overflow (aritmética módulo `2^n`).

| Operador | O que faz neste exercício |
| --- | --- |
| `BitVec(nome, n)` | Declara uma variável simbólica com `n` bits. |
| `ULT(a, b)` | Compara `a < b` como números **sem sinal**. |
| `Extract(high, low, x)` | Extrai de `x` os bits do índice `high` ao `low`, inclusive. |
| `BitVecVal(valor, n)` | Cria uma constante com o valor e a largura de `n` bits. |
| `And(c1, ...)` | Exige que todas as restrições fornecidas sejam verdadeiras. |
| `LShR(x, k)` | Desloca `x` `k` bits à direita, preenchendo os bits à esquerda com zeros. |
| `Or(c1, ...)` | Exige que pelo menos uma das restrições fornecidas seja verdadeira. |
| `Not(c)` | Nega uma restrição lógica. |
| `ZeroExt(k, x)` | Aumenta a largura de `x` em `k` bits, acrescentando zeros à esquerda; aqui permite calcular com `2n` bits. |

## Lista de tarefas do enunciado

Estado com base no código atual. As caixas assinaladas indicam funcionalidades
já codificadas em `ex3_py.py`; ainda falta validar os resultados e completar os
itens pendentes abaixo.

- [x] Modelar o SFOTS: variáveis, estado inicial, transições e estado de erro.
- [x] Usar `k`-indução para verificar `x*y + z = a*b`, tanto com aritmética de `n` bits como numa versão alargada a `2n` bits.
- [x] Restringir os valores iniciais a `a, b < 2^(n/2)` e verificar que o estado `ERROR` não é alcançado.
- [x] Codificar a verificação de terminação por BMC, procurando caminhos que não chegam a `STOP` nem a `ERROR` em `4n` passos.
- [ ] Generalizar e validar o exercício para diferentes valores de `n` (o script atual usa apenas `n = 4`).
- [ ] Completar o notebook Marimo com a explicação de todas as partes: modelo SFOTS, transições, overflow, propriedades, `k`-indução, segurança e terminação.
- [ ] Criar e executar testes para validar o modelo e os resultados do solver, incluindo diferentes valores de `n`.
- [ ] Executar `ex3_py.py` e confirmar que os resultados do solver correspondem ao esperado antes de entregar.
