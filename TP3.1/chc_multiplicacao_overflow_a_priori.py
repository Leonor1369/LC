import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import z3
    import time
    return mo, time, z3


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # CHC's para a "Multiplicação de inteiros com erros" — overflow testado a priori (z3 / Spacer)

    Este notebook codifica em **z3** os dois sistemas de CHC's do Capítulo 4 (2ª parte),
    secção *"Verificação da correção parcial do programa Multiplicação de Inteiros com Erros"*,
    com $L = 2^{16}-1 = 65535$, numa **variante em que o overflow é testado a priori**:
    `do` só passa o controlo a `even`/`odd` se o passo seguinte não exceder $L$; caso contrário
    o controlo vai diretamente de `do` para `error`.

    | ramo | guarda |
    |---|---|
    | `(do,even)` | $y\neq 0 \land \mathit{even}(y) \land 2x \le L$ |
    | `(do,odd)` | $y\neq 0 \land \mathit{odd}(y) \land x + z \le L$ |
    | `(do,error)` *(novo)* | $y\neq 0 \land \big((\mathit{even}(y) \land 2x > L) \lor (\mathit{odd}(y) \land x+z > L)\big)$ |
    | `(even,do)`, `(odd,do)` | $\mathtt{True}$ |
    | `(do,stop)` | $y = 0$ |

    Os ramos `(even,error)` e `(odd,error)` desaparecem: ficam **7 ramos**. Assim nenhuma variável
    chega a exceder $L$ (os valores ficam sempre representáveis), ao contrário da versão
    original, onde o overflow só é detetado depois de acontecer.

    * **orientado às pré-condições** — incógnitas $P_\ell$, uma CHC por ramo $(\ell,\ell')$:
      $\;\models\;\mathsf{T}_\ell(\mathsf{X},\mathsf{X}')\land \mathsf{sw}_{\ell,\ell'}(\mathsf{X}')\land P_\ell(\mathsf{X}) \to P_{\ell'}(\mathsf{X}')$
    * **orientado às pós-condições** — incógnitas $Q_\ell$, uma CHC por ramo $(\ell',\ell)$:
      $\;\models\;\mathsf{T}_\ell(\mathsf{X},\mathsf{X}')\land \mathsf{sw}_{\ell',\ell}(\mathsf{X})\land Q_{\ell'}(\mathsf{X}) \to Q_{\ell}(\mathsf{X}')$

    mais as CHC's de `system`, `stop` ($\neg\varphi\land\cdot\to\mathtt{False}$) e `error` ($\cdot\to\mathtt{False}$).
    Pelo texto, *existe modelo* $\iff$ o CFA é **parcialmente correto e seguro**.

    As variáveis são inteiros matemáticos (`Int`); o `overflow` é testado a priori, em `do`,
    pelas condições $2x > L$ (passo `even`) e $x + z > L$ (passo `odd`).

    O `havoc(a,b)` gera inteiros positivos representáveis, $0 \le a, b \le L$, de acordo com o
    enunciado ("multiplicação de dois inteiros positivos").

    * **Sem mais restrições nas entradas**, o Spacer encontra rapidamente a violação (**unsat**), e o
      notebook mostra um contra-exemplo concreto.
    * **Com a pré-condição adicional** $a\cdot b \le L$, o sistema tem modelo, mas o
      Spacer não o encontra dentro do tempo limite: a aritmética é não-linear ($a\cdot b$ e o
      invariante $z + x\cdot y = a\cdot b$). Por isso o notebook **verifica um modelo candidato**:
      dá interpretações explícitas às variáveis de predicado e prova com z3 que cada CHC é válida.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    restr_ui = mo.ui.checkbox(value=False, label="restringir as entradas: a·b ≤ L")
    spacer_ui = mo.ui.checkbox(value=False, label="com a restrição, tentar também o Spacer (timeout de 20 s por sistema)")
    run_ui = mo.ui.run_button(label="Resolver os dois sistemas")
    mo.vstack([mo.md("### Parâmetros  (L = 2¹⁶ − 1 = 65535)"), restr_ui, spacer_ui, run_ui])
    return restr_ui, run_ui, spacer_ui


@app.cell
def _(z3):
    L = 2**16 - 1
    NAMES = ["a", "b", "x", "y", "z"]
    LOCS = ["system", "do", "even", "odd", "stop", "error"]
    EDGES = [("system", "do"), ("do", "even"), ("do", "odd"),
             ("even", "do"), ("odd", "do"),
             ("do", "stop"), ("do", "error")]

    def cfa(restringir=False):
        """CFA da multiplicação com teste de overflow a priori: variáveis, T_ℓ, sw_{ℓ,ℓ'} e φ."""
        X = {n: z3.Int(n) for n in NAMES}
        Xp = {n: z3.Int(n + "'") for n in NAMES}

        def same(*vs):
            return z3.And([Xp[v] == X[v] for v in vs])

        T = {
            "system": same("x", "y", "z"),          # havoc(a,b)
            "do": same(*NAMES),
            "stop": same(*NAMES),
            "error": same(*NAMES),
            "even": z3.And(Xp["x"] == 2 * X["x"], Xp["y"] == X["y"] / 2, same("z", "a", "b")),
            "odd": z3.And(Xp["x"] == X["x"], Xp["y"] == X["y"] - 1,
                          Xp["z"] == X["x"] + X["z"], same("a", "b")),
        }

        def sw(e, S):
            """guarda do ramo e, avaliada no vetor de variáveis S"""
            even = S["y"] % 2 == 0
            ovf_even = 2 * S["x"] > L            # o passo even daria x' = 2x > L
            ovf_odd = S["x"] + S["z"] > L        # o passo odd daria z' = x + z > L
            init = [S["x"] == S["a"], S["y"] == S["b"], S["z"] == 0,
                    S["a"] >= 0, S["a"] <= L, S["b"] >= 0, S["b"] <= L]  # positivos representáveis
            if restringir:
                init += [S["a"] * S["b"] <= L]
            g = {
                ("system", "do"): z3.And(init),
                ("do", "even"): z3.And(S["y"] != 0, even, z3.Not(ovf_even)),
                ("do", "odd"): z3.And(S["y"] != 0, z3.Not(even), z3.Not(ovf_odd)),
                ("do", "error"): z3.And(S["y"] != 0, z3.Or(z3.And(even, ovf_even),
                                                           z3.And(z3.Not(even), ovf_odd))),
                ("even", "do"): z3.BoolVal(True),
                ("odd", "do"): z3.BoolVal(True),
                ("do", "stop"): S["y"] == 0,
            }
            return g[e]

        def phi(S):
            return S["z"] == S["a"] * S["b"]

        return dict(X=X, Xp=Xp, T=T, sw=sw, phi=phi)
    return EDGES, L, LOCS, NAMES, cfa


@app.cell
def _(EDGES, LOCS, NAMES, z3):
    def chc_system(M, abordagem):
        """Lista de CHC's (sem quantificadores; variáveis X, X' universais)."""
        X, Xp, T, sw, phi = M["X"], M["Xp"], M["T"], M["sw"], M["phi"]
        V = [X[n] for n in NAMES]
        Vp = [Xp[n] for n in NAMES]
        I = z3.IntSort()
        pre = abordagem == "pre"
        R = {l: z3.Function(("P_" if pre else "Q_") + l, *[I] * 5, z3.BoolSort()) for l in LOCS}
        clauses, nomes = [], []
        for (l, m) in EDGES:
            if pre:   # T_ℓ(X,X') ∧ sw_{ℓ,ℓ'}(X') ∧ P_ℓ(X) → P_ℓ'(X')
                clauses.append(z3.Implies(z3.And(T[l], sw((l, m), Xp), R[l](*V)), R[m](*Vp)))
            else:     # T_ℓ(X,X') ∧ sw_{ℓ',ℓ}(X) ∧ Q_ℓ'(X) → Q_ℓ(X')   (ℓ' = l, ℓ = m)
                clauses.append(z3.Implies(z3.And(T[m], sw((l, m), X), R[l](*V)), R[m](*Vp)))
            nomes.append(f"ramo ({l},{m})")
        if pre:
            clauses.append(R["system"](*V))                                  # True → P_system(X)
        else:
            clauses.append(z3.Implies(T["system"], R["system"](*Vp)))        # T_system → Q_system(X')
        clauses.append(z3.Implies(z3.And(z3.Not(phi(X)), R["stop"](*V)), False))
        clauses.append(z3.Implies(R["error"](*V), False))
        nomes += ["system", "stop: ¬φ ∧ · → False", "error: · → False"]
        return R, clauses, V + Vp, nomes
    return (chc_system,)


@app.cell
def _(L, NAMES, z3):
    def modelo_candidato(M, abordagem):
        """Interpretação explícita das variáveis de predicado (só para o caso com restrição)."""
        a, b, x, y, z = [M["X"][n] for n in NAMES]
        base = z3.And(a >= 0, b >= 0, a * b <= L, x >= 0, y >= 0, z >= 0, z + x * y == a * b)
        T, F = z3.BoolVal(True), z3.BoolVal(False)
        if abordagem == "pre":   # P_ℓ: estados à entrada de ℓ
            return {"system": T, "do": base,
                    "even": z3.And(base, y != 0, y % 2 == 0, 2 * x <= L),
                    "odd": z3.And(base, y % 2 == 1, x + z <= L),
                    "stop": z3.And(base, y == 0), "error": F}
        else:                    # Q_ℓ: estados à saída de ℓ
            return {"system": T, "do": base,
                    "even": z3.And(base, y >= 1),
                    "odd": base,
                    "stop": z3.And(base, y == 0), "error": F}
    return (modelo_candidato,)


@app.cell
def _(EDGES, LOCS, NAMES, chc_system, modelo_candidato, time, z3):
    def resolve(M, abordagem, timeout_ms=5_000, sementes=range(12)):
        """Spacer (SolverFor('HORN')). O Spacer pode devolver 'unknown' consoante a semente
        aleatória (por causa da multiplicação não-linear em φ); tenta-se várias sementes."""
        R, clauses, allv, _ = chc_system(M, abordagem)
        t0 = time.time()
        r = None
        for seed in sementes:
            s = z3.SolverFor("HORN")
            s.set("timeout", timeout_ms)
            s.set("random_seed", seed)
            for c in clauses:
                s.add(z3.ForAll(allv, c))
            r = s.check()
            if r != z3.unknown:
                break
        return dict(res=str(r), model=s.model() if r == z3.sat else None, R=R,
                    tempo=time.time() - t0, semente=seed)

    def verifica_modelo(M, abordagem):
        """Substitui as variáveis de predicado pelo modelo candidato e prova cada CHC."""
        R, clauses, allv, nomes = chc_system(M, abordagem)
        C = modelo_candidato(M, abordagem)
        V = [M["X"][n] for n in NAMES]
        subs = [(R[l], z3.substitute(C[l], *[(V[i], z3.Var(i, z3.IntSort())) for i in range(5)]))
                for l in LOCS]
        linhas = []
        for nome, c in zip(nomes, clauses):
            s = z3.Solver()
            s.set("timeout", 30_000)
            s.add(z3.Not(z3.substitute_funs(c, *subs)))
            t0 = time.time()
            r = s.check()
            linhas.append({"CHC": nome, "válida": r == z3.unsat,
                           "z3": str(r), "tempo (s)": round(time.time() - t0, 3)})
        return linhas, C

    def contraexemplo(M, max_passos=40):
        """BMC sobre o CFA: procura uma execução que chegue a `error`, ou a `stop` com ¬φ.
        A execução é a mesma qualquer que seja a abordagem (pré ou pós-condições)."""
        locs = list(LOCS)
        cod = {l: i for i, l in enumerate(locs)}

        def sub(f, A, B):
            return z3.substitute(f, *[(M["X"][n], A[n]) for n in NAMES],
                                 *[(M["Xp"][n], B[n]) for n in NAMES])

        St = [{n: z3.Int(f"{n}_0") for n in NAMES}]
        pc = [z3.Int("pc_0")]
        s = z3.Solver()
        s.add(pc[0] == cod["system"])
        for d in range(1, max_passos + 1):
            St.append({n: z3.Int(f"{n}_{d}") for n in NAMES})
            pc.append(z3.Int(f"pc_{d}"))
            s.add(z3.Or([z3.And(pc[d - 1] == cod[l], pc[d] == cod[m],
                                sub(M["T"][l], St[d - 1], St[d]),
                                sub(M["sw"]((l, m), M["Xp"]), St[d - 1], St[d]))
                         for (l, m) in EDGES]))
            mau = z3.Or(pc[d] == cod["error"],
                        z3.And(pc[d] == cod["stop"], z3.Not(sub(M["phi"](M["X"]), St[d], St[d]))))
            s.push()
            s.add(mau)
            if s.check() == z3.sat:
                mdl = s.model()
                estados = [{"local": locs[mdl.eval(pc[i]).as_long()],
                            **{n: mdl.eval(St[i][n], model_completion=True).as_long() for n in NAMES}}
                           for i in range(d + 1)]
                return dict(path=[e["local"] for e in estados], estados=estados)
            s.pop()
        return None

    return contraexemplo, resolve, verifica_modelo


@app.cell
def _(cfa, restr_ui):
    M = cfa(restringir=restr_ui.value)
    return (M,)


@app.cell(hide_code=True)
def _(M, chc_system, mo):
    def _show(ab):
        _, _cl, _, _nm = chc_system(M, ab)
        return mo.md("```\n" + "\n\n".join(f"[{n}]\n{c}" for n, c in zip(_nm, _cl)) + "\n```")

    mo.accordion({
        "CHC's — abordagem orientada às pré-condições (P_ℓ)": _show("pre"),
        "CHC's — abordagem orientada às pós-condições (Q_ℓ)": _show("post"),
    })
    return


@app.cell
def _(M, contraexemplo, mo, resolve, restr_ui, run_ui, spacer_ui, verifica_modelo):
    mo.stop(not run_ui.value, mo.md("_Carregue em **Resolver os dois sistemas**._"))
    resultados = {}
    _cex = None
    for _ab in ("pre", "post"):
        _r = {}
        if not restr_ui.value:
            _r = resolve(M, _ab)
            if _r["res"] == "unsat":
                # o contra-exemplo é uma execução do CFA, logo é o mesmo nas duas abordagens
                if _cex is None:
                    _cex = contraexemplo(M)
                _r["cex"] = _cex
        else:
            if spacer_ui.value:
                _r = resolve(M, _ab, timeout_ms=20_000, sementes=range(1))
            _r["certificado"] = verifica_modelo(M, _ab)
        resultados[_ab] = _r
    return (resultados,)


@app.cell(hide_code=True)
def _(L, mo, resultados):
    _blocos = []
    for _ab, _nome in (("pre", "pré-condições (P_ℓ)"), ("post", "pós-condições (Q_ℓ)")):
        _r = resultados[_ab]
        _out = [mo.md(f"### Abordagem orientada às {_nome}")]
        if "res" in _r:
            _out.append(mo.md(f"Spacer: **{_r['res']}** ({_r['tempo']:.1f} s, semente {_r['semente']}), com L = {L}."))
        if _r.get("res") == "unsat":
            _c = _r.get("cex")
            _out.append(mo.md("Não existe modelo, logo o CFA **não** é parcialmente correto e seguro."))
            if _c and _c["estados"]:
                _out.append(mo.md("Contra-exemplo (BMC sobre o CFA): `" + " → ".join(_c["path"]) + "`  \n"
                                  "_Cada linha dá os valores à entrada do local; a 1ª linha é o "
                                  "estado antes do `havoc(a,b)`._"))
                _out.append(mo.ui.table(_c["estados"], selection=None))
        if "certificado" in _r:
            _linhas, _C = _r["certificado"]
            _ok = all(l["válida"] for l in _linhas)
            _letra = "P" if _ab == "pre" else "Q"
            _out.append(mo.md(
                "**Verificação do modelo candidato:** "
                + ("todas as CHC's são válidas, logo **existe modelo** e o CFA é parcialmente correto e seguro."
                   if _ok else "há CHC's que falham (ver tabela).")))
            _out.append(mo.ui.table(_linhas, selection=None))
            _out.append(mo.md("Modelo candidato:\n```\n" +
                              "\n".join(f"{_letra}_{l} := {f}" for l, f in _C.items()) + "\n```"))
        _blocos.append(mo.vstack(_out))
    mo.vstack(_blocos)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Resultados de referência (L = 65535, overflow testado a priori)

    | entradas | pré-condições | pós-condições | interpretação |
    |---|---|---|---|
    | `havoc(a,b)` com `0 ≤ a, b ≤ L` (inteiros positivos representáveis) | Spacer: **unsat** | Spacer: **unsat** | `error` é alcançável pelo ramo `(do,error)`, por ex. `a > L/2` e `b` par; o programa **não** é parcialmente correto e seguro |
    | idem, e ainda `a·b ≤ L` | modelo verificado (10 CHC's válidas) | modelo verificado (10 CHC's válidas) | **parcialmente correto e seguro**; o invariante-chave é `z + x·y = a·b` |

    Com a restrição, o Spacer devolve `unknown` (timeout), por causa da aritmética não-linear.
    A existência de modelo fica provada pela verificação explícita do modelo candidato.

    **Porque é que o modelo funciona.** Em `do` tem-se `z + x·y = a·b ≤ L`, com `x, y, z ≥ 0`.
    Se `y` é par e não nulo, `y ≥ 2`, logo `2x ≤ x·y ≤ L`; se `y` é ímpar, `y ≥ 1`, logo
    `x + z ≤ x·y + z = a·b ≤ L`. Portanto a guarda de `(do,error)` é sempre falsa e `error` nunca
    é alcançado. Em `stop`, `y = 0` dá `z = a·b`, que é `φ`.

    **Diferença em relação à versão original.** Na versão original o teste é feito *a posteriori*
    (`(even,error)`, `(odd,error)` com `x > L ∨ z > L`), o que pressupõe que os valores acima de
    `L` existem, isto é, inteiros matemáticos. Aqui o teste é feito *a priori*, e por isso todos os
    valores calculados ficam em `[0, L]`, como num programa real com inteiros de 16 bits.
    Os contra-exemplos também mudam: a violação é agora `system → do → error`, num passo a menos.
    """)
    return


if __name__ == "__main__":
    app.run()
