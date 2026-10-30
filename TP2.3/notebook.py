import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import time
    from pysmt.shortcuts import (
        Symbol, BV, TRUE, And, Or, Not, Implies, Ite, Equals, NotEquals, Solver,
        BVAdd, BVSub, BVMul, BVAnd, BVLShl, BVLShr, BVExtract, BVZExt, BVSExt,
        BVULT, BVULE, BVSGE,
    )
    from pysmt.typing import BVType

    return (
        And,
        BV,
        BVAdd,
        BVAnd,
        BVExtract,
        BVLShl,
        BVLShr,
        BVMul,
        BVSExt,
        BVSGE,
        BVSub,
        BVType,
        BVULE,
        BVULT,
        BVZExt,
        Equals,
        Implies,
        Ite,
        Not,
        NotEquals,
        Or,
        Solver,
        Symbol,
        TRUE,
        mo,
        time,
    )


@app.cell
def _(mo):
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

    O autómato de controlo tem cinco nodos:

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
def _(mo):
    n_ui = mo.ui.dropdown(options=["8", "16"], value="8", label="n (bits)")
    sinal_ui = mo.ui.switch(label="com sinal")
    K_MAX = 6      # limite para a k-indução (invariante e segurança reforçada)
    mo.hstack([n_ui, sinal_ui], justify="start")
    return K_MAX, n_ui, sinal_ui


@app.cell
def _():
    LOOP, EVEN, ODD, STOP, ERROR = range(5)
    NOME = {LOOP: "LOOP", EVEN: "EVEN", ODD: "ODD", STOP: "STOP", ERROR: "ERROR"}
    return ERROR, EVEN, LOOP, NOME, ODD, STOP


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. O SFOTS (classe `Mult`)

    - **Variáveis:** `pc` é um `BitVec(3)`; `a, b, x, y, z` são `BitVec(n)`. `a` e `b` não mudam.
    - **Estado inicial:** $pc=\mathrm{LOOP}\land x=a\land y=b\land z=0\land a\ge0\land b\ge0$
      (a condição $\ge0$ só tem efeito no modo com sinal).
    - **Transição $T(s,s')$:** disjunção das ligações do autómato de controlo, cada uma com a sua guarda e a atualização
      das variáveis (as não mencionadas mantêm-se). As guardas normais de `EVEN` e `ODD` excluem o caso
      de overflow, o que dá a precedência ao erro.
    - **Erro:** $pc=\mathrm{ERROR}$.
    """)
    return


@app.cell
def _(
    And,
    BV,
    BVAdd,
    BVAnd,
    BVExtract,
    BVLShl,
    BVLShr,
    BVSExt,
    BVSGE,
    BVSub,
    BVType,
    BVZExt,
    ERROR,
    EVEN,
    Equals,
    LOOP,
    Not,
    NotEquals,
    ODD,
    Or,
    STOP,
    Symbol,
    TRUE,
):
    class Mult:
        def __init__(mult, n, com_sinal=False):
            mult.n, mult.com_sinal = n, com_sinal
            mult.zero, mult.um = BV(0, n), BV(1, n)

        def declare(mult, i):
            # BVType(3) define o tipo de um vetor de bits (Bit-Vector) com tamanho fixo de 3 bits.
            s = {'pc': Symbol(f'pc{i}', BVType(3))}
            for v in 'abxyz':
                s[v] = Symbol(f'{v}{i}', BVType(mult.n))
            return s

        def esta(mult, s, pc):
            return Equals(s['pc'], BV(pc, 3))

        def nao_negativo(mult, v):
            # Bit-Vector Signed Greater Than or Equal 
            return BVSGE(v, mult.zero) if mult.com_sinal else TRUE()

        def init(mult, s, extra=None):
            c = [mult.esta(s, LOOP),
                 Equals(s['x'], s['a']),
                 Equals(s['y'], s['b']),
                 Equals(s['z'], mult.zero),
                 mult.nao_negativo(s['a']),
                 mult.nao_negativo(s['b'])]
            if extra is not None:
                c.append(extra(s))
            return And(c)

        # deteção explícita do overflow (os BitVec nunca o assinalam)

        def overflow_soma(mult, s):
            # soma em n+1 bits; sem sinal o bit n é o carry
            n = mult.n
            # BVSExt aumenta o tamanho do vetor copiando o bit de sinal, enquanto BVZExt aumenta-o preenchendo os novos bits com zeros.
            ext = BVSExt if mult.com_sinal else BVZExt
            soma = BVAdd(ext(s['z'], 1), ext(s['x'], 1))
            # BVExtract extrai uma sub-sequência contígua de bits de um vetor, criando um novo vetor mais pequeno.
            if mult.com_sinal:
                return NotEquals(BVExtract(soma, n, n), BVExtract(soma, n - 1, n - 1))
            return Equals(BVExtract(soma, n, n), BV(1, 1))

        def overflow_shift(mult, s):
            x, n = s['x'], mult.n
            if mult.com_sinal:
                return NotEquals(BVExtract(x, n - 1, n - 1), BVExtract(x, n - 2, n - 2))
            return Equals(BVExtract(x, n - 1, n - 1), BV(1, 1))

        def condicoes(mult, s):
            y = s['y']
            y0 = Equals(y, mult.zero)
            # BVAnd realiza uma operação lógica E (AND bit a bit) entre dois vetores de bits do mesmo tamanho.
            par = Equals(BVAnd(y, mult.um), mult.zero)
            ovf_add, ovf_shl = mult.overflow_soma(s), mult.overflow_shift(s)
            return {
                'loop_stop': And(mult.esta(s, LOOP), y0),
                'loop_even': And(mult.esta(s, LOOP), Not(y0), par),
                'loop_odd':  And(mult.esta(s, LOOP), Not(y0), Not(par)),
                'even_err':  And(mult.esta(s, EVEN), ovf_shl),
                'even_loop': And(mult.esta(s, EVEN), Not(ovf_shl)),
                'odd_err':   And(mult.esta(s, ODD), ovf_add),
                'odd_loop':  And(mult.esta(s, ODD), Not(ovf_add)),
                'stop':      mult.esta(s, STOP),
                'err':       mult.esta(s, ERROR),
            }


        # BVLShl - Bit-vector Logical Shift Left a<<b - Shifts the bits of a to the left by b positions, filling lower-order bits with 0s.
        # BVLShr - Bit-Vector Logical Shift Right a >>b - Shifts the bits of a to the right by b positions, filling higher-order bits with 0s regardless of sign.
        # BVSub .- Bit Vector Substration a-b - Subtracts bit-vector b from bit-vector a modulo $2^N$ (where $N$ is the bit width).
        def transicoes(mult, s, p):
            g = mult.condicoes(s)

            def update(pc, **novos):
                # pc' = pc; x, y, z mudam para `novos[v]` ou mantêm-se
                return And(mult.esta(p, pc),
                           *[Equals(p[v], novos.get(v, s[v])) for v in 'xyz'])

            return And(
                Equals(p['a'], s['a']),
                Equals(p['b'], s['b']),
                Or(
                    And(g['loop_stop'], update(STOP)),
                    And(g['loop_even'], update(EVEN)),
                    And(g['loop_odd'],  update(ODD)),
                    And(g['even_err'],  update(ERROR)),
                    And(g['even_loop'], update(LOOP, x=BVLShl(s['x'], mult.um),y=BVLShr(s['y'], mult.um))),
                    And(g['odd_err'],   update(ERROR)),
                    And(g['odd_loop'],  update(LOOP, y=BVSub(s['y'], mult.um), z=BVAdd(s['z'], s['x']))),
                    And(g['stop'],      update(STOP)),
                    And(g['err'],       update(ERROR)),
                ),
            )

        def erro(mult, s):
            return mult.esta(s, ERROR)

        def terminal(mult, s):
            return Or(mult.esta(s, STOP), mult.esta(s, ERROR))

        # BVSExt - Bit-Vector Sign Extension - Extends an $N$-bit bit-vector to a larger width $(N + m)$ bits by replicating its Most Significant Bit (the sign bit) into the new high-order positions.
        # BVZExt - Bit-Vector Zero Extension - Extends an $N$-bit bit-vector to a larger width $(N + m)$ bits by filling all new high-order bits with 0s, treating the bit-vector as an unsigned integer.
        def W(mult, v):
            # extensão para 2n bits: aritmética exata
            return BVSExt(v, mult.n) if mult.com_sinal else BVZExt(v, mult.n)

    return (Mult,)


@app.cell
def _(Mult, n_ui, sinal_ui):
    n = int(n_ui.value)
    M = Mult(n, sinal_ui.value)
    return M, n


@app.cell
def _(ERROR, NOME, STOP, Solver):
    def resolve(*formulas):
        """
        Verifica se a conjunção das fórmulas é satisfazível.

        Parâmetros:
            *formulas: fórmulas pySMT (FNode) a impor em conjunto.

        Devolve:
            o modelo (valores das variáveis) se forem satisfazíveis,
            ou None se forem insatisfazíveis.
        """
        # o "with" cria um solver Z3 novo e fecha-o no fim
        with Solver(name="z3") as solver:
            for f in formulas:
                solver.add_assertion(f)          # impõe cada fórmula
            # solve() é True se existe modelo; o modelo tem de ser lido ainda dentro do "with"
            return solver.get_model() if solver.solve() else None


    def unroll(M, k):
        """
        Desdobra (unrolling) a relação de transição k vezes.

        Parâmetros:
            M: instância da classe Mult (o SFOTS).
            k: número de transições.

        Devolve:
            tr: lista de k+1 estados (s0, s1, ..., sk), cada um um dicionário de variáveis.
            lista de k fórmulas T(s0,s1), T(s1,s2), ..., T(s(k-1),sk).
        """
        # k transições ligam k+1 estados (por isso range(k + 1)); foi aqui que estava o IndexError original
        tr = [M.declare(i) for i in range(k + 1)]
        return tr, [M.transicoes(tr[i], tr[i + 1]) for i in range(k)]


    def valor(M, m, e):
        """
        Lê o valor da expressão `e` no modelo `m` como inteiro Python.

        O pySMT devolve os BitVec como inteiros sem sinal. No modo com sinal
        (complemento para dois), valores >= 2^(n-1) representam números
        negativos, por isso subtrai-se 2^n.
        """
        v = m.get_py_value(e)
        if M.com_sinal and v >= 2 ** (M.n - 1):
            v -= 2 ** M.n
        return v


    def mostra(M, m, tr):
        """
        Formata um traço de execução como tabela de texto.

        Parâmetros:
            M:  o SFOTS (usado por `valor` para o modo com/sem sinal).
            m:  modelo devolvido por `resolve`.
            tr: lista de estados (de `unroll`).

        Devolve:
            string com uma linha por instante t: pc, x, y, z e x*y+z.
            A coluna x*y+z é calculada com inteiros Python (sem overflow) e deve
            ser sempre igual a a*b (invariante do algoritmo).
            A tabela pára no primeiro estado STOP ou ERROR.
        """
        linhas = [f"{'t':>3} {'pc':>6} {'x':>6} {'y':>6} {'z':>6}   x*y+z"]   # cabeçalho
        for i, s in enumerate(tr):
            pc = m.get_py_value(s['pc'])                    # pc é um número (0..4)
            x, y, z = (valor(M, m, s[v]) for v in 'xyz')    # valores já com sinal, se for o caso
            linhas.append(f"{i:>3} {NOME[pc]:>6} {x:>6} {y:>6} {z:>6}   {x * y + z}")
            if pc in (STOP, ERROR):                         # estados finais têm laço: não repetir
                break
        return "\n".join(linhas)

    return mostra, resolve, unroll, valor


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Execução de exemplo

    Uma execução concreta obtida por *unrolling* da relação de transição.
    """)
    return


@app.cell
def _(BV, Equals, M, mo, mostra, n, resolve, unroll):
    _a0, _b0 = (13, 11) if n >= 5 else (5, 3)
    _tr, _T = unroll(M, 4 * n)
    _m = resolve(M.init(_tr[0]), Equals(_tr[0]['a'], BV(_a0, n)),
                 Equals(_tr[0]['b'], BV(_b0, n)), *_T)
    _txt = ("sem traço" if _m is None
            else f"a={_a0}, b={_b0}, a*b={_a0 * _b0}\n\n" + mostra(M, _m, _tr))
    mo.md(f"```\n{_txt}\n```")
    return


@app.cell
def _(mo):
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
def _(And, BVAdd, BVMul, Equals, Not, Or, resolve, unroll):
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


    def invariantes(M):
        W = M.W
        P_mod = lambda s: Equals(BVAdd(BVMul(s['x'], s['y']), s['z']),
                                 BVMul(s['a'], s['b']))
        P_exato = lambda s: And(
            Equals(BVAdd(BVMul(W(s['x']), W(s['y'])), W(s['z'])),
                   BVMul(W(s['a']), W(s['b']))),
            M.nao_negativo(s['x']), M.nao_negativo(s['y']), M.nao_negativo(s['z']))   # >= 0 só conta com sinal
        return P_mod, P_exato

    return invariantes, kinducao


@app.cell
def _(K_MAX, M, invariantes, kinducao, mo, n, time):
    P_mod, P_exato = invariantes(M)
    if n <= 8:
        _t0 = time.time()
        _r_mod = kinducao(M, P_mod, K_MAX)[0]
        _r_ex = kinducao(M, P_exato, K_MAX)[0]
        _msg = f"""
    * invariante módulo $2^n$: **{_r_mod}**
    * invariante exato (2n bits): **{_r_ex}**

    ({time.time() - _t0:.1f}s). Em `STOP` tem-se $y=0$, logo $z=a\\cdot b$: a asserção final é válida sempre que se chega a `STOP`.
    """
    else:
        _msg = "*(omitido para n > 8: as multiplicações de n e de 2n bits tornam o problema demasiado pesado para o solver; use n ≤ 8)*"
    mo.md(_msg)
    return (P_exato,)


@app.cell
def _(mo):
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
def _(Solver):
    def bmc(M, mau, K, extra=None):
        """Primeiro k <= K em que `mau` é alcançável: (k, modelo, estados)."""
        with Solver(name="z3") as solver:
            tr = [M.declare(0)]
            solver.add_assertion(M.init(tr[0], extra))
            for k in range(K + 1):
                if k > 0:
                    tr.append(M.declare(k))
                    solver.add_assertion(M.transicoes(tr[k - 1], tr[k]))
                solver.push()
                solver.add_assertion(mau(tr[k]))
                if solver.solve():
                    return k, solver.get_model(), tr
                solver.pop()
        return None

    return (bmc,)


@app.cell
def _(M, bmc, mo, mostra, n, valor):
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
def _(And, BV, BVULT, K_MAX, M, Not, P_exato, kinducao, mo, n, time):
    _h = BV(2 ** (n // 2), n)
    pequenos = lambda s: And(BVULT(s['a'], _h), BVULT(s['b'], _h))
    seguro = lambda s: And(Not(M.erro(s)), pequenos(s))
    seguro_r = lambda s: And(seguro(s), P_exato(s))

    if n <= 8:
        _t0 = time.time()
        _r_ref = kinducao(M, seguro_r, K_MAX, extra=pequenos)[0]
        _t1 = time.time() - _t0
        _t0 = time.time()
        _r_dir = kinducao(M, seguro, 4 * n + 2, extra=pequenos)[0]
        _t2 = time.time() - _t0
        _msg = f"""
    * reforçada com o invariante exato: **{_r_ref}** ({_t1:.1f}s)
    * direta (sem reforço): **{_r_dir}** ({_t2:.1f}s)

    A prova direta só tem sucesso quando $k$ atinge o comprimento do caminho mais longo, perto de $4n$.
    Com o reforço por $xy+z=ab$ basta $k=2$.
    """
    else:
        _msg = "*(omitido para n > 8: usa a multiplicação de 2n bits; use n ≤ 8)*"
    mo.md(_msg)
    return


@app.cell
def _(mo):
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
def _(
    And,
    BV,
    BVAdd,
    BVAnd,
    BVMul,
    BVULE,
    BVULT,
    BVZExt,
    EVEN,
    Equals,
    Implies,
    Ite,
    LOOP,
    M,
    Not,
    NotEquals,
    ODD,
    Or,
    kinducao,
    mo,
    n,
    resolve,
    time,
    unroll,
):
    _um, _zero = M.um, M.zero
    _r_pc = lambda s: Ite(M.esta(s, LOOP), BV(2, n + 2),
                          Ite(Or(M.esta(s, ODD), M.esta(s, EVEN)), BV(1, n + 2), BV(0, n + 2)))
    _V = lambda s: BVAdd(BVMul(BV(3, n + 2), BVZExt(s['y'], 2)), _r_pc(s))
    _impar = lambda s: Equals(BVAnd(s['y'], _um), _um)
    _par = lambda s: Equals(BVAnd(s['y'], _um), _zero)
    _J = lambda s: And(BVULE(s['pc'], BV(4, 3)),
                       Implies(M.esta(s, ODD), _impar(s)),
                       Implies(M.esta(s, EVEN), And(_par(s), NotEquals(s['y'], _zero))))

    _t0 = time.time()
    _ra = kinducao(M, _J, 3)[0]
    _s0, _s1 = M.declare(0), M.declare(1)
    _rb = "PROVADO" if resolve(_J(_s0), Not(M.terminal(_s0)), M.transicoes(_s0, _s1),
                               Not(BVULT(_V(_s1), _V(_s0)))) is None else "FALSO"
    _rc = "PROVADO" if resolve(_J(_s0), Not(M.terminal(_s0)),
                               Not(Or(list(M.condicoes(_s0).values())))) is None else "FALSO"
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
def _(mo):
    mo.md(r"""
    ## 5. Validação exaustiva (sem SMT)

    O programa é simulado em Python para **todos** os pares $(a,b)$ com $n=8$ e a mesma semântica de overflow.
    Verifica-se que o invariante nunca é violado, quais os pares que terminam em `ERROR` e o máximo de passos.
    """)
    return


@app.cell
def _(ERROR, EVEN, LOOP, ODD, STOP, mo):
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
def _(mo):
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
    | outra ordem de teste | `condicoes` e `transicoes` | o invariante e a variante mantêm-se; com sinal, `y > 0` é necessário para a terminação |
    | remover a precedência do erro | tirar `Not(ovf…)` das guardas normais | aparecem traços que continuam após o overflow com valores truncados |
    """)
    return


if __name__ == "__main__":
    app.run()
