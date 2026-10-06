# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.24.2",
#     "ortools",
# ]
# ///
# (O bloco acima diz que versão do Python e que bibliotecas o notebook precisa.)

import marimo 

__generated_with = "0.25.0"  
app = marimo.App(width="medium")  


# ---------------------------------------------------------------------------
# NOTA SOBRE O MARIMO (vale para todas as células):
#   @app.cell       -> marca a função seguinte como uma célula do notebook.
#   def _(a, b):    -> os argumentos são os nomes que a célula usa de outras células.
#   return (x, y)   -> os nomes que esta célula disponibiliza às outras.
#   Nomes começados por _ (ex.: _n) são "privados": só existem dentro da célula.
# ---------------------------------------------------------------------------


@app.cell
def _():
    import marimo as mo
    import random  
    from ortools.sat.python import cp_model  # cp_model -> o solver CP-SAT do OR-Tools

    return cp_model, mo, random  # disponibiliza as três bibliotecas às outras células


@app.cell
def _(mo):
    
    mo.md(r"""
    # Sudoku com restrições (CP-SAT)

    **Autores:** Diana Mota e Leonor Sousa
    """)
    return  # esta célula não disponibiliza nada às outras


@app.cell
def _(mo):
    mo.md(r"""
    ## Visão geral do problema

    Este notebook resolve um Sudoku genérico usando um modelo de
    restrições. A ideia é simples: cada célula é uma variável, e cada
    conjunto que tem de conter valores distintos é uma restrição.

    Em vez de tratar linhas, colunas e blocos como casos diferentes, a
    solução usa uma abstração comum: a classe `box`. Um `box` representa
    qualquer grupo de células em que todos os valores têm de ser
    distintos. A partir desta ideia, construímos as linhas, as colunas e
    os blocos como casos particulares desse mesmo conceito.

    **Porquê CP-SAT?** Porque o problema é um CSP clássico e OR-Tools
    já tem a restrição `AllDifferent` pronta. Isso faz com que o modelo
    seja curto, claro e muito mais fácil de manter do que escrever uma
    codificação manual em SAT.

    **Como guardo cada grupo.** Cada grupo usa um dicionário em que a
    chave é `(linha, coluna)` e o valor é o número fixo da célula, ou
    `None` se a célula estiver livre. Isso permite validar rapidamente se
    uma célula pertence ao grupo e também guardar apenas o que é
    relevante.

    **Pistas aleatórias.** As pistas são elas próprias um `box`, e por isso
    também têm de respeitar a regra "todos diferentes". Para evitar
    conflitos imediatos, os valores são escolhidos sem repetição, o que
    implica que o número de pistas, `k`, tem de satisfazer $k \le n^2$.

    **Se o puzzle não tiver solução.** Mesmo com valores distintos e bem
    escolhidos, às vezes a combinação de pistas pode tornar o problema
    impossível. Nesse caso, o notebook tenta gerar novas pistas várias
    vezes e só depois informa que não houve solução. A intenção é manter
    a experiência simples e garantir que o utilizador vê a resolução do
    Sudoku em vez de um erro de modelação.

    **Como é apresentada a solução.** O resultado aparece numa tabela HTML,
    com as fronteiras dos blocos mais fortes e as pistas destacadas a
    vermelho e a negrito.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Vocabulário e convenções

    | Símbolo | Significado | Exemplo |
    |---|---|---|
    | `n` | parâmetro do Sudoku: cada bloco é $n \times n$ | `n = 3` |
    | `N` | tamanho da grelha e maior valor possível, $N = n^2$ | `N = 9` |
    | `i` | número da **linha**, de `0` a `N-1` (começa em 0!) | `i = 0` é a 1.ª linha |
    | `j` | número da **coluna**, de `0` a `N-1` | `j = 8` é a 9.ª coluna |
    | `val` | valor de uma célula, de `1` a `N` | `val = 5` |
    | pista | célula cujo valor já vem fixo | `(0, 0) = 5` |

    Para $n = 3$ temos o Sudoku clássico $9 \times 9$; para $n = 2$ temos
    um mini-Sudoku $4 \times 4$ (valores de 1 a 4), muito útil para testar.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Restrições do modelo

    O modelo tem **uma variável por célula**, $x_{i,j} \in [1, n^2]$, e
    quatro famílias de restrições. As três primeiras vêm de `grupos_sudoku(n)`
    e a quarta das pistas.

    | # | Restrição | Grupos | Classe | Quantos |
    |---|---|---|---|---|
    | C1 | Linhas: $x_{i,0}, \ldots, x_{i,N-1}$ todas diferentes | uma por linha | `path` | $n^2$ |
    | C2 | Colunas: $x_{0,j}, \ldots, x_{N-1,j}$ todas diferentes | uma por coluna | `path` | $n^2$ |
    | C3 | Blocos: as $n \times n$ células de cada bloco todas diferentes | um por bloco | `cube` | $n^2$ |
    | C4 | Pistas: as células sorteadas ficam fixas ao valor sorteado (e são todas diferentes entre si) | um grupo | `box` | $\ge 1$ |

    Para uma restrição ser fixa a um valor, o modelo acrescenta
    $x_{i,j} = v$. Quando o puzzle é impossível, é porque C1–C3 e C4 não
    podem ser satisfeitas **ao mesmo tempo**.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Passo 1: a classe `box`

    O `box` é o bloco de construção de tudo o resto: **um grupo de
    células que têm de ser todas diferentes**. Não sabe se é uma linha,
    uma coluna ou um bloco; só guarda células.

    | Método | O que faz |
    |---|---|
    | `add(i, j, val)` | acrescenta a célula `(i, j)`, opcionalmente fixa a `val` |
    | `matriz()` | devolve o grupo como grelha $N \times N$ (0 = célula livre) |
    | `len(b)` | número de células do grupo |

    O `add` **valida** o que recebe: coordenadas fora da grelha ou valores
    fora de $[1, N]$ dão `ValueError`. Assim apanhamos erros logo à
    entrada, em vez de descobrirmos um resultado estranho mais à frente.
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

    def __init__(self, n, celulas=None):  # construtor: corre quando se escreve box(n)
        """Cria o grupo. `celulas` é um dicionário opcional
        (linha, coluna) -> valor ou None (vazio por omissão)."""
        self.n = n  # guarda o parâmetro do Sudoku dentro do objeto
        self.N = n * n  # tamanho da grelha (e maior valor possível)
        self.celulas = {}  # dicionário vazio: ainda não há células no grupo
        if celulas is not None:  # se recebemos células iniciais...
            for (i, j), val in celulas.items():  # ...percorre cada par (coordenada, valor)
                self.add(i, j, val)  # e junta-a com add, para passar pela validação

    def add(self, i, j, val=None):  # val =None quer dizer "célula livre" por omissão
        """Acrescenta a célula (i, j) ao grupo, opcionalmente fixa a `val`.

        Levanta ValueError se a coordenada estiver fora da grelha
        ou se o valor estiver fora de [1, N].
        """
        if not (0 <= i < self.N and 0 <= j < self.N):  # linha ou coluna fora de [0, N)?
            raise ValueError(  # lança um erro e pára a função
                f"Coordenada ({i}, {j}) fora da grelha {self.N}x{self.N}"
            )
        if val is not None and not (1 <= val <= self.N):  # há valor e está fora de [1, N]?
            raise ValueError(f"Valor {val} fora do intervalo [1, {self.N}]")
        self.celulas[(i, j)] = val  # tudo válido: guarda a célula no dicionário

    def matriz(self):
        """Devolve o grupo como matriz N x N: o valor fixo nas células
        fixas e 0 em todas as outras."""
        m = [[0] * self.N for _ in range(self.N)]  # cria uma grelha N x N cheia de zeros
        for (i, j), val in self.celulas.items():  # percorre as células do grupo
            if val is not None:  # se a célula tem valor fixo
                m[i][j] = val  #escreve-o na posição certa
        return m  # devolve a grelha

    def __len__(self):  # permite escrever len(b)
        """Número de células do grupo."""
        return len(self.celulas)  # nº de entradas do dicionário = nº de células

    def __repr__(self):  # permite imprimir o objeto de forma legível
        """Texto que aparece ao imprimir o objeto, ex.: `box(9 células)`."""
        # type(self).__name__ dá o nome da classe (box, cube ou path)
        return f"{type(self).__name__}({len(self)} células)"


@app.cell
def _(mo):
    mo.md(r"""
    ## Passo 2: `cube` e `path`, dois tipos de `box`

    Ambos **herdam** de `box`: só mudam a forma de escolher as células.

    - **`cube(n, i, j)`**: o bloco $n \times n$ número `(i, j)`. Atenção que
      aqui `i, j` são índices de **bloco** (de `0` a `n-1`), não de
      célula. O canto superior esquerdo do bloco é a célula `(i*n, j*n)`.
      Ex.: com $n = 3$, o bloco `(1, 2)` começa na célula `(3, 6)`.
    - **`path(n, inicio, fim)`**: uma linha reta de células, horizontal
      ou vertical, de `inicio` até `fim` (inclusive). Serve para linhas
      e colunas inteiras.
      Ex.: `path(3, (0, 0), (0, 8))` é a linha 0 inteira.
    """)
    return


@app.cell
def _():
    class cube(box):  # cube "herda" de box: tem add, matriz, etc. sem os reescrever
        """Bloco n x n de índices (i, j), com 0 <= i, j < n (R2).

        O canto superior esquerdo é a célula (i*n, j*n).
        """

        def __init__(self, n, i, j):
            super().__init__(n)  # corre o construtor do box: cria o grupo vazio
            if not (0 <= i < n and 0 <= j < n):  # índices de bloco válidos?
                raise ValueError(f"Índices de bloco ({i}, {j}) fora de [0, {n})")
            for a in range(n):  # a = deslocamento na vertical dentro do bloco
                for b in range(n):  # b = deslocamento na horizontal dentro do bloco
                    self.add(i * n + a, j * n + b)  # junta a célula (canto + deslocamento)

    class path(box):  # path também herda de box
        """Troço reto (horizontal ou vertical) de `inicio` até `fim`,
        inclusive (R3). Funciona nos dois sentidos."""

        def __init__(self, n, inicio, fim):
            super().__init__(n)  # cria o grupo vazio
            i1, j1 = inicio  # separa a coordenada inicial em linha e coluna
            i2, j2 = fim  # separa a coordenada final em linha e coluna
            if i1 != i2 and j1 != j2:  # nem mesma linha nem mesma coluna -> não é reto
                raise ValueError("Um path tem de ser horizontal ou vertical")

            # Direção do passo em cada eixo: -1, 0 ou +1
            di = 0  # por omissão não se mexe na vertical
            if i2 > i1:  # o fim está mais abaixo...
                di = 1  # ...então desce
            elif i2 < i1:  # o fim está mais acima...
                di = -1  # ...então sobe
            dj = 0  # por omissão não se mexe na horizontal
            if j2 > j1:  # o fim está mais à direita...
                dj = 1  # ...então anda para a direita
            elif j2 < j1:  # o fim está mais à esquerda...
                dj = -1  # ...então anda para a esquerda

            # Quantos passos dar para ir de `inicio` a `fim`
            passos = max(abs(i2 - i1), abs(j2 - j1))  # a distância maior (a outra é 0)
            for k in range(passos + 1):  # +1 para incluir a célula final
                self.add(i1 + k * di, j1 + k * dj)  # célula k passos à frente do início

    return cube, path  # disponibiliza as duas classes às outras células


@app.cell
def _(mo):
    mo.md(r"""
    ## Passo 3: pistas aleatórias

    `pistas_aleatorias(n, k)` devolve um `box` com `k` células sorteadas,
    cada uma com um valor sorteado. Os dois sorteios usam
    `random.sample`, que escolhe **sem repetição**, e por isso:

    - não saem duas pistas na mesma célula;
    - não saem dois valores iguais (o grupo das pistas também é "todos
      diferentes"), o que obriga a $k \le N$.

    Se não indicarmos `k`, usa-se `k = n`.

    > Nada garante que as pistas sorteadas tenham solução. Isso é tratado
    >  em `gerar_e_resolver`, e demonstrado na secção
    > "Puzzles sem solução".
    """)
    return


@app.cell
def _(random):
    def pistas_aleatorias(n, k=None):
        """Devolve um `box` com k células aleatórias, cada uma fixa a um
        valor aleatório de [1, N] (R4). Por omissão k = n.

        Os valores são distintos entre si porque o próprio grupo das pistas
        fica sujeito a "todos diferentes" no modelo; por isso k <= N.
        """
        N = n * n  # tamanho da grelha
        if k is None:  # se não nos disseram quantas pistas...
            k = n  # ...usamos n
        if not (0 <= k <= N):  # mais de N pistas nunca podiam ser todas diferentes
            raise ValueError(f"k tem de estar em [0, {N}]")

        # Lista de todas as células possíveis: (0,0), (0,1), ..., (N-1,N-1)
        todas = [(i, j) for i in range(N) for j in range(N)]
        posicoes = random.sample(todas, k)  # sorteia k posições diferentes
        valores = random.sample(range(1, N + 1), k)  # sorteia k valores diferentes de 1 a N

        pistas = box(n)  # grupo vazio onde vamos pôr as pistas
        # zip junta as duas listas par a par: (posição 1, valor 1), (posição 2, valor 2), ...
        for (i, j), val in zip(posicoes, valores):
            pistas.add(i, j, val)  # junta a célula (i, j) fixa ao valor val
        return pistas  # devolve o box com as k pistas

    return (pistas_aleatorias,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Passo 4: o modelo `SudokuCSP`

    Esta é a ponte para o solver. O que acontece:

    1. **Construção.** Para cada célula cria-se uma variável inteira
       `x[i][j]` com valores possíveis de 1 a `N`. Ainda não há valores,
       só "incógnitas".
    2. **`adicionar(*grupos)`.** Para cada grupo impõe-se
       `add_all_different` (todas as variáveis diferentes) e, para as
       células com valor fixo, `x[i][j] == val`. O método não quer saber
       se o grupo é uma linha, um bloco ou as pistas, e é aqui que a
       abstração `box` compensa.
    3. **`resolver()`.** Entrega o modelo ao CP-SAT. Devolve a grelha
       preenchida, ou `None` se não houver solução.

    Quando devolve `None`, o motivo fica em `modelo.estado`:

    | Estado | Significado |
    |---|---|
    | `OPTIMAL` / `FEASIBLE` | encontrou solução |
    | `INFEASIBLE` | provou que **não existe** solução |
    | `UNKNOWN` | acabou o tempo (`tempo_max`) sem concluir |
    """)
    return


@app.cell
def _(cp_model):
    class SudokuCSP:
        """Modelo CSP de uma grelha N x N (R5).

        Uma variável inteira por célula, com domínio [1, N].
        """

        def __init__(self, n):
            self.n = n  # guarda o parâmetro do Sudoku
            self.N = n * n  # tamanho da grelha
            self.modelo = cp_model.CpModel()  # o "caderno" onde se escrevem as regras
            # x[i][j] é a variável da célula (i, j): uma lista de linhas
            self.x = []  # começa sem linhas
            for i in range(self.N):  # para cada linha da grelha...
                linha = []  # ...cria uma lista vazia
                for j in range(self.N):  # para cada coluna dessa linha...
                    # ...cria uma variável inteira com valores de 1 a N e um nome para depuração
                    linha.append(self.modelo.new_int_var(1, self.N, f"x_{i}_{j}"))
                self.x.append(linha)  # junta a linha completa à matriz de variáveis
            self.estado = None  # ainda não resolvemos; preenchido por resolver()

        def adicionar(self, *grupos):  # o * permite receber quantos grupos quisermos
            """Recebe qualquer número de grupos (box, cube, path, pistas...)
            e, para cada um, impõe "todos diferentes" e fixa as células
            com valor. Não distingue a origem dos grupos."""
            for g in grupos:  # trata cada grupo da mesma forma
                # Evita misturar um grupo de uma grelha 4x4 com uma 9x9
                if g.n != self.n:
                    raise ValueError("O grupo foi criado para outro n")
                # As variáveis das células do grupo...
                variaveis = [self.x[i][j] for (i, j) in g.celulas]
                # ...têm de ser todas diferentes
                self.modelo.add_all_different(variaveis)
                # Células com valor fixo (as pistas): x[i][j] == val
                for (i, j), val in g.celulas.items():  # percorre as células do grupo
                    if val is not None:  # se a célula está fixa...
                        self.modelo.add(self.x[i][j] == val)  # ...obriga a variável a esse valor

        def resolver(self, tempo_max=60):  # tempo_max em segundos (60 por omissão)
            """Devolve a grelha preenchida (lista de listas) ou None se
            não houver solução. O motivo fica em self.estado
            ("INFEASIBLE" = sem solução, "UNKNOWN" = acabou o tempo)."""
            solver = cp_model.CpSolver()  # cria o "resolvedor"
            solver.parameters.max_time_in_seconds = tempo_max  # limite de tempo
            resultado = solver.solve(self.modelo)  # resolve o modelo (é aqui que se faz o trabalho)
            self.estado = solver.status_name(resultado)  # guarda o estado em texto ("OPTIMAL", ...)

            if resultado == cp_model.OPTIMAL or resultado == cp_model.FEASIBLE:  # encontrou solução?
                # Lê o valor que o solver escolheu para cada variável
                grelha = []  # grelha da solução, começa vazia
                for i in range(self.N):  # para cada linha...
                    # ...lê os valores das N variáveis dessa linha
                    grelha.append([solver.value(self.x[i][j]) for j in range(self.N)])
                return grelha  # devolve a solução
            return None  # não há solução (ou acabou o tempo)

    return (SudokuCSP,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Passo 5: as restrições C1, C2 e C3

    Cada função devolve uma **lista de grupos**:

    | Função | Devolve | Como |
    |---|---|---|
    | `restricao_linhas(n)` | $N$ grupos (C1) | um `path` horizontal por linha |
    | `restricao_colunas(n)` | $N$ grupos (C2) | um `path` vertical por coluna |
    | `restricao_blocos(n)` | $n^2$ grupos (C3) | um `cube` por bloco |

    Depois `grupos_sudoku(n)` junta as três listas numa só (em Python,
    `lista1 + lista2` concatena). As pistas (C4) ficam de fora porque
    mudam a cada puzzle, enquanto linhas, colunas e blocos são sempre iguais.
    """)
    return


@app.cell
def _(path):
    def restricao_linhas(n):
        """C1: uma linha = um `path` horizontal, todas diferentes."""
        N = n * n  # tamanho da grelha
        # para cada linha i: path da coluna 0 até à coluna N-1
        return [path(n, (i, 0), (i, N - 1)) for i in range(N)]

    return (restricao_linhas,)


@app.cell
def _(path):
    def restricao_colunas(n):
        """C2: uma coluna = um `path` vertical, todas diferentes."""
        N = n * n  # tamanho da grelha
        # para cada coluna j: path da linha 0 até à linha N-1
        return [path(n, (0, j), (N - 1, j)) for j in range(N)]

    return (restricao_colunas,)


@app.cell
def _(cube):
    def restricao_blocos(n):
        """C3: um bloco n x n = um `cube`, todas diferentes."""
        # um cube para cada par de índices de bloco (i, j), com i e j de 0 a n-1
        return [cube(n, i, j) for i in range(n) for j in range(n)]

    return (restricao_blocos,)


@app.cell
def _(restricao_blocos, restricao_colunas, restricao_linhas):
    def grupos_sudoku(n):
        """Junta C1 + C2 + C3 (as pistas, C4, vêm à parte) (R6)."""
        return (
            restricao_linhas(n)  # lista das linhas
            + restricao_colunas(n)  # + lista das colunas
            + restricao_blocos(n)  # + lista dos blocos = uma só lista
        )

    return (grupos_sudoku,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Passo 6: gerar e resolver

    `gerar_e_resolver` junta tudo o que construímos. Em cada tentativa:

    1. sorteia pistas;
    2. cria um modelo novo e adiciona linhas + colunas + blocos
       (+ grupos `extra`, se existirem, como diagonais) + pistas;
    3. tenta resolver. Se houver solução, termina; senão sorteia outras
       pistas.

    Devolve **três coisas**: as pistas usadas, a solução (ou `None`) e o
    número de tentativas feitas. Em Python, uma função pode devolver um
    tuplo e quem a chama separa-o: `pistas, sol, t = gerar_e_resolver(3)`.

    Porque é preciso repetir? Porque pistas todas diferentes **não
    garantem** que o puzzle tenha solução (ver o caso B mais abaixo).
    """)
    return


@app.cell
def _(SudokuCSP, grupos_sudoku, pistas_aleatorias):
    def gerar_e_resolver(n, k=None, extra=None, tentativas=20):
        """Fluxo completo: pistas aleatórias -> linhas + colunas + blocos + pistas -> resolver.

        `extra` é uma lista opcional de grupos adicionais (ex.: diagonais).
        Se as pistas tornarem o puzzle impossível, sorteia outras.

        Devolve (pistas, solucao, numero_de_tentativas);
        solucao é None se nenhuma tentativa resultou.
        """
        if extra is None:  # se não há grupos extra...
            extra = []  # ...usa uma lista vazia (assim o *extra abaixo não dá erro)
        for t in range(1, tentativas + 1):  # t = 1, 2, ..., tentativas
            pistas = pistas_aleatorias(n, k)  # 1. sorteia pistas novas
            modelo = SudokuCSP(n)  # 2. cria um modelo novo (vazio)
            modelo.adicionar(*grupos_sudoku(n))  # junta linhas + colunas + blocos
            modelo.adicionar(*extra)  # junta os grupos extra (se houver)
            modelo.adicionar(pistas)  # junta as pistas
            solucao = modelo.resolver()  # 3. tenta resolver
            if solucao is not None:  # se encontrou solução...
                return pistas, solucao, t  # ...devolve tudo e acaba aqui
        return pistas, None, tentativas  # nenhuma tentativa resultou

    return (gerar_e_resolver,)


@app.cell
def _(SudokuCSP, grupos_sudoku, random):
    def pistas_por_bloco(n, por_bloco=3):
        """Devolve uma lista de `box`, um por bloco, cada um com
        `por_bloco` células fixas.

        Os valores vêm de uma grelha completa sorteada, por isso o
        puzzle tem sempre solução.
        """
        N = n * n  # tamanho da grelha
        if not (0 <= por_bloco <= N):  # um bloco só tem N células
            raise ValueError(f"por_bloco tem de estar em [0, {N}]")

        # 1. Grelha completa aleatória: baralha a primeira linha
        #    e deixa o solver completar o resto
        primeira = box(n)  # grupo para a primeira linha
        valores = random.sample(range(1, N + 1), N)  # os números 1..N por ordem aleatória
        for j in range(N):  # para cada coluna da primeira linha...
            primeira.add(0, j, valores[j])  # ...fixa o valor sorteado
        modelo = SudokuCSP(n)  # modelo novo
        modelo.adicionar(*grupos_sudoku(n))  # regras do Sudoku
        modelo.adicionar(primeira)  # primeira linha fixa
        completa = modelo.resolver()  # o solver preenche o resto da grelha

        # 2. Em cada bloco, escolhe `por_bloco` células ao calhas
        #    e copia o valor que têm na grelha completa
        lista = []  # lista de grupos de pistas (um por bloco)
        for bi in range(n):  # bi = linha do bloco
            for bj in range(n):  # bj = coluna do bloco
                # todas as células deste bloco
                celulas = [(bi * n + a, bj * n + b)
                           for a in range(n) for b in range(n)]
                pistas_bloco = box(n)  # grupo vazio para as pistas deste bloco
                for (i, j) in random.sample(celulas, por_bloco):  # sorteia por_bloco células
                    pistas_bloco.add(i, j, completa[i][j])  # fixa-as ao valor da grelha completa
                lista.append(pistas_bloco)  # guarda o grupo deste bloco
        return lista  # devolve um grupo de pistas por bloco

    return (pistas_por_bloco,)


@app.cell
def _(path):
    def validar_grelha(grelha, n):
        """True se cada linha, coluna e bloco tem exatamente 1..N."""
        N = n * n  # tamanho da grelha
        esperado = set(range(1, N + 1))  # o conjunto {1, 2, ..., N}

        for i in range(N):  # verifica cada linha
            if set(grelha[i]) != esperado:  # um set tira os repetidos: só é igual se não faltar nada
                return False  # linha inválida

        for j in range(N):  # verifica cada coluna
            col = {grelha[i][j] for i in range(N)}  # conjunto dos valores da coluna j
            if col != esperado:
                return False  # coluna inválida

        for bi in range(n):  # verifica cada bloco: linha do bloco...
            for bj in range(n):  # ...e coluna do bloco
                bloco = set()  # conjunto vazio para os valores do bloco
                for a in range(n):  # percorre as n linhas do bloco
                    for b in range(n):  # e as n colunas do bloco
                        bloco.add(grelha[bi * n + a][bj * n + b])  # junta o valor ao conjunto
                if bloco != esperado:
                    return False  # bloco inválido
        return True  # passou todas as verificações

    def validar_pistas(grelha, pistas):
        """True se todas as pistas mantêm o seu valor na solução."""
        for (i, j), val in pistas.celulas.items():  # percorre as pistas
            if val is not None and grelha[i][j] != val:  # a solução mudou o valor da pista?
                return False
        return True  # todas as pistas foram respeitadas

    def testar_add_rejeita(n):
        """True se `add` rejeita coordenadas e valores inválidos."""
        N = n * n  # tamanho da grelha
        casos_invalidos = [  # lista de (linha, coluna, valor) que DEVEM dar erro
            (-1, 0, None),   # linha negativa
            (N, 0, None),    # linha demasiado grande
            (0, N, None),    # coluna demasiado grande
            (0, 0, 0),       # valor abaixo de 1
            (0, 0, N + 1),   # valor acima de N
        ]
        for i, j, val in casos_invalidos:  # testa cada caso
            try:  # tenta executar...
                box(n).add(i, j, val)
                return False  # chegou aqui sem erro -> o add não rejeitou: teste falha
            except ValueError:  # ...se der ValueError, era o esperado
                pass  # não faz nada e passa ao caso seguinte
        return True  # todos os casos foram rejeitados

    def testar_path_sentidos(n):
        """True se um path dá as mesmas células nos dois sentidos."""
        N = n * n  # tamanho da grelha
        ida = path(n, (0, 0), (0, N - 1))  # linha 0 da esquerda para a direita
        volta = path(n, (0, N - 1), (0, 0))  # linha 0 da direita para a esquerda
        # as mesmas células nos dois sentidos, e N células no total
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
        N = n * n  # tamanho da grelha
        fixas = {}  # por omissão não há pistas para destacar
        if pistas is not None:  # se recebemos pistas...
            fixas = pistas.celulas  # ...usamos o dicionário delas

        # início da tabela HTML (bordas coladas, letra de largura fixa)
        html = '<table style="border-collapse: collapse; font-family: monospace;">'
        for i in range(N):  # para cada linha da grelha...
            html += "<tr>"  # ...abre uma linha da tabela
            for j in range(N):  # para cada coluna...
                estilo = (  # estilo base da célula: tamanho, centrada, borda fina
                    "width: 2em; height: 2em; text-align: center;"
                    "border: 1px solid #999;"
                )
                # Linhas mais grossas nas fronteiras dos blocos
                if i % n == 0:  # primeira linha de um bloco
                    estilo += "border-top: 2px solid currentColor;"
                if j % n == 0:  # primeira coluna de um bloco
                    estilo += "border-left: 2px solid currentColor;"
                if i == N - 1:  # última linha da grelha
                    estilo += "border-bottom: 2px solid currentColor;"
                if j == N - 1:  # última coluna da grelha
                    estilo += "border-right: 2px solid currentColor;"
                if fixas.get((i, j)) is not None:  # esta célula é uma pista?
                    estilo += "font-weight: bold; color: #c0392b;"  # negrito e vermelho

                texto = str(grelha[i][j]) if grelha[i][j] != 0 else ""  # 0 aparece vazio
                html += f'<td style="{estilo}">{texto}</td>'  # acrescenta a célula
            html += "</tr>"  # fecha a linha da tabela
        html += "</table>"  # fecha a tabela
        return mo.Html(html)  # devolve o HTML para o Marimo mostrar

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
    slider_n = mo.ui.slider(2, 5, value=3, label="n")  # slider de 2 a 5, começa em 3
    botao = mo.ui.run_button(label="Gerar novo puzzle")  # botão que faz a célula correr de novo
    return botao, slider_n


@app.cell
def _(mo, slider_n):
    slider_k = mo.ui.slider(  # slider das pistas: o máximo depende de n (N = n²)
        0, slider_n.value ** 2, value=slider_n.value, label="k (pistas)"
    )
    mo.hstack([slider_n, slider_k])  # mostra os dois sliders lado a lado
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
    _ = botao.value  # ler o botão faz a célula correr de novo a cada clique
    _n = slider_n.value  # valor de n escolhido no slider
    _pistas, _sol, _t = gerar_e_resolver(_n, slider_k.value)  # gera e resolve um puzzle

    if _sol is None:  # não houve solução em nenhuma tentativa
        _saida = mo.md(f"**Sem solução** ao fim de {_t} tentativas.")
    else:  # houve solução: monta o que se vai mostrar
        _saida = mo.vstack([  # vstack empilha na vertical
            botao,  # o botão por cima
            mo.hstack([  # hstack põe lado a lado
                mo.vstack([mo.md("**Pistas**"), mostrar(_pistas.matriz(), _n, _pistas)]),
                mo.vstack([mo.md("**Solução**"), mostrar(_sol, _n, _pistas)]),
            ], justify="start", gap=2),  # alinhado à esquerda, com espaço entre as grelhas
            mo.md(  # linha de resumo por baixo
                f"Tentativas: {_t} · Grelha válida: {validar_grelha(_sol, _n)}"
                f" · Pistas respeitadas: {validar_pistas(_sol, _pistas)}"
            ),
        ])
    _saida  # a última expressão de uma célula é o que o Marimo mostra
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
    def _marca(ok):  # converte True/False em texto para a tabela
        return "yes" if ok else "no"

    # cabeçalho da tabela em Markdown
    _linhas = ["| n | grelha válida | pistas respeitadas | add rejeita inválidos | path nos 2 sentidos |",
               "|---|---|---|---|---|"]
    for _n in (2, 3):  # testa com grelhas 4x4 e 9x9
        _pistas, _sol, _t = gerar_e_resolver(_n)  
        _grelha_ok = _sol is not None and validar_grelha(_sol, _n)  # solução existe e é válida?
        _pistas_ok = _sol is not None and validar_pistas(_sol, _pistas)  # pistas respeitadas?
        _linhas.append(  # acrescenta uma linha à tabela com os 4 resultados
            f"| {_n} | {_marca(_grelha_ok)} | {_marca(_pistas_ok)} "
            f"| {_marca(testar_add_rejeita(_n))} | {_marca(testar_path_sentidos(_n))} |"
        )
    mo.md("\n".join(_linhas))  # junta as linhas com quebras de linha e mostra a tabela
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Puzzles sem solução

    `resolver()` devolve `None` e deixa o motivo em `modelo.estado`.
    `"INFEASIBLE"` quer dizer que o puzzle é mesmo impossível, e
    `"UNKNOWN"` que o tempo acabou antes de se saber.

    Dois exemplos construídos à mão, para $n = 2$ (grelha $4 \times 4$):

    - **A, valor repetido.** Duas pistas fixam `(0,0) = 1` e `(0,1) = 1`.
      Estão na mesma linha, por isso a restrição C1 falha.
    - **B, célula sem valor possível.** A linha 0 tem `1 2 3` e a coluna 3
      já tem um `4` em `(1,3)`. A linha pede `(0,3) = 4`, mas a coluna
      não deixa. As pistas são todas diferentes entre si, por isso o grupo
      das pistas está válido, e o conflito só aparece quando se juntam
      linhas, colunas e blocos.

    O caso B mostra porque é que o sorteio sem repetição **não chega** para
    garantir um puzzle solúvel, e porque é que `gerar_e_resolver` precisa
    de tentar outra vez.
    """)
    return


@app.cell
def _(SudokuCSP, grupos_sudoku):
    def _resolver_com(n, *grupos_pistas):  # função auxiliar (privada a esta célula)
        modelo = SudokuCSP(n)  # modelo novo
        modelo.adicionar(*grupos_sudoku(n))  # regras do Sudoku
        modelo.adicionar(*grupos_pistas)  # as pistas do caso a testar
        return modelo.resolver(), modelo.estado  # devolve a solução (ou None) e o estado

    def sem_solucao_valor_repetido():
        """A: duas pistas iguais na mesma linha, em grupos separados."""
        a = box(2); a.add(0, 0, 1)  # grupo a: célula (0,0) = 1
        b = box(2); b.add(0, 1, 1)  # grupo b: célula (0,1) = 1 (mesma linha!)
        return _resolver_com(2, a, b)  # grupos separados para não ser o box a acusar o erro

    def sem_solucao_celula_sem_valor():
        """B: pistas distintas, mas (0,3) fica sem valor possível."""
        p = box(2)  # um só grupo de pistas
        p.add(0, 0, 1); p.add(0, 1, 2); p.add(0, 2, 3)  # linha 0 = 1 2 3 _
        p.add(1, 3, 4)  # coluna 3 já tem um 4, por isso (0,3) não pode ser 4
        return _resolver_com(2, p)

    return sem_solucao_celula_sem_valor, sem_solucao_valor_repetido


@app.cell
def _(mo, sem_solucao_celula_sem_valor, sem_solucao_valor_repetido):
    _casos = [  # lista de (descrição, função que monta e resolve o caso)
        ("A: duas pistas com valor 1 na linha 0", sem_solucao_valor_repetido),
        ("B: linha 0 = 1 2 3 _ e coluna 3 já tem 4", sem_solucao_celula_sem_valor),
    ]
    _linhas = ["| caso | solução | estado | correto? |", "|---|---|---|---|"]  # cabeçalho
    for _nome, _f in _casos:  # para cada caso...
        _sol, _estado = _f()  # ...corre a função
        _ok = _sol is None and _estado == "INFEASIBLE"  # o esperado: sem solução, provado
        _linhas.append(f"| {_nome} | {_sol} | {_estado} | {'yes' if _ok else 'no'} |")
    mo.md("\n".join(_linhas))  
    return


@app.cell
def _(
    SudokuCSP,
    grupos_sudoku,
    mo,
    mostrar,
    pistas_por_bloco,
    validar_grelha,
    validar_pistas,
):
    _n = 3  # Sudoku clássico 9x9
    _lista = pistas_por_bloco(_n, por_bloco=3)  # 9 grupos, cada um com 3 pistas

    _modelo = SudokuCSP(_n)  
    _modelo.adicionar(*grupos_sudoku(_n))  # regras do Sudoku
    _modelo.adicionar(*_lista)  # um grupo de pistas por bloco
    _sol = _modelo.resolver()  

    # Junta as pistas num só box APENAS para mostrar e validar
    # (este box não entra no modelo, porque 27 pistas não podiam ser todas diferentes)
    _todas = box(_n)
    for _p in _lista:  # para cada grupo de pistas...
        for (_i, _j), _v in _p.celulas.items():  # ...e cada pista dentro dele
            _todas.add(_i, _j, _v)  # junta-a ao box de apresentação

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


@app.cell
def _(mo):
    mo.md(r"""
    ## Utilização de LLMs

    Neste trabalho usámos o Claude, através de claude.ai.

    O LLM ajudou-nos a estruturar o início do projeto e a perceber a
    estrutura pedida no enunciado (a abstração `box` e as suas
    especializações).

    Nenhuma resposta do LLM foi aceite sem ser executada e testada.
    Link: https://claude.ai/share/c00ad75c-5111-48f9-9c65-902284ac7b8e

    ### Verificação

    Todo o código gerado foi executado e verificado pelos testes automáticos
    do notebook: cada linha, coluna e bloco contém $1 \ldots n^2$ sem
    repetições, as pistas são respeitadas e entradas inválidas são
    rejeitadas. Testámos também grelhas $4 \times 4$ e $9 \times 9$.
    """)
    return


if __name__ == "__main__":  
    app.run()  