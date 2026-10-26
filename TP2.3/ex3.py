import marimo

__generated_with = "0.9.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import time 
    from z3 import *


@app.cell
def _(mo):
    mo.md(
        r"""
        # TP2 — Exercício 3 
        # Multiplicação de inteiros como SFOTS (BitVec, Z3)

        ```
        INPUT a, b                        # n bits, a, b >= 0
        x, y, z = a, b, 0
        LOOP:  while y != 0:
        ODD(y):      if y & 1 == 1:  x, y, z = x, y-1, z+x      (overflow em z+x  → ERROR)
        EVEN(y):     else:           x, y, z = x<<1, y>>1, z    (overflow em x<<1 → ERROR)
        STOP:  assert z == a*b
        ```
        *interpretação da documentação: https://www.dropbox.com/scl/fi/zozzuriwaw7db9abpewyh/Logica-Computacional-Multiplicacao-de-Inteiros.paper?rlkey=j92tgvb8emq3ybb0aiv8jz33q&dl=0 *
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        O autómato de controlo (CFA) modela a multiplicação por deslocamentos e somas, 
        explicitando o overflow em x << 1 e z + x. As transições de erro por overflow 
        têm precedência absoluta sobre as restantes.
        
        Funcionamento dos Estados:
        LOOP (inicial): Testa $y$. Se $y = 0$ vai para STOP; 
                        se $y \neq 0$ e par vai para EVEN; 
                        se $y \neq 0$ e ímpar vai para ODD.
        EVEN: Executa x, y = x << 1, y >> 1. 
                Transita para ERROR se ocorrer overflow em x << 1; 
                caso contrário, regressa a LOOP.
        ODD: Executa y, z = y − 1, z + x. 
                Transita para ERROR se ocorrer overflow em z + x; 
                caso contrário, regressa a LOOP.
        STOP: Estado final ($z = a \cdot b$) em laço próprio.
        ERROR: Estado de erro por overflow em laço próprio.
        
        Deteção de Overflow no Z3:
        Como as operações em Bit-Vectors no Z3 são totais (calculadas módulo $2^n$ 
        sem assinalar erro), a deteção é programada explicitamente:
        Sem sinal: Ocorre overflow em z + x se ¬BVAddNoOverflow(z, x, False) (existência de carry); 
                em x << 1 ocorre se o bit $n-1$ de x for 1.
        Com sinal (COM_SINAL = True): Ocorre overflow em z + x se ¬BVAddNoOverflow(z, x, True);
                 em x << 1 ocorre se os bits $n-1$ e $n-2$ de x forem diferentes (alteração do bit de sinal).
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        #Parâmetros
        """
    )
    return

@app.cell
def _():
    bit = 8        # tamanho dos BitVec (bits)
    Com_Sinal = False    # False: overflow = carry (naturais);  True: overflow com sinal (bit V da ALU)
    k_ind = 6        # limite para a k-indução das alíneas 2 e 3 (reforçada)
    return(bit,Com_sinal,k_ind)

@app.cell
def _(mo):
    mo.md(
        r"""
        O SFOTS (Symbolic First-Order Transition System) formaliza o autómato como um 
        sistema de transição simbólico:
        
        Componentes do Sistema:
        
        - Variáveis: O contador de programa $pc \in \{\text{Loop}, \text{Even}, \text{Odd}, 
        \text{STOP}, \text{ERROR}\}$ é representado por um BitVec(3). Os inputs $a, b$ (constantes) 
        e as variáveis $x, y, z$ são BitVec(n).
        
        - Estado Inicial ($I$): Define-se por $pc = \text{Loop} \land x = a \land y = b \land z = 0 
        \land a \ge 0 \land b \ge 0$ (a restrição $\ge 0$ aplica-se apenas no modo com sinal).
        
        - Relação de Transição ($T(s, s')$): Corresponde à disjunção de todas as ligações do CFA. 
        Cada transição conjuga a sua guarda com a atualização das variáveis (as variáveis não 
        mencionadas mantêm o valor). As guardas de erro excluem as transições normais para garantir
        a precedência.
          
        - Estado de Erro: Caraterizado pela condição $pc = \text{ERROR}$.
        """
    )
    return


