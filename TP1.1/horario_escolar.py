# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.24.2",
#     "ortools>=9.10",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # ------------------------------------------------------------------
    # Bibliotecas usadas no trabalho
    #   - marimo:     o notebook e a apresentação dos resultados
    #   - DictReader: ler os ficheiros CSV (módulo csv da biblioteca padrão)
    #   - os:         juntar o nome da pasta ao nome de cada ficheiro
    #   - time:       medir tempos de execução (vai ser usado no R9)
    #   - cp_model:   o solver CP-SAT do OR-Tools
    # ------------------------------------------------------------------
    import marimo as mo
    import os
    import time
    from csv import DictReader
    from ortools.sat.python import cp_model

    return DictReader, cp_model, mo, os, time


@app.cell
def _(mo):
    mo.md(r"""
    # Gerador de Horário Escolar — Resolução

    Este notebook resolve o problema em várias etapas:

    1. **Leitura e validação dos dados** a partir dos ficheiros CSV (R8).
    2. **Modelo** em CP-SAT, baseado em **sessões** (R1–R7).
    3. **Resolução** e **apresentação** do horário por turma e por professor.

    As etapas seguintes (verificação automática, objetivo O1 e construção
    incremental R9) são acrescentadas nas próximas secções.
    """)
    return


@app.cell
def _():
    # Dias da semana, com a mesma escrita usada no ficheiro de exceções
    DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex"]

    # Tempos letivos de cada dia (1 = primeiro tempo, 5 = último)
    PERIODOS = [1, 2, 3, 4, 5]
    return DIAS, PERIODOS


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Leitura dos dados (R8)

    **Escolha:** usamos o `DictReader` do módulo `csv` da biblioteca padrão
    em vez do `pandas`. Os ficheiros são pequenos e têm uma estrutura
    simples; o `DictReader` devolve cada linha como um dicionário
    (`{"coluna": valor}`), fácil de percorrer com ciclos normais. Assim não
    precisamos de mais nenhuma dependência.

    Cada ficheiro tem a sua função de leitura, que:

    - confirma que as colunas obrigatórias existem;
    - limpa os valores (tira espaços, converte números e `sim`/`nao`);
    - devolve listas e dicionários simples.

    Depois, `validar_dados` confirma que os dados fazem sentido (turmas
    repetidas, cargas inválidas, salas inexistentes, exceções repetidas...)
    **antes** de construir o modelo.

    Todos os valores são lidos dos ficheiros: se trocarmos a pasta por
    outra com o mesmo formato, o resto do notebook continua a funcionar sem
    alterar o código.
    """)
    return


@app.cell
def _(DIAS, DictReader, PERIODOS, os):
    def _ler_csv(caminho, colunas_obrigatorias):
        """
        Lê um ficheiro CSV e devolve uma lista de dicionários (um por linha).
        Se faltar alguma das colunas obrigatórias, pára com um erro claro.
        """
        with open(caminho, newline="", encoding="utf8") as ficheiro:
            reader = DictReader(ficheiro)
            colunas = set(reader.fieldnames or [])
            em_falta = colunas_obrigatorias - colunas
            if em_falta:
                raise ValueError(f"{caminho}: faltam as colunas {sorted(em_falta)}")
            return list(reader)

    def ler_turmas(caminho):
        """Devolve a lista com os nomes das turmas (ex.: ["7ºA", "7ºB"])."""
        linhas = _ler_csv(caminho, {"turma"})
        return [(linha["turma"] or "").strip() for linha in linhas]

    def ler_salas(caminho):
        """
        Devolve uma lista de salas, cada uma um dicionário com:
          - "sala":       nome (ex.: "Laboratório")
          - "tipo":       "normal" ou "especial"
          - "quantidade": quantas salas desse tipo existem em simultâneo
        """
        linhas = _ler_csv(caminho, {"sala", "tipo", "quantidade"})
        return [{
            "sala": (linha["sala"] or "").strip(),
            "tipo": (linha["tipo"] or "").strip().lower(),
            "quantidade": int(linha["quantidade"]),
        } for linha in linhas]

    def ler_disciplinas(caminho):
        """
        Devolve uma lista de disciplinas, cada uma um dicionário com:
          - "disciplina", "professor"
          - "carga_semanal": número de tempos por semana (inteiro)
          - "duplo_periodo": True se é dada em blocos de 2 tempos
          - "sala_especial": nome da sala especial ("" = sala normal)
        """
        linhas = _ler_csv(caminho, {
            "disciplina", "professor", "carga_semanal", "duplo_periodo", "sala_especial"
        })
        disciplinas = []
        for linha in linhas:
            duplo = (linha["duplo_periodo"] or "").strip().lower()
            if duplo not in {"sim", "nao"}:
                raise ValueError(
                    f"{caminho}: duplo_periodo deve ser 'sim' ou 'nao'; valor recebido: {duplo!r}"
                )
            disciplinas.append({
                "disciplina": (linha["disciplina"] or "").strip(),
                "professor": (linha["professor"] or "").strip(),
                "carga_semanal": int(linha["carga_semanal"]),
                "duplo_periodo": duplo == "sim",
                "sala_especial": (linha["sala_especial"] or "").strip(),
            })
        return disciplinas

    def ler_dispo_exc(caminho):
        """
        Devolve a lista dos tempos em que um professor NÃO está disponível.
        Cada exceção é um dicionário com "professor", "dia" e "periodo".
        """
        linhas = _ler_csv(caminho, {"professor", "dia", "periodo"})
        return [{
            "professor": (linha["professor"] or "").strip(),
            "dia": (linha["dia"] or "").strip(),
            "periodo": int(linha["periodo"]),
        } for linha in linhas]

    def validar_dados(dados):
        """
        Confirma que os dados lidos fazem sentido antes de construir o modelo.
        Se encontrar um problema, pára com uma mensagem de erro clara.
        """
        turmas = dados["turmas"]
        salas = dados["salas"]
        disciplinas = dados["disciplinas"]
        excecoes = dados["disponibilidade_excecoes"]

        # Turmas: não pode haver lista vazia, nomes vazios nem repetidos
        if not turmas or any(not turma for turma in turmas):
            raise ValueError("A lista de turmas não pode estar vazia nem conter nomes vazios.")
        if len(turmas) != len(set(turmas)):
            raise ValueError("Existem turmas repetidas em turmas.csv.")
        if not salas or not disciplinas:
            raise ValueError("É necessário definir pelo menos uma sala e uma disciplina.")

        # Salas: nome preenchido, tipo "normal" ou "especial", quantidade positiva
        tipos_sala = {"normal", "especial"}
        for sala in salas:
            if not sala["sala"] or sala["tipo"] not in tipos_sala:
                raise ValueError(f"Sala com nome vazio ou tipo inválido: {sala}")
            if sala["quantidade"] <= 0:
                raise ValueError(f"A quantidade da sala tem de ser positiva: {sala}")

        # Disciplinas: campos preenchidos, carga válida e sala existente
        nomes_especiais = {sala["sala"] for sala in salas if sala["tipo"] == "especial"}
        professores = {disciplina["professor"] for disciplina in disciplinas}
        for disciplina in disciplinas:
            if not disciplina["disciplina"] or not disciplina["professor"]:
                raise ValueError(f"Disciplina ou professor vazio: {disciplina}")
            if disciplina["carga_semanal"] <= 0:
                raise ValueError(f"A carga semanal tem de ser positiva: {disciplina}")
            if disciplina["duplo_periodo"] and disciplina["carga_semanal"] % 2 != 0:
                raise ValueError(
                    f"A carga de uma disciplina de duplo período tem de ser par: {disciplina}"
                )
            sala_especial = disciplina["sala_especial"]
            if sala_especial and sala_especial not in nomes_especiais:
                raise ValueError(
                    f"A sala especial {sala_especial!r} de {disciplina['disciplina']} "
                    "não existe como sala do tipo 'especial'."
                )
            if not sala_especial and not any(sala["tipo"] == "normal" for sala in salas):
                raise ValueError(
                    f"{disciplina['disciplina']} precisa de sala normal, mas não há salas normais."
                )

        # Exceções: professor conhecido, dia/tempo válidos, sem repetições
        vistos = set()
        for excecao in excecoes:
            chave = (excecao["professor"], excecao["dia"], excecao["periodo"])
            if excecao["professor"] not in professores:
                raise ValueError(f"Professor desconhecido na disponibilidade: {excecao}")
            if excecao["dia"] not in DIAS or excecao["periodo"] not in PERIODOS:
                raise ValueError(f"Dia ou período inválido na disponibilidade: {excecao}")
            if chave in vistos:
                raise ValueError(f"Exceção de disponibilidade repetida: {excecao}")
            vistos.add(chave)

    def carregar_dados(pasta):
        """
        Lê todos os ficheiros de uma pasta de dados, valida-os e devolve
        tudo num único dicionário. É esta a função usada no resto do notebook.
        """
        dados = {
            "pasta": pasta,
            "turmas": ler_turmas(os.path.join(pasta, "turmas.csv")),
            "salas": ler_salas(os.path.join(pasta, "salas.csv")),
            "disciplinas": ler_disciplinas(os.path.join(pasta, "disciplinas.csv")),
            "disponibilidade_excecoes": ler_dispo_exc(
                os.path.join(pasta, "disponibilidade_excecoes.csv")
            ),
        }
        validar_dados(dados)
        return dados

    return (carregar_dados,)


@app.cell
def _(carregar_dados):
    # Pasta com os dados de exemplo do enunciado.
    # Para testar outro conjunto de dados basta mudar este nome.
    PASTA_DADOS = "dados"
    dados = carregar_dados(PASTA_DADOS)
    return (dados,)


@app.cell
def _(dados, mo):
    # Mostrar os dados lidos, para confirmar que a leitura está correta
    _tabela_disciplinas = []
    for _d in dados["disciplinas"]:
        _tabela_disciplinas.append({
            "Disciplina": _d["disciplina"],
            "Professor": _d["professor"],
            "Carga semanal": _d["carga_semanal"],
            "Bloco duplo": "sim" if _d["duplo_periodo"] else "não",
            "Sala especial": _d["sala_especial"] if _d["sala_especial"] else "—",
        })

    _tabela_salas = []
    for _s in dados["salas"]:
        _tabela_salas.append({"Sala": _s["sala"], "Tipo": _s["tipo"], "Quantidade": _s["quantidade"]})

    _tabela_excecoes = []
    for _e in dados["disponibilidade_excecoes"]:
        _tabela_excecoes.append({"Professor": _e["professor"], "Dia": _e["dia"], "Tempo": _e["periodo"]})

    mo.vstack([
        mo.md("### Dados lidos de `" + dados["pasta"] + "/`"),
        mo.md("**Turmas:** " + ", ".join(dados["turmas"])),
        mo.md("**Disciplinas**"),
        mo.ui.table(_tabela_disciplinas, selection=None),
        mo.md("**Salas**"),
        mo.ui.table(_tabela_salas, selection=None),
        mo.md("**Indisponibilidades dos professores**"),
        mo.ui.table(_tabela_excecoes, selection=None, page_size=20),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Modelo baseado em sessões (R1–R7)

    Uma **sessão** é uma aula que tem de ser marcada no horário: um tempo
    simples, ou um bloco de 2 tempos seguidos nas disciplinas de duplo
    período. Por exemplo, Matemática (carga 4) dá 4 sessões de 1 tempo por
    turma; Educação Física (carga 2, duplo) dá 1 sessão de 2 tempos.

    **Variável de decisão** (booleana, 0 ou 1):

    - `x[(i, dia, inicio)]` = 1 se a sessão número `i` começa nesse dia e
      nesse tempo. Só criamos a variável se a sessão couber no dia (um bloco
      duplo não pode começar no último tempo).

    **Como cada requisito entra no modelo:**

    | Requisito | Onde é garantido |
    |---|---|
    | R2 — carga semanal exata | `construir_sessoes` cria o número certo de sessões e o ponto 1 obriga cada uma a ser marcada **exatamente uma vez** |
    | R4 — blocos duplos seguidos | uma sessão dupla ocupa sempre `inicio` e `inicio + 1` no mesmo dia |
    | R1 e R5 — sem sobreposições | ponto 2 |
    | R3 — uma aula da disciplina por dia | ponto 3 |
    | R6 — disponibilidade | ponto 4 |
    | R7 — capacidade das salas | ponto 5 |
    """)
    return


@app.cell
def _(DIAS, PERIODOS, cp_model):
    def construir_sessoes(turmas, disciplinas):
        """
        Cria a lista de todas as sessões a marcar.
        Para cada turma e disciplina: carga_semanal // duração sessões,
        em que a duração é 2 (duplo período) ou 1.
        """
        sessoes = []
        for turma in turmas:
            for disciplina in disciplinas:
                duracao = 2 if disciplina["duplo_periodo"] else 1
                numero_sessoes = disciplina["carga_semanal"] // duracao
                for numero in range(numero_sessoes):
                    sessoes.append({
                        "turma": turma,
                        "disciplina": disciplina["disciplina"],
                        "professor": disciplina["professor"],
                        "duracao": duracao,
                        "sala_especial": disciplina["sala_especial"],
                        "ocorrencia": numero + 1,
                    })
        return sessoes

    def tipo_de_sala(sessao):
        """Tipo de sala que a sessão usa: "normal" ou o nome da sala especial."""
        if sessao["sala_especial"] == "":
            return "normal"
        return sessao["sala_especial"]

    def criar_variaveis(model, sessoes):
        """
        Cria x[(i, dia, inicio)] para cada sessão i, cada dia e cada tempo
        em que a sessão pode começar (tem de acabar até ao último tempo).
        """
        x = {}
        for i in range(len(sessoes)):
            duracao = sessoes[i]["duracao"]
            for dia in DIAS:
                for inicio in PERIODOS:
                    if inicio + duracao - 1 <= PERIODOS[-1]:
                        x[(i, dia, inicio)] = model.NewBoolVar(f"x_{i}_{dia}_{inicio}")
        return x

    def mapa_ocupacao(x, sessoes):
        """
        Devolve um dicionário (dia, periodo) -> lista de (i, variável) com
        todas as sessões que, se forem escolhidas, estão a decorrer nesse tempo.
        Uma sessão dupla que começa no tempo 4 aparece nos tempos 4 e 5.
        Este mapa é usado nos pontos 2, 4 e 5.
        """
        ocupacao = {}
        for dia in DIAS:
            for periodo in PERIODOS:
                ocupacao[(dia, periodo)] = []
        for (i, dia, inicio) in x:
            for periodo in range(inicio, inicio + sessoes[i]["duracao"]):
                ocupacao[(dia, periodo)].append((i, x[(i, dia, inicio)]))
        return ocupacao

    def r_cada_sessao_uma_vez(model, x, sessoes):
        """1. Cada sessão é marcada exatamente uma vez na semana (garante R2)."""
        for i in range(len(sessoes)):
            variaveis_da_sessao = []
            for (j, dia, inicio) in x:
                if j == i:
                    variaveis_da_sessao.append(x[(j, dia, inicio)])
            model.AddExactlyOne(variaveis_da_sessao)

    def r1_r5_sem_sobreposicoes(model, ocupacao, sessoes, dados):
        """
        2. Sobreposições no horário da turma (R1) e do professor (R5):
        em cada tempo, uma turma tem no máximo uma sessão a decorrer,
        e um professor também.
        """
        professores = []
        for disciplina in dados["disciplinas"]:
            if disciplina["professor"] not in professores:
                professores.append(disciplina["professor"])

        for (dia, periodo) in ocupacao:
            # R1: turma
            for turma in dados["turmas"]:
                da_turma = []
                for (i, var) in ocupacao[(dia, periodo)]:
                    if sessoes[i]["turma"] == turma:
                        da_turma.append(var)
                if len(da_turma) > 1:
                    model.Add(sum(da_turma) <= 1)
            # R5: professor
            for professor in professores:
                do_professor = []
                for (i, var) in ocupacao[(dia, periodo)]:
                    if sessoes[i]["professor"] == professor:
                        do_professor.append(var)
                if len(do_professor) > 1:
                    model.Add(sum(do_professor) <= 1)

    def r3_uma_por_dia(model, x, sessoes, dados):
        """
        3. No máximo uma sessão da mesma disciplina por dia, por turma (R3).
        Nos duplos o bloco é uma só sessão, por isso conta como uma ocorrência.
        """
        for turma in dados["turmas"]:
            for disciplina in dados["disciplinas"]:
                for dia in DIAS:
                    variaveis_da_disciplina_nesse_dia = []
                    for (i, d, inicio) in x:
                        if (d == dia and sessoes[i]["turma"] == turma
                                and sessoes[i]["disciplina"] == disciplina["disciplina"]):
                            variaveis_da_disciplina_nesse_dia.append(x[(i, d, inicio)])
                    if len(variaveis_da_disciplina_nesse_dia) > 1:
                        model.Add(sum(variaveis_da_disciplina_nesse_dia) <= 1)

    def r6_disponibilidade(model, ocupacao, sessoes, dados):
        """
        4. Disponibilidade dos professores (R6): uma sessão não pode estar a
        decorrer num tempo em que o seu professor está indisponível.
        Nos blocos duplos isto vale para os dois tempos do bloco.
        """
        indisponiveis = set()
        for item in dados["disponibilidade_excecoes"]:
            indisponiveis.add((item["professor"], item["dia"], item["periodo"]))

        for (dia, periodo) in ocupacao:
            for (i, var) in ocupacao[(dia, periodo)]:
                if (sessoes[i]["professor"], dia, periodo) in indisponiveis:
                    model.Add(var == 0)

    def r7_capacidade_salas(model, ocupacao, sessoes, dados):
        """
        5. Salas e capacidade (R7): em cada tempo, o número de sessões a
        decorrer num tipo de sala não pode passar da quantidade desse tipo.
        Todas as salas "normal" contam juntas; cada sala especial conta
        pelo seu nome.
        """
        capacidade = {}
        for linha in dados["salas"]:
            if linha["tipo"] == "normal":
                tipo = "normal"
            else:
                tipo = linha["sala"]
            if tipo not in capacidade:
                capacidade[tipo] = 0
            capacidade[tipo] = capacidade[tipo] + linha["quantidade"]

        for tipo in capacidade:
            for (dia, periodo) in ocupacao:
                a_decorrer = []
                for (i, var) in ocupacao[(dia, periodo)]:
                    if tipo_de_sala(sessoes[i]) == tipo:
                        a_decorrer.append(var)
                if len(a_decorrer) > capacidade[tipo]:
                    model.Add(sum(a_decorrer) <= capacidade[tipo])

    def gerar_horarios(dados):
        """
        Constrói o modelo CP-SAT completo (pontos 1 a 5).
        Devolve o modelo, as variáveis x e a lista de sessões.
        """
        model = cp_model.CpModel()
        sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])
        x = criar_variaveis(model, sessoes)
        ocupacao = mapa_ocupacao(x, sessoes)

        r_cada_sessao_uma_vez(model, x, sessoes)               # 1. (R2)
        r1_r5_sem_sobreposicoes(model, ocupacao, sessoes, dados)  # 2. (R1, R5)
        r3_uma_por_dia(model, x, sessoes, dados)               # 3. (R3)
        r6_disponibilidade(model, ocupacao, sessoes, dados)     # 4. (R6)
        r7_capacidade_salas(model, ocupacao, sessoes, dados)    # 5. (R7)
        return model, x, sessoes

    return gerar_horarios, tipo_de_sala


@app.cell
def _(cp_model, tipo_de_sala):
    def resolver(model, x, sessoes, limite_segundos=30):
        """
        Corre o solver e, se encontrar solução, devolve a lista de aulas.
        Cada sessão escolhida dá uma aula por cada tempo que ocupa (uma
        sessão dupla dá duas). Devolve também o estado e o tempo gasto.
        """
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = limite_segundos
        estado = solver.Solve(model)

        aulas = []
        if estado == cp_model.OPTIMAL or estado == cp_model.FEASIBLE:
            for (i, dia, inicio) in x:
                if solver.Value(x[(i, dia, inicio)]) == 1:
                    sessao = sessoes[i]
                    for periodo in range(inicio, inicio + sessao["duracao"]):
                        aulas.append({
                            "sessao": i,
                            "turma": sessao["turma"],
                            "disciplina": sessao["disciplina"],
                            "professor": sessao["professor"],
                            "dia": dia,
                            "periodo": periodo,
                            "tipo_sala": tipo_de_sala(sessao),
                            "sala_especial": sessao["sala_especial"],
                        })
        return aulas, solver.StatusName(estado), solver.WallTime()

    def salas_compativeis(disciplina, salas):
        """
        Devolve as salas (linhas de salas.csv) que uma disciplina pode usar:
        a sua sala especial, ou todas as salas do tipo "normal".
        """
        if disciplina["sala_especial"]:
            return [
                sala for sala in salas
                if sala["tipo"] == "especial" and sala["sala"] == disciplina["sala_especial"]
            ]
        return [sala for sala in salas if sala["tipo"] == "normal"]

    def atribuir_salas(aulas, dados):
        """
        Dá a cada aula uma sala concreta (ex.: "Sala Normal 2").

        O modelo só garante que não há mais aulas do que salas de cada tipo
        em cada tempo (R7). Aqui escolhemos a sala de cada sessão:
          - um bloco duplo fica na mesma sala nos dois tempos;
          - cada turma tenta ficar sempre na "sua" sala normal
            (turma 1 -> sala 1, turma 2 -> sala 2, ...); se essa estiver
            ocupada, fica com a primeira livre.
        """
        ocupadas = set()  # (sala concreta, dia, periodo) já usados

        # Juntar as aulas de cada sessão (um bloco duplo tem 2 aulas)
        por_sessao = {}
        for aula in aulas:
            if aula["sessao"] not in por_sessao:
                por_sessao[aula["sessao"]] = []
            por_sessao[aula["sessao"]].append(aula)

        for sessao in por_sessao:
            aulas_da_sessao = por_sessao[sessao]
            primeira = aulas_da_sessao[0]

            # Lista das salas concretas possíveis para esta sessão
            salas_possiveis = []
            for sala in salas_compativeis(primeira, dados["salas"]):
                if sala["quantidade"] == 1:
                    salas_possiveis.append(sala["sala"])
                else:
                    for numero in range(1, sala["quantidade"] + 1):
                        salas_possiveis.append(sala["sala"] + " " + str(numero))

            # Pôr primeiro a sala preferida da turma (se existir)
            posicao = dados["turmas"].index(primeira["turma"])
            if posicao < len(salas_possiveis):
                preferida = salas_possiveis[posicao]
                salas_possiveis.remove(preferida)
                salas_possiveis.insert(0, preferida)

            # Escolher a primeira sala livre em todos os tempos da sessão
            escolhida = None
            for sala in salas_possiveis:
                livre = True
                for aula in aulas_da_sessao:
                    if (sala, aula["dia"], aula["periodo"]) in ocupadas:
                        livre = False
                if livre:
                    escolhida = sala
                    break

            for aula in aulas_da_sessao:
                aula["sala"] = escolhida
                ocupadas.add((escolhida, aula["dia"], aula["periodo"]))
        return aulas

    return atribuir_salas, resolver


@app.cell
def _(atribuir_salas, dados, gerar_horarios, resolver):
    # Construir o modelo, resolver e atribuir as salas concretas
    modelo_h0, x_h0, sessoes_h0 = gerar_horarios(dados)
    aulas_h0, estado_h0, tempo_h0 = resolver(modelo_h0, x_h0, sessoes_h0)
    aulas_h0 = atribuir_salas(aulas_h0, dados)
    return aulas_h0, estado_h0, sessoes_h0, tempo_h0


@app.cell
def _(DIAS, PERIODOS, mo):
    def tabela_horario(aulas, filtro_campo, filtro_valor, mostrar):
        """
        Constrói uma tabela (tempos x dias) com as aulas em que
        aula[filtro_campo] == filtro_valor. Em cada célula aparece a
        disciplina e os campos indicados em 'mostrar'.
        Ex.: tabela da turma 7ºA -> filtro_campo="turma", filtro_valor="7ºA".
        """
        linhas = []
        for periodo in PERIODOS:
            linha = {"Tempo": str(periodo) + "º"}
            for dia in DIAS:
                texto = "—"
                for aula in aulas:
                    if aula[filtro_campo] == filtro_valor and aula["dia"] == dia and aula["periodo"] == periodo:
                        extras = []
                        for campo in mostrar:
                            extras.append(aula[campo])
                        texto = aula["disciplina"] + " (" + ", ".join(extras) + ")"
                linha[dia] = texto
            linhas.append(linha)
        return mo.ui.table(linhas, selection=None, pagination=False)

    return (tabela_horario,)


@app.cell
def _(aulas_h0, dados, estado_h0, mo, sessoes_h0, tabela_horario, tempo_h0):
    # Apresentação do horário gerado
    _blocos = [
        mo.md("## 3. Horário gerado (H0)"),
        mo.md(
            "Estado do solver: **" + estado_h0 + "** — tempo: **" + str(round(tempo_h0, 3))
            + " s** — sessões: **" + str(len(sessoes_h0)) + "** — tempos de aula: **"
            + str(len(aulas_h0)) + "**"
        ),
    ]

    if len(aulas_h0) == 0:
        _blocos.append(mo.md("Não foi encontrado nenhum horário válido para estes dados."))
    else:
        _blocos.append(mo.md("### Por turma"))
        for _turma in dados["turmas"]:
            _blocos.append(mo.md("**" + _turma + "**"))
            _blocos.append(tabela_horario(aulas_h0, "turma", _turma, ["professor", "sala"]))

        _blocos.append(mo.md("### Por professor"))
        _professores = []
        for _d in dados["disciplinas"]:
            if _d["professor"] not in _professores:
                _professores.append(_d["professor"])
        for _prof in _professores:
            _blocos.append(mo.md("**" + _prof + "**"))
            _blocos.append(tabela_horario(aulas_h0, "professor", _prof, ["turma", "sala"]))

    mo.vstack(_blocos)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Próximos passos

    - Verificação automática de R1–R8 (função `verificar`), independente do solver.
    - Objetivo O1: minimizar os buracos nos horários dos professores.
    - Construção incremental (R9) com `dados_v2/`.
    """)
    return
app.cell
def _(mo):
    mo.md(r"""
    ## Declaração de utilização de LLMs
 
    Neste trabalho recorremos a modelos de linguagem (LLMs), nomeadamente o
    Claude  
    
    - Estrutura do notebook:organização das células em secções
      (leitura, modelo, resolução e apresentação) e documentação do código
      (docstrings e explicações em Markdown).
    - README: apoio na redação das instruções de instalação
    As decisões sobre a abordagem (modelo por sessões, uso do CP-SAT e do
    módulo `csv`) foram nossas. Corremos e testámos o notebook com os dados
    do enunciado.
    """)
    return

if __name__ == "__main__":
    app.run()