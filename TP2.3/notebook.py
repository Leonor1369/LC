import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from pysmt.shortcuts import (
        Symbol, BV, And, Or, Not, Equals, NotEquals, Solver,
        BVAdd, BVSub, BVAnd, BVLShl, BVLShr, BVExtract, BVZExt, BVSExt, BVSGE,
    )
    from pysmt.typing import BVType

    return (
        And, BV, BVAdd, BVAnd, BVExtract, BVLShl, BVLShr, BVSExt, BVSGE, BVSub,
        BVType, BVZExt, Equals, Not, NotEquals, Or, Solver, Symbol, mo,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # TP2 — Exercício 3
    # Multiplicação de inteiros como SFOTS (BitVec, pySMT)

    ```
    INPUT a, b                        # n bits, a, b >= 0
    x, y, z = a, b, 0
    LOOP:  while y != 0:
    ODD(y):      if y & 1 == 1:  x, y, z = x, y-1, z+x      (overflow em z+x  → ERROR)
    EVEN(y):     else:           x, y, z = x<<1, y>>1, z    (overflow em x<<1 → ERROR)
    STOP:  assert z == a*b
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Como ler os BitVec e as condições

    Um `BitVec` é um vetor de bits com largura fixa. Por exemplo, `BV(5, 8)`
    representa `00000101`: o segundo argumento (`8`) é o número de bits.
    Valores e operações ficam limitados a essa largura; por isso, uma soma
    de 8 bits pode dar a volta (overflow) em vez de guardar um nono bit.
    O BitVec, por si só, não é marcado como assinado ou não assinado. A
    interpretação depende da operação usada: por exemplo, `BVSGE` compara
    como valores com sinal.

    - `esta(state, pc)` compara o campo `state['pc']` com o código do estado
      de controlo. `BV(pc, 3)` transforma o código inteiro (`LOOP`, `EVEN`,
      etc.) num BitVec de 3 bits. Assim, `esta(state, LOOP)` é uma condição
      lógica que significa “o estado atual está em LOOP”.
    - `BVZExt(valor, 1)` acrescenta um bit `0` à esquerda; `BVSExt(valor, 1)`
      repete o bit de sinal. O `1` indica quantos bits acrescentar, não a
      largura final. Por exemplo, em 8 bits, `11111111` passa a
      `011111111` com extensão a zero, ou a `111111111` com extensão de sinal.
    - A deteção de overflow da soma alarga `x` e `z` para 9 bits antes de
      somar. No modo sem sinal, o bit extra é o carry. No modo com sinal,
      overflow acontece quando os dois bits mais significativos do resultado
      alargado diferem.
    - `BVExtract(valor, alto, baixo)` seleciona os bits entre os índices
      `alto` e `baixo`, inclusive. Por exemplo,
      `BVExtract(valor, 7, 7)` extrai o bit mais significativo de um BitVec
      de 8 bits.

    Estas funções constroem fórmulas simbólicas para o solver; não calculam
    imediatamente valores Python. `Equals`, `And`, `Or` e `Not` combinam
    essas fórmulas, e o solver procura valores que as tornem verdadeiras.
    """)
    return


@app.cell
def _():
    BITS = 8            # tamanho dos BitVec
    COM_SINAL = False   # False: overflow = carry (naturais); True: overflow com sinal
    K_IND = 6           # limite para a k-indução (alíneas seguintes)

    LOOP, EVEN, ODD, STOP, ERROR = range(5)
    NOME = {LOOP: "LOOP", EVEN: "EVEN", ODD: "ODD", STOP: "STOP", ERROR: "ERROR"}
    return BITS, COM_SINAL, ERROR, EVEN, LOOP, NOME, ODD, STOP


@app.cell
def _(
    And, BITS, BV, BVAdd, BVAnd, BVExtract, BVLShl, BVLShr, BVSExt, BVSGE, BVSub,
    BVType, BVZExt, COM_SINAL, ERROR, EVEN, Equals, LOOP, Not, NotEquals, ODD, Or,
    STOP, Symbol,
):
    def declare(i):
        state = {'pc': Symbol(f'pc{i}', BVType(3))} # 001 to 111 - 1 to 9 
        # todo o estado de variavel para todo o estado do pc
        for v in 'abxyz':
            state[v] = Symbol(f'{v}{i}', BVType(BITS))

        return state


    def esta(state, pc):
        """Constrói a condição lógica que identifica o estado de controlo `pc`."""
        return Equals(state['pc'], BV(pc, 3))


    def init(state):
        # a >= 0 e b >= 0 só interessa no modo com sinal
        nao_negativos = []
        if COM_SINAL:
            nao_negativos = [BVSGE(state['a'], BV(0, BITS)), # a >=0
                             BVSGE(state['b'], BV(0, BITS))] # b>= 0
        return And(
            esta(state, LOOP),
            Equals(state['x'], state['a']), # x = a
            Equals(state['y'], state['b']), # y = b
            Equals(state['z'], BV(0, BITS)), # z >= 0
            *nao_negativos,
        )


    # deteção explícita do overflow (os BitVec nunca o assinalam)

    def overflow_soma(state):
        # soma em n+1 bits: sem sinal, o bit n é o carry;
        
        # com sinal, há overflow se os dois bits de topo forem diferentes
        ext = BVSExt if COM_SINAL else BVZExt
        
        soma = BVAdd(ext(state['z'], 1), ext(state['x'], 1))
        
        if COM_SINAL:
            return NotEquals(BVExtract(soma, BITS, BITS), BVExtract(soma, BITS - 1, BITS - 1))
        
        return Equals(BVExtract(soma, BITS, BITS), BV(1, 1))


    def overflow_shift(state):
        x = state['x']
        
        if COM_SINAL:
            return NotEquals(BVExtract(x, BITS - 1, BITS - 1), BVExtract(x, BITS - 2, BITS - 2))
        
        return Equals(BVExtract(x, BITS - 1, BITS - 1), BV(1, 1))


    def trans(curr, prox): # current , proximo

        um = BV(1, BITS)

        y_zero = Equals(curr['y'], BV(0, BITS))

        par = Equals(BVAnd(curr['y'], um), BV(0, BITS))

        def vai(destino, **novos):
            # pc' = destino; 
            # x, y, z mudam para o valor em `novos` ou mantêm-se
            return And(
                esta(prox, destino),
                *[Equals(prox[v], novos.get(v, curr[v])) for v in 'xyz'],
            )

        return And(
            Equals(prox['a'], curr['a']),
            Equals(prox['b'], curr['b']),
            Or(
                # LOOP
                And(esta(curr, LOOP), y_zero, vai(STOP)),
                And(esta(curr, LOOP), Not(y_zero), par, vai(EVEN)),
                And(esta(curr, LOOP), Not(y_zero), Not(par), vai(ODD)),
                # EVEN (o erro tem precedência)
                And(esta(curr, EVEN), overflow_shift(curr), vai(ERROR)),
                And(esta(curr, EVEN), Not(overflow_shift(curr)),
                    vai(LOOP, x=BVLShl(curr['x'], um), y=BVLShr(curr['y'], um))),
                # ODD (o erro tem precedência)
                And(esta(curr, ODD), overflow_soma(curr), vai(ERROR)),
                And(esta(curr, ODD), Not(overflow_soma(curr)),
                    vai(LOOP, y=BVSub(curr['y'], um), z=BVAdd(curr['z'], curr['x']))),
                # estados finais com laço
                And(esta(curr, STOP), vai(STOP)),
                And(esta(curr, ERROR), vai(ERROR)),
            ),
        )


    def error(state):
        return esta(state, ERROR)


    return declare, init, trans


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Execução de exemplo

    Uma execução concreta obtida por *unrolling* da relação de transição.
    """)
    return


@app.cell
def _(And, BITS, BV, COM_SINAL, ERROR, Equals, NOME, STOP, Solver, declare, init, trans):
    def valor(modelo, expr):
        v = modelo.get_py_value(expr)
        if COM_SINAL and v >= 2 ** (BITS - 1):   # BitVec com sinal
            v -= 2 ** BITS
        return v


    def gera_traco(a0, b0, k):
        # k transições precisam de k+1 estados
        estados = [declare(i) for i in range(k + 1)]

        with Solver(name="z3") as s:
            s.add_assertion(init(estados[0]))
            s.add_assertion(Equals(estados[0]['a'], BV(a0, BITS)))
            s.add_assertion(Equals(estados[0]['b'], BV(b0, BITS)))
            for i in range(k):
                s.add_assertion(trans(estados[i], estados[i + 1]))

            if not s.solve():
                print("Nenhum traço encontrado.")
                return

            m = s.get_model()
            print(f"a={a0}, b={b0}, a*b={a0 * b0}\n")
            print(f"{'t':>3} {'pc':>6} {'x':>6} {'y':>6} {'z':>6}  x*y+z")
            for i, st in enumerate(estados):
                pc = m.get_py_value(st['pc'])
                x, y, z = valor(m, st['x']), valor(m, st['y']), valor(m, st['z'])
                print(f"{i:>3} {NOME[pc]:>6} {x:>6} {y:>6} {z:>6}  {x * y + z}")
                if pc in (STOP, ERROR):
                    break


    gera_traco(13, 11, 4 * BITS)
    return


if __name__ == "__main__":
    app.run()