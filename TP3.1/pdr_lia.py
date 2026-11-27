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
    # Um PDR didático sobre CHC's com aritmética linear de inteiros (LIA)

    Este notebook acompanha o Capítulo 4 (2ª parte), secção *"Verificação da correção usando CHC's"*.
    Mostra como um sistema de CHC's **lineares** (um predicado no corpo de cada cláusula) é resolvido
    por um algoritmo do tipo **PDR/IC3**, com os *frames* à vista. É uma versão muito simplificada do
    que o **Spacer** (z3) faz.

    **Sistema de CHC's** (abordagem orientada às pré-condições). Para cada ramo $(\ell,\ell')$ do CFA
    junta-se a transição e a guarda numa relação
    $\tau_{\ell,\ell'}(\mathsf{X},\mathsf{X}') \equiv \mathsf{T}_\ell(\mathsf{X},\mathsf{X}')\land\mathsf{sw}_{\ell,\ell'}(\mathsf{X}')$:

    $$\mathtt{True}\to P_{\mathsf{system}}(\mathsf{X})\qquad
    P_\ell(\mathsf{X})\land\tau_{\ell,\ell'}(\mathsf{X},\mathsf{X}')\to P_{\ell'}(\mathsf{X}')\qquad
    P_{\mathsf{error}}(\mathsf{X})\to\mathtt{False}$$

    A pós-condição $\varphi$ de `stop` é tratada com um ramo `stop → error` de guarda $\neg\varphi$.

    **Frames.** Para cada local $\ell$ mantém-se $F_0(\ell)\subseteq F_1(\ell)\subseteq\dots\subseteq F_N(\ell)$.
    Cada $F_i(\ell)$ é uma conjunção de **lemas** e sobre-aproxima os estados que chegam a $\ell$ em
    $\le i$ passos. $F_i(\mathsf{system}) = \mathtt{True}$ e $F_0(\ell)=\mathtt{False}$ para $\ell\neq\mathsf{system}$.

    **Ciclo.**

    1. **Obrigação de prova** $(s,\ell',i)$: o cubo $s$ em $\ell'$ tem de ser excluído de $F_i(\ell')$.
       Começa-se com $(\mathtt{True},\mathsf{error},N)$.
    2. **Bloqueio.** Para cada ramo $(\ell,\ell')$ pergunta-se ao SMT se
       $F_{i-1}(\ell)\land\tau_{\ell,\ell'}\land s'$ é satisfazível.
       * **SAT** — do modelo tira-se um **predecessor**: um cubo em $\ell$, nova obrigação de nível $i-1$.
         Uma obrigação em `system` é um **contra-exemplo** (o sistema de CHC's não tem modelo).
       * **UNSAT** em todos os ramos — aprende-se o lema $\neg g$ em $F_i(\ell')$, com $g\supseteq s$ **generalizado**.
    3. **Propagação.** Um lema de $F_i(\ell')$ passa para $F_{i+1}(\ell')$ se continuar a valer depois de um passo.
       Se $F_i = F_{i+1}$ em todos os locais, esse frame é um **modelo** das CHC's (um invariante indutivo).

    **O que muda com inteiros.** O espaço de estados é infinito, por isso:

    * o predecessor não pode ser um estado concreto. Usa-se **MBP** (*model-based projection*):
      elimina-se $\mathsf{X}'$ de $\tau\land s'$ guiado pelo modelo, o que dá um cubo de (des)igualdades
      lineares que cobre infinitos estados;
    * a generalização trabalha sobre desigualdades: cada $e_1 = e_2$ é partida em $e_1\le e_2$ e $e_1\ge e_2$,
      e retiram-se os literais desnecessários. (O Spacer usa também interpolação via lemas de Farkas.)
    * a **terminação não é garantida**: o resultado pode ser `sat`, `unsat` ou `unknown`.
    """)
    return


@app.cell
def _(z3):
    def mbp(model, elim, fml):
        """Model-based projection: elimina as variáveis `elim` de `fml`, guiado por `model`.
        O resultado R satisfaz  model ⊨ R  e  R → ∃ elim · fml."""
        n = len(elim)
        arr = (z3.z3types.Ast * n)(*[v.as_ast() for v in elim])
        r = z3.Z3_qe_model_project(fml.ctx_ref(), model.model, n, arr, fml.as_ast())
        return z3.ExprRef(r, fml.ctx)

    def literais(f):
        """Fórmula (conjunção) -> lista de literais; igualdades inteiras partidas em ≤ e ≥."""
        f = z3.simplify(f)
        if z3.is_true(f):
            return []
        if z3.is_and(f):
            return [l for c in f.children() for l in literais(c)]
        if z3.is_eq(f) and z3.is_int(f.arg(0)):
            return [f.arg(0) <= f.arg(1), f.arg(0) >= f.arg(1)]
        return [f]

    def conj(cubo):
        return z3.And(cubo) if len(cubo) > 1 else (cubo[0] if cubo else z3.BoolVal(True))

    return conj, literais, mbp


@app.cell
def _(z3):
    class CFA:
        """Variáveis inteiras, local inicial, local de erro e uma relação τ(X,X') por ramo."""

        def __init__(self, nomes, ramos, programa, init="system", error="error"):
            self.nomes = nomes
            self.X = [z3.Int(n) for n in nomes]
            self.Xp = [z3.Int(n + "'") for n in nomes]
            self.init, self.error = init, error
            self.ramos = ramos
            self.programa = programa
            self.locais = sorted({l for e in ramos for l in e},
                                 key=lambda l: (l != init, l == error))

        def linha(self, f):                 # f(X) -> f(X')
            return z3.substitute(f, *zip(self.X, self.Xp))

        def entradas(self, l):              # ramos que chegam a l
            return [(a, t) for (a, b), t in self.ramos.items() if b == l]

    def exemplos():
        x, y, n = z3.Ints("x y n")
        xp, yp, np_ = z3.Ints("x' y' n'")
        And = z3.And
        return {
            "1. contador (seguro)": CFA(
                ["x", "n"],
                {("system", "do"): And(xp == 0, np_ >= 0),
                 ("do", "do"): And(x < n, xp == x + 1, np_ == n),
                 ("do", "stop"): And(x >= n, xp == x, np_ == n),
                 ("stop", "error"): And(x != n, xp == x, np_ == n)},
                "assume n ≥ 0; x := 0; while x < n: x := x+1; assert x = n"),
            "2. contador sem n ≥ 0 (inseguro)": CFA(
                ["x", "n"],
                {("system", "do"): xp == 0,
                 ("do", "do"): And(x < n, xp == x + 1, np_ == n),
                 ("do", "stop"): And(x >= n, xp == x, np_ == n),
                 ("stop", "error"): And(x != n, xp == x, np_ == n)},
                "x := 0; while x < n: x := x+1; assert x = n"),
            "3. passo 2 (inseguro, contra-exemplo longo)": CFA(
                ["x"],
                {("system", "do"): xp == 0,
                 ("do", "do"): And(x < 5, xp == x + 2),
                 ("do", "stop"): And(x >= 5, xp == x),
                 ("stop", "error"): And(x != 5, xp == x)},
                "x := 0; while x < 5: x := x+2; assert x = 5"),
            "4. duas velocidades (seguro; precisa de generalização)": CFA(
                ["x", "y"],
                {("system", "do"): And(xp == 0, yp == 0),
                 ("do", "do"): And(x < 100, xp == x + 1, yp == y + 2),
                 ("do", "stop"): And(x >= 100, xp == x, yp == y),
                 ("stop", "error"): And(y < x, xp == x, yp == y)},
                "x := 0; y := 0; while x < 100: x := x+1, y := y+2; assert y ≥ x"),
            "5. transferência (seguro; este PDR diverge)": CFA(
                ["x", "y", "n"],
                {("system", "do"): And(xp == 0, yp == np_, np_ >= 0),
                 ("do", "do"): And(y > 0, xp == x + 1, yp == y - 1, np_ == n),
                 ("do", "stop"): And(y <= 0, xp == x, yp == y, np_ == n),
                 ("stop", "error"): And(x != n, xp == x, yp == y, np_ == n)},
                "assume n ≥ 0; x := 0; y := n; while y > 0: x := x+1, y := y-1; assert x = n"),
        }

    return (exemplos,)


@app.cell
def _(conj, literais, mbp, z3):
    class Limite(Exception):
        pass

    class PDR:
        def __init__(self, S, generalizar=True, usar_mbp=True, max_N=10, max_passos=300):
            self.S, self.generalizar, self.usar_mbp = S, generalizar, usar_mbp
            self.max_N, self.max_passos = max_N, max_passos
            self.lemas = {l: [] for l in S.locais}    # local -> [[cubo, nível]] ; lema = ¬cubo
            self.N, self.passos, self.log = 0, 0, []

        def nota(self, acao, local, formula):
            self.log.append({"N": self.N, "ação": acao, "local": local, "fórmula": formula})

        def F(self, i, l):
            """Frame F_i(ℓ): conjunção dos lemas de nível ≥ i."""
            if l == self.S.init:
                return z3.BoolVal(True)
            if i == 0:
                return z3.BoolVal(False)
            return z3.And([z3.Not(conj(c)) for c, k in self.lemas[l] if k >= i])

        def tem_predecessor(self, cubo, l, i):
            """Algum ramo (a,l) com F_{i-1}(a) ∧ τ ∧ cubo' satisfazível?"""
            for a, tau in self.S.entradas(l):
                s = z3.Solver()
                s.add(self.F(i - 1, a), tau, self.S.linha(conj(cubo)))
                if s.check() == z3.sat:
                    return a, tau, s.model()
            return None

        def predecessor(self, tau, cubo, m):
            S = self.S
            if self.usar_mbp:      # cubo de (des)igualdades lineares: cobre infinitos estados
                return literais(mbp(m, S.Xp, z3.And(tau, S.linha(conj(cubo)))))
            return [v == m.eval(v, model_completion=True) for v in S.X]   # um só estado

        def generaliza(self, cubo, l, i):
            """Retira literais enquanto o cubo continuar sem predecessores em F_{i-1}."""
            if not self.generalizar:
                return cubo
            cubo = list(cubo)
            for lit in list(cubo):
                menor = [k for k in cubo if not k.eq(lit)]
                if self.tem_predecessor(menor, l, i) is None:
                    cubo = menor
            return cubo

        def novo_lema(self, cubo, l, nivel):
            for lem in self.lemas[l]:
                if len(lem[0]) == len(cubo) and all(a.eq(b) for a, b in zip(lem[0], cubo)):
                    lem[1] = max(lem[1], nivel)
                    return
            self.lemas[l].append([cubo, nivel])

        def bloqueia(self, cubo, l, i):
            """Trata a obrigação (cubo, l, i). Devolve None ou o caminho de um contra-exemplo."""
            S = self.S
            pilha = [(cubo, l, i, None)]
            while pilha:
                self.passos += 1
                if self.passos > self.max_passos:
                    raise Limite
                ob = pilha[-1]
                cubo, l, i, _ = ob
                if l == S.init:                       # P_system = True: é um estado inicial
                    caminho = []
                    while ob:
                        caminho.append(ob[1])
                        ob = ob[3]
                    self.nota("contra-exemplo", "", " → ".join(caminho))
                    return caminho
                r = self.tem_predecessor(cubo, l, i)
                if r is None:
                    g = self.generaliza(cubo, l, i)
                    j = i                             # empurra o lema o mais longe possível
                    while j < self.N and self.tem_predecessor(g, l, j + 1) is None:
                        j += 1
                    self.novo_lema(g, l, j)
                    self.nota(f"lema em F_{j}", l, str(z3.simplify(z3.Not(conj(g)))))
                    pilha.pop()
                else:
                    a, tau, m = r
                    p = self.predecessor(tau, cubo, m)
                    self.nota(f"obrigação de nível {i - 1}", a, str(conj(p)))
                    pilha.append((p, a, i - 1, ob))
            return None

        def propaga(self):
            """Empurra lemas; devolve i se F_i = F_{i+1} em todos os locais."""
            for i in range(1, self.N + 1):
                for l in self.S.locais:
                    for lem in self.lemas[l]:
                        if lem[1] == i and self.tem_predecessor(lem[0], l, i + 1) is None:
                            lem[1] = i + 1
                if all(k != i for l in self.S.locais for _, k in self.lemas[l]):
                    return i
            return None

        def resolve(self):
            S = self.S
            try:
                while self.N < self.max_N:
                    self.N += 1
                    self.nota("novo frame", "", f"N = {self.N}")
                    cex = self.bloqueia([], S.error, self.N)
                    if cex:
                        return "unsat", cex
                    i = self.propaga()
                    if i is not None:
                        self.nota("ponto fixo", "", f"F_{i} = F_{i + 1}")
                        return "sat", {l: z3.simplify(self.F(i + 1, l)) for l in S.locais}
            except Limite:
                self.nota("limite de passos", "", f"{self.max_passos} obrigações tratadas")
            return "unknown", None

    return (PDR,)


@app.cell
def _(z3):
    def e_modelo(S, inv):
        """Verificação independente: `inv` satisfaz todas as CHC's?"""
        if not z3.is_true(inv[S.init]):
            return False
        for (a, b), tau in S.ramos.items():
            s = z3.Solver()
            s.add(inv[a], tau, z3.Not(S.linha(inv[b])))
            if s.check() != z3.unsat:
                return False
        s = z3.Solver()
        s.add(inv[S.error])
        return s.check() == z3.unsat

    def concretiza(S, caminho):
        """Valores concretos ao longo do caminho do contra-exemplo (BMC sobre esse caminho)."""
        E = [[z3.Int(f"{n}_{i}") for n in S.nomes] for i in range(len(caminho))]
        s = z3.Solver()
        for i, e in enumerate(zip(caminho, caminho[1:])):
            s.add(z3.substitute(S.ramos[e], *zip(S.X, E[i]), *zip(S.Xp, E[i + 1])))
        if s.check() != z3.sat:
            return None
        m = s.model()
        return [{"local": caminho[i],
                 **{n: m.eval(v, model_completion=True).as_long() for n, v in zip(S.nomes, E[i])}}
                for i in range(len(caminho))]

    def spacer(S, timeout_ms=10_000):
        """O mesmo sistema de CHC's entregue ao Spacer."""
        P = {l: z3.Function("P_" + l, *[z3.IntSort()] * len(S.X), z3.BoolSort()) for l in S.locais}
        s = z3.SolverFor("HORN")
        s.set("timeout", timeout_ms)
        s.add(z3.ForAll(S.X, P[S.init](*S.X)))
        for (a, b), tau in S.ramos.items():
            s.add(z3.ForAll(S.X + S.Xp, z3.Implies(z3.And(P[a](*S.X), tau), P[b](*S.Xp))))
        s.add(z3.ForAll(S.X, z3.Implies(P[S.error](*S.X), False)))
        r = s.check()
        inv = None
        if r == z3.sat:
            m = s.model()
            inv = {l: z3.simplify(m.eval(P[l](*S.X))) for l in S.locais}
        return str(r), inv

    return concretiza, e_modelo, spacer


@app.cell
def _(exemplos, mo):
    EX = exemplos()
    ex_ui = mo.ui.dropdown(list(EX), value=list(EX)[0], label="Exemplo")
    mbp_ui = mo.ui.checkbox(value=True, label="predecessores por MBP (desligado: um estado concreto)")
    gen_ui = mo.ui.checkbox(value=True, label="generalizar os lemas (retirar literais)")
    n_ui = mo.ui.slider(2, 14, value=10, label="número máximo de frames N", show_value=True)
    mo.vstack([mo.md("### Parâmetros"), ex_ui, mbp_ui, gen_ui, n_ui])
    return EX, ex_ui, gen_ui, mbp_ui, n_ui


@app.cell(hide_code=True)
def _(EX, ex_ui, mo):
    S = EX[ex_ui.value]
    mo.md(
        f"**Programa:** `{S.programa}`\n\n**Ramos e relações $\\tau_{{\\ell,\\ell'}}$:**\n\n```\n"
        + "\n".join(f"{a:>6} → {b:<6} {t}" for (a, b), t in S.ramos.items())
        + "\n```"
    )
    return (S,)


@app.cell
def _(PDR, S, gen_ui, mbp_ui, n_ui, spacer, time):
    pdr = PDR(S, generalizar=gen_ui.value, usar_mbp=mbp_ui.value, max_N=n_ui.value)
    _t0 = time.time()
    resultado, testemunha = pdr.resolve()
    tempo = time.time() - _t0
    res_spacer, inv_spacer = spacer(S)
    return inv_spacer, pdr, res_spacer, resultado, tempo, testemunha


@app.cell(hide_code=True)
def _(S, concretiza, e_modelo, inv_spacer, mo, pdr, res_spacer, resultado, tempo, testemunha):
    _txt = [f"## Resultado: **{resultado}**",
            f"N = {pdr.N}, {pdr.passos} obrigações tratadas, {tempo:.2f} s. "
            f"O Spacer dá **{res_spacer}** para o mesmo sistema."]
    _extra = []
    if resultado == "sat":
        _txt.append("Existe modelo: o CFA é **seguro**. Interpretação dos predicados (o último frame):")
        _txt.append("```\n" + "\n".join(f"P_{l}(X) ≡ {testemunha[l]}" for l in S.locais) + "\n```")
        _txt.append(f"Verificação independente de que é um modelo das CHC's: **{e_modelo(S, testemunha)}**.")
    elif resultado == "unsat":
        _txt.append("Não existe modelo: `error` é alcançável. Caminho: `" + " → ".join(testemunha) + "`")
        _est = concretiza(S, testemunha)
        if _est:
            _txt.append("_Cada linha dá os valores das variáveis à entrada do local._")
            _extra.append(mo.ui.table(_est, selection=None))
    else:
        _txt.append("O algoritmo **não convergiu** dentro dos limites. Veja no registo a sequência "
                    "de lemas: cada um exclui só uma parte de um conjunto infinito de estados.")
    if inv_spacer and resultado != "sat":
        _txt.append("Modelo encontrado pelo Spacer:\n```\n"
                    + "\n".join(f"P_{l}(X) ≡ {inv_spacer[l]}" for l in S.locais) + "\n```")
    mo.vstack([mo.md("\n\n".join(_txt))] + _extra)
    return


@app.cell(hide_code=True)
def _(S, conj, mo, pdr, z3):
    _frames = [{"local": l, "nível": k, "lema": str(z3.simplify(z3.Not(conj(c))))}
               for l in S.locais for c, k in sorted(pdr.lemas[l], key=lambda p: p[1])]
    mo.accordion({
        f"Registo do algoritmo ({len(pdr.log)} linhas)":
            mo.ui.table(pdr.log, selection=None, page_size=25),
        f"Lemas no fim ({len(_frames)}). F_i(ℓ) é a conjunção dos lemas de ℓ com nível ≥ i":
            mo.ui.table(_frames, selection=None, page_size=25) if _frames else mo.md("_sem lemas_"),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## O que observar

    | exemplo | MBP + generalização | sem MBP | sem generalização |
    |---|---|---|---|
    | 1. contador | **sat** (N = 3) | unknown | sat |
    | 2. contador sem `n ≥ 0` | **unsat**: `n < 0` chega a `stop` com `x = 0 ≠ n` | unknown | unsat |
    | 3. passo 2 | **unsat** (N = 6): `x = 0, 2, 4, 6` | unknown | unsat |
    | 4. duas velocidades | **sat**: `P_do ≡ x ≤ y` | unknown | unknown |
    | 5. transferência | **unknown** (o Spacer dá sat) | unknown | unknown |

    1. **Sem MBP nada converge**, nem os exemplos inseguros. Cada obrigação é um único estado
       (`x = 2 ∧ n = 3`), e em cada frame `stop` tem infinitos estados maus a um passo de `error`.
       O algoritmo bloqueia-os um a um até esgotar o orçamento de obrigações.
    2. **Generalização (exemplo 4).** O cubo a bloquear em `do` é `x > y ∧ x ≥ 100`. Retirando
       `x ≥ 100` fica o lema `x ≤ y`, que é indutivo. Sem generalização, o algoritmo aprende
       `¬(x > y ∧ x ≥ 100)`, depois `¬(x > y + 1 ∧ x = 99)`, … e recua uma iteração do ciclo
       por frame: teria de percorrer as 100 iterações.
    3. **Divergência (exemplo 5).** O invariante é `x + y = n ∧ y ≥ 0`. Este PDR aprende
       `¬(y = 0 ∧ x ≠ n)`, `¬(y = 1 ∧ x ≠ n − 1)`, `¬(y = 2 ∧ x ≠ n − 2)`, … sem nunca chegar à
       igualdade. Retirar literais não chega para *inventar* `x + y = n`. O Spacer consegue
       porque generaliza com interpolação (lemas de Farkas) e com heurísticas globais sobre
       conjuntos de lemas.
    4. **Não-linearidade.** O MBP só existe para aritmética linear. É por isso que o exemplo da
       multiplicação, com o invariante `z + x·y = a·b`, só foi resolvido com *bit-vectors*
       (ver `chc_multiplicacao.py`).

    ## Simplificações em relação ao Spacer

    * Só CHC's lineares (um predicado no corpo). O Spacer trata as não-lineares (chamadas de
      procedimentos) com sub- e sobre-aproximações em simultâneo.
    * Não se usa indução relativa ($\neg s$ como hipótese no frame anterior), nem interpolação.
    * As obrigações são tratadas por uma pilha, sem fila de prioridade nem reutilização.
    """)
    return


if __name__ == "__main__":
    app.run()
