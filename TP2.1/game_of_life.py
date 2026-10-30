import marimo
 
__generated_with = "0.25.2"
app = marimo.App(width="medium")
 
 
@app.cell
def _():
    import marimo as mo
    import random
    import time
    import itertools
    from collections import deque
    from z3 import (Solver, Bool, BoolVal, And, Or, Not, If, Sum,
                    sat, unsat, is_true)
    return (And, Bool, BoolVal, If, Not, Or, Solver, Sum, deque, is_true,
            itertools, mo, random, sat, time, unsat)
 
 
@app.cell
def _(mo):
    mo.md(r"""
    # TP2 — Exercício 1: *Game of Life* finito como máquina de estados finita
 
    **Lógica Computacional 2026/27**
    
    # Enunciado
 
    O espaço de células usa índices $(i,j)\in\{0,\dots,N+1\}^2$, com $N>3$:
 
    | tipo | células | quantidade | comportamento |
    |---|---|---|---|
    | **normais** | $1\le i,j\le N$ | $N^2$ | evoluem pela regra **B3/S23** |
    | **iniciais** | $i=0$ ou $j=0$ | $2N+3$ | constantes; sorteadas no estado inicial (viva com probabilidade $p$) |
    | **finais** | não iniciais, com $i=N+1$ ou $j=N+1$ | $2N+1$ | constantemente mortas |
 
    - **Vizinhança:** $(i_0,j_0)$ e $(i_1,j_1)$ são vizinhas sse $\max(|i_0-i_1|,|j_0-j_1|)=1$. Toda a célula normal tem exatamente 8 vizinhos.
    - **Estado inicial:** as células normais com $i,j\le 3$ estão vivas e as restantes mortas.
    - **Estado de erro:** todas as células normais mortas.
    - **Transições:** o parâmetro `MODO` escolhe uma de duas relações.
        - `"async"`: em cada transição muda **uma e só uma** célula normal.
        - `"sync"`: em cada transição mudam **todas** as células normais em simultâneo.
 
    > **Nota sobre a contagem.** As células $(0,N+1)$ e $(N+1,0)$ têm um índice $0$ e outro $N+1$. A expressão *"finais que não são iniciais"* indica que são contadas como **iniciais**. Daí $2N+3$ iniciais e $2N+1$ finais. Para mudar esta convenção basta alterar as listas `iniciais`/`finais` em `GameOfLife.__init__`.
    """)
    return
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## Parâmetros
 
    Todos os parâmetros do problema estão nesta célula. `MODO` seleciona a relação de transição.
 
    A regra B/S também é um parâmetro (`NASCE`, `SOBREVIVE`). Assim é fácil estudar o impacto de pequenas modificações ao enunciado (ver a última secção).
    """)
    return

    @app.cell
def _():
    N         = 6                        # dimensão da grelha de células normais (N > 3)
    MODO      = "sync"                   # "sync": todas as células mudam; "async": uma e só uma muda
    P_VIVA    = 0.5                      # probabilidade de uma célula inicial estar viva
    SEED      = 2026                     # semente do sorteio das células iniciais
    NASCE     = {3}                      # regra B3 ...
    SOBREVIVE = {2, 3}                   # ... /S23
    VIVAS_T0  = lambda i, j: i <= 3 and j <= 3   # células normais vivas no estado inicial
    K_MAX     = 30                       # limite para BMC / k-indução
    return K_MAX, MODO, N, NASCE, P_VIVA, SEED, SOBREVIVE, VIVAS_T0

    @app.cell
def _(mo):
    mo.md(r"""
    ## 1. A máquina de estados finita
 
    **Variáveis de estado.** Um booleano $s_{i,j}$ por célula normal.
 
    **Células constantes.** As células iniciais e finais **não** são variáveis de estado. São constantes partilhadas por todos os estados:
 
    - uma célula final é `False`;
    - uma célula inicial pode ser concreta (`BoolVal`, sorteada) ou **simbólica** (uma constante `Bool` livre e rígida no tempo). No caso simbólico, uma só verificação cobre as $2^{2N+3}$ configurações possíveis.
 
    **Regra.** Seja $n_c(s)$ o número de vizinhos vivos da célula $c$ no estado $s$. Então
 
    $$\rho_c(s) \;\equiv\; (n_c(s)\in \mathrm{NASCE}) \;\lor\; (s_c \land n_c(s)\in\mathrm{SOBREVIVE}).$$
 
    **Estado inicial.** $I(s) \equiv \bigwedge_c\; s_c = [c_i\le 3 \land c_j\le 3]$.
 
    **Relação de transição.**
 
    | `MODO` | $T(s,s')$ |
    |---|---|
    | `sync` | $\bigwedge_c\; s'_c = \rho_c(s)$ |
    | `async` | $\bigvee_c \big(s'_c\neq s_c \;\land\; s'_c=\rho_c(s) \;\land\; \bigwedge_{d\neq c} s'_d = s_d\big) \;\lor\; \big(\bigwedge_c \rho_c(s)=s_c \;\land\; s'=s\big)$ |
 
    No modo `async` muda exatamente uma célula: uma das que **podem** mudar segundo a regra, escolhida de forma não determinista. Quando nenhuma célula pode mudar, o estado é estável e repete-se (*stuttering*). Sem isso, a relação teria estados de bloqueio e não seria total.
 
    **Estado de erro.** $E(s)\equiv \bigwedge_c \lnot s_c$.
    """)
    return 

    app.cell
def _(And, Bool, BoolVal, If, NASCE, Not, Or, SOBREVIVE, Sum, VIVAS_T0,
      is_true, random):
    class GameOfLife:
        def __init__(self, N, modo, iniciais=None, nasce=NASCE, sobrevive=SOBREVIVE, vivas0=VIVAS_T0):
            assert N > 3 and modo in ("sync", "async")
            self.N, self.modo, self.vivas0 = N, modo, vivas0
            self.nasce, self.sobrevive = set(nasce), set(sobrevive)
            R = range(N + 2)
            self.normais  = [(i, j) for i in range(1, N + 1) for j in range(1, N + 1)]
            self.iniciais = [(i, j) for i in R for j in R if i == 0 or j == 0]
            self.finais   = [(i, j) for i in R for j in R
                             if (i, j) not in self.iniciais and (i == N + 1 or j == N + 1)]
            if iniciais is None:               # simbólicas: todas as configurações de uma vez
                self.cte = {c: Bool(f"ini_{c[0]}_{c[1]}") for c in self.iniciais}
            else:                              # concretas (sorteadas)
                self.cte = {c: BoolVal(bool(iniciais[c])) for c in self.iniciais}
            self.cte.update({c: BoolVal(False) for c in self.finais})
            self.viz = {c: [(c[0] + a, c[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
                        for c in self.normais}
 
        # ---- variáveis de estado: uma cópia por instante ----
        def declare(self, k):
            return {c: Bool(f"c{c[0]}_{c[1]}_t{k}") for c in self.normais}
 
        def val(self, s, c):
            return s[c] if c in s else self.cte[c]
 
        def regra(self, s, c):
            n = Sum([If(self.val(s, d), 1, 0) for d in self.viz[c]])
            return Or(Or([n == v for v in self.nasce]),
                      And(s[c], Or([n == v for v in self.sobrevive])))
 
        def init(self, s):
            return And([s[c] == BoolVal(bool(self.vivas0(*c))) for c in self.normais])
 
        def trans(self, s, p):
            if self.modo == "sync":
                return And([p[c] == self.regra(s, c) for c in self.normais])
            muda = [And(p[c] != s[c], p[c] == self.regra(s, c),
                        And([p[d] == s[d] for d in self.normais if d != c]))
                    for c in self.normais]
            estavel = And(And([self.regra(s, c) == s[c] for c in self.normais]),
                          And([p[c] == s[c] for c in self.normais]))
            return Or(muda + [estavel])
 
        def erro(self, s):
            return And([Not(s[c]) for c in self.normais])
 
        # ---- visualização: '#'/'.' inicial viva/morta, 'X'/'-' normal viva/morta, ' ' final ----
        def grelha(self, m, s):
            linhas = []
            for i in range(self.N + 2):
                r = ""
                for j in range(self.N + 2):
                    c = (i, j)
                    if c in s:
                        r += "X" if is_true(m.eval(s[c], model_completion=True)) else "-"
                    elif c in self.finais:
                        r += " "
                    else:
                        r += "#" if is_true(m.eval(self.cte[c], model_completion=True)) else "."
                linhas.append(r)
            return linhas
 
 
    def mostra_traco(M, m, tr, cols=6):
        gs = [M.grelha(m, s) for s in tr]
        w = M.N + 2
        for b in range(0, len(gs), cols):
            bloco = gs[b:b + cols]
            print("   ".join(f"t={b + i}".ljust(w) for i in range(len(bloco))))
            for r in range(w):
                print("   ".join(g[r] for g in bloco))
            print()
 
 
    def sorteia_iniciais(N, p, seed):
        rng = random.Random(seed)
        R = range(N + 2)
        return {c: rng.random() < p for c in [(i, j) for i in R for j in R if i == 0 or j == 0]}
    return GameOfLife, mostra_traco, sorteia_iniciais