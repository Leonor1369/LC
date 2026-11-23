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
    # CHC's para a "Multiplicação de inteiros com erros" — overflow a priori, `BitVec` de 6 bits (z3 / Spacer)

    Este notebook codifica em **z3** os dois sistemas de CHC's do Capítulo 4 (2ª parte),
    secção *"Verificação da correção parcial do programa Multiplicação de Inteiros com Erros"*,
    com as variáveis representadas como **bit-vectors sem sinal de $N = 6$ bits** e
    $L = 2^{6}-1 = 63$, numa **variante em que o overflow é testado a priori**:
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

    **Codificação em `BitVec`.** Todas as variáveis `a, b, x, y, z` são `BitVec(·, 6)` e todas as
    comparações são **sem sinal** (`ULE`, `UGT`). Como o overflow é testado *antes* de cada passo,
    os valores calculados ficam sempre em $[0, L]$: nenhuma operação "dá a volta", e os 6 bits
    representam exatamente os inteiros do programa.

    * `even(y)` é o bit menos significativo de `y` a zero; `y/2` é `LShR(y, 1)`; `2x` é `x << 1`.
    * Os testes de overflow evitam calcular o valor que excederia $L$:
      $2x > L \iff x > \lfloor L/2\rfloor$ e $x + z > L \iff x > L - z$ (com $z \le L$, $L - z$ não dá a volta).
    * O `havoc(a,b)` gera um valor qualquer de 6 bits, isto é, $0 \le a, b \le L$ fica implícito.
    * Em $\varphi \equiv z = a\cdot b$, na pré-condição $a\cdot b \le L$ e no invariante
      $z + x\cdot y = a\cdot b$, os produtos são calculados com $2N+1 = 13$ bits (`ZeroExt`):
      são os produtos inteiros, sem perda.

    * **Sem mais restrições nas entradas**, o Spacer encontra rapidamente a violação (**unsat**), e o
      notebook mostra um contra-exemplo concreto.
    * **Com a pré-condição adicional** $a\cdot b \le L$, o sistema tem modelo, mas o
      Spacer não o encontra dentro do tempo limite, mesmo com só 6 bits: o invariante necessário,
      $z + x\cdot y = a\cdot b$, envolve multiplicações. Por isso o notebook **verifica um modelo candidato**:
      dá interpretações explícitas às variáveis de predicado e prova com z3 que cada CHC é válida
      (com bit-vectors esta prova é decidível e demora décimas de segundo).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    restr_ui = mo.ui.checkbox(value=False, label="restringir as entradas: a·b ≤ L")
    spacer_ui = mo.ui.checkbox(value=False, label="com a restrição, tentar também o Spacer (timeout de 20 s por sistema)")
    run_ui = mo.ui.run_button(label="Resolver os dois sistemas")
    mo.vstack([mo.md("### Parâmetros  (BitVec de 6 bits, L = 2⁶ − 1 = 63)"), restr_ui, spacer_ui, run_ui])
    return restr_ui, run_ui, spacer_ui


@app.cell
def _(z3):
    N = 6                      # número de bits
    L = 2**N - 1               # maior inteiro representável (63)
    NAMES = ["a", "b", "x", "y", "z"]
    LOCS = ["system", "do", "even", "odd", "stop", "error"]
    EDGES = [("system", "do"), ("do", "even"), ("do", "odd"),
             ("even", "do"), ("odd", "do"),
             ("do", "stop"), ("do", "error")]
    BV = z3.BitVecSort(N)

    def bv(v):
        return z3.BitVecVal(v, N)

    def largo(*vs, w=N + 1):
        """estende sem sinal para 2N+1 bits: aí a·b, x·y e z + x·y nunca dão a volta"""
        return [z3.ZeroExt(w, v) for v in vs]

    def cfa(restringir=False):
        """CFA da multiplicação com teste de overflow a priori, em bit-vectors de N bits:
        variáveis, T_ℓ, sw_{ℓ,ℓ'} e φ."""
        X = {n: z3.BitVec(n, N) for n in NAMES}
        Xp = {n: z3.BitVec(n + "'", N) for n in NAMES}

        def same(*vs):
            return z3.And([Xp[v] == X[v] for v in vs])

        T = {
            "system": same("x", "y", "z"),          # havoc(a,b): qualquer valor de N bits
            "do": same(*NAMES),
            "stop": same(*NAMES),
            "error": same(*NAMES),
            "even": z3.And(Xp["x"] == X["x"] << 1, Xp["y"] == z3.LShR(X["y"], 1),
                           same("z", "a", "b")),
            "odd": z3.And(Xp["x"] == X["x"], Xp["y"] == X["y"] - 1,
                          Xp["z"] == X["x"] + X["z"], same("a", "b")),
        }

        def sw(e, S):
            """guarda do ramo e, avaliada no vetor de variáveis S (comparações sem sinal)"""
            even = z3.Extract(0, 0, S["y"]) == 0
            ovf_even = z3.UGT(S["x"], bv(L // 2))         # 2x > L, sem calcular 2x
            ovf_odd = z3.UGT(S["x"], bv(L) - S["z"])      # x + z > L, sem calcular x + z
            init = [S["x"] == S["a"], S["y"] == S["b"], S["z"] == bv(0)]
            if restringir:
                _a, _b = largo(S["a"], S["b"])
                init += [z3.ULE(_a * _b, L)]              # a·b ≤ L, calculado sem dar a volta
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
            # z = a·b como inteiros: o produto é calculado com 2N+1 bits
            _a, _b, _z = largo(S["a"], S["b"], S["z"])
            return _z == _a * _b

        return dict(X=X, Xp=Xp, T=T, sw=sw, phi=phi)
    return BV, EDGES, L, LOCS, N, NAMES, bv, cfa, largo


@app.cell
def _(BV, EDGES, LOCS, NAMES, z3):
    def chc_system(M, abordagem):
        """Lista de CHC's (sem quantificadores; variáveis X, X' universais)."""
        X, Xp, T, sw, phi = M["X"], M["Xp"], M["T"], M["sw"], M["phi"]
        V = [X[n] for n in NAMES]
        Vp = [Xp[n] for n in NAMES]
        pre = abordagem == "pre"
        R = {l: z3.Function(("P_" if pre else "Q_") + l, *[BV] * 5, z3.BoolSort()) for l in LOCS}
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
def _(L, NAMES, bv, largo, z3):
    def modelo_candidato(M, abordagem):
        """Interpretação explícita das variáveis de predicado (só para o caso com restrição).
        Os produtos são calculados com 2N+1 bits, logo são os produtos inteiros."""
        a, b, x, y, z = [M["X"][n] for n in NAMES]
        A, B, X_, Y, Z = largo(a, b, x, y, z)
        base = z3.And(z3.ULE(A * B, L), Z + X_ * Y == A * B)
        par = z3.Extract(0, 0, y) == 0
        T, F = z3.BoolVal(True), z3.BoolVal(False)
        if abordagem == "pre":   # P_ℓ: estados à entrada de ℓ
            return {"system": T, "do": base,
                    "even": z3.And(base, y != bv(0), par, z3.ULE(x, bv(L // 2))),
                    "odd": z3.And(base, z3.Not(par), z3.ULE(x, bv(L) - z)),
                    "stop": z3.And(base, y == bv(0)), "error": F}
        else:                    # Q_ℓ: estados à saída de ℓ
            return {"system": T, "do": base,
                    "even": z3.And(base, y != bv(0)),
                    "odd": base,
                    "stop": z3.And(base, y == bv(0)), "error": F}
    return (modelo_candidato,)


@app.cell
def _(BV, EDGES, LOCS, N, NAMES, chc_system, modelo_candidato, time, z3):
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
        subs = [(R[l], z3.substitute(C[l], *[(V[i], z3.Var(i, BV)) for i in range(5)]))
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

        St = [{n: z3.BitVec(f"{n}_0", N) for n in NAMES}]
        pc = [z3.Int("pc_0")]
        s = z3.Solver()
        s.add(pc[0] == cod["system"])
        for d in range(1, max_passos + 1):
            St.append({n: z3.BitVec(f"{n}_{d}", N) for n in NAMES})
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
    ## Resultados de referência (BitVec de 6 bits, L = 63, overflow testado a priori)

    | entradas | pré-condições | pós-condições | interpretação |
    |---|---|---|---|
    | `havoc(a,b)`: qualquer valor de 6 bits, `0 ≤ a, b ≤ 63` | Spacer: **unsat** (0,01 s) | Spacer: **unsat** (0,01 s) | `error` é alcançável pelo ramo `(do,error)`, por ex. `a = 53, b = 52` (`b` par e `2a > 63`); o programa **não** é parcialmente correto e seguro |
    | idem, e ainda `a·b ≤ L` | modelo verificado (10 CHC's válidas, ≈0,1 s cada) | modelo verificado (10 CHC's válidas, ≈0,1 s cada) | **parcialmente correto e seguro**; o invariante-chave é `z + x·y = a·b` |

    Com a restrição, o Spacer devolve `unknown` ao fim de 60 s (testado com várias sementes), apesar
    de o espaço de estados ser finito ($2^{30}$ estados). A existência de modelo fica provada pela
    verificação explícita do modelo candidato. Essa verificação não é vácua: se se retirar o
    invariante `z + x·y = a·b` do modelo de `do`, as CHC's dos ramos `(do,even)`, `(do,odd)`,
    `(do,stop)` e `(do,error)` deixam de ser válidas.

    **Porque é que o modelo funciona.** Em `do` tem-se `z + x·y = a·b ≤ L`, com `x, y, z ≥ 0`.
    Se `y` é par e não nulo, `y ≥ 2`, logo `2x ≤ x·y ≤ L`; se `y` é ímpar, `y ≥ 1`, logo
    `x + z ≤ x·y + z = a·b ≤ L`. Portanto a guarda de `(do,error)` é sempre falsa e `error` nunca
    é alcançado. Em `stop`, `y = 0` dá `z = a·b`, que é `φ`.

    **Diferença em relação à versão original.** Na versão original o teste é feito *a posteriori*
    (`(even,error)`, `(odd,error)` com `x > L ∨ z > L`), o que pressupõe que os valores acima de
    `L` existem, isto é, inteiros matemáticos. Aqui o teste é feito *a priori*, e por isso todos os
    valores calculados ficam em `[0, L]`, e é isso que permite usar bit-vectors de exatamente 6 bits,
    como num programa real com inteiros de 6 bits sem sinal.
    Os contra-exemplos também mudam: a violação é agora `system → do → error`, num passo a menos.
    """)
    return


if __name__ == "__main__":
    app.run()
