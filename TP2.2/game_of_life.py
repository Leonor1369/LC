import marimo
 
__generated_with = "0.25.2"
app = marimo.App(width="medium")
 
 
@app.cell
def _():
    import marimo as mo
    import random
    import time
    from pysmt.shortcuts import (Symbol, Int, And, Or, Not, Iff, Ite,
                                 Equals, Plus, GE, LT, FALSE, Solver)
    from pysmt.typing import BOOL, INT
    return (And, BOOL, Equals, FALSE, GE, INT, Iff, Int, Ite, LT, Not,
            Or, Plus, Solver, Symbol, mo, random, time)
 
 
@app.cell
def _(mo):
    mo.md(r"""
    # Lógica Computacional — Conway's Game of Life como FSM
 
    **Objetivo.** Modelar uma variante finita do *Game of Life* como uma
    máquina de estados finita (FSM) em pySMT e verificar duas propriedades:
 
    1. nunca se alcança o *estado de erro* (todas as células normais mortas);
    2. nenhuma célula normal está *permanentemente* morta ou viva.
 """)