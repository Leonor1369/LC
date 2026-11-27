import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from z3 import (
        And, Bool, BoolSort, BoolVal, ForAll, Function, If, Implies, Not, Or,
        Solver, SolverFor, Sum, is_true, sat, unsat,
    )

    return (
        And,
        Bool,
        BoolSort,
        BoolVal,
        ForAll,
        Function,
        If,
        Implies,
        Not,
        Or,
        Solver,
        SolverFor,
        Sum,
        is_true,
        mo,
        sat,
    )


@app.cell
def _(mo):
    mo.md(r"""
    ## O problema do barqueiro: lobo, cordeiro e couve

    Um barqueiro está na margem esquerda de um rio com um **lobo**, um
    **cordeiro** e uma **couve**. O barco leva o barqueiro e, no máximo,
    mais um item. Sem o barqueiro presente:

    * o lobo come o cordeiro;
    * o cordeiro come a couve.

    Pretende-se levar tudo para a margem direita.

    ### Modelação como sistema de transição (SFOTS)

    * **Estado:** quatro variáveis booleanas $b, l, c, v$ (barqueiro, lobo,
      cordeiro, couve). `False` é a margem esquerda e `True` a direita.
      São $2^4 = 16$ estados.
    * **Estado inicial:** $\neg b \wedge \neg l \wedge \neg c \wedge \neg v$.
    * **Transição:** o barqueiro muda sempre de margem ($b' = \neg b$). Cada
      item ou fica onde está, ou estava com o barqueiro e acompanha-o.
      Muda no máximo um item.
    * **Estados seguros:**
      $\neg(l = c \wedge c \neq b) \wedge \neg(c = v \wedge c \neq b)$.
    * **Objetivo:** $b \wedge l \wedge c \wedge v$.

    Procurar uma solução é procurar um caminho, só por estados seguros,
    do estado inicial até ao objetivo. Se o objetivo for tratado como
    "estado de erro", a solução é o **contraexemplo** que um verificador
    de modelos encontra.
    """)
    return


@app.cell
def _(And, Bool, If, Implies, Not, Or, Sum):
    NOMES = ["barqueiro", "lobo", "cordeiro", "couve"]
    ITENS = NOMES[1:]

    def estado(k):
        """Variáveis de estado na cópia k."""
        return [Bool(f"{n}_{k}") for n in NOMES]

    def init(s):
        return And([Not(x) for x in s])

    def objetivo(s):
        return And(s)

    def seguro(s):
        b, l, c, v = s
        return And(Not(And(l == c, c != b)),   # lobo sozinho com o cordeiro
                   Not(And(c == v, c != b)))   # cordeiro sozinho com a couve

    def trans(s, t, pode_trazer=True):
        """Relação de transição entre os estados s e t.
        Com pode_trazer=False os itens só podem ir para a margem direita."""
        b, b_ = s[0], t[0]
        conds = [b_ == Not(b)]
        for i in range(1, 4):
            # o item fica, ou estava com o barqueiro e vai com ele
            conds.append(Or(t[i] == s[i], And(s[i] == b, t[i] == b_)))
            if not pode_trazer:
                conds.append(Implies(s[i], t[i]))
        # o barco leva no máximo um item
        conds.append(Sum([If(t[i] != s[i], 1, 0) for i in range(1, 4)]) <= 1)
        return And(conds)

    return ITENS, NOMES, estado, init, objetivo, seguro, trans


@app.cell
def _(mo):
    mo.md(r"""
    ### Bounded Model Checking

    Para $k = 0, 1, 2, \dots$ desenrola-se a transição $k$ vezes e
    pergunta-se ao Z3 se

    $$
    \mathsf{init}(s_0) \wedge \bigwedge_{j<k} \mathsf{trans}(s_j, s_{j+1})
    \wedge \bigwedge_{j \le k} \mathsf{seguro}(s_j)
    \wedge \mathsf{objetivo}(s_k)
    $$

    é satisfazível. O primeiro $k$ com resposta `sat` é o comprimento da
    solução mínima. Cada resposta `unsat` anterior prova que não há
    solução mais curta.
    """)
    return


@app.cell
def _(Or, Solver, estado, init, is_true, objetivo, sat, seguro, trans):
    def avalia(m, S):
        return [[is_true(m.eval(x, model_completion=True)) for x in st] for st in S]

    def bmc(K, pode_trazer=True):
        """Devolve (k, traço, registo) para o menor k <= K, ou (None, None, registo)."""
        registo = []
        S = [estado(0)]
        s = Solver()
        s.add(init(S[0]), seguro(S[0]))
        for k in range(K + 1):
            s.push()
            s.add(objetivo(S[k]))
            r = s.check()
            registo.append((k, str(r)))
            if r == sat:
                return k, avalia(s.model(), S), registo
            s.pop()
            S.append(estado(k + 1))
            s.add(trans(S[k], S[k + 1], pode_trazer), seguro(S[k + 1]))
        return None, None, registo

    def todas_solucoes(k, pode_trazer=True):
        """Enumera todos os traços de comprimento exatamente k."""
        S = [estado(j) for j in range(k + 1)]
        s = Solver()
        s.add(init(S[0]), objetivo(S[k]))
        s.add([seguro(st) for st in S])
        s.add([trans(S[j], S[j + 1], pode_trazer) for j in range(k)])
        sols = []
        while s.check() == sat:
            tr = avalia(s.model(), S)
            sols.append(tr)
            # bloqueia este traço
            s.add(Or([x != v for st, vals in zip(S, tr) for x, v in zip(st, vals)]))
        return sols

    return bmc, todas_solucoes


@app.cell
def _(bmc, mo):
    k_min, traco, registo = bmc(15)
    mo.md(
        "| k | resultado |\n|---|---|\n"
        + "\n".join(f"| {k} | `{r}` |" for k, r in registo)
        + f"\n\n**Solução mínima: {k_min} travessias.**"
    )
    return (k_min,)


@app.cell
def _(ITENS):
    def descreve(tr):
        """Traduz um traço numa lista de travessias."""
        passos = []
        for s, t in zip(tr, tr[1:]):
            mov = [ITENS[i - 1] for i in range(1, 4) if s[i] != t[i]]
            sentido = "→ direita" if t[0] else "← esquerda"
            passos.append(f"leva o {mov[0]} {sentido}" if mov
                          else f"volta sozinho {sentido}")
        return passos

    return (descreve,)


@app.cell
def _(descreve, k_min, mo, todas_solucoes):
    solucoes = todas_solucoes(k_min)
    mo.md(
        f"Há **{len(solucoes)}** soluções de comprimento {k_min}:\n\n"
        + "\n\n".join(
            f"**Solução {n + 1}**\n\n"
            + "\n".join(f"{j + 1}. {p}" for j, p in enumerate(descreve(tr)))
            for n, tr in enumerate(solucoes))
    )
    return (solucoes,)


@app.cell
def _(mo, solucoes):
    escolha = mo.ui.dropdown(
        options={f"Solução {n + 1}": n for n in range(len(solucoes))},
        value="Solução 1", label="Solução")
    escolha
    return (escolha,)


@app.cell
def _(escolha, k_min, mo):
    passo = mo.ui.slider(0, k_min, value=0, label="Passo", show_value=True)
    mo.vstack([mo.md(f"### Visualização: solução {escolha.value + 1}"), passo])
    return (passo,)


@app.cell
def _(NOMES, descreve, escolha, mo, passo, solucoes):
    _tr = solucoes[escolha.value]
    _s = _tr[passo.value]
    _esq = [n for n, x in zip(NOMES, _s) if not x] or ["—"]
    _dir = [n for n, x in zip(NOMES, _s) if x] or ["—"]
    _acao = "estado inicial" if passo.value == 0 else descreve(_tr)[passo.value - 1]
    mo.md(
        f"*{_acao}*\n\n"
        "| margem esquerda | rio | margem direita |\n"
        "|:---:|:---:|:---:|\n"
        f"| {', '.join(_esq)} | {'barco →' if _s[0] else '← barco'} | {', '.join(_dir)} |"
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Alcançabilidade com CHC's (Spacer)

    A mesma pergunta pode pôr-se como um sistema de CHC's sobre um
    predicado incógnito $\mathit{Inv}(b,l,c,v)$:

    * $\forall x \cdot \mathsf{init}(x) \to \mathit{Inv}(x)$
    * $\forall x, x' \cdot \mathit{Inv}(x) \wedge \mathsf{trans}(x,x')
      \wedge \mathsf{seguro}(x') \to \mathit{Inv}(x')$
    * $\forall x \cdot \mathit{Inv}(x) \wedge \mathsf{objetivo}(x) \to \bot$

    Se o sistema for **`sat`**, o modelo de $\mathit{Inv}$ é um invariante
    indutivo que exclui o objetivo: o problema **não tem solução**.
    Se for **`unsat`**, o objetivo é alcançável.

    Comparam-se duas versões. Na original, o barqueiro pode trazer itens
    de volta. Na restringida, os itens só podem ir para a margem direita.
    """)
    return


@app.cell
def _(
    And,
    BoolSort,
    BoolVal,
    ForAll,
    Function,
    Implies,
    SolverFor,
    estado,
    init,
    objetivo,
    sat,
    seguro,
    trans,
):
    def chc(pode_trazer):
        x, x_ = estado("x"), estado("x_")
        Inv = Function("Inv", *[BoolSort()] * 4, BoolSort())
        hs = SolverFor("HORN")
        hs.add(ForAll(x, Implies(init(x), Inv(*x))))
        hs.add(ForAll(x + x_, Implies(And(Inv(*x), trans(x, x_, pode_trazer), seguro(x_)),
                                      Inv(*x_))))
        hs.add(ForAll(x, Implies(And(Inv(*x), objetivo(x)), BoolVal(False))))
        r = hs.check()
        return r, (hs.model().eval(Inv(*x)) if r == sat else None)

    return (chc,)


@app.cell
def _(chc, mo):
    _r1, _ = chc(pode_trazer=True)
    _r2, _inv2 = chc(pode_trazer=False)

    def _concl(r):
        return "objetivo alcançável" if str(r) == "unsat" else "sem solução"

    mo.md(
        "| versão | resultado | conclusão |\n|---|---|---|\n"
        f"| pode trazer itens de volta | `{_r1}` | {_concl(_r1)} |\n"
        f"| só leva para a direita | `{_r2}` | {_concl(_r2)} |\n\n"
        f"Invariante obtido para a versão restringida:\n\n```\n{_inv2}\n```"
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Verificação independente (pesquisa em largura, sem Z3)

    Com apenas 16 estados, uma pesquisa em largura explícita confirma os
    resultados anteriores.
    """)
    return


@app.cell
def _(mo):
    from collections import deque
    from itertools import product

    def seguro_py(s):
        b, l, c, v = s
        return not (l == c != b) and not (c == v != b)

    def sucessores_py(s, pode_trazer=True):
        for i in (None, 1, 2, 3):
            if i is not None and (s[i] != s[0] or (not pode_trazer and s[i])):
                continue
            t = list(s)
            t[0] = not s[0]
            if i:
                t[i] = t[0]
            if seguro_py(t):
                yield tuple(t)

    def bfs(pode_trazer=True):
        ini, fim = (False,) * 4, (True,) * 4
        dist, fila = {ini: 0}, deque([ini])
        while fila:
            s = fila.popleft()
            for t in sucessores_py(s, pode_trazer):
                if t not in dist:
                    dist[t] = dist[s] + 1
                    fila.append(t)
        return dist.get(fim)

    _n_seguros = sum(seguro_py(s) for s in product([False, True], repeat=4))
    mo.md(
        f"* estados seguros: **{_n_seguros}** de 16\n"
        f"* comprimento mínimo (versão original): **{bfs(True)}**\n"
        f"* comprimento mínimo (versão restringida): **{bfs(False)}**"
    )
    return


if __name__ == "__main__":
    app.run()
