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
    N         = 16                     
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
 
 
    def mostra_traco(M, m, tr, cols=16):
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

    app.cell
def _(GameOfLife, MODO, N, P_VIVA, SEED, Solver, mostra_traco,
      sorteia_iniciais):
    INICIAIS = sorteia_iniciais(N, P_VIVA, SEED)
    M_conc = GameOfLife(N, MODO, INICIAIS)     # células iniciais sorteadas
    M_simb = GameOfLife(N, MODO)               # células iniciais simbólicas (todas as configurações)
 
    print(f"N={N}  modo={MODO}  normais={len(M_conc.normais)}  iniciais={len(M_conc.iniciais)}  finais={len(M_conc.finais)}")
    print("Estado inicial com as células iniciais sorteadas:\n")
    _s0 = M_conc.declare(0); _sol = Solver(); _sol.add(M_conc.init(_s0)); _sol.check()
    mostra_traco(M_conc, _sol.model(), [_s0])
    return INICIAIS, M_conc, M_simb
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Métodos de verificação
 
    - **BMC** (*bounded model checking*): procura um traço $s_0\dots s_k$ com $I(s_0)\land\bigwedge T(s_i,s_{i+1})\land\lnot P(s_k)$. Se o encontra, é um **contra-exemplo**.
    - **k-indução com caminhos simples.** O passo indutivo exige estados $s_0,\dots,s_k$ distintos dois a dois. Acrescenta-se o teste do **diâmetro de recorrência**: se não existe nenhum caminho simples com $k$ estados a partir de $I$, todos os estados alcançáveis já foram visitados pelo caso base. Com estas duas condições, a k-indução é **completa** para sistemas finitos: termina sempre com prova ou contra-exemplo.
    - **Laços (*lassos*).** Uma propriedade de animação como $\mathsf{GF}\,c$ é refutada por um traço finito que fecha um ciclo, $s_0\dots s_l\dots s_k$ com $s_k=s_l$. Esse traço representa uma execução infinita.
    """)
    return
 
 
@app.cell
def _(And, Not, Or, Solver, is_true, sat, unsat):
    def unroll(M, k):
        tr = [M.declare(i) for i in range(k + 1)]
        return tr, [M.trans(tr[i], tr[i + 1]) for i in range(k)]
 
 
    def distintos(M, a, b):
        return Or([a[c] != b[c] for c in M.normais])
 
 
    def bmc(M, bad, K):
        # Devolve (k, modelo, traço) do contra-exemplo mais curto até K, ou None.
        s = Solver(); tr = [M.declare(0)]; s.add(M.init(tr[0]))
        for k in range(K + 1):
            if k > 0:
                tr.append(M.declare(k)); s.add(M.trans(tr[k - 1], tr[k]))
            s.push(); s.add(bad(tr[k]))
            if s.check() == sat:
                return k, s.model(), tr
            s.pop()
        return None
 
 
    def kinducao(M, P, K):
        # k-indução com caminhos simples + diâmetro de recorrência (completa para FSM).
        for k in range(1, K + 1):
            tr, T = unroll(M, k - 1)
            s = Solver(); s.add(M.init(tr[0]), *T, Or([Not(P(x)) for x in tr]))
            if s.check() == sat:
                return "FALSO", k
            s = Solver(); s.add(M.init(tr[0]), *T,
                                *[distintos(M, tr[i], tr[j]) for i in range(k) for j in range(i + 1, k)])
            if s.check() == unsat:
                return "PROVADO (diâmetro de recorrência)", k
            tr, T = unroll(M, k)
            s = Solver(); s.add(*T, *[P(x) for x in tr[:-1]], Not(P(tr[-1])),
                                *[distintos(M, tr[i], tr[j]) for i in range(k + 1) for j in range(i + 1, k + 1)])
            if s.check() == unsat:
                return "PROVADO (passo indutivo)", k
        return "INCONCLUSIVO", K
 
 
    def laco(M, K, celulas=None):
        # Laço s0..sl..sk (sk = sl) em que alguma célula normal é constante no ciclo sl..sk.
        celulas = celulas or M.normais
        for k in range(1, K + 1):
            tr, T = unroll(M, k)
            s = Solver(); s.add(M.init(tr[0]), *T)
            ops = []
            for l in range(k):
                fecha = And([tr[k][c] == tr[l][c] for c in M.normais])
                cte = Or([And([tr[i][c] == tr[l][c] for i in range(l, k)]) for c in celulas])
                ops.append(And(fecha, cte))
            s.add(Or(ops))
            if s.check() == sat:
                m = s.model()
                l = next(l for l in range(k) if is_true(m.eval(ops[l], model_completion=True)))
                ev = lambda e: is_true(m.eval(e, model_completion=True))
                ctes = [c for c in celulas if all(ev(tr[i][c] == tr[l][c]) for i in range(l, k))]
                vivas = [c for c in ctes if ev(tr[l][c])]
                mortas = [c for c in ctes if not ev(tr[l][c])]
                return dict(k=k, l=l, vivas=vivas, mortas=mortas, modelo=m, traco=tr)
        return None
    return bmc, kinducao, laco
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Propriedade 1: "nunca se alcança o estado de erro"
 
    Esta é uma propriedade de segurança, $\mathsf{G}\,\lnot E$. Analisam-se dois casos:
 
    - **(a)** com as células iniciais **sorteadas** (`SEED`), como no enunciado;
    - **(b)** para **todas** as configurações das células iniciais (simbólicas). A propriedade só é *universalmente* verdadeira se nenhuma configuração leva ao erro.
    """)
    return
 
 
@app.cell
def _(K_MAX, M_conc, MODO, Not, bmc, kinducao, mostra_traco, time):
    def propriedade1(M, nome):
        t0 = time.time()
        r = bmc(M, M.erro, K_MAX)
        if r:
            k, m, tr = r
            print(f"[{nome}] G ¬erro é FALSA: o erro é alcançado em {k} transições ({time.time()-t0:.1f}s)\n")
            mostra_traco(M, m, tr[:k + 1])
            return False
        res = kinducao(M, lambda s: Not(M.erro(s)), K_MAX)
        print(f"[{nome}] sem contra-exemplo até K={K_MAX}; k-indução: {res}  ({time.time()-t0:.1f}s)")
        return res[0].startswith("PROVADO")
 
    print(f"===== modo {MODO} =====")
    p1_conc = propriedade1(M_conc, "(a) células iniciais sorteadas")
    return (propriedade1,)
 
 
@app.cell
def _(M_simb, propriedade1):
    p1_simb = propriedade1(M_simb, "(b) todas as configurações de células iniciais")
    return
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Propriedade 2: "nenhuma célula normal está permanentemente morta ou permanentemente viva"
 
    A frase admite duas leituras formais:
 
    1. **Leitura LTL (animação).** Em todos os traços, cada célula muda infinitas vezes:
       $$\textstyle\bigwedge_c \big(\mathsf{GF}\,s_c \land \mathsf{GF}\,\lnot s_c\big).$$
       Um contra-exemplo é um laço em que alguma célula $c$ é constante no ciclo, ou seja, um traço que satisfaz $\mathsf{FG}\,s_c$ ou $\mathsf{FG}\,\lnot s_c$.
    2. **Leitura "desde o início".** Nenhuma célula tem o mesmo valor em **todos** os estados alcançáveis:
       $$\textstyle\bigwedge_c \big(\mathsf{EF}\,s_c \land \mathsf{EF}\,\lnot s_c\big).$$

 
    No modo `async` o não-determinismo levanta uma questão de **justiça** (*fairness*): um laço pode ignorar indefinidamente uma célula que podia mudar. Indica-se por isso se o ciclo encontrado é um **estado estável**. Um estado estável é um laço justo, onde nenhuma célula pode mudar.
    """)
    return
 
 
@app.cell
def _(K_MAX, M_conc, laco, mostra_traco, time):
    def propriedade2_ltl(M, nome):
        t0 = time.time()
        r = laco(M, K_MAX)
        if r is None:
            print(f"[{nome}] nenhum laço contra-exemplo até K={K_MAX}")
            return None
        k, l, m, tr = r["k"], r["l"], r["modelo"], r["traco"]
        estavel = (k - l == 1)
        print(f"[{nome}] FALSA: laço s{l}..s{k} (s{k} = s{l}), ciclo de comprimento {k-l}"
              f"{' — estado ESTÁVEL (laço justo)' if estavel else ''}  ({time.time()-t0:.1f}s)")
        print(f"   permanentemente vivas no ciclo : {r['vivas']}")
        print(f"   permanentemente mortas no ciclo: {r['mortas']}\n")
        mostra_traco(M, m, tr[:k + 1])
        return r
 
    L2 = propriedade2_ltl(M_conc, "(a) células iniciais sorteadas")
    return (propriedade2_ltl,)
 
 
@app.cell
def _(K_MAX, M_conc, MODO, Solver, distintos, sat, time, unroll, unsat):
    def diametro_recorrencia(M, K):
        # Menor k tal que não existe caminho simples com k estados a partir de I.
        # Nesse caso todos os estados alcançáveis aparecem nos primeiros k-1 estados.
        for k in range(1, K + 1):
            tr, T = unroll(M, k - 1)
            s = Solver(); s.add(M.init(tr[0]), *T,
                                *[distintos(M, tr[i], tr[j]) for i in range(k) for j in range(i + 1, k)])
            if s.check() == unsat:
                return k
        return None
 
 
    def propriedade2_inicio(M):
        # Para cada célula: existe estado alcançável com valor oposto ao inicial?
        # BMC incremental partilhado por todas as células: em cada profundidade k
        # testam-se só as células para as quais ainda não se encontrou testemunha.
        pendentes = {c: bool(M.vivas0(*c)) for c in M.normais}
        s = Solver(); tr = [M.declare(0)]; s.add(M.init(tr[0]))
        for k in range(K_MAX + 1):
            if k > 0:
                tr.append(M.declare(k)); s.add(M.trans(tr[k - 1], tr[k]))
            for c in list(pendentes):
                s.push(); s.add(tr[k][c] == (not pendentes[c]))
                if s.check() == sat:
                    del pendentes[c]
                s.pop()
            if not pendentes:
                return [], [], []
        # As células que restam nunca mudaram até K_MAX. Se o diâmetro de
        # recorrência D <= K_MAX + 1, o BMC já percorreu todos os estados
        # alcançáveis e isso prova que essas células são constantes.
        D = diametro_recorrencia(M, K_MAX + 1)
        if D is None:
            return [], [], list(pendentes)
        sempre_viva = [c for c, v0 in pendentes.items() if v0]
        sempre_morta = [c for c, v0 in pendentes.items() if not v0]
        return sempre_viva, sempre_morta, []
 
    _t0 = time.time()
    _sv, _sm, _inc = propriedade2_inicio(M_conc)
    print(f"Leitura 'desde o início' (modo {MODO}, células iniciais sorteadas)  ({time.time()-_t0:.1f}s)")
    print("   vivas em todos os estados alcançáveis :", _sv)
    print("   mortas em todos os estados alcançáveis:", _sm)
    if _inc: print("   inconclusivas:", _inc)
    print("   => propriedade", "FALSA" if (_sv or _sm) else ("VERDADEIRA" if not _inc else "INCONCLUSIVA"))
    return (propriedade2_inicio,)
 
 
@app.cell
def _(M_simb, propriedade2_ltl):
    L2s = propriedade2_ltl(M_simb, "(b) células iniciais simbólicas")
    return
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Os dois modos lado a lado
 
    Repete-se a análise para `sync` e `async` com o mesmo `N` e as mesmas células iniciais sorteadas.
    """)
    return
 
 
@app.cell
def _(GameOfLife, INICIAIS, K_MAX, N, Not, bmc, kinducao, laco,
      propriedade2_inicio):
    _linhas = []
    for _modo in ("sync", "async"):
        _Mc = GameOfLife(N, _modo, INICIAIS); _Ms = GameOfLife(N, _modo)
        _rc = bmc(M=_Mc, bad=_Mc.erro, K=K_MAX)
        _p1c = f"FALSA (erro em {_rc[0]})" if _rc else kinducao(_Mc, lambda s: Not(_Mc.erro(s)), K_MAX)[0]
        _rs = bmc(M=_Ms, bad=_Ms.erro, K=K_MAX)
        _p1s = f"FALSA (erro em {_rs[0]})" if _rs else kinducao(_Ms, lambda s: Not(_Ms.erro(s)), K_MAX)[0]
        _l = laco(M=_Mc, K=K_MAX)
        _p2 = (f"FALSA (laço s{_l['l']}..s{_l['k']}, {len(_l['vivas'])} vivas / {len(_l['mortas'])} mortas constantes)"
               if _l else "sem contra-exemplo")
        _sv, _sm, _inc = propriedade2_inicio(M=_Mc)
        _p2b = ("FALSA (sempre vivas %s, sempre mortas %s)" % (_sv, _sm)) if (_sv or _sm) else \
               ("VERDADEIRA" if not _inc else "INCONCLUSIVA")
        _linhas.append((_modo, _p1c, _p1s, _p2, _p2b))
 
    for _r in _linhas:
        print(f"== {_r[0]} ==")
        print(f"   P1, células iniciais sorteadas : {_r[1]}")
        print(f"   P1, todas as configurações     : {_r[2]}")
        print(f"   P2, leitura LTL                : {_r[3]}")
        print(f"   P2, leitura 'desde o início'   : {_r[4]}")
    return
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## 6. Validação independente por enumeração explícita
 
    Este verificador não usa o Z3. Os estados são *bitmasks* das $N^2$ células normais e calculam-se por BFS todos os estados alcançáveis. O resultado tem de coincidir com o do Z3.
 
    Para $N=4$ e o modo `sync` percorrem-se também **todas** as $2^{2N+3}=2048$ configurações das células iniciais.
    """)
    return
 
 
@app.cell
def _(INICIAIS, N, NASCE, SOBREVIVE, VIVAS_T0, deque, itertools):
    def explicito(N, iniciais, modo, nasce=NASCE, sobrevive=SOBREVIVE, vivas0=VIVAS_T0):
        normais = [(i, j) for i in range(1, N + 1) for j in range(1, N + 1)]
        idx = {c: k for k, c in enumerate(normais)}
        vizn, cte = [], []
        for (i, j) in normais:
            vs = [(i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
            vizn.append([idx[v] for v in vs if v in idx])
            cte.append(sum(1 for v in vs if iniciais.get(v, False)))      # finais contam 0
        s0 = sum(1 << idx[c] for c in normais if vivas0(*c))
 
        def regra(s, k):
            n = cte[k] + sum((s >> d) & 1 for d in vizn[k])
            return 1 if (n in nasce or (((s >> k) & 1) and n in sobrevive)) else 0
 
        def succ(s):
            if modo == "sync":
                return [sum(regra(s, k) << k for k in range(N * N))]
            out = [s ^ (1 << k) for k in range(N * N) if regra(s, k) != (s >> k) & 1]
            return out or [s]
 
        dist = {s0: 0}; q = deque([s0])
        while q:
            s = q.popleft()
            for t in succ(s):
                if t not in dist:
                    dist[t] = dist[s] + 1; q.append(t)
        sempre_viva = [normais[k] for k in range(N * N) if all((s >> k) & 1 for s in dist)]
        sempre_morta = [normais[k] for k in range(N * N) if all(not (s >> k) & 1 for s in dist)]
        return dict(alcancaveis=len(dist), erro=dist.get(0), sempre_viva=sempre_viva, sempre_morta=sempre_morta)
 
    for _modo in ("sync", "async"):
        if _modo == "async" and N > 4:
            print("async: enumeração explícita omitida para N > 4 (2^(N^2) estados)"); continue
        _r = explicito(N, INICIAIS, _modo)
        print(f"{_modo:5}: {_r['alcancaveis']} estados alcançáveis; erro em "
              f"{'nunca' if _r['erro'] is None else str(_r['erro']) + ' transições'}; "
              f"sempre vivas {_r['sempre_viva']}; sempre mortas {_r['sempre_morta']}")
 
    if N == 4:
        _ini = [(i, j) for i in range(N + 2) for j in range(N + 2) if i == 0 or j == 0]
        _cnt, _dmin = 0, None
        for _bits in itertools.product((0, 1), repeat=len(_ini)):
            _e = explicito(N, dict(zip(_ini, _bits)), "sync")["erro"]
            if _e is not None:
                _cnt += 1; _dmin = _e if _dmin is None else min(_dmin, _e)
        print(f"\nsync, todas as {2**len(_ini)} configurações: o erro é alcançável em {_cnt} "
              f"({100*_cnt/2**len(_ini):.1f}%), no mínimo em {_dmin} transições")
    return
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## 7. Conclusões
 
    Resultados obtidos com $N=4$ e `SEED = 2026` (confirmados pela enumeração explícita da secção 6):
 
    | | `sync` | `async` |
    |---|---|---|
    | **P1** (sorteadas, `SEED=2026`) | **verdadeira**: provada por k-indução (diâmetro de recorrência). A trajetória é determinista e cai num ponto fixo. | **falsa**: o erro é alcançado em 9 transições, matando as células uma a uma |
    | **P1** (todas as configurações) | **falsa**: há configurações (10,1% para $N=4$) que levam ao erro em 3 transições | **falsa** |
    | **P2**, leitura LTL | **falsa**: o sistema entra num ponto fixo ($t=11$), e todas as células ficam constantes | **falsa**: há traços que chegam a um estado estável (um laço justo) em 5 transições |
    | **P2**, leitura "desde o início" | **falsa**: $(4,1)$ e $(4,4)$ estão mortas em todos os estados alcançáveis | **verdadeira**: cada célula normal está viva nalgum estado alcançável e morta noutro (confirmado pela enumeração explícita dos 65 144 estados alcançáveis) |
 
    Com $N=6$ (valor por omissão) as conclusões são as mesmas: no modo `sync`, P1 fica provada para o sorteio (diâmetro de recorrência 11), é falsa para todas as configurações (erro em 3 transições), há ponto fixo em $t=9$ e 20 células normais nunca nascem; no modo `async`, o erro é alcançado em 9 transições, há um estado estável em 5 transições e a leitura "desde o início" da P2 é verdadeira. A enumeração explícita do modo `sync` confirma os 10 estados alcançáveis e as mesmas 20 células sempre mortas.
 
    - **P1 no modo `async`.** Como cada transição escolhe *qual* célula muda, o sistema pode sempre escolher matar uma célula com menos de 2 vizinhos vivos. Assim é muito mais fácil chegar ao erro do que no modo síncrono.
    - **P1 depende das células iniciais.** Com o sorteio `SEED=2026` o erro nunca é alcançado no modo `sync`, mas a versão simbólica mostra que isto não é verdade para todos os sorteios: basta uma configuração desfavorável das células iniciais.
    - **P2.** Num sistema finito e determinista (`sync`), todo o traço acaba num ciclo, e com estas fronteiras o ciclo é quase sempre um ponto fixo. Por isso a leitura LTL é falsa. Algumas células junto às células finais (mortas) nunca chegam a nascer, o que torna falsa também a leitura "desde o início". No modo `async` o não-determinismo permite alcançar valores diferentes em cada célula, mas *cada traço individual* acaba igualmente num estado estável.
    - **Contagem das células.** O enunciado indica $2N+1$ iniciais e $2N+3$ finais. Seguimos a convenção do notebook do professor ($2N+3$ iniciais e $2N+1$ finais), contando $(0,N+1)$ e $(N+1,0)$ como iniciais. Esta escolha só muda o valor de duas células da fronteira.
    - **Dimensão.** O enunciado pede $N>16$. Com $N=17$ o modo `sync` continua tratável, mas o modo `async` tem $2^{289}$ estados e 289 escolhas por passo. Por isso a análise completa usa $N=4$ e $N=6$, como no notebook do professor.
    """)
    return
 
 
@app.cell
def _(mo):
    mo.md(r"""
    ## 8. Impacto de pequenas modificações nos requisitos
 
    O código foi escrito para que cada alteração plausível do enunciado seja **uma linha** na célula de parâmetros ou em `GameOfLife`:
 
    | modificação | onde | efeito esperado |
    |---|---|---|
    | outra regra (ex.: *HighLife* B36/S23, *Seeds* B2/S) | `NASCE`, `SOBREVIVE` | o modelo não muda. Com B2/S, nenhuma célula sobrevive e o erro torna-se muito mais provável |
    | outra configuração inicial | `VIVAS_T0` | só muda `init` |
    | outra probabilidade $p$ | `P_VIVA` | só afeta o caso (a). O caso (b), simbólico, já cobre todas as configurações |
    | células finais vivas, ou aleatórias como as iniciais | `self.cte` para `finais` | aumenta o número de vizinhos vivos junto à fronteira. A análise é a mesma |
    | grelha toroidal (sem células iniciais/finais) | `self.viz` com índices `mod N` | o sistema fica fechado. Desaparecem as constantes e a simetria aumenta |
    | $k$ células a mudar por transição (em vez de 1 ou todas) | `trans`: `AtMost`/`AtLeast` sobre as células que mudam | interpola entre `async` e `sync` |
    | justiça forte no modo `async` | `laco`: exigir que cada célula *habilitada* mude no ciclo | elimina contra-exemplos artificiais à P2. Os estados estáveis continuam a ser contra-exemplos |
    | N maior | `N` | o modo `sync` escala bem (BMC/k-indução em segundos para N ≤ 16). O modo `async` cresce depressa, porque o espaço de estados é $2^{N^2}$ e há $N^2$ escolhas por passo. Para N ≥ 16 a prova de P1, quando verdadeira, pode exigir um invariante reforçado ou IC3/PDR em vez de caminhos simples |
    """)
    return
 
 
if __name__ == "__main__":
    app.run()
 