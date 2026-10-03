# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.24.2",
#     "ortools",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import random
    from ortools.sat.python import cp_model

    return cp_model, mo, random


@app.cell
def _(mo):
    mo.md(r"""
    # Trabalho Prático: Sudoku Genérico como CSP

    Este notebook constrói um gerador/resolvedor de Sudoku $n^2 \times n^2$
    (com $n$ parametrizável) usando uma única abstração: **um grupo de
    células com a restrição "todos diferentes"**, algumas delas possivelmente
    já fixas a um valor.

    ### Correspondência com os requisitos do enunciado

    | Requisito | Nome neste notebook |
    |---|---|
    | R1 – grupo genérico | classe `box` (métodos `add` e `matriz`) |
    | R2 – bloco $n \times n$ | classe `cube(n, i, j)` |
    | R3 – troço reto | classe `path(n, inicio, fim)` |
    | R4 – pistas aleatórias | função `pistas_aleatorias(n, k)` |
    | R5 – modelo e resolução | classe `SudokuCSP` (métodos `adicionar` e `resolver`) |
    | R6 – Sudoku completo | funções `grupos_sudoku(n)` e `gerar_e_resolver(n, k)` |
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Decisões de implementação

    **Técnica de resolução: CP-SAT (OR-Tools).** O Sudoku é naturalmente um
    CSP com variáveis inteiras em $[1, n^2]$ e restrições "todos diferentes".
    O CP-SAT tem a restrição `AllDifferent` nativa, por isso cada grupo
    (`box`) traduz-se diretamente numa única restrição, sem termos de
    codificar à mão cláusulas proposicionais. Internamente o CP-SAT
    transforma o problema em SAT e usa técnicas de aprendizagem de cláusulas,
    o que o torna rápido mesmo para grelhas grandes. Uma codificação em SAT
    puro (uma variável booleana por célula e valor) também funcionaria, mas
    precisaria de $O(n^6)$ cláusulas "no máximo um" escritas à mão.

    **Estrutura de dados do grupo: dicionário** `(linha, coluna) → valor ou None`.
    Permite testar rapidamente se uma célula pertence ao grupo e guarda só
    as células que interessam (um grupo tem no máximo $n^2$ células, muito
    menos do que as $n^4$ da grelha).

    **Pistas aleatórias.** As pistas são, elas próprias, um `box`, e o modelo
    trata todos os grupos da mesma forma. Por isso o grupo das pistas também
    fica sujeito a "todos diferentes". Para isso nunca tornar o puzzle
    impossível por si só, os valores das pistas são escolhidos
    aleatoriamente **sem repetição**. Consequência: $k \le n^2$ (um grupo
    "todos diferentes" nunca pode ter mais de $n^2$ células com valores
    distintos em $[1, n^2]$).

    **Puzzle sem solução.** Mesmo assim, pistas aleatórias podem gerar um
    puzzle impossível. Nesse caso `gerar_e_resolver` sorteia novas pistas e
    tenta outra vez (até 20 tentativas) e só depois reporta insucesso.
    Escolhemos isto porque o objetivo é mostrar um Sudoku resolvido, e
    sortear de novo é barato.

    **Apresentação.** Uma tabela HTML com as fronteiras dos blocos
    destacadas e as pistas a vermelho e a negrito.
    """)
    return


@app.class_definition
class box:
    """Grupo genérico de células com a restrição "todos diferentes" (R1).

    Não sabe nada sobre linhas, colunas ou blocos: só guarda um conjunto
    de células de uma grelha N x N (com N = n*n), algumas delas fixas.

    Atributos:
        n       -- parâmetro do Sudoku (a grelha tem N = n*n linhas)
        N       -- tamanho da grelha e maior valor possível
        celulas -- dicionário (linha, coluna) -> valor fixo ou None
    """

    def __init__(self, n, celulas=None):
        """Cria o grupo. `celulas` é um dicionário opcional
        (linha, coluna) -> valor ou None (vazio por omissão)."""
        self.n = n
        self.N = n * n
        self.celulas = {}
        if celulas is not None:
            for (i, j), val in celulas.items():
                self.add(i, j, val)  # passa pela validação do add

    def add(self, i, j, val=None):
        """Acrescenta a célula (i, j) ao grupo, opcionalmente fixa a `val`.

        Levanta ValueError se a coordenada estiver fora da grelha
        ou se o valor estiver fora de [1, N].
        """
        if not (0 <= i < self.N and 0 <= j < self.N):
            raise ValueError(
                f"Coordenada ({i}, {j}) fora da grelha {self.N}x{self.N}"
            )
        if val is not None and not (1 <= val <= self.N):
            raise ValueError(f"Valor {val} fora do intervalo [1, {self.N}]")
        self.celulas[(i, j)] = val

    def matriz(self):
        """Devolve o grupo como matriz N x N: o valor fixo nas células
        fixas e 0 em todas as outras."""
        m = [[0] * self.N for _ in range(self.N)]
        for (i, j), val in self.celulas.items():
            if val is not None:
                m[i][j] = val
        return m

    def __len__(self):
        """Número de células do grupo."""
        return len(self.celulas)

    def __repr__(self):
        return f"{type(self).__name__}({len(self)} células)"


@app.cell
def _():
    class cube(box):
        """Bloco n x n de índices (i, j), com 0 <= i, j < n (R2).

        O canto superior esquerdo é a célula (i*n, j*n).
        """

        def __init__(self, n, i, j):
            super().__init__(n)
            if not (0 <= i < n and 0 <= j < n):
                raise ValueError(f"Índices de bloco ({i}, {j}) fora de [0, {n})")
            for a in range(n):
                for b in range(n):
                    self.add(i * n + a, j * n + b)

    class path(box):
        """Troço reto (horizontal ou vertical) de `inicio` até `fim`,
        inclusive (R3). Funciona nos dois sentidos."""

        def __init__(self, n, inicio, fim):
            super().__init__(n)
            i1, j1 = inicio
            i2, j2 = fim
            if i1 != i2 and j1 != j2:
                raise ValueError("Um path tem de ser horizontal ou vertical")

            # Direção do passo em cada eixo: -1, 0 ou +1
            di = 0
            if i2 > i1:
                di = 1
            elif i2 < i1:
                di = -1
            dj = 0
            if j2 > j1:
                dj = 1
            elif j2 < j1:
                dj = -1

            passos = max(abs(i2 - i1), abs(j2 - j1))
            for k in range(passos + 1):
                self.add(i1 + k * di, j1 + k * dj)

    return cube, path


@app.cell
def _(random):
    def pistas_aleatorias(n, k=None):
        """Devolve um `box` com k células aleatórias, cada uma fixa a um
        valor aleatório de [1, N] (R4). Por omissão k = n.

        Os valores são distintos entre si porque o próprio grupo das pistas
        fica sujeito a "todos diferentes" no modelo; por isso k <= N.
        """
        N = n * n
        if k is None:
            k = n
        if not (0 <= k <= N):
            raise ValueError(f"k tem de estar em [0, {N}]")

        todas = [(i, j) for i in range(N) for j in range(N)]
        posicoes = random.sample(todas, k)
        valores = random.sample(range(1, N + 1), k)

        pistas = box(n)
        for (i, j), val in zip(posicoes, valores):
            pistas.add(i, j, val)
        return pistas

    return (pistas_aleatorias,)


@app.cell
def _(cp_model):
    class SudokuCSP:
        """Modelo CSP de uma grelha N x N (R5).

        Uma variável inteira por célula, com domínio [1, N].
        """

        def __init__(self, n):
            self.n = n
            self.N = n * n
            self.modelo = cp_model.CpModel()
            self.x = []
            for i in range(self.N):
                linha = []
                for j in range(self.N):
                    linha.append(self.modelo.new_int_var(1, self.N, f"x_{i}_{j}"))
                self.x.append(linha)
            self.estado = None  # preenchido por resolver()

        def adicionar(self, *grupos):
            """Recebe qualquer número de grupos (box, cube, path, pistas...)
            e, para cada um, impõe "todos diferentes" e fixa as células
            com valor. Não distingue a origem dos grupos."""
            for g in grupos:
                if g.n != self.n:
                    raise ValueError("O grupo foi criado para outro n")
                variaveis = [self.x[i][j] for (i, j) in g.celulas]
                self.modelo.add_all_different(variaveis)
                for (i, j), val in g.celulas.items():
                    if val is not None:
                        self.modelo.add(self.x[i][j] == val)

        def resolver(self, tempo_max=60):
            """Devolve a grelha preenchida (lista de listas) ou None se
            não houver solução. O motivo fica em self.estado
            ("INFEASIBLE" = sem solução, "UNKNOWN" = acabou o tempo)."""
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = tempo_max
            resultado = solver.solve(self.modelo)
            self.estado = solver.status_name(resultado)

            if resultado == cp_model.OPTIMAL or resultado == cp_model.FEASIBLE:
                grelha = []
                for i in range(self.N):
                    grelha.append([solver.value(self.x[i][j]) for j in range(self.N)])
                return grelha
            return None

    return (SudokuCSP,)


@app.cell
def _(cube, path):
    def grupos_sudoku(n):
        """Todas as linhas, colunas e blocos de um Sudoku N x N (R6)."""
        N = n * n
        grupos = []
        for i in range(N):
            grupos.append(path(n, (i, 0), (i, N - 1)))  # linha i
        for j in range(N):
            grupos.append(path(n, (0, j), (N - 1, j)))  # coluna j
        for i in range(n):
            for j in range(n):
                grupos.append(cube(n, i, j))  # bloco (i, j)
        return grupos

    return (grupos_sudoku,)


@app.cell
def _(SudokuCSP, grupos_sudoku, pistas_aleatorias):
    def gerar_e_resolver(n, k=None, extra=None, tentativas=20):
        """Fluxo completo: pistas aleatórias -> linhas + colunas + blocos + pistas -> resolver.

        `extra` é uma lista opcional de grupos adicionais (ex.: diagonais).
        Se as pistas tornarem o puzzle impossível, sorteia outras.

        Devolve (pistas, solucao, numero_de_tentativas);
        solucao é None se nenhuma tentativa resultou.
        """
        if extra is None:
            extra = []
        for t in range(1, tentativas + 1):
            pistas = pistas_aleatorias(n, k)
            modelo = SudokuCSP(n)
            modelo.adicionar(*grupos_sudoku(n))
            modelo.adicionar(*extra)
            modelo.adicionar(pistas)
            solucao = modelo.resolver()
            if solucao is not None:
                return pistas, solucao, t
        return pistas, None, tentativas

    return (gerar_e_resolver,)
@app.cell
def _(SudokuCSP, box, grupos_sudoku, random):
    def pistas_por_bloco(n, por_bloco=3):
        """Devolve uma lista de `box`, um por bloco, cada um com
        `por_bloco` células fixas.

        Os valores vêm de uma grelha completa sorteada, por isso o
        puzzle tem sempre solução.
        """
        N = n * n
        if not (0 <= por_bloco <= N):
            raise ValueError(f"por_bloco tem de estar em [0, {N}]")

        # 1. Grelha completa aleatória: baralha a primeira linha
        #    e deixa o solver completar o resto
        primeira = box(n)
        valores = random.sample(range(1, N + 1), N)
        for j in range(N):
            primeira.add(0, j, valores[j])
        modelo = SudokuCSP(n)
        modelo.adicionar(*grupos_sudoku(n))
        modelo.adicionar(primeira)
        completa = modelo.resolver()

        # 2. Em cada bloco, escolhe `por_bloco` células ao calhas
        #    e copia o valor que têm na grelha completa
        lista = []
        for bi in range(n):
            for bj in range(n):
                celulas = [(bi * n + a, bj * n + b)
                           for a in range(n) for b in range(n)]
                pistas_bloco = box(n)
                for (i, j) in random.sample(celulas, por_bloco):
                    pistas_bloco.add(i, j, completa[i][j])
                lista.append(pistas_bloco)
        return lista

    return (pistas_por_bloco,)

@app.cell
def _(path):
    def validar_grelha(grelha, n):
        """True se cada linha, coluna e bloco tem exatamente 1..N."""
        N = n * n
        esperado = set(range(1, N + 1))
        for i in range(N):
            if set(grelha[i]) != esperado:
                return False
        for j in range(N):
            if set(grelha[i][j] for i in range(N)) != esperado:
                return False
        for bi in range(n):
            for bj in range(n):
                bloco = set()
                for a in range(n):
                    for b in range(n):
                        bloco.add(grelha[bi * n + a][bj * n + b])
                if bloco != esperado:
                    return False
        return True

    def validar_pistas(grelha, pistas):
        """True se todas as pistas mantêm o seu valor na solução."""
        for (i, j), val in pistas.celulas.items():
            if val is not None and grelha[i][j] != val:
                return False
        return True

    def testar_add_rejeita(n):
        """True se `add` rejeita coordenadas e valores inválidos."""
        N = n * n
        casos_invalidos = [
            (-1, 0, None),   # linha negativa
            (N, 0, None),    # linha demasiado grande
            (0, N, None),    # coluna demasiado grande
            (0, 0, 0),       # valor abaixo de 1
            (0, 0, N + 1),   # valor acima de N
        ]
        for i, j, val in casos_invalidos:
            try:
                box(n).add(i, j, val)
                return False  # devia ter levantado exceção
            except ValueError:
                pass
        return True

    def testar_path_sentidos(n):
        """True se um path dá as mesmas células nos dois sentidos."""
        N = n * n
        ida = path(n, (0, 0), (0, N - 1))
        volta = path(n, (0, N - 1), (0, 0))
        return set(ida.celulas) == set(volta.celulas) and len(ida) == N

    return (
        testar_add_rejeita,
        testar_path_sentidos,
        validar_grelha,
        validar_pistas,
    )


@app.cell
def _(mo):
    def mostrar(grelha, n, pistas=None):
        """Desenha a grelha como tabela HTML. Células vazias (0) ficam em
        branco e as pistas aparecem a vermelho e a negrito."""
        N = n * n
        fixas = {}
        if pistas is not None:
            fixas = pistas.celulas

        html = '<table style="border-collapse: collapse; font-family: monospace;">'
        for i in range(N):
            html += "<tr>"
            for j in range(N):
                estilo = (
                    "width: 2em; height: 2em; text-align: center;"
                    "border: 1px solid #999;"
                )
                # Linhas mais grossas nas fronteiras dos blocos
                if i % n == 0:
                    estilo += "border-top: 2px solid currentColor;"
                if j % n == 0:
                    estilo += "border-left: 2px solid currentColor;"
                if i == N - 1:
                    estilo += "border-bottom: 2px solid currentColor;"
                if j == N - 1:
                    estilo += "border-right: 2px solid currentColor;"
                if fixas.get((i, j)) is not None:
                    estilo += "font-weight: bold; color: #c0392b;"

                texto = str(grelha[i][j]) if grelha[i][j] != 0 else ""
                html += f'<td style="{estilo}">{texto}</td>'
            html += "</tr>"
        html += "</table>"
        return mo.Html(html)

    return (mostrar,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Demonstração

    Escolhe $n$ e o número de pistas $k$ e carrega no botão para gerar
    um novo puzzle.
    """)
    return


@app.cell
def _(mo):
    slider_n = mo.ui.slider(2, 5, value=3, label="n")
    botao = mo.ui.run_button(label="Gerar novo puzzle")
    return botao, slider_n


@app.cell
def _(mo, slider_n):
    slider_k = mo.ui.slider(
        0, slider_n.value ** 2, value=slider_n.value, label="k (pistas)"
    )
    mo.hstack([slider_n, slider_k])
    return (slider_k,)


@app.cell
def _(
    botao,
    gerar_e_resolver,
    mo,
    mostrar,
    slider_k,
    slider_n,
    validar_grelha,
    validar_pistas,
):
    _ = botao.value  # faz a célula correr de novo a cada clique
    _n = slider_n.value
    _pistas, _sol, _t = gerar_e_resolver(_n, slider_k.value)

    if _sol is None:
        _saida = mo.md(f"**Sem solução** ao fim de {_t} tentativas.")
    else:
        _saida = mo.vstack([
            botao,
            mo.hstack([
                mo.vstack([mo.md("**Pistas**"), mostrar(_pistas.matriz(), _n, _pistas)]),
                mo.vstack([mo.md("**Solução**"), mostrar(_sol, _n, _pistas)]),
            ], justify="start", gap=2),
            mo.md(
                f"Tentativas: {_t} · Grelha válida: {validar_grelha(_sol, _n)}"
                f" · Pistas respeitadas: {validar_pistas(_sol, _pistas)}"
            ),
        ])
    _saida
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Testes automáticos

    Para $n = 2$ ($4 \times 4$) e $n = 3$ ($9 \times 9$) corremos o fluxo
    completo e verificamos que:

    - cada linha, coluna e bloco tem exatamente os valores $1 \ldots n^2$;
    - as pistas mantêm o seu valor na solução;
    - `add` rejeita coordenadas fora da grelha e valores fora de $[1, n^2]$;
    - `path` dá as mesmas células nos dois sentidos.
    """)
    return


@app.cell
def _(
    gerar_e_resolver,
    mo,
    testar_add_rejeita,
    testar_path_sentidos,
    validar_grelha,
    validar_pistas,
):
    def _marca(ok):
        return "yes" if ok else "no"

    _linhas = ["| n | grelha válida | pistas respeitadas | add rejeita inválidos | path nos 2 sentidos |",
               "|---|---|---|---|---|"]
    for _n in (2, 3):
        _pistas, _sol, _t = gerar_e_resolver(_n)
        _grelha_ok = _sol is not None and validar_grelha(_sol, _n)
        _pistas_ok = _sol is not None and validar_pistas(_sol, _pistas)
        _linhas.append(
            f"| {_n} | {_marca(_grelha_ok)} | {_marca(_pistas_ok)} "
            f"| {_marca(testar_add_rejeita(_n))} | {_marca(testar_path_sentidos(_n))} |"
        )
    mo.md("\n".join(_linhas))
    return

 

@app.cell
def _(SudokuCSP, box, grupos_sudoku, mo, mostrar, pistas_por_bloco, validar_grelha, validar_pistas):
    _n = 3
    _lista = pistas_por_bloco(_n, por_bloco=3)

    _modelo = SudokuCSP(_n)
    _modelo.adicionar(*grupos_sudoku(_n))
    _modelo.adicionar(*_lista)          # um grupo por bloco
    _sol = _modelo.resolver()

    # Junta as pistas num só box APENAS para mostrar e validar
    # (este box não entra no modelo)
    _todas = box(_n)
    for _p in _lista:
        for (_i, _j), _v in _p.celulas.items():
            _todas.add(_i, _j, _v)

    mo.vstack([
        mo.md("### Sudoku com 3 pistas por bloco"),
        mo.hstack([
            mo.vstack([mo.md("**Pistas**"), mostrar(_todas.matriz(), _n, _todas)]),
            mo.vstack([mo.md("**Solução**"), mostrar(_sol, _n, _todas)]),
        ], justify="start", gap=2),
        mo.md(f"Grelha válida: {validar_grelha(_sol, _n)}"
              f" · Pistas respeitadas: {validar_pistas(_sol, _todas)}"),
    ])
    return

if __name__ == "__main__":
    app.run()
