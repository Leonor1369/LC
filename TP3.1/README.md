
## Exercício 1

Exclusão mútua num anel com testemunho.

$$N\,$$ processos estão dispostos em anel. O processo $$\,i\,$$ tem três variáveis booleanas: $$\,w\,$$ (à espera), $$\,c\,$$ (na secção crítica) e $$\,t\,$$ (tem o testemunho). No estado inicial todos os processos estão inativos e só o processo $$\,0\,$$ tem o testemunho. Em cada transição move-se um único processo $$\,i\,$$, de acordo com uma das regras seguintes:

- pedir: um processo inativo passa a estar à espera;
- entrar: um processo à espera e com testemunho entra na secção crítica;
- sair: um processo na secção crítica passa a inativo e o testemunho passa para o processo $$\;(i+1)\bmod N\,$$;
- passar: um processo inativo com testemunho entrega-o ao processo $$\,i+1\bmod N$$ .

O estado de erro é $$\;\bigvee_{i<j}\, c_i \land c_j\;$$; i.e. dois processos não podem estar simultaneamente na secção crítica.

Pretende-se:

1. Construir o SFOTS proposicional em Z3, parametrizado por $$\,N$$.
2. Mostrar que a $$\,k$$-indução usada no TP2 falha para valores pequenos de $$\,k\,$$, mesmo com traços simples. Apresentar o contra-exemplo ao passo indutivo e explicar por que não é acessível.
3. Verificar a segurança do sistema com dois algoritmos: o PDR usando a implementação `pdr_lia.py` que está no [repositório LC](https://github.com/jmvalenca/LC) , e o algoritmo de interpolantes e invariantes da 1ª parte, com os interpolantes calculados via CHCs. Em ambos os casos extrair o invariante indutivo obtido e verificá-lo de forma independente.
4. Considerar a variante em que um processo à espera e sem testemunho pode regenerar um testemunho (recuperação de perda). Ambos os algoritmos da alínea anterior devem detetar a insegurança; apresentar um traço de erro obtido com BMC.
5. Comparar, para $$\,N\,$$ crescente, o comportamento do PDR, do algoritmo de interpolantes e invariantes e do Spacer: tempo de execução, número de iterações e dimensão do invariante obtido.

## Entrega

A resolução deste exercício deve ser implementada num **notebook Marimo** nesta pasta.

```text
TP3.1/
├── README.md
└── notebook.py
```

Para editar/executar o notebook:

```bash
marimo edit TP3.1/notebook.py
```

### Estrutura recomendada

- [ ] Criar uma célula para configurar $N$.
- [ ] Criar uma célula para declarar $w_i$, $c_i$ e $t_i$ em Z3.
- [ ] Implementar o estado inicial e as transições `pedir`, `entrar`, `sair` e `passar`.
- [ ] Implementar o predicado de erro $\bigvee_{i<j}(c_i\land c_j)$.
- [ ] Demonstrar concretamente a falha da $k$-indução para pequenos valores de $k$.
- [ ] Mostrar o contraexemplo ao passo indutivo e explicar por que não é acessível.
- [ ] Implementar ou integrar o PDR com `pdr_lia.py`.
- [ ] Implementar o algoritmo baseado em interpolantes e CHCs.
- [ ] Extrair e verificar independentemente os invariantes indutivos obtidos.
- [ ] Implementar a variante com regeneração do testemunho.
- [ ] Obter um contraexemplo de segurança com BMC.
- [ ] Produzir uma tabela comparativa para PDR, interpolantes/invariantes e Spacer.
- [ ] Executar o notebook até ao fim e verificar os resultados apresentados pelo solver.