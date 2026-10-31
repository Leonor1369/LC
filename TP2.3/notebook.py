import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


with app.setup:
    import marimo as mo
    import time
    from pysmt.shortcuts import (
        Symbol, BV, TRUE, And, Or, Not, Implies, Ite, Equals, NotEquals, Solver,
        BVAdd, BVSub, BVMul, BVAnd, BVLShl, BVLShr, BVExtract, BVZExt, BVSExt,
        BVULT, BVULE, BVSGE, simplify, substitute,
    )
    from pysmt.typing import BVType

    # estados de controlo do CFA
    LOOP, EVEN, ODD, STOP, ERROR = range(5)
    NOME = {LOOP: "LOOP", EVEN: "EVEN", ODD: "ODD", STOP: "STOP", ERROR: "ERROR"}


@app.class_definition
class Mult:
    def __init__(self, n, com_sinal=False):
        self.n, self.com_sinal = n, com_sinal
        self.zero, self.um = BV(0, n), BV(1, n)

    def declare(self, i):
        # o pySMT guarda os símbolos por nome: a largura entra no nome para que
        # Mult(4) e Mult(8) (ou mudar o n no seletor) não colidam
        s = {'pc': Symbol(f'pc{i}', BVType(3))}
        for v in 'abxyz':
            s[v] = Symbol(f'{v}{i}_{self.n}', BVType(self.n))
        return s

    def esta(self, s, pc):
        return Equals(s['pc'], BV(pc, 3))

    def nao_neg(self, v):
        return BVSGE(v, self.zero) if self.com_sinal else TRUE()

    def init(self, s, extra=None):
        c = [self.esta(s, LOOP),
             Equals(s['x'], s['a']),
             Equals(s['y'], s['b']),
             Equals(s['z'], self.zero),
             self.nao_neg(s['a']),
             self.nao_neg(s['b'])]
        if extra is not None:
            c.append(extra(s))
        return And(c)

    # deteção explícita do overflow (os BitVec nunca o assinalam)

    def ovf_soma(self, s):
        # soma em n+1 bits; sem sinal o bit n é o carry
        n = self.n
        ext = BVSExt if self.com_sinal else BVZExt
        soma = BVAdd(ext(s['z'], 1), ext(s['x'], 1))
        if self.com_sinal:
            return NotEquals(BVExtract(soma, n, n), BVExtract(soma, n - 1, n - 1))
        return Equals(BVExtract(soma, n, n), BV(1, 1))

    def ovf_shift(self, s):
        x, n = s['x'], self.n
        if self.com_sinal:
            return NotEquals(BVExtract(x, n - 1, n - 1), BVExtract(x, n - 2, n - 2))
        return Equals(BVExtract(x, n - 1, n - 1), BV(1, 1))

    def guards(self, s):
        y = s['y']
        y0 = Equals(y, self.zero)
        par = Equals(BVAnd(y, self.um), self.zero)
        ovf_add, ovf_shl = self.ovf_soma(s), self.ovf_shift(s)
        return {
            'loop_stop': And(self.esta(s, LOOP), y0),
            'loop_even': And(self.esta(s, LOOP), Not(y0), par),
            'loop_odd':  And(self.esta(s, LOOP), Not(y0), Not(par)),
            'even_err':  And(self.esta(s, EVEN), ovf_shl),
            'even_loop': And(self.esta(s, EVEN), Not(ovf_shl)),
            'odd_err':   And(self.esta(s, ODD), ovf_add),
            'odd_loop':  And(self.esta(s, ODD), Not(ovf_add)),
            'stop':      self.esta(s, STOP),
            'err':       self.esta(s, ERROR),
        }

    def trans(self, s, p):
        g = self.guards(s)

        def upd(pc, **novos):
            # pc' = pc; x, y, z mudam para `novos[v]` ou mantêm-se
            return And(self.esta(p, pc),
                       *[Equals(p[v], novos.get(v, s[v])) for v in 'xyz'])

        return And(
            Equals(p['a'], s['a']),
            Equals(p['b'], s['b']),
            Or(
                And(g['loop_stop'], upd(STOP)),
                And(g['loop_even'], upd(EVEN)),
                And(g['loop_odd'],  upd(ODD)),
                And(g['even_err'],  upd(ERROR)),
                And(g['even_loop'], upd(LOOP, x=BVLShl(s['x'], self.um),
                                              y=BVLShr(s['y'], self.um))),
                And(g['odd_err'],   upd(ERROR)),
                And(g['odd_loop'],  upd(LOOP, y=BVSub(s['y'], self.um),
                                              z=BVAdd(s['z'], s['x']))),
                And(g['stop'],      upd(STOP)),
                And(g['err'],       upd(ERROR)),
            ),
        )

    def erro(self, s):
        return self.esta(s, ERROR)

    def terminal(self, s):
        return Or(self.esta(s, STOP), self.esta(s, ERROR))

    def W(self, v):
        # extensão para 2n bits: aritmética exata
        return BVSExt(v, self.n) if self.com_sinal else BVZExt(v, self.n)


@app.function
def resolve(*formulas):
    """Modelo das fórmulas, ou None se forem insatisfazíveis."""
    with Solver(name="z3") as solver:
        for f in formulas:
            solver.add_assertion(f)
        return solver.get_model() if solver.solve() else None


@app.function
def unroll(M, k):
    # k transições precisam de k+1 estados
    tr = [M.declare(i) for i in range(k + 1)]
    return tr, [M.trans(tr[i], tr[i + 1]) for i in range(k)]


@app.function
def valor(M, m, e):
    v = m.get_py_value(e)
    if M.com_sinal and v >= 2 ** (M.n - 1):
        v -= 2 ** M.n
    return v


@app.function
def mostra(M, m, tr):
    linhas = [f"{'t':>3} {'pc':>6} {'x':>6} {'y':>6} {'z':>6}   x*y+z"]
    for i, s in enumerate(tr):
        pc = m.get_py_value(s['pc'])
        x, y, z = (valor(M, m, s[v]) for v in 'xyz')
        linhas.append(f"{i:>3} {NOME[pc]:>6} {x:>6} {y:>6} {z:>6}   {x * y + z}")
        if pc in (STOP, ERROR):
            break
    return "\n".join(linhas)


@app.function
def kinducao(M, P, K, extra=None):
    for k in range(1, K + 1):
        # caso base: k estados a partir de I
        tr, T = unroll(M, k - 1)
        m = resolve(M.init(tr[0], extra), *T, Or([Not(P(s)) for s in tr]))
        if m is not None:
            return f"FALSO (contra-exemplo no caso base, k={k})", (m, tr)
        # passo indutivo
        tr, T = unroll(M, k)
        m = resolve(*T, *[P(s) for s in tr[:-1]], Not(P(tr[-1])))
        if m is None:
            return f"PROVADO com k={k}", None
    return f"INCONCLUSIVO até k={K}", None


@app.function
def invariantes(M):
    W = M.W
    P_mod = lambda s: Equals(BVAdd(BVMul(s['x'], s['y']), s['z']),
                             BVMul(s['a'], s['b']))
    P_exato = lambda s: And(
        Equals(BVAdd(BVMul(W(s['x']), W(s['y'])), W(s['z'])),
               BVMul(W(s['a']), W(s['b']))),
        M.nao_neg(s['x']), M.nao_neg(s['y']), M.nao_neg(s['z']))   # >= 0 só conta com sinal
    return P_mod, P_exato


@app.function
def bmc(M, mau, K, extra=None):
    """Primeiro k <= K em que `mau` é alcançável: (k, modelo, estados)."""
    with Solver(name="z3") as solver:
        tr = [M.declare(0)]
        solver.add_assertion(M.init(tr[0], extra))
        for k in range(K + 1):
            if k > 0:
                tr.append(M.declare(k))
                solver.add_assertion(M.trans(tr[k - 1], tr[k]))
            solver.push()
            solver.add_assertion(mau(tr[k]))
            if solver.solve():
                return k, solver.get_model(), tr
            solver.pop()
    return None


@app.function
def termina_J(M):
    """Invariante auxiliar J: pc <= 4, ODD => y ímpar, EVEN => y par e != 0."""
    impar = lambda s: Equals(BVAnd(s['y'], M.um), M.um)
    par = lambda s: Equals(BVAnd(s['y'], M.um), M.zero)
    return lambda s: And(BVULE(s['pc'], BV(4, 3)),
                         Implies(M.esta(s, ODD), impar(s)),
                         Implies(M.esta(s, EVEN), And(par(s), NotEquals(s['y'], M.zero))))


@app.function
def termina_V(M):
    """Variante V = 3y + r(pc), calculada em n+2 bits sem sinal (não há overflow)."""
    w = M.n + 2
    r_pc = lambda s: Ite(M.esta(s, LOOP), BV(2, w),
                         Ite(Or(M.esta(s, ODD), M.esta(s, EVEN)), BV(1, w), BV(0, w)))
    return lambda s: BVAdd(BVMul(BV(3, w), BVZExt(s['y'], 2)), r_pc(s))


@app.function
def decresce(M, J, V):
    """True se J(s) /\\ ~terminal(s) /\\ T(s,s') => V(s') < V(s) (fórmula insatisfazível)."""
    s0, s1 = M.declare(0), M.declare(1)
    return resolve(J(s0), Not(M.terminal(s0)), M.trans(s0, s1),
                   Not(BVULT(V(s1), V(s0)))) is None


@app.function
def sem_bloqueio(M, J):
    """True se todo o estado não terminal que satisfaz J tem alguma guarda ativa."""
    s0 = M.declare(0)
    return resolve(J(s0), Not(M.terminal(s0)),
                   Not(Or(list(M.guards(s0).values())))) is None


@app.cell
def _():
    mo.md(r"""
    # TP2 — Exercício 3: multiplicação de inteiros como SFOTS (BitVec, pySMT)

    ```
    INPUT a, b                        # n bits, a, b >= 0
    x, y, z = a, b, 0
    LOOP:  while y != 0:
    ODD:      if y & 1 == 1:  x, y, z = x, y-1, z+x      (overflow em z+x  → ERROR)
    EVEN:     else:           x, y, z = x<<1, y>>1, z    (overflow em x<<1 → ERROR)
    STOP:  assert z == a*b
    ```

    O autómato de controlo (CFA) tem cinco nodos:

    | nodo | ação | ligações |
    |---|---|---|
    | `LOOP` (inicial) | teste do ciclo | `y = 0` → `STOP`; `y ≠ 0` e par → `EVEN`; `y ≠ 0` e ímpar → `ODD` |
    | `EVEN` | `x, y = x << 1, y >> 1` | overflow em `x << 1` → `ERROR` (precedência); senão → `LOOP` |
    | `ODD` | `y, z = y − 1, z + x` | overflow em `z + x` → `ERROR` (precedência); senão → `LOOP` |
    | `STOP` | fim (`z = a·b`) | laço em si próprio |
    | `ERROR` | overflow | laço em si próprio |

    Os `BitVec` fazem aritmética módulo $2^n$ e **nunca assinalam overflow**, por isso a deteção é programada:

    - **sem sinal:** overflow em `z + x` se houver *carry*; overflow em `x << 1` se o bit $n-1$ de `x` for 1;
    - **com sinal:** overflow em `z + x` se os dois bits de topo da soma em $n+1$ bits forem diferentes;
      overflow em `x << 1` se os bits $n-1$ e $n-2$ de `x` forem diferentes (o sinal muda).
    """)
    return


@app.cell
def _():
    n_ui = mo.ui.dropdown(options=["8", "16"], value="8", label="n (bits)")
    sinal_ui = mo.ui.switch(label="com sinal")
    K_MAX = 6      # limite para a k-indução (invariante e segurança reforçada)
    mo.hstack([n_ui, sinal_ui], justify="start")
    return K_MAX, n_ui, sinal_ui


@app.cell
def _():
    mo.md(r"""
    ## 1. O SFOTS (classe `Mult`)

    - **Variáveis:** `pc` é um `BitVec(3)`; `a, b, x, y, z` são `BitVec(n)`. `a` e `b` não mudam.
    - **Estado inicial:** $pc=\mathrm{LOOP}\land x=a\land y=b\land z=0\land a\ge0\land b\ge0$
      (a condição $\ge0$ só tem efeito no modo com sinal).
    - **Transição $T(s,s')$:** disjunção das ligações do CFA, cada uma com a sua guarda e a atualização
      das variáveis (as não mencionadas mantêm-se). As guardas normais de `EVEN` e `ODD` excluem o caso
      de overflow, o que dá a precedência ao erro.
    - **Erro:** $pc=\mathrm{ERROR}$.
    """)
    return


@app.cell
def _(Mult, n_ui, sinal_ui):
    n = int(n_ui.value)
    M = Mult(n, sinal_ui.value)
    return M, n


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Execução de exemplo

    Uma execução concreta obtida por *unrolling* da relação de transição.
    """)
    return


@app.cell
def _(M, mostra, n, resolve, unroll):
    _a0, _b0 = (13, 11) if n >= 5 else (5, 3)
    _tr, _T = unroll(M, 4 * n)
    _m = resolve(M.init(_tr[0]), Equals(_tr[0]['a'], BV(_a0, n)),
                 Equals(_tr[0]['b'], BV(_b0, n)), *_T)
    _txt = ("sem traço" if _m is None
            else f"a={_a0}, b={_b0}, a*b={_a0 * _b0}\n\n" + mostra(M, _m, _tr))
    mo.md(f"```\n{_txt}\n```")
    return


@app.cell
def _():
    mo.md(r"""
    ## 2. O invariante $x\cdot y+z=a\cdot b$ por k-indução

    - **caso base:** nenhum traço com $k$ estados a partir de $I$ viola $P$;
    - **passo:** $P(s_0)\land\cdots\land P(s_{k-1})\land T(s_0,s_1)\land\cdots\land T(s_{k-1},s_k)\Rightarrow P(s_k)$.

    Verifica-se em duas versões: **módulo $2^n$** (aritmética `BitVec` usual) e **exata**, em $2n$ bits
    (`BVZExt`, ou `BVSExt` com sinal, e $x,y,z\ge0$ para excluir estados inalcançáveis com $y<0$).
    Com $k=1$ o passo falha: estados inalcançáveis como $pc=\mathrm{EVEN}$ com $y$ ímpar satisfazem $P$
    mas o sucessor não. Com $k=2$ o predecessor obriga a $y$ par.
    """)
    return


@app.cell
def _(K_MAX, M, invariantes, kinducao):
    P_mod, P_exato = invariantes(M)
    _t0 = time.time()
    _r_mod = kinducao(M, P_mod, K_MAX)[0]
    _r_ex = kinducao(M, P_exato, K_MAX)[0]
    mo.md(f"""
    * invariante módulo $2^n$: **{_r_mod}**
    * invariante exato (2n bits): **{_r_ex}**

    ({time.time() - _t0:.1f}s). Em `STOP` tem-se $y=0$, logo $z=a\\cdot b$: a asserção final é válida sempre que se chega a `STOP`.
    """)
    return (P_exato,)


@app.cell
def _():
    mo.md(r"""
    ## 3. Segurança com $a<2^{n/2}\land b<2^{n/2}$

    Primeiro mostra-se, por BMC, que **sem** a condição o erro é alcançável. Depois prova-se
    $\mathsf G\,\lnot\mathrm{ERROR}$ **com** a condição, de duas formas:

    - **diretamente** com $P\equiv\lnot\mathrm{ERROR}\land a,b<2^{n/2}$ (como $a,b$ são constantes,
      a condição inclui-se em $P$);
    - com a propriedade **reforçada** $P^+\equiv\lnot\mathrm{ERROR}\land a,b<2^{n/2}\land xy+z=ab$:
      em `ODD`, $y\ge1$ e $x+z\le xy+z=ab<2^n$ (sem *carry*); em `EVEN`, $y\ge2$ e $2x\le xy\le ab<2^n$.
    """)
    return


@app.cell
def _(M, bmc, mostra, n, valor):
    _r = bmc(M, M.erro, 4 * n)
    if _r is None:
        _txt = f"ERROR não alcançável até {4 * n} transições"
    else:
        _k, _m, _tr = _r
        _txt = (f"SEM restrição: ERROR alcançável em {_k} transições, "
                f"com a={valor(M, _m, _tr[0]['a'])}, b={valor(M, _m, _tr[0]['b'])}\n\n"
                + mostra(M, _m, _tr))
    mo.md(f"```\n{_txt}\n```")
    return


@app.cell
def _(K_MAX, M, P_exato, kinducao, n):
    _h = BV(2 ** (n // 2), n)
    pequenos = lambda s: And(BVULT(s['a'], _h), BVULT(s['b'], _h))
    seguro = lambda s: And(Not(M.erro(s)), pequenos(s))
    seguro_r = lambda s: And(seguro(s), P_exato(s))

    _t0 = time.time()
    _r_ref = kinducao(M, seguro_r, K_MAX, extra=pequenos)[0]
    _t1 = time.time() - _t0
    _t0 = time.time()
    _r_dir = kinducao(M, seguro, 4 * n + 2, extra=pequenos)[0]
    _t2 = time.time() - _t0
    mo.md(f"""
    * reforçada com o invariante exato: **{_r_ref}** ({_t1:.1f}s)
    * direta (sem reforço): **{_r_dir}** ({_t2:.1f}s)

    A prova direta só tem sucesso quando $k$ atinge o comprimento do caminho mais longo, perto de $4n$.
    Com o reforço por $xy+z=ab$ basta $k=2$.
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## 4. Terminação (propriedade de animação)

    Para quaisquer $a,b$: $\mathsf F\,(pc=\mathrm{STOP}\lor pc=\mathrm{ERROR})$. Parar em `ERROR` também é terminar.

    Usa-se uma **variante** $V(s)=3\,y+r(pc)$, com $r(\mathrm{LOOP})=2$, $r(\mathrm{EVEN})=r(\mathrm{ODD})=1$,
    $r(\mathrm{STOP})=r(\mathrm{ERROR})=0$, calculada em $n+2$ bits sem sinal (não há overflow e $V\ge0$). Prova-se:

    - **(a)** o invariante auxiliar $J\equiv pc\le4\land(pc=\mathrm{ODD}\to y\text{ ímpar})\land(pc=\mathrm{EVEN}\to y\text{ par}\ne0)$, por k-indução;
    - **(b)** $J(s)\land\lnot\mathrm{term}(s)\land T(s,s')\to V(s')<V(s)$;
    - **(c)** ausência de bloqueio: todo o estado não terminal que satisfaz $J$ tem sucessor;
    - **(d)** como confirmação, um BMC procura um traço de $4n$ transições que evite `STOP` e `ERROR`.
    """)
    return


@app.cell
def _(M, decresce, kinducao, n, resolve, sem_bloqueio, termina_J, termina_V, unroll):
    _J, _V = termina_J(M), termina_V(M)
    _t0 = time.time()
    _ra = kinducao(M, _J, 3)[0]
    _rb = "PROVADO" if decresce(M, _J, _V) else "FALSO"
    _rc = "PROVADO" if sem_bloqueio(M, _J) else "FALSO"
    if n <= 8:
        _tr, _T = unroll(M, 4 * n)
        _rd = "PROVADO" if resolve(M.init(_tr[0]), *_T,
                                   *[Not(M.terminal(s)) for s in _tr]) is None else "FALSO"
    else:
        _rd = "(omitido para n > 8)"
    mo.md(f"""
    * (a) invariante auxiliar J: **{_ra}**
    * (b) V decresce estritamente fora dos estados terminais: **{_rb}**
    * (c) ausência de *deadlock*: **{_rc}**
    * (d) BMC: nenhum traço com {4 * n} transições evita `STOP`/`ERROR`: **{_rd}**

    ({time.time() - _t0:.1f}s). Com $V\\ge0$ bem-fundado, todo o traço termina em no máximo $V(s_0)$ passos.
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## 5. Validação exaustiva (sem SMT)

    O programa é simulado em Python para **todos** os pares $(a,b)$ com $n=8$ e a mesma semântica de overflow.
    Verifica-se que o invariante nunca é violado, quais os pares que terminam em `ERROR` e o máximo de passos.
    """)
    return


@app.cell
def _():
    def simula(a, b, n, com_sinal=False):
        lim = (1 << (n - 1)) if com_sinal else (1 << n)      # valores admissíveis (não negativos)
        pc, x, y, z = LOOP, a, b, 0
        passos, inv_ok = 0, True
        while pc not in (STOP, ERROR):
            inv_ok &= (x * y + z == a * b)
            if pc == LOOP:
                pc = STOP if y == 0 else (EVEN if y % 2 == 0 else ODD)
            elif pc == EVEN:
                if 2 * x >= lim:
                    pc = ERROR
                else:
                    x, y, pc = 2 * x, y // 2, LOOP
            else:
                if x + z >= lim:
                    pc = ERROR
                else:
                    y, z, pc = y - 1, z + x, LOOP
            passos += 1
        return pc, z, passos, inv_ok


    _nn = 8
    _linhas = []
    for _sinal in (False, True):
        _gama = range(1 << (_nn - 1)) if _sinal else range(1 << _nn)
        _res = [(a, b, *simula(a, b, _nn, _sinal)) for a in _gama for b in _gama]
        _erros = sum(1 for r in _res if r[2] == ERROR)
        _errado = sum(1 for r in _res if r[2] == STOP and r[3] != r[0] * r[1])
        _viol = sum(1 for r in _res if not r[5])
        _peq = sum(1 for r in _res if r[2] == ERROR and r[0] < 2 ** (_nn // 2) and r[1] < 2 ** (_nn // 2))
        _linhas.append(f"| {'com' if _sinal else 'sem'} sinal | {len(_res)} | {_erros} | {_errado} | "
                       f"{_viol} | {max(r[4] for r in _res)} | {_peq} |")
    mo.md("| n=8 | pares | ERROR | STOP com z≠ab | invariante violado | máx. passos | ERROR com a,b<2^(n/2) |\n"
          "|---|---|---|---|---|---|---|\n" + "\n".join(_linhas))
    return


@app.cell
def _():
    mo.md(r"""
    ## 6. Conclusões

    | alínea | resultado |
    |---|---|
    | 1. SFOTS | variáveis $pc,a,b,x,y,z$; estado inicial $pc=\mathrm{LOOP}$, $x=a$, $y=b$, $z=0$; 9 ligações com precedência das de erro; estado de erro $pc=\mathrm{ERROR}$ |
    | 2. $xy+z=ab$ | invariante provado por k-indução (secção 2); $k=1$ falha por estados inalcançáveis |
    | 3. segurança com $a,b<2^{n/2}$ | provada, diretamente ou reforçando com o invariante; sem a condição o erro é alcançável |
    | 4. terminação | variante $V=3y+r(pc)$ com invariante auxiliar e ausência de bloqueio (secção 4) |

    Os valores de $k$ e os resultados `PROVADO`/`FALSO` das secções 2 a 4 são calculados pelo solver para o
    $n$ e o modo (com ou sem sinal) escolhidos no topo.

    ## 7. Impacto de pequenas modificações nos requisitos

    | modificação | alteração | efeito |
    |---|---|---|
    | overflow **com sinal** | ligar o interruptor "com sinal" | a condição $a,b<2^{n/2}$ pode deixar de garantir segurança, porque o produto pode atingir $2^{n-1}$, que já muda o sinal. A extensão exata passa a usar `BVSExt` |
    | condição mais fraca $a\cdot b<2^n$ | `pequenos` com `BVULT(BVMul(W(a), W(b)), 2**n)` | o argumento do reforço só usa $ab<2^n$ |
    | $n$ maior (16, 32) | dropdown | as secções 2 e 3 são omitidas (multiplicações de $n$ e $2n$ bits pesadas demais para o solver); o exemplo, o BMC do erro e a terminação (a)–(c) continuam a correr |
    | outra ordem de teste | `guards` e `trans` | o invariante e a variante mantêm-se; com sinal, `y > 0` é necessário para a terminação |
    | remover a precedência do erro | tirar `Not(ovf…)` das guardas normais | aparecem traços que continuam após o overflow com valores truncados |
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## 8. Testes

    Os testes estão fora do notebook, em `test_mult.py`, e importam daqui a classe `Mult` e as funções
    de verificação (declaradas com `@app.class_definition` e `@app.function`):

    ```
    pip install pytest
    pytest test_mult.py -v
    ```
    """)
    return


if __name__ == "__main__":
    app.run()