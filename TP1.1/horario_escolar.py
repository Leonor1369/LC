# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.24.2",
#     "ortools>=9.10",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="full")


@app.cell
def _():
    # Bibliotecas principais do notebook:
    # - marimo: interface e visualização do documento interativo;
    # - os: acesso às pastas de dados e caminhos dos CSV;
    # - deepcopy: cópia segura dos dados para testes de sabotagem;
    # - DictReader: leitura dos ficheiros CSV em formato tabular;
    # - cp_model: solver CP-SAT do OR-Tools para o problema de horário.
    import marimo as mo
    import os
    from copy import deepcopy
    from csv import DictReader
    from ortools.sat.python import cp_model

    return DictReader, cp_model, deepcopy, mo, os


@app.cell
def _(mo):                                                                                                                             
    mo.md(r"""
    # Gerador de horário escolar

    Trabalho prático de **Lógica Computacional**: um problema de
    planeamento estático. Temos **recursos** (professores,
    salas, tempos da semana) e **compromissos** (as aulas que cada turma
    tem de ter). Procuramos uma alocação que cumpra as restrições e,
    entre as soluções válidas, minimize os buracos dos professores.

    A resolução segue os três níveis da aula:

    1. **SAT** — construir um modelo CP-SAT com R1–R7 e pedir uma
       atribuição viável às variáveis.
    2. **Optimização** — entre as soluções do SAT, minimizar O1
       (buracos) no horário inicial H0; no H1 incremental, maximizar
       as aulas que ficam no mesmo sítio.
    3. **Verificação** — a função `verificar` **não usa o
       solver**: percorre o horário gerado e confirma R1–R8 com ciclos
       simples (uma testemunha independente).

    **Porque CP-SAT e não o SCIP da ficha 3?** A ficha modela um
    horário com programação linear inteira (`pywraplp`). Aqui as
    restrições são típicas de *constraint programming* (exactamente
    uma colocação por sessão, blocos de 2 tempos, capacidade por
    tipo de sala). O CP-SAT do OR-Tools é a ferramenta sugerida no
    enunciado para este tipo de modelo discreto.

    Os dados vêm sempre de CSV (R8). Mudar de escola = mudar a pasta.
    """)
    return

@app.cell
def _(mo):
    mo.md(r"""
    ## Mapa do documento: o que é o quê
 
    Este trabalho mistura três tipos de coisas que convém não confundir.
    O documento está organizado para as manter separadas.
 
    | Tipo | O que é | Onde está | Quem o garante |
    |---|---|---|---|
    | **Restrição obrigatória** (R1–R7) | Regras que **qualquer** horário tem de cumprir. Se uma falhar, o horário é inválido. | Secção 2 (Parte A) | O solver (modelo CP-SAT); confirmado por `verificar` |
    | **Restrição sobre os dados** (R8) | Os dados vêm de CSV e são consistentes. | Secção 1 | `validar_dados` (antes do solver); confirmado por `verificar` |
    | **Objetivo de otimização** (O1) | Entre os horários válidos, preferir o que tem menos buracos. **Nunca** torna um horário inválido. | Secção 3 (Parte B) | O solver, com limite de tempo (pode não ser ótimo) |
    | **Objetivo de estabilidade** (R9) | No H1, preferir manter as sessões onde o H0 as tinha. | Secção 6 | O solver, com `AddHint` |
    | **Sala concreta** (R7) | Escolher uma sala livre e compatível para cada sessão. | Secções 2 e 4 | O modelo CP-SAT; confirmado por `verificar` |
 
    **Nota sobre a R7:** a capacidade por tipo, a escolha da sala concreta
    e as indisponibilidades por período são restrições do modelo.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Constantes da grelha

    Cinco dias, cinco tempos por dia. São a única informação fixa
    do problema (o enunciado define esta grelha); turmas, professores
    e salas vêm dos ficheiros.
    """)
    return



@app.cell
def _():
    DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex"]
    PERIODOS = [1, 2, 3, 4, 5]
    return DIAS, PERIODOS


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Dados de entrada (R8)

    Usamos `csv.DictReader` da biblioteca padrão: os ficheiros são
    pequenos e assim o notebook não depende de `pandas`.

    A leitura é uma **função da pasta**, não uma lista escrita à mão.
    O mesmo código serve para `dados/` (H0) e `dados_v2/` (H1).
    """)
    return


@app.cell
def _(DictReader):
    def ler_csv(caminho, colunas_obrigatorias):
        """Lê um CSV e recusa-o se faltar alguma coluna do enunciado."""
        with open(caminho, newline="", encoding="utf8") as ficheiro:
            # O `DictReader` devolve uma lista de dicionários, um por linha.
            reader = DictReader(ficheiro)
            # Verifica se todas as colunas obrigatórias estão presentes.
            em_falta = colunas_obrigatorias - set(reader.fieldnames or [])
            if em_falta:
                raise ValueError(f"{caminho}: faltam as colunas {sorted(em_falta)}")
            return list(reader)

    return (ler_csv,)


@app.cell
def _(mo):
    mo.md(r"""
    Antes de montar o modelo, validamos os dados: turmas únicas,
    cargas positivas, carga par nas disciplinas de duplo período,
    salas especiais que existem, professores conhecidos nas
    excepções, dias e tempos da grelha. Se isto falhar, o solver
    nem chega a correr — é consistência das restrições *sobre os
    dados*, ainda não sobre o horário.
    """)
    return


@app.cell
def _(DIAS, PERIODOS):
    def salas_concretas(salas):
        concretas = []
        for sala in salas:
            nomes = (
                [sala["sala"]]
                if sala["quantidade"] == 1
                else [f"{sala['sala']} {n}" for n in range(1, sala["quantidade"] + 1)]
            )
            tipo = "normal" if sala["tipo"] == "normal" else sala["sala"]
            concretas.extend({"sala": nome, "tipo": tipo} for nome in nomes)
        return concretas

    def validar_dados(dados):
        # Valida consistência dos dados lidos do CSV. Lança `ValueError`
        turmas = dados["turmas"]
        salas = dados["salas"]
        disciplinas = dados["disciplinas"]

        if not turmas or any(not t for t in turmas):
            raise ValueError("A lista de turmas não pode estar vazia nem ter nomes vazios.")
        if len(turmas) != len(set(turmas)):
            raise ValueError("Existem turmas repetidas.")
        if not salas or not disciplinas:
            raise ValueError("É preciso pelo menos uma sala e uma disciplina.")

        for s in salas:
            if not s["sala"] or s["tipo"] not in {"normal", "especial"}:
                raise ValueError(f"Sala inválida: {s}")
            if s["quantidade"] <= 0:
                raise ValueError(f"Quantidade de sala inválida: {s}")

        especiais = {s["sala"] for s in salas if s["tipo"] == "especial"} # 
  
        professores = {d["professor"] for d in disciplinas}
        for d in disciplinas:
            if not d["disciplina"] or not d["professor"]:
                raise ValueError(f"Disciplina ou professor vazio: {d}")
            if d["carga_semanal"] <= 0:
                raise ValueError(f"Carga semanal inválida: {d}")
            if d["duplo_periodo"] and d["carga_semanal"] % 2 != 0:
                raise ValueError(f"Carga de duplo período tem de ser par: {d}")
            if d["sala_especial"] and d["sala_especial"] not in especiais:
                raise ValueError(f"Sala especial inexistente: {d}")
            if not d["sala_especial"] and not any(s["tipo"] == "normal" for s in salas):
                raise ValueError(f"{d['disciplina']} precisa de sala normal e não há.")

        # Valida consistência das excepções de disponibilidade do professor.
        vistos = set()
        for e in dados["disponibilidade_excecoes"]:
            chave = (e["professor"], e["dia"], e["periodo"])
            if e["professor"] not in professores:
                raise ValueError(f"Professor desconhecido: {e}")
            if e["dia"] not in DIAS or e["periodo"] not in PERIODOS:
                raise ValueError(f"Dia ou período inválido: {e}")
            if chave in vistos:
                raise ValueError(f"Excepção repetida: {e}")
            vistos.add(chave)

        # Valida consistência das indisponibilidades de salas concretas.
        nomes_salas = {s["sala"] for s in salas_concretas(salas)}
        vistos_salas = set()
        for e in dados.get("disponibilidade_salas", []):
            chave = (e["sala"], e["dia"], e["periodo"])
            if e["sala"] not in nomes_salas:
                raise ValueError(f"Sala desconhecida na indisponibilidade: {e}")
            if e["dia"] not in DIAS or e["periodo"] not in PERIODOS:
                raise ValueError(f"Dia ou período inválido na indisponibilidade da sala: {e}")
            if chave in vistos_salas:
                raise ValueError(f"Indisponibilidade de sala repetida: {e}")
            vistos_salas.add(chave)

    return salas_concretas, validar_dados


@app.cell
def _(mo):
    mo.md(r"""
    Os quatro ficheiros obrigatórios e um opcional:

    | Ficheiro | O que descreve |
    |---|---|
    | `turmas.csv` | nomes das turmas |
    | `salas.csv` | tipo (`normal` / `especial`) e quantas existem em simultâneo |
    | `disciplinas.csv` | currículo: professor, carga, duplo período, sala especial |
    | `disponibilidade_excecoes.csv` | tempos em que o professor **não** pode dar aulas |
    | `disponibilidade_salas.csv` (opcional) | sala concreta, dia e período em que não pode ser usada |

    O CSV opcional usa as colunas `sala`, `dia` e `periodo`. Por exemplo:

    | sala | dia | periodo |
    |---|---|---|
    | Sala Normal 2 | Sex | 3 |

    Se `quantidade` for 1, indica o nome de `salas.csv`. Se for maior
    que 1, indica o nome concreto gerado, como `Sala Normal 2`.
    """)
    return


@app.cell
def _(ler_csv, os, validar_dados):
    def carregar_dados(pasta):
        """Lê os CSV obrigatórios e o opcional de salas, depois valida os dados."""
        turmas = [
            (linha["turma"] or "").strip()
            for linha in ler_csv(os.path.join(pasta, "turmas.csv"), {"turma"})
        ]

        salas = [{
            "sala": (linha["sala"] or "").strip(),
            "tipo": (linha["tipo"] or "").strip().lower(),
            "quantidade": int(linha["quantidade"]),
        } for linha in ler_csv(
            os.path.join(pasta, "salas.csv"),
            {"sala", "tipo", "quantidade"},
        )]

        disciplinas = []
        for linha in ler_csv(os.path.join(pasta, "disciplinas.csv"), {
            "disciplina", "professor", "carga_semanal", "duplo_periodo", "sala_especial"
        }):
            duplo = (linha["duplo_periodo"] or "").strip().lower()
            if duplo not in {"sim", "nao"}:
                raise ValueError(f"duplo_periodo deve ser 'sim' ou 'nao': {duplo!r}")
            disciplinas.append({
                "disciplina": (linha["disciplina"] or "").strip(),
                "professor": (linha["professor"] or "").strip(),
                "carga_semanal": int(linha["carga_semanal"]),
                "duplo_periodo": duplo == "sim",
                "sala_especial": (linha["sala_especial"] or "").strip(),
            })

        excecoes = [{
            "professor": (linha["professor"] or "").strip(),
            "dia": (linha["dia"] or "").strip(),
            "periodo": int(linha["periodo"]),
        } for linha in ler_csv(
            os.path.join(pasta, "disponibilidade_excecoes.csv"),
            {"professor", "dia", "periodo"},
        )]

        caminho_salas = os.path.join(pasta, "disponibilidade_salas.csv")
        indisponibilidades_salas = []
        if os.path.exists(caminho_salas):
            indisponibilidades_salas = [{
                "sala": (linha["sala"] or "").strip(),
                "dia": (linha["dia"] or "").strip(),
                "periodo": int(linha["periodo"]),
            } for linha in ler_csv(
                caminho_salas,
                {"sala", "dia", "periodo"},
            )]

        dados = {
            "pasta": pasta,
            "turmas": turmas,
            "salas": salas,
            "disciplinas": disciplinas,
            "disponibilidade_excecoes": excecoes,
            "disponibilidade_salas": indisponibilidades_salas,
        }
        validar_dados(dados)
        return dados

    return (carregar_dados,)


@app.cell
def _(carregar_dados):
    PASTA_DADOS = "dados"
    dados = carregar_dados(PASTA_DADOS)
    return (dados,)


@app.cell
def _(dados, mo):
    disciplinas_tabela = [{
        "Disciplina": d["disciplina"],
        "Professor": d["professor"],
        "Carga por turma": d["carga_semanal"],
        "Duplo": "sim" if d["duplo_periodo"] else "não",
        "Sala especial": d["sala_especial"] or "—",
    } for d in dados["disciplinas"]]
    salas_tabela = [
        {"Sala": s["sala"], "Tipo": s["tipo"], "Quantidade": s["quantidade"]}
        for s in dados["salas"]
    ]
    excecoes_tabela = [
        {"Professor": e["professor"], "Dia": e["dia"], "Tempo": e["periodo"]}
        for e in dados["disponibilidade_excecoes"]
    ]
    salas_indisponiveis_tabela = [
        {"Sala": e["sala"], "Dia": e["dia"], "Tempo": e["periodo"]}
        for e in dados["disponibilidade_salas"]
    ]

    mo.vstack([
        mo.md(f"### Dados lidos de `{dados['pasta']}/`"),
        mo.md("**Turmas:** " + ", ".join(dados["turmas"])),
        mo.md("**Disciplinas**"),
        mo.ui.table(disciplinas_tabela, selection=None),
        mo.md("**Salas**"),
        mo.ui.table(salas_tabela, selection=None),
        mo.md("**Exceções de disponibilidade** (o professor *não* está livre)"),
        mo.ui.table(excecoes_tabela, selection=None, page_size=20),
        mo.md("**Salas temporariamente indisponíveis**"),
        mo.ui.table(salas_indisponiveis_tabela, selection=None, page_size=20),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Parte A — Restrições obrigatórias (R1–R7)
 
    > Tudo o que está nesta parte é **obrigatório**: um horário que
    > viole qualquer uma destas regras é inválido, por mais bonito que
    > pareça. Ainda não há nenhum objetivo a otimizar.
 
    ### Modelo: sessões e matriz de alocação
 
    Na ficha 3 a variável era $x_{p,s,d,h}$ (professor × sala × dia ×
    hora). Aqui o compromisso atómico é uma **sessão**:
 
    - uma aula de 1 tempo, ou
    - um bloco de 2 tempos seguidos (disciplinas com `duplo_periodo=sim`).
 
    Exemplo: Matemática, carga 4 → 4 sessões de 1 tempo **por turma**.
    Educação Física, carga 2 e duplo → 1 sessão de 2 tempos por turma.
 
    Variável booleana (matriz de alocação):
 
    $$x_{i,d,h} = 1 \iff \text{a sessão } i \text{ começa no dia } d \text{ no tempo } h.$$
 
    Só criamos a variável se o bloco cabe no dia (um duplo não pode
    começar no 5.º tempo). O mapa `ocupacao[(dia, tempo)]` lista as
    sessões que **ocupam** esse tempo — um duplo que começa em 4
    aparece em 4 e em 5. As limitações R1, R5, R6 e R7 leem este mapa.
 
    Na linguagem da aula:
 
    - **Obrigações** (animação): R2 — cada sessão acontece exactamente
      uma vez.
    - **Limitações** (segurança): R1, R3, R5, R6, R7 — «não pode».
    - **R4** fica na representação: um bloco é *uma* variável que
      ocupa dois tempos consecutivos.
    """)
    return


@app.cell
def _(DIAS, PERIODOS):
    def construir_sessoes(turmas, disciplinas):
        """Uma sessão por cada bloco que a carga da disciplina exige."""
        sessoes = []
        for turma in turmas:
            for d in disciplinas:
                duracao = 2 if d["duplo_periodo"] else 1
                n_blocos = d["carga_semanal"] // duracao # divisao inteira arredonda para baixo
                # Cada bloco é uma sessão separada, mesmo que sejam da mesma disciplina.
                for _ in range(n_blocos):
                    sessoes.append({
                        "turma": turma,
                        "disciplina": d["disciplina"],
                        "professor": d["professor"],
                        "duracao": duracao,
                        "sala_especial": d["sala_especial"],
                    })
        return sessoes

    def tipo_de_sala(sessao):
        """Chave de capacidade: 'normal' ou o nome da sala especial."""
        return sessao["sala_especial"] or "normal"

    def criar_variaveis(model, sessoes):
        x = {}
        ultimo = PERIODOS[-1] # último tempo do dia
        for i, sessao in enumerate(sessoes):
            for dia in DIAS:
                for inicio in PERIODOS:
                    if inicio + sessao["duracao"] - 1 <= ultimo:
                        x[(i, dia, inicio)] = model.NewBoolVar(f"x_{i}_{dia}_{inicio}") # 
        return x

    def mapa_ocupacao(x, sessoes):
        ocupacao = {(dia, p): [] for dia in DIAS for p in PERIODOS}
        for (i, dia, inicio), var in x.items():
            fim = inicio + sessoes[i]["duracao"]
            for p in range(inicio, fim):
                ocupacao[(dia, p)].append((i, var)) 
        return ocupacao

    return construir_sessoes, criar_variaveis, mapa_ocupacao, tipo_de_sala


@app.cell
def _(mo):
    mo.md(r"""
    ### R2 — obrigação: carga semanal exacta

    `construir_sessoes` já cria `carga // duração` sessões. Falta
    obrigar cada uma a ser marcada **exactamente uma vez** na semana
    (`AddExactlyOne`).
    """)
    return


@app.function
def r2_cada_sessao_uma_vez(model, x, sessoes):
    for i in range(len(sessoes)):
        escolhas = [var for (j, _, _), var in x.items() if j == i]
        model.AddExactlyOne(escolhas)


@app.cell
def _(mo):
    mo.md(r"""
    ### R1 — limitação: uma turma, uma aula de cada vez

    Em cada `(dia, tempo)`, a soma das sessões da mesma turma que
    ocupam esse tempo é $\le 1$.
    """)
    return


@app.function
def r1_turmas(model, ocupacao, sessoes, dados):
    for tempo in ocupacao:
        for turma in dados["turmas"]:
            da_turma = [
                var for (i, var) in ocupacao[tempo]
                if sessoes[i]["turma"] == turma
            ]
            if len(da_turma) > 1:
                model.Add(sum(da_turma) <= 1)


@app.cell
def _(mo):
    mo.md(r"""
    ### R5 — limitação: um professor, uma aula de cada vez

    Igual à R1, agrupando por professor (mesmo que as turmas sejam
    diferentes — a Prof. Diana dá História e Inglês).
    """)
    return


@app.function
def r5_professores(model, ocupacao, sessoes, dados):
    professores = {d["professor"] for d in dados["disciplinas"]}
    for tempo in ocupacao:
        for prof in professores:
            do_prof = [
                var for (i, var) in ocupacao[tempo]
                if sessoes[i]["professor"] == prof
            ]
            if len(do_prof) > 1:
                model.Add(sum(do_prof) <= 1)


@app.cell
def _(mo):
    mo.md(r"""
    ### R3 — limitação: no máximo uma sessão da mesma disciplina por dia

    Por turma, disciplina e dia, somamos as variáveis que **começam**
    nesse dia. Um bloco duplo conta como **uma** ocorrência (é uma
    só sessão).
    """)
    return


@app.cell
def _(DIAS):
    def r3_uma_por_dia(model, x, sessoes, dados):
        for turma in dados["turmas"]:
            for d in dados["disciplinas"]:
                for dia in DIAS:
                    do_dia = [
                        var for (i, dd, _), var in x.items()
                        if dd == dia
                        and sessoes[i]["turma"] == turma
                        and sessoes[i]["disciplina"] == d["disciplina"]
                    ]
                    if len(do_dia) > 1:
                        model.Add(sum(do_dia) <= 1)

    return (r3_uma_por_dia,)


@app.cell
def _(mo):
    mo.md(r"""
    ### R4 — duplo período em tempos seguidos

    Não há uma função `r4_...`. A variável é o bloco inteiro: ocupa
    sempre `inicio` e `inicio+1` no mesmo dia (`mapa_ocupacao`). Se
    não couber, a variável **não existe**. Um tempo isolado de
    Educação Física é impossível por construção.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### R6 — limitação: disponibilidade do professor

    As excepções do CSV são tempos *proibidos*. Se uma sessão ocupa
    um desses tempos, a variável fica a 0 (nos duplos, vale para os
    dois tempos).
    """)
    return


@app.function
def r6_disponibilidade(model, ocupacao, sessoes, dados):
    indisponiveis = {
        (e["professor"], e["dia"], e["periodo"])
        for e in dados["disponibilidade_excecoes"]
    }
    for (dia, periodo) in ocupacao:
        for (i, var) in ocupacao[(dia, periodo)]:
            if (sessoes[i]["professor"], dia, periodo) in indisponiveis:
                model.Add(var == 0)


@app.cell
def _(mo):
    mo.md(r"""
    ### R7 — limitação: capacidade e disponibilidade das salas
 
    Em cada tempo, o número de sessões de um tipo de sala não pode
    passar da quantidade desse tipo. Todas as salas `normal` somam
    para o mesmo balde; cada especial (Laboratório, Ginásio) tem o
    seu.
 
    Se existir `disponibilidade_salas.csv`, as salas fechadas nesse
    dia e período não podem ser escolhidas. O solver cria uma escolha
    para cada combinação de sessão, horário e sala concreta; uma opção
    só existe se a sala estiver livre em **todos** os períodos da sessão.
    Por isso, um bloco duplo fica sempre na mesma sala. Cada sala
    concreta só pode receber uma sessão por período.
    """)
    return


@app.cell
def _(salas_concretas, tipo_de_sala):
    def criar_variaveis_sala(model, x, sessoes, dados):
        """Escolhe uma sala compatível e livre para cada aula.

        Uma aula só pode usar uma sala do tipo certo e disponível durante
        todos os seus períodos. Se a aula for marcada num horário, escolhe
        exatamente uma sala; a mesma sala não pode receber duas aulas ao
        mesmo tempo.

        `construir_modelo` chama esta função para criar as escolhas de sala.
        `r7_capacidade_salas` é chamada separadamente para limitar a
        capacidade por tipo; 
        """
        indisponiveis = {
            (e["sala"], e["dia"], e["periodo"])
            for e in dados.get("disponibilidade_salas", [])
        }
        salas = salas_concretas(dados["salas"])
        y = {}
        uso_sala = {}
        
        for (i, dia, inicio), var_inicio in x.items():
            escolhas = []
            for sala in salas:
                # Se a sessão precisa de uma sala especial, só pode ir para essa sala.
                if sala["tipo"] != tipo_de_sala(sessoes[i]):
                    continue
                # Se a sessão ocupa mais de um período, verifica se a sala está livre em todos eles.
                periodos = range(inicio, inicio + sessoes[i]["duracao"])
                # Se a sala está indisponível em qualquer período da sessão, não pode ser escolhida.
                if any(
                    (sala["sala"], dia, periodo) in indisponiveis
                    for periodo in periodos
                ):
                    continue
                var_sala = model.NewBoolVar(
                    f"sala_{i}_{dia}_{inicio}_{sala['sala']}"
                )
                
                y[(i, dia, inicio, sala["sala"])] = var_sala
                escolhas.append(var_sala)
                # Marca a sala como ocupada em todos os períodos da sessão.
                for periodo in range(inicio, inicio + sessoes[i]["duracao"]):
                    uso_sala.setdefault(
                        (sala["sala"], dia, periodo), []
                    ).append(var_sala)
            # Se a aula acontece neste horário, tem de escolher uma sala;
            # caso contrário, não escolhe nenhuma.
            model.Add(sum(escolhas) == var_inicio)
        
        # Impede que a mesma sala seja usada por duas aulas ao mesmo tempo.
        for variaveis in uso_sala.values():
            model.Add(sum(variaveis) <= 1)
        return y

    def r7_capacidade_salas(model, ocupacao, sessoes, dados):
        indisponiveis = {
            (e["sala"], e["dia"], e["periodo"])
            for e in dados.get("disponibilidade_salas", [])
        }
        salas = salas_concretas(dados["salas"])
        tipos = {sala["tipo"] for sala in salas}

        for tipo in tipos:
            for tempo in ocupacao:
                dia, periodo = tempo
                maximo = sum(
                    sala["tipo"] == tipo
                    and (sala["sala"], dia, periodo) not in indisponiveis
                    for sala in salas
                )
                a_decorrer = [
                    var for (i, var) in ocupacao[tempo]
                    if tipo_de_sala(sessoes[i]) == tipo
                ]
                model.Add(sum(a_decorrer) <= maximo)

    return criar_variaveis_sala, r7_capacidade_salas


@app.cell
def _(
    construir_sessoes,
    cp_model,
    criar_variaveis,
    criar_variaveis_sala,
    mapa_ocupacao,
    r3_uma_por_dia,
    r7_capacidade_salas,
):
    def construir_modelo(dados):
        """Variáveis + SAT (R1–R7)."""
        model = cp_model.CpModel()
        sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])
        x = criar_variaveis(model, sessoes)
        ocupacao = mapa_ocupacao(x, sessoes)
        y = criar_variaveis_sala(model, x, sessoes, dados)

        r2_cada_sessao_uma_vez(model, x, sessoes)
        r1_turmas(model, ocupacao, sessoes, dados)
        r5_professores(model, ocupacao, sessoes, dados)
        r3_uma_por_dia(model, x, sessoes, dados)
        r6_disponibilidade(model, ocupacao, sessoes, dados)
        r7_capacidade_salas(model, ocupacao, sessoes, dados)
        return model, x, y, sessoes, ocupacao

    return (construir_modelo,)


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Parte B — Objetivo de otimização O1 (minimizar buracos)
 
    > Esta parte **não** acrescenta regras: acrescenta uma
    > *preferência*. Qualquer horário da Parte A continua válido; o
    > objetivo só serve para escolher o melhor entre eles.
 
    Um **buraco** é um tempo livre *no meio* do dia: há aula antes e
    depois, no mesmo professor. Não conta chegar mais tarde de
    manhã nem ir embora mais cedo.
 
    Para cada professor e dia:
 
    - `ocupado[t] = 1` se tem aula no tempo `t` (a soma das sessões;
      a R5 garante que essa soma é 0 ou 1);
    - `buraco[t] ≥ ocupado[s] + ocupado[u] − ocupado[t] − 1`
      para todos os `s < t < u`.
 
    O solver minimiza a soma dos `buraco`. Há limite de tempo: a
    solução pode não ser óptima, mas continua a ser válida (SAT).
 
    `adicionar_buracos` acrescenta as variáveis e restrições ao modelo.
    `contar_buracos` refaz a conta no horário já extraído — é EVAL
    do objectivo, independente do modelo.
    """)
    return


@app.cell
def _(DIAS, PERIODOS):
    def adicionar_buracos(model, ocupacao, sessoes, dados):
        professores = sorted({d["professor"] for d in dados["disciplinas"]})
        buracos = []
        for prof in professores:
            for dia in DIAS:
                ocupado = {}
                for t in PERIODOS:
                    ocupado[t] = model.NewBoolVar(f"oc_{prof}_{dia}_{t}")
                    do_prof = [
                        var for (i, var) in ocupacao[(dia, t)]
                        if sessoes[i]["professor"] == prof
                    ]
                    # Se não houver nenhuma sessão do professor nesse tempo, a soma é 0.
                    model.Add(ocupado[t] == sum(do_prof))
                for t in PERIODOS:
                    buraco = model.NewBoolVar(f"buraco_{prof}_{dia}_{t}")
                    for s in PERIODOS:
                        for u in PERIODOS:
                            if s < t < u:
                                # A soma das aulas antes e depois menos a aula no tempo t menos 1
                                # deve ser menor ou igual a buraco[t]. Se houver aula antes e depois
                                # e não houver aula no tempo t, então buraco[t] deve ser 1.
                                model.Add(
                                    buraco >= ocupado[s] + ocupado[u] - ocupado[t] - 1
                                )
                    buracos.append(buraco)
        model.Minimize(sum(buracos))

    def contar_buracos(aulas, dados):
        """Conta buracos no horário final, sem usar o solver."""
        total = 0
        professores = {d["professor"] for d in dados["disciplinas"]}
        for prof in professores:
            for dia in DIAS:
                tempos = {
                    a["periodo"] for a in aulas
                    if a["professor"] == prof and a["dia"] == dia
                }
                # Um buraco é um tempo livre entre dois tempos ocupados. 
                # Se os tempos ocupados forem {1, 3, 4}, então há um buraco no tempo 2. 
                # A fórmula (max - min + 1) - len(tempos) conta quantos tempos 
                # estão entre o primeiro e o último ocupado, menos os que estão realmente ocupados.
                if tempos:
                    total += (max(tempos) - min(tempos) + 1) - len(tempos)
        return total

    return adicionar_buracos, contar_buracos


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Resolver e mostrar
 
    O CP-SAT escolhe o dia, o início e a sala concreta de cada sessão.
    Um bloco duplo usa a mesma sala nos dois períodos. Se houver um H0,
    o modelo prefere manter primeiro o horário e depois a sala antiga.
    """)
    return


@app.cell
def _(cp_model):
    def resolver(model, x, y, sessoes, limite_segundos=30):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = limite_segundos
        estado = solver.Solve(model)

        aulas = []
        if estado in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            salas_escolhidas = {
                (i, dia, inicio): sala
                for (i, dia, inicio, sala), var in y.items()
                if solver.Value(var) == 1
            }
            for (i, dia, inicio), var in x.items():
                if solver.Value(var) == 1:
                    s = sessoes[i]
                    for p in range(inicio, inicio + s["duracao"]):
                        aulas.append({
                            "sessao": i,
                            "turma": s["turma"],
                            "disciplina": s["disciplina"],
                            "professor": s["professor"],
                            "dia": dia,
                            "periodo": p,
                            "tipo_sala": s["sala_especial"] or "normal",
                            "sala_especial": s["sala_especial"],
                            "sala": salas_escolhidas[(i, dia, inicio)],
                        })
        return aulas, solver.StatusName(estado), solver.WallTime()

    return (resolver,)


@app.cell
def _(salas_concretas):
    def salas_compativeis(aula, salas):
        return [
            sala for sala in salas_concretas(salas)
            if sala["tipo"] == aula["tipo_sala"]
        ]

    return (salas_compativeis,)

@app.cell
def _(adicionar_buracos, construir_modelo, resolver):
    def gerar_horario(dados, limite_segundos=30, aulas_referencia=None):
        """H0 (minimizar buracos) ou H1 incremental (maximizar estabilidade)."""
        # Parte A: restrições obrigatórias (R1–R7)
        model, x, y, sessoes, ocupacao = construir_modelo(dados)
        # Parte B / R9: objetivo (O1 no H0; estabilidade no H1)
        if aulas_referencia is None:
            adicionar_buracos(model, ocupacao, sessoes, dados)
        else:
            preferir_horario_anterior(model, x, y, sessoes, aulas_referencia)
        aulas, estado, tempo = resolver(model, x, y, sessoes, limite_segundos)
        return aulas, estado, tempo, sessoes

    return (gerar_horario,)


@app.cell
def _(DIAS, PERIODOS, contar_buracos, mo):
    def grelha(aulas, campo, valor, mostrar):
        linhas = []
        for p in PERIODOS:
            linha = {"Tempo": f"{p}º"}
            for dia in DIAS:
                texto = "—"
                for a in aulas:
                    if a[campo] == valor and a["dia"] == dia and a["periodo"] == p:
                        extra = ", ".join(a[c] for c in mostrar)
                        texto = f"{a['disciplina']} ({extra})"
                linha[dia] = texto
            linhas.append(linha)
        return linhas

    def mostrar_horario(titulo, aulas, dados, estado, tempo, n_sessoes):
        blocos = [mo.md(
            f"### {titulo} — estado: **{estado}**, "
            f"tempo: **{round(tempo, 2)} s**, "
            f"sessões: **{n_sessoes}**, "
            f"buracos: **{contar_buracos(aulas, dados)}**"
        )]
        if not aulas:
            blocos.append(mo.md("Não foi encontrado nenhum horário válido."))
            return mo.vstack(blocos)

        professores = sorted({d["professor"] for d in dados["disciplinas"]})
        vistas = [
            ("turma", "Por turma", dados["turmas"], ["professor", "sala"]),
            ("professor", "Por professor", professores, ["turma", "sala"]),
        ]
        for campo, cabecalho, valores, mostrar in vistas:
            blocos.append(mo.md(f"#### {cabecalho}"))
            for valor in valores:
                blocos.append(mo.md(f"**{valor}**"))
                blocos.append(mo.ui.table(
                    grelha(aulas, campo, valor, mostrar),
                    selection=None,
                    pagination=False,
                ))
        return mo.vstack(blocos)

    return (mostrar_horario,)


@app.cell
def _(dados, gerar_horario):
    aulas_h0, estado_h0, tempo_h0, sessoes_h0 = gerar_horario(dados)
    return aulas_h0, estado_h0, sessoes_h0, tempo_h0


@app.cell
def _(aulas_h0, dados, estado_h0, mostrar_horario, sessoes_h0, tempo_h0):
    mostrar_horario("Resultado H0", aulas_h0, dados, estado_h0, tempo_h0, len(sessoes_h0))
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Verificação automática (EVAL)

    `verificar` olha para a lista de aulas e para os CSV. Devolve,
    para cada restrição R1–R8, a lista de erros (vazia = cumprida).
    É outro código, de propósito: se o modelo e a verificação
    concordam, há menos risco de um bug escondido nas duas.

    Repara que a `verificar` confirma também a parte que **não** é do
    solver: a sala concreta de cada aula, dentro da R7.
    """)
    return


@app.cell
def _(salas_compativeis, validar_dados):
    def verificar(dados, aulas):
        erros = {f"R{n}": [] for n in range(1, 9)}

        def repetidos(chaves):
            contagem = {}
            for c in chaves:
                contagem[c] = contagem.get(c, 0) + 1
            return [c for c, n in contagem.items() if n > 1]

        try:
            validar_dados(dados)
        except ValueError as erro:
            erros["R8"].append(str(erro))

        disciplinas = {d["disciplina"]: d for d in dados["disciplinas"]}
        indisponiveis = {
            (e["professor"], e["dia"], e["periodo"])
            for e in dados["disponibilidade_excecoes"]
        }
        salas_indisponiveis = {
            (e["sala"], e["dia"], e["periodo"])
            for e in dados.get("disponibilidade_salas", [])
        }

        erros["R1"] = repetidos([(a["turma"], a["dia"], a["periodo"]) for a in aulas])
        erros["R5"] = repetidos([(a["professor"], a["dia"], a["periodo"]) for a in aulas])

        for turma in dados["turmas"]:
            for d in dados["disciplinas"]:
                n = sum(
                    1 for a in aulas
                    if a["turma"] == turma and a["disciplina"] == d["disciplina"]
                )
                if n != d["carga_semanal"]:
                    erros["R2"].append((turma, d["disciplina"], n))

        por_sessao = {}
        for a in aulas:
            por_sessao.setdefault(a["sessao"], []).append(a)

        sessoes_por_dia = {}
        for lista in por_sessao.values():
            a0 = lista[0]
            chave = (a0["turma"], a0["disciplina"], a0["dia"])
            sessoes_por_dia[chave] = sessoes_por_dia.get(chave, 0) + 1
            if disciplinas[a0["disciplina"]]["duplo_periodo"]:
                tempos = sorted(a["periodo"] for a in lista)
                mesmo_dia = len({a["dia"] for a in lista}) == 1
                seguidos = tempos == list(range(tempos[0], tempos[0] + 2))
                if not (mesmo_dia and seguidos):
                    erros["R4"].append((a0["turma"], a0["disciplina"], tempos))
        erros["R3"] = [c for c, n in sessoes_por_dia.items() if n > 1]

        for a in aulas:
            if (a["professor"], a["dia"], a["periodo"]) in indisponiveis:
                erros["R6"].append((a["professor"], a["dia"], a["periodo"]))

        uso = {}
        for a in aulas:
            chave = (a["tipo_sala"], a["dia"], a["periodo"])
            uso[chave] = uso.get(chave, 0) + 1
        for (tipo, dia, periodo), n in uso.items():
            disponiveis = sum(
                (sala["sala"], dia, periodo) not in salas_indisponiveis
                for sala in salas_compativeis({"tipo_sala": tipo}, dados["salas"])
            )
            if n > disponiveis:
                erros["R7"].append(("capacidade", tipo, dia, periodo))
        for chave in repetidos([(a["sala"], a["dia"], a["periodo"]) for a in aulas]):
            erros["R7"].append(("sala repetida", chave))
        for a in aulas:
            nomes = {s["sala"] for s in salas_compativeis(a, dados["salas"])}
            if a["sala"] not in nomes:
                erros["R7"].append(("sala inválida", a["sala"]))
            if (a["sala"], a["dia"], a["periodo"]) in salas_indisponiveis:
                erros["R7"].append(("sala indisponível", a["sala"], a["dia"], a["periodo"]))

        return erros

    return (verificar,)


@app.cell
def _(aulas_h0, dados, mo, verificar):
    erros_h0 = verificar(dados, aulas_h0)
    mo.vstack([
        mo.md("### Verificação do H0 — cada linha deve ter **0** erros"),
        mo.ui.table([{
            "Restrição": r,
            "Erros": len(e),
            "Estado": "cumprida" if not e else "VIOLADA",
        } for r, e in erros_h0.items()], selection=None),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Testes: estragar de propósito

    Se a verificação só diz «está tudo bem», pode estar sempre a
    devolver lista vazia. Por isso corrompemos o H0, **uma restrição
    de cada vez**, e exigimos que esse código de erro apareça.
    """)
    return


@app.cell
def _(aulas_h0, dados, deepcopy, gerar_horario, mo, verificar):
    
    def estragar_r1(aulas):
        novas = deepcopy(aulas)
        a = novas[0]
        b = next(
            x for x in novas
            if x["turma"] == a["turma"] and x["sessao"] != a["sessao"]
        )
        b["dia"], b["periodo"] = a["dia"], a["periodo"]
        return novas

    def estragar_r2(aulas):
        return deepcopy(aulas)[1:]

    def estragar_r3(aulas):
        novas = deepcopy(aulas)
        a = novas[0]
        b = next(
            x for x in novas
            if x["turma"] == a["turma"]
            and x["disciplina"] == a["disciplina"]
            and x["sessao"] != a["sessao"]
        )
        b["dia"] = a["dia"]
        return novas

    def estragar_r4(aulas):
        novas = deepcopy(aulas)
        por_sessao = {}
        for a in novas:
            por_sessao.setdefault(a["sessao"], []).append(a)
        bloco = next(lista for lista in por_sessao.values() if len(lista) == 2)
        bloco.sort(key=lambda a: a["periodo"])
        bloco[1]["periodo"] = 1 if bloco[0]["periodo"] != 1 else 3
        return novas

    def estragar_r5(aulas):
        novas = deepcopy(aulas)
        a = novas[0]
        b = next(
            x for x in novas
            if x["professor"] == a["professor"] and x["sessao"] != a["sessao"]
        )
        b["dia"], b["periodo"] = a["dia"], a["periodo"]
        return novas

    def estragar_r6(aulas):
        novas = deepcopy(aulas)
        e = dados["disponibilidade_excecoes"][0]
        a = next(x for x in novas if x["professor"] == e["professor"])
        a["dia"], a["periodo"] = e["dia"], e["periodo"]
        return novas

    def estragar_r7(aulas):
        novas = deepcopy(aulas)
        novas[0]["sala"] = "Sala inexistente"
        return novas

    testes = {
        "R1": estragar_r1,
        "R2": estragar_r2,
        "R3": estragar_r3,
        "R4": estragar_r4,
        "R5": estragar_r5,
        "R6": estragar_r6,
        "R7": estragar_r7,
    }

    linhas = [{
        "Caso": "H0 original",
        "Erros no código testado": sum(len(v) for v in verificar(dados, aulas_h0).values()),
        "Esperado": 0,
    }]
    for restricao_teste, funcao_teste in testes.items():
        encontrados = len(verificar(dados, funcao_teste(aulas_h0))[restricao_teste])
        linhas.append({
            "Caso": f"{restricao_teste} estragada",
            "Erros no código testado": encontrados,
            "Esperado": ">0",
        })

    dados_maus = deepcopy(dados)
    dados_maus["turmas"] = dados["turmas"] + dados["turmas"]
    erros_r8 = len(verificar(dados_maus, aulas_h0)["R8"])
    linhas.append({
        "Caso": "R8 dados inválidos (turmas repetidas)",
        "Erros no código testado": erros_r8,
        "Esperado": ">0",
    })

    dados_sala_fechada = deepcopy(dados)
    aula_fechada = aulas_h0[0]
    dados_sala_fechada["disponibilidade_salas"] = [{
        "sala": aula_fechada["sala"],
        "dia": aula_fechada["dia"],
        "periodo": aula_fechada["periodo"],
    }]
    aulas_sala_fechada, estado_sala_fechada, _, _ = gerar_horario(
        dados_sala_fechada,
        limite_segundos=10,
    )
    erros_sala_fechada = sum(
        len(erros) for erros in verificar(dados_sala_fechada, aulas_sala_fechada).values()
    )
    linhas.append({
        "Caso": f"R7 sala fechada num período ({estado_sala_fechada})",
        "Erros no código testado": erros_sala_fechada,
        "Esperado": 0,
    })

    mo.vstack([
        mo.md("O original deve ter **0**; cada sabotagem deve ter **mais de 0** na restrição visada."),
        mo.ui.table(linhas, selection=None),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 6. Construção incremental (R9)

    Na escola o horário quase nunca nasce do zero: muda um recurso e
    queremos um H1 **válido** (R1–R8 com os dados novos), **rápido**,
    e com **poucas aulas a saltar** de sítio. O O1 deixa de ser o
    objectivo — o enunciado diz-o explicitamente.

    Em `dados_v2/` a Prof. Ana passa a estar indisponível à sexta
    nos dois últimos tempos. O código **não assume** que é só este
    cenário: qualquer pasta no mesmo formato serve (turma nova,
    outra excepção, outra sala).

    Dois métodos, o mesmo modelo SAT:

    1. **Do zero** — como o H0, a minimizar buracos, sem olhar para
       o H0.
     2. **Incremental** — maximizar o número de sessões que repetem
         `(turma, disciplina, dia, tempo de início, sala)` do H0 e dar
         essas colocações como `AddHint` ao solver.

     Assim, o objetivo conta como mantida apenas uma sessão que conserva
     o horário e a sala.

    Para a resoluçao deste capitulo foi utilizado o copilot do vscode, 
    que ajudou a escrever algumas funções de comparação de horários e 
    de contagem de alterações. O código foi escrito com base nas funções 
    já existentes e adaptado para o novo contexto do horário incremental.
    """)
    return


@app.function
def slots(aulas, com_salas=False):
    """Devolve um conjunto de assinaturas, uma por sessão.

    Um bloco duplo usa o seu primeiro período como início e continua a
    aparecer só uma vez. Cada assinatura contém turma, disciplina, dia
    e início; com `com_salas=True`, acrescenta o nome da sala.

    A função serve para comparar posições, não para manter a identidade
    interna (`sessao`) entre duas execuções do solver.
    """
    primeiras = {}
    for a in aulas:
        s = a["sessao"]
        if s not in primeiras or a["periodo"] < primeiras[s]["periodo"]:
            primeiras[s] = a
    if com_salas:
        return {
            (a["turma"], a["disciplina"], a["dia"], a["periodo"], a["sala"])
            for a in primeiras.values()
        }
    return {
        (a["turma"], a["disciplina"], a["dia"], a["periodo"])
        for a in primeiras.values()
    }

@app.function
def comparar_sessoes(aulas_antes, aulas_depois, dias_semana):
    """Emparelha sessões por turma e disciplina e descreve as diferenças.

    Primeiro remove as sessões com dia, períodos e sala iguais. As
    restantes são ordenadas e emparelhadas por dia, início e sala; cada
    par diferente produz uma linha antes/depois. Uma sessão sem par é
    indicada como `Sem sessão`. Como as sessões não têm um identificador
    persistente entre horários, o emparelhamento é determinístico, mas
    não representa uma identidade pessoal da aula. `dias_semana` define
    a ordem cronológica usada.
    """
    dias = {dia: indice for indice, dia in enumerate(dias_semana)}

    def agrupar(aulas):
        por_sessao = {}
        for aula in aulas:
            por_sessao.setdefault(aula["sessao"], []).append(aula)

        grupos = {}
        for lista in por_sessao.values():
            primeira = lista[0]
            periodos = tuple(sorted(a["periodo"] for a in lista))
            grupos.setdefault((primeira["turma"], primeira["disciplina"]), []).append({
                "dia": primeira["dia"],
                "periodos": periodos,
                "sala": primeira["sala"],
            })
        for sessoes in grupos.values():
            sessoes.sort(key=lambda s: (dias[s["dia"]], s["periodos"][0], s["sala"] or ""))
        return grupos

    antes = agrupar(aulas_antes)
    depois = agrupar(aulas_depois)
    mudancas = []
    for turma, disciplina in sorted(set(antes) | set(depois)):
        antigas = antes.get((turma, disciplina), []).copy()
        novas = depois.get((turma, disciplina), []).copy()
        mantidas = []
        for antiga in antigas:
            if antiga in novas:
                novas.remove(antiga)
            else:
                mantidas.append(antiga)

        antigas = mantidas
        quantidade = max(len(antigas), len(novas))
        for indice in range(quantidade):
            antiga = antigas[indice] if indice < len(antigas) else None
            nova = novas[indice] if indice < len(novas) else None

            def descrever(sessao):
                if sessao is None:
                    return "Sem sessão"
                tempos = str(sessao["periodos"][0])
                if len(sessao["periodos"]) > 1:
                    tempos += f"-{sessao['periodos'][-1]}"
                return f"{sessao['dia']} {tempos} | {sessao['sala']}"

            mudancas.append({
                "Turma": turma,
                "Disciplina": disciplina,
                "Antes (dia/tempo | sala)": descrever(antiga),
                "Depois (dia/tempo | sala)": descrever(nova),
            })
    return mudancas


@app.function
def preferir_horario_anterior(model, x, y, sessoes, aulas_antigas):
    """Maximiza sessões que mantêm turma, disciplina, horário e sala do H0.

    Só conta uma sessão se a combinação completa existir no H0. Os
    `AddHint` sugerem ao solver uma solução inicial; não fixam as aulas,
    que continuam livres para mudar se as novas restrições o exigirem.
    """
    antigas = slots(aulas_antigas, com_salas=True)
    mantidas = []
    usados = set()
    for (i, dia, inicio, sala), var in y.items():
        s = sessoes[i]
        chave = (s["turma"], s["disciplina"], dia, inicio, sala)
        if chave in antigas:
            mantidas.append(var)
            if chave not in usados:
                model.AddHint(x[(i, dia, inicio)], 1)
                model.AddHint(var, 1)
                usados.add(chave)
    model.Maximize(sum(mantidas))


@app.cell
def _(carregar_dados):
    dados_v2 = carregar_dados("dados_v2")
    return (dados_v2,)


@app.cell
def _(aulas_h0, dados_v2, gerar_horario):
    aulas_zero, estado_zero, tempo_zero, _s0 = gerar_horario(dados_v2)
    aulas_inc, estado_inc, tempo_inc, _s1 = gerar_horario(
        dados_v2, aulas_referencia=aulas_h0
    )
    return (
        aulas_inc,
        aulas_zero,
        estado_inc,
        estado_zero,
        tempo_inc,
        tempo_zero,
    )


@app.cell
def _(
    aulas_h0,
    aulas_inc,
    aulas_zero,
    DIAS,
    contar_buracos,
    dados_v2,
    estado_inc,
    estado_zero,
    mo,
    tempo_inc,
    tempo_zero,
    verificar,
):
    comparacao = []
    for metodo_h1, aulas, estado, tempo in [
        ("Do zero (O1, ignora H0)", aulas_zero, estado_zero, tempo_zero),
        ("Incremental (estabilidade + hints)", aulas_inc, estado_inc, tempo_inc),
    ]:
        comparacao.append({
            "Método": metodo_h1,
            "Estado": estado,
            "Tempo (s)": round(tempo, 3),
            "Sessões alteradas (horário ou sala)": len(
                comparar_sessoes(aulas_h0, aulas, DIAS)
            ),
            "Buracos": contar_buracos(aulas, dados_v2),
            "Erros R1–R8": sum(len(v) for v in verificar(dados_v2, aulas).values()),
        })

    mo.vstack([
        mo.md(
            "### Comparação H1\n\n"
            "O incremental deve **mudar menos sessões**. O tempo pode "
            "ou não ser menor (o SAT com hints costuma arrancar melhor; "
            "o do zero ainda optimiza buracos e pode gastar o limite)."
        ),
        mo.ui.table(comparacao, selection=None),
    ])
    return


@app.cell
def _(DIAS, aulas_h0, aulas_inc, dados_v2, estado_inc, mostrar_horario, mo, tempo_inc):
    mudancas_h1 = comparar_sessoes(aulas_h0, aulas_inc, DIAS)
    mo.vstack([
        mostrar_horario(
            "Resultado H1 incremental",
            aulas_inc,
            dados_v2,
            estado_inc,
            tempo_inc,
            len(slots(aulas_inc)),
        ),
        mo.md("### Sessões que mudaram de horário ou sala (H0 → H1 incremental)"),
        mo.ui.table(
            mudancas_h1 or [{
                "Turma": "—",
                "Disciplina": "Nenhuma sessão mudou de horário ou sala",
                "Antes (dia/tempo | sala)": "—",
                "Depois (dia/tempo | sala)": "—",
            }],
            selection=None,
        ),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 7. Teste com mais dados

    Também testamos `dados_extra/`, que aumenta o exemplo inicial de
    2 para 6 turmas e de 5 para 10 professores. Inclui 11 disciplinas.

    **Porquê?** O enunciado pede que o programa funcione com dados
    diferentes. Este teste ajuda a confirmar que o horário é construído
    a partir dos CSV e que o código não depende só do exemplo inicial.

    A carga de cada disciplina é para **cada turma**. Por exemplo, uma
    carga semanal de 3 tempos com 6 turmas pede `3 × 6 = 18` tempos
    dessa disciplina na semana. Em `dados_extra/`, as cargas de todas
    as disciplinas somam 22 tempos por turma, ou `22 × 6 = 132` tempos
    no total. O modelo cria essas aulas para cada turma e R2 verifica
    que cada uma cumpre a carga indicada no CSV.

    Usamos o mesmo processo: carregar os CSV, gerar o horário e
    verificar R1–R8. Isto confirma o funcionamento para estes dados,
    mas não garante que qualquer conjunto seja possível: alguns podem
    ter restrições incompatíveis.
    """)
    return


@app.cell
def _(carregar_dados):
    # carregar_dados já chama validar_dados (R8): se os CSV tiverem
    # erros, o notebook pára aqui com uma mensagem clara.
    dados_extra = carregar_dados("dados_extra")
    return (dados_extra,)


@app.cell
def _(dados_extra, mo):
    disciplinas_extra = [{
        "Disciplina": d["disciplina"],
        "Professor": d["professor"],
        "Carga por turma": d["carga_semanal"],
        "Duplo": "sim" if d["duplo_periodo"] else "não",
        "Sala especial": d["sala_especial"] or "—",
    } for d in dados_extra["disciplinas"]]
    salas_extra = [{
        "Sala": s["sala"],
        "Tipo": s["tipo"],
        "Quantidade": s["quantidade"],
    } for s in dados_extra["salas"]]
    excecoes_extra = [{
        "Professor": e["professor"],
        "Dia": e["dia"],
        "Tempo": e["periodo"],
    } for e in dados_extra["disponibilidade_excecoes"]]
    salas_indisponiveis_extra = [{
        "Sala": e["sala"],
        "Dia": e["dia"],
        "Tempo": e["periodo"],
    } for e in dados_extra["disponibilidade_salas"]]

    mo.vstack([
        mo.md(f"### Dados lidos de `{dados_extra['pasta']}/`"),
        mo.md("**Turmas:** " + ", ".join(dados_extra["turmas"])),
        mo.md("**Disciplinas**"),
        mo.ui.table(disciplinas_extra, selection=None),
        mo.md("**Salas**"),
        mo.ui.table(salas_extra, selection=None),
        mo.md("**Exceções de disponibilidade dos professores**"),
        mo.ui.table(excecoes_extra, selection=None, page_size=20),
        mo.md("**Salas temporariamente indisponíveis**"),
        mo.ui.table(salas_indisponiveis_extra, selection=None, page_size=20),
    ])
    return


@app.cell
def _(dados_extra, gerar_horario, verificar):
    aulas_extra, estado_extra, tempo_extra, sessoes_extra = gerar_horario(dados_extra)
    erros_extra = verificar(dados_extra, aulas_extra)
    return aulas_extra, erros_extra, estado_extra, sessoes_extra, tempo_extra


@app.cell
def _(
    aulas_extra,
    dados_extra,
    erros_extra,
    estado_extra,
    mostrar_horario,
    mo,
    sessoes_extra,
    tempo_extra,
):
    mo.vstack([
        mostrar_horario(
            "Resultado dados_extra",
            aulas_extra,
            dados_extra,
            estado_extra,
            tempo_extra,
            len(sessoes_extra),
        ),
        mo.md("**Verificação R1–R8** (tudo deve ter 0 erros)"),
        mo.ui.table([{
            "Restrição": r,
            "Erros": len(e),
            "Estado": "cumprida" if not e else "VIOLADA",
        } for r, e in erros_extra.items()], selection=None),
    ])
    return


@app.cell
def _(mo):
        mo.md(r"""
        ## Declaração de utilização de LLMs

        Neste trabalho recorremos a modelos de linguagem (LLMs), nomeadamente o
        Claude e o Copilot.

        - Estrutura do notebook: organização das células em secções (leitura,
            modelo, resolução e apresentação) e documentação do código (docstrings
            e explicações em Markdown).
        - README: apoio na redação das instruções de instalação.

        Link: https://claude.ai/share/9bb95eea-6552-4d3a-bc18-74c0b092a88b
        
        As decisões sobre a abordagem (modelo por sessões, uso do CP-SAT e do
        módulo `csv`) foram nossas. Corremos e testámos o notebook com os dados
        do enunciado.
        """)
        return


if __name__ == "__main__":
    app.run()
