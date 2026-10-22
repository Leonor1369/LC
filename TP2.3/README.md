# Exercício 3

Considere o problema descrito no documento +Lógica Computacional: Multiplicação de Inteiros . Nesse documento usa-se um “Control Flow Automaton” como  modelo do programa imperativo que calcula a multiplicação de  inteiros positivos representados por vetores de bits.


1. Construir um SFOTS, usando BitVec’s de tamanho $$n$$ , que descreva o comportamento deste autómato; para isso identifique e codifique em `Z3` , as variáveis do modelo, o estado inicial , a relação de transição e o estado de erro.
2. Usando $$k$$-indução verifique nesse SFOTS se $$\;$$a propriedade $$\;(x*y + z = a*b)\;$$ $$\;$$é um invariante do seu comportamento.
3. Usando $$k$$-indução no SFOTS acima e adicionando ao estado inicial  a condição  $$\,$$ $$\,(a < 2^{n/2})\land(b < 2^{n/2})\,$$, verifique a segurança do programa; nomeadamente  prove que, com tal estado inicial, o estado de erro nunca é acessível.
4. Codifique a propriedade de animação que exprime que o programa termina quaisquer que sejam os valores iniciais de $$\,a\,$$ e $$\,b\,$$ e prove que ela se verifica no SFOTS  que construiu.