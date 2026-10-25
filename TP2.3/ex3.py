import marimo

__generated_with = "0.9.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from z3 import (BitVec, BitVecVal, And, Or, Not, Implies, If, Extract, ZeroExt, LShR,
                    ULT, ULE, BVAddNoOverflow, Solver, sat, unsat)
    return (And, BVAddNoOverflow, BitVec, BitVecVal, Extract, If, Implies, LShR, Not, Or,
            Solver, ULE, ULT, ZeroExt, mo, sat, unsat)


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
