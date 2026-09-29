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
    import marimo as mo
    import os
    from copy import deepcopy
    from csv import DictReader
    from ortools.sat.python import cp_model

    return DictReader, cp_model, deepcopy, mo, os


@app.cell
def _(mo):
    mo.md(r"""
    # Gerador de Horário Escolar

    1. **Dados** — leitura e validação dos CSV (R8)
    2. **Restrições R1–R7** — cada uma com o texto e o código lado a lado
    3. **Objetivo O1** — minimizar os buracos dos professores
    4. **Horário H0** — resolver e mostrar
    5. **Verificação** e **testes** das restrições
    6. **Construção incremental (R9)** — H1 com `dados_v2/`
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Constantes

    A semana tem 5 dias e cada dia tem 5 tempos. Aparecem em todo o
    notebook (validação, modelo, tabelas).
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
    ## 1. Dados (R8)

    Usamos o `DictReader` (biblioteca padrão) em vez do `pandas`: os
    ficheiros são pequenos e assim não há dependências extra.
    Nada está escrito à mão no código: para outro conjunto de dados
    basta mudar o nome da pasta. Por isso a leitura é uma função — vai
    ser usada para `dados/` (H0) e para `dados_v2/` (H1).

    **Passo 1 — ler um CSV** e confirmar que tem as colunas obrigatórias.
    """)
    return


@app.cell
def _(DictReader):
    def ler_csv(caminho, colunas_obrigatorias):
        with open(caminho, newline="", encoding="utf8") as ficheiro:
            reader = DictReader(ficheiro)
            em_falta = colunas_obrigatorias - set(reader.fieldnames or [])
            if em_falta:
                raise ValueError(f"{caminho}: faltam as colunas {sorted(em_falta)}")
            return list(reader)

    return (ler_csv,)


@app.cell
def _(mo):
    mo.md(r"""
    **Passo 2 — validar** (R8). Confirma que os dados fazem sentido
    **antes** de construir o modelo: sem turmas repetidas, cargas
    positivas, cargas pares nos duplos períodos, salas especiais que
    existem, professores conhecidos nas exceções, dias e tempos válidos.
    Esta função é também usada mais abaixo pela `verificar` (para a R8).
    """)
    return


@app.cell
def _(DIAS, PERIODOS):
    def validar_dados(dados):
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
 
        especiais = {s["sala"] for s in salas if s["tipo"] == "especial"}
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
 
        vistos = set()
        for e in dados["disponibilidade_excecoes"]:
            chave = (e["professor"], e["dia"], e["periodo"])
            if e["professor"] not in professores:
                raise ValueError(f"Professor desconhecido: {e}")
            if e["dia"] not in DIAS or e["periodo"] not in PERIODOS:
                raise ValueError(f"Dia ou período inválido: {e}")
            if chave in vistos:
                raise ValueError(f"Exceção repetida: {e}")
            vistos.add(chave)
 

    return (validar_dados,)


@app.cell
def _(mo):
    mo.md(r"""
    **Passo 3 — carregar uma pasta inteira.** Lê os 4 ficheiros, limpa
    os valores (espaços, maiúsculas, números) e valida.

    | Ficheiro | Colunas |
    |---|---|
    | `turmas.csv` | `turma` |
    | `salas.csv` | `sala`, `tipo` (normal/especial), `quantidade` |
    | `disciplinas.csv` | `disciplina`, `professor`, `carga_semanal`, `duplo_periodo` (sim/nao), `sala_especial` |
    | `disponibilidade_excecoes.csv` | `professor`, `dia`, `periodo` (tempos em que o professor **não** pode dar aulas) |
    """)
    return


@app.cell
def _(ler_csv, os, validar_dados):
    def carregar_dados(pasta):
        turmas = [(l["turma"] or "").strip()
                  for l in ler_csv(os.path.join(pasta, "turmas.csv"), {"turma"})]

        salas = [{
            "sala": (l["sala"] or "").strip(),
            "tipo": (l["tipo"] or "").strip().lower(),
            "quantidade": int(l["quantidade"]),
        } for l in ler_csv(os.path.join(pasta, "salas.csv"), {"sala", "tipo", "quantidade"})]

        disciplinas = []
        for l in ler_csv(os.path.join(pasta, "disciplinas.csv"), {
            "disciplina", "professor", "carga_semanal", "duplo_periodo", "sala_especial"
        }):
            duplo = (l["duplo_periodo"] or "").strip().lower()
            if duplo not in {"sim", "nao"}:
                raise ValueError(f"duplo_periodo deve ser 'sim' ou 'nao': {duplo!r}")
            disciplinas.append({
                "disciplina": (l["disciplina"] or "").strip(),
                "professor": (l["professor"] or "").strip(),
                "carga_semanal": int(l["carga_semanal"]),
                "duplo_periodo": duplo == "sim",
                "sala_especial": (l["sala_especial"] or "").strip(),
            })

        excecoes = [{
            "professor": (l["professor"] or "").strip(),
            "dia": (l["dia"] or "").strip(),
            "periodo": int(l["periodo"]),
        } for l in ler_csv(os.path.join(pasta, "disponibilidade_excecoes.csv"),
                           {"professor", "dia", "periodo"})]

        dados = {
            "pasta": pasta,
            "turmas": turmas,
            "salas": salas,
            "disciplinas": disciplinas,
            "disponibilidade_excecoes": excecoes,
        }
        validar_dados(dados)
        return dados

    return (carregar_dados,)


@app.cell
def _(mo):
    mo.md(r"""
    **Passo 4 — carregar os dados do horário H0.** Para usar outro
    conjunto de dados, mudar só o nome da pasta.
    """)
    return


@app.cell
def _(carregar_dados):
    PASTA_DADOS = "dados"
    dados = carregar_dados(PASTA_DADOS)
    return (dados,)


@app.cell
def _(dados, mo):
    _disciplinas = [{
        "Disciplina": d["disciplina"],
        "Professor": d["professor"],
        "Carga por Turma": d["carga_semanal"],
        "Duplo": "sim" if d["duplo_periodo"] else "não",
        "Sala especial": d["sala_especial"] or "—",
    } for d in dados["disciplinas"]]
    _salas = [{"Sala": s["sala"], "Tipo": s["tipo"], "Quantidade": s["quantidade"]}
              for s in dados["salas"]]
    _excecoes = [{"Professor": e["professor"], "Dia": e["dia"], "Tempo": e["periodo"]}
                 for e in dados["disponibilidade_excecoes"]]

    mo.vstack([
        mo.md("### Dados lidos de `" + dados["pasta"] + "/`"),
        mo.md("**Turmas:** " + ", ".join(dados["turmas"])),
        mo.ui.table(_disciplinas, selection=None),
        mo.ui.table(_salas, selection=None),
        mo.ui.table(_excecoes, selection=None, page_size=20),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Modelo baseado em sessões

    Uma **sessão** é uma aula a marcar: 1 tempo, ou um bloco de 2 tempos
    seguidos nas disciplinas de duplo período. Ex.: Matemática (carga 4)
    dá 4 sessões de 1 tempo por turma; Ed. Física (carga 2, duplo) dá 1
    sessão de 2 tempos.

    **Variável:** `x[(i, dia, inicio)] = 1` se a sessão `i` começa nesse
    dia e tempo. Só existe se a sessão cabe no dia.

    `mapa_ocupacao` diz, para cada `(dia, tempo)`, que sessões o ocupam
    (um bloco duplo que começa no tempo 4 aparece nos tempos 4 e 5).
    As restrições R1, R5, R6 e R7 usam este mapa.
    """)
    return


@app.cell
def _(DIAS, PERIODOS):
    def construir_sessoes(turmas, disciplinas):
        sessoes = []
        for turma in turmas:
            for d in disciplinas:
                duracao = 2 if d["duplo_periodo"] else 1
                for _ in range(d["carga_semanal"] // duracao):
                    sessoes.append({
                        "turma": turma,
                        "disciplina": d["disciplina"],
                        "professor": d["professor"],
                        "duracao": duracao,
                        "sala_especial": d["sala_especial"],
                    })
        return sessoes

    def tipo_de_sala(sessao):
        """'normal' ou o nome da sala especial."""
        return sessao["sala_especial"] or "normal"

    def criar_variaveis(model, sessoes):
        x = {}
        for i, sessao in enumerate(sessoes):
            for dia in DIAS:
                for inicio in PERIODOS:
                    if inicio + sessao["duracao"] - 1 <= PERIODOS[-1]:
                        x[(i, dia, inicio)] = model.NewBoolVar(f"x_{i}_{dia}_{inicio}")
        return x

    def mapa_ocupacao(x, sessoes):
        ocupacao = {(dia, p): [] for dia in DIAS for p in PERIODOS}
        for (i, dia, inicio), var in x.items():
            for p in range(inicio, inicio + sessoes[i]["duracao"]):
                ocupacao[(dia, p)].append((i, var))
        return ocupacao

    return construir_sessoes, criar_variaveis, mapa_ocupacao, tipo_de_sala


@app.cell
def _(mo):
    mo.md(r"""
    ### R2 — Carga semanal exata

    `construir_sessoes` cria o número certo de sessões
    (`carga // duração`) e aqui obrigamos cada sessão a ser marcada
    **exatamente uma vez** na semana.
    """)
    return


@app.function
def r2_cada_sessao_uma_vez(model, x, sessoes):
    for i in range(len(sessoes)):
        model.AddExactlyOne([var for (j, _, _), var in x.items() if j == i])


@app.cell
def _(mo):
    mo.md(r"""
    ### R1 — Uma turma não tem duas aulas ao mesmo tempo

    Em cada `(dia, tempo)`, somar as sessões de uma turma que o ocupam
    e exigir `<= 1`.
    """)
    return


@app.function
def r1_turmas(model, ocupacao, sessoes, dados):
    for tempo in ocupacao:
        for turma in dados["turmas"]:
            da_turma = [var for (i, var) in ocupacao[tempo] if sessoes[i]["turma"] == turma]
            if len(da_turma) > 1:
                model.Add(sum(da_turma) <= 1)


@app.cell
def _(mo):
    mo.md(r"""
    ### R5 — Um professor não dá duas aulas ao mesmo tempo

    Igual à R1, mas agrupando por professor (mesmo em turmas diferentes).
    """)
    return


@app.function
def r5_professores(model, ocupacao, sessoes, dados):
    professores = {d["professor"] for d in dados["disciplinas"]}
    for tempo in ocupacao:
        for prof in professores:
            do_prof = [var for (i, var) in ocupacao[tempo] if sessoes[i]["professor"] == prof]
            if len(do_prof) > 1:
                model.Add(sum(do_prof) <= 1)


@app.cell
def _(mo):
    mo.md(r"""
    ### R3 — No máximo uma aula da mesma disciplina por dia (por turma)

    Para cada turma, disciplina e dia, somar as sessões que começam
    nesse dia e exigir `<= 1`. Um bloco duplo é **uma** sessão, por isso
    conta como uma só ocorrência.
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
                        if dd == dia and sessoes[i]["turma"] == turma
                        and sessoes[i]["disciplina"] == d["disciplina"]
                    ]
                    if len(do_dia) > 1:
                        model.Add(sum(do_dia) <= 1)

    return (r3_uma_por_dia,)


@app.cell
def _(mo):
    mo.md(r"""
    ### R4 — Duplo período em tempos seguidos

    Não precisa de função própria: como o modelo usa **uma variável por
    bloco**, um bloco duplo ocupa sempre `inicio` e `inicio + 1` no mesmo
    dia (ver `criar_variaveis` e `mapa_ocupacao`). O bloco também não
    pode começar no último tempo, porque a variável nem chega a existir.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### R6 — Disponibilidade dos professores

    Se o professor está indisponível num `(dia, tempo)`, qualquer sessão
    que ocupe esse tempo fica a `0`. Nos blocos duplos vale para os dois
    tempos.
    """)
    return


@app.function
def r6_disponibilidade(model, ocupacao, sessoes, dados):
    indisponiveis = {(e["professor"], e["dia"], e["periodo"])
                     for e in dados["disponibilidade_excecoes"]}
    for (dia, periodo) in ocupacao:
        for (i, var) in ocupacao[(dia, periodo)]:
            if (sessoes[i]["professor"], dia, periodo) in indisponiveis:
                model.Add(var == 0)


@app.cell
def _(mo):
    mo.md(r"""
    ### R7 — Capacidade das salas

    Em cada tempo, o número de sessões num tipo de sala não pode passar
    da quantidade desse tipo. As salas `normal` contam todas juntas;
    cada sala especial conta pelo seu nome.
    """)
    return


@app.cell
def _(tipo_de_sala):
    def r7_capacidade_salas(model, ocupacao, sessoes, dados):
        capacidade = {}
        for s in dados["salas"]:
            tipo = "normal" if s["tipo"] == "normal" else s["sala"]
            capacidade[tipo] = capacidade.get(tipo, 0) + s["quantidade"]

        for tipo, maximo in capacidade.items():
            for tempo in ocupacao:
                a_decorrer = [var for (i, var) in ocupacao[tempo]
                              if tipo_de_sala(sessoes[i]) == tipo]
                if len(a_decorrer) > maximo:
                    model.Add(sum(a_decorrer) <= maximo)

    return (r7_capacidade_salas,)


@app.cell
def _(
    construir_sessoes,
    cp_model,
    criar_variaveis,
    mapa_ocupacao,
    r3_uma_por_dia,
    r7_capacidade_salas,
):
    def construir_modelo(dados):
        """Junta tudo: variáveis + restrições R1–R7."""
        model = cp_model.CpModel()
        sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])
        x = criar_variaveis(model, sessoes)
        ocupacao = mapa_ocupacao(x, sessoes)

        r2_cada_sessao_uma_vez(model, x, sessoes)
        r1_turmas(model, ocupacao, sessoes, dados)
        r5_professores(model, ocupacao, sessoes, dados)
        r3_uma_por_dia(model, x, sessoes, dados)
        r6_disponibilidade(model, ocupacao, sessoes, dados)
        r7_capacidade_salas(model, ocupacao, sessoes, dados)
        return model, x, sessoes, ocupacao

    return (construir_modelo,)


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Objetivo O1 — minimizar buracos dos professores

    Um **buraco** é um tempo livre entre duas aulas do mesmo professor
    no mesmo dia. Para cada professor e dia:

    - `ocupado[t]` = 1 se o professor tem aula no tempo `t`
      (é a soma das sessões que o ocupam; nunca passa de 1 por causa da R5);
    - `buraco[t]` = 1 se `t` está livre **e** há aula antes e depois:
      `buraco[t] >= ocupado[s] + ocupado[u] - ocupado[t] - 1` para `s < t < u`.

    O solver minimiza a soma dos buracos. Como pode demorar, o solver
    tem um limite de tempo: a solução final pode não ser ótima, mas é
    sempre válida.

    `contar_buracos` conta os buracos a partir do horário já pronto
    (independente do modelo) — serve para mostrar e comparar.
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
                    do_prof = [var for (i, var) in ocupacao[(dia, t)]
                               if sessoes[i]["professor"] == prof]
                    model.Add(ocupado[t] == sum(do_prof))
                for t in PERIODOS:
                    buraco = model.NewBoolVar(f"buraco_{prof}_{dia}_{t}")
                    for s in PERIODOS:
                        for u in PERIODOS:
                            if s < t < u:
                                model.Add(buraco >= ocupado[s] + ocupado[u] - ocupado[t] - 1)
                    buracos.append(buraco)
        model.Minimize(sum(buracos))

    def contar_buracos(aulas, dados):
        total = 0
        professores = {d["professor"] for d in dados["disciplinas"]}
        for prof in professores:
            for dia in DIAS:
                tempos = {a["periodo"] for a in aulas
                          if a["professor"] == prof and a["dia"] == dia}
                if tempos:
                    total += (max(tempos) - min(tempos) + 1) - len(tempos)
        return total

    return adicionar_buracos, contar_buracos


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Horário H0

    `resolver` corre o CP-SAT e transforma as sessões escolhidas em aulas
    (uma por tempo). O modelo só garante que não há mais aulas do que
    salas de cada tipo (R7); `atribuir_salas` escolhe depois a sala
    concreta (um bloco duplo fica na mesma sala; cada turma tenta ficar
    sempre na mesma sala normal).
    """)
    return


@app.cell
def _(cp_model, tipo_de_sala):
    def resolver(model, x, sessoes, limite_segundos=30):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = limite_segundos
        estado = solver.Solve(model)

        aulas = []
        if estado in (cp_model.OPTIMAL, cp_model.FEASIBLE):
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
                            "tipo_sala": tipo_de_sala(s),
                            "sala_especial": s["sala_especial"],
                        })
        return aulas, solver.StatusName(estado), solver.WallTime()

    return (resolver,)


@app.cell
def _(mo):
    mo.md(r"""
    **Atribuir salas.** O modelo só garante que não há mais aulas do que
    salas de cada tipo (R7); `atribuir_salas` escolhe depois a sala
    concreta (um bloco duplo fica na mesma sala; cada turma tenta ficar
    sempre na mesma sala normal). `salas_compativeis` é usada também
    pela `verificar`.
    """)
    return


@app.cell
def _():
    def salas_compativeis(aula, salas):
        """Salas que a aula pode usar: a especial dela, ou as normais."""
        if aula["sala_especial"]:
            return [s for s in salas
                    if s["tipo"] == "especial" and s["sala"] == aula["sala_especial"]]
        return [s for s in salas if s["tipo"] == "normal"]

    def atribuir_salas(aulas, dados):
        ocupadas = set()
        por_sessao = {}
        for a in aulas:
            por_sessao.setdefault(a["sessao"], []).append(a)

        for aulas_da_sessao in por_sessao.values():
            primeira = aulas_da_sessao[0]
            possiveis = []
            for sala in salas_compativeis(primeira, dados["salas"]):
                if sala["quantidade"] == 1:
                    possiveis.append(sala["sala"])
                else:
                    possiveis += [f"{sala['sala']} {n}" for n in range(1, sala["quantidade"] + 1)]

            posicao = dados["turmas"].index(primeira["turma"])
            if posicao < len(possiveis):
                possiveis.insert(0, possiveis.pop(posicao))

            escolhida = None
            for sala in possiveis:
                if all((sala, a["dia"], a["periodo"]) not in ocupadas for a in aulas_da_sessao):
                    escolhida = sala
                    break
            for a in aulas_da_sessao:
                a["sala"] = escolhida
                ocupadas.add((escolhida, a["dia"], a["periodo"]))
        return aulas

    return atribuir_salas, salas_compativeis


@app.cell
def _(adicionar_buracos, atribuir_salas, construir_modelo, dados, resolver):
    modelo_h0, x_h0, sessoes_h0, ocupacao_h0 = construir_modelo(dados)
    adicionar_buracos(modelo_h0, ocupacao_h0, sessoes_h0, dados)
    aulas_h0, estado_h0, tempo_h0 = resolver(modelo_h0, x_h0, sessoes_h0)
    aulas_h0 = atribuir_salas(aulas_h0, dados)
    return aulas_h0, estado_h0, sessoes_h0, tempo_h0


@app.cell
def _(mo):
    mo.md(r"""
    **Mostrar o H0.** Uma tabela tempos × dias por turma e outra por
    professor.
    """)
    return


@app.cell
def _(
    DIAS,
    PERIODOS,
    aulas_h0,
    contar_buracos,
    dados,
    estado_h0,
    mo,
    sessoes_h0,
    tempo_h0,
):
    _blocos = [mo.md(
        "### Resultado H0 — estado: **" + estado_h0 + "**, tempo: **" + str(round(tempo_h0, 2))
        + " s**, sessões: **" + str(len(sessoes_h0)) + "**, buracos dos professores: **"
        + str(contar_buracos(aulas_h0, dados)) + "**"
    )]
 
    if len(aulas_h0) == 0:
        _blocos.append(mo.md("Não foi encontrado nenhum horário válido."))
    else:
        _professores = sorted({d["professor"] for d in dados["disciplinas"]})
        _vistas = [
            ("turma", "Por turma", dados["turmas"], ["professor", "sala"]),
            ("professor", "Por professor", _professores, ["turma", "sala"]),
        ]
        for _campo, _titulo, _valores, _mostrar in _vistas:
            _blocos.append(mo.md("#### " + _titulo))
            for _valor in _valores:
                _linhas = []
                for _p in PERIODOS:
                    _linha = {"Tempo": f"{_p}º"}
                    for _dia in DIAS:
                        _texto = "—"
                        for _a in aulas_h0:
                            if _a[_campo] == _valor and _a["dia"] == _dia and _a["periodo"] == _p:
                                _texto = (_a["disciplina"] + " ("
                                          + ", ".join(_a[c] for c in _mostrar) + ")")
                        _linha[_dia] = _texto
                    _linhas.append(_linha)
                _blocos.append(mo.md("**" + _valor + "**"))
                _blocos.append(mo.ui.table(_linhas, selection=None, pagination=False))
 
    mo.vstack(_blocos)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Verificação automática (R1–R8)

    `verificar` **não usa o solver**: olha para a lista de aulas e
    confere cada restrição com ciclos simples. Devolve, para cada
    restrição, a lista de erros encontrados (lista vazia = cumprida).
    Assim confirmamos o resultado do modelo com outro código.
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

        # R8 — dados válidos
        try:
            validar_dados(dados)
        except ValueError as erro:
            erros["R8"].append(str(erro))

        disciplinas = {d["disciplina"]: d for d in dados["disciplinas"]}
        indisponiveis = {(e["professor"], e["dia"], e["periodo"])
                         for e in dados["disponibilidade_excecoes"]}

        # R1 — turma sem aulas em simultâneo
        erros["R1"] = repetidos([(a["turma"], a["dia"], a["periodo"]) for a in aulas])

        # R5 — professor sem aulas em simultâneo
        erros["R5"] = repetidos([(a["professor"], a["dia"], a["periodo"]) for a in aulas])

        # R2 — carga semanal exata
        for turma in dados["turmas"]:
            for d in dados["disciplinas"]:
                n = sum(1 for a in aulas
                        if a["turma"] == turma and a["disciplina"] == d["disciplina"])
                if n != d["carga_semanal"]:
                    erros["R2"].append((turma, d["disciplina"], n))

        # R3 e R4 — vistos sessão a sessão
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

        # R6 — disponibilidade
        for a in aulas:
            if (a["professor"], a["dia"], a["periodo"]) in indisponiveis:
                erros["R6"].append((a["professor"], a["dia"], a["periodo"]))

        # R7 — capacidade por tipo de sala + sala concreta válida e sem repetição
        capacidade = {}
        for s in dados["salas"]:
            tipo = "normal" if s["tipo"] == "normal" else s["sala"]
            capacidade[tipo] = capacidade.get(tipo, 0) + s["quantidade"]
        uso = {}
        for a in aulas:
            chave = (a["tipo_sala"], a["dia"], a["periodo"])
            uso[chave] = uso.get(chave, 0) + 1
        for (tipo, dia, periodo), n in uso.items():
            if n > capacidade.get(tipo, 0):
                erros["R7"].append(("capacidade", tipo, dia, periodo))
        for chave in repetidos([(a["sala"], a["dia"], a["periodo"]) for a in aulas]):
            erros["R7"].append(("sala repetida", chave))
        for a in aulas:
            nomes = [s["sala"] for s in salas_compativeis(a, dados["salas"])]
            if not any((a["sala"] or "").startswith(n) for n in nomes):
                erros["R7"].append(("sala inválida", a["sala"]))

        return erros

    return (verificar,)


@app.cell
def _(mo):
    mo.md(r"""
    ### Verificação do H0

    Cada restrição deve ter **0** erros. (A R9 é avaliada na secção 6.)
    """)
    return


@app.cell
def _(aulas_h0, dados, mo, verificar):
    _erros_h0 = verificar(dados, aulas_h0)
    mo.ui.table([{
        "Restrição": _r,
        "Erros": len(_e),
        "Estado": "cumprida" if not _e else "VIOLADA",
    } for _r, _e in _erros_h0.items()], selection=None)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Testes das restrições

    Para provar que `verificar` funciona, **estragamos** o horário de
    propósito (uma alteração por restrição) e vemos se o erro é detetado.
    Cada teste é uma função pequena que devolve uma cópia alterada das
    aulas. Para testar outra restrição basta escrever mais uma função
    igual e juntá-la ao dicionário `_testes`.
    """)
    return


@app.cell
def _(aulas_h0, dados, deepcopy, mo, verificar):
    def _r1(aulas):
        """Duas aulas da mesma turma ao mesmo tempo."""
        novas = deepcopy(aulas)
        a = novas[0]
        b = next(x for x in novas if x["turma"] == a["turma"] and x["sessao"] != a["sessao"])
        b["dia"], b["periodo"] = a["dia"], a["periodo"]
        return novas

    def _r2(aulas):
        """Falta uma aula (carga semanal errada)."""
        return deepcopy(aulas)[1:]

    def _r5(aulas):
        """Duas aulas do mesmo professor ao mesmo tempo."""
        novas = deepcopy(aulas)
        a = novas[0]
        b = next(x for x in novas if x["professor"] == a["professor"] and x["sessao"] != a["sessao"])
        b["dia"], b["periodo"] = a["dia"], a["periodo"]
        return novas

    def _r6(aulas):
        """Aula num tempo em que o professor está indisponível."""
        novas = deepcopy(aulas)
        e = dados["disponibilidade_excecoes"][0]
        a = next(x for x in novas if x["professor"] == e["professor"])
        a["dia"], a["periodo"] = e["dia"], e["periodo"]
        return novas

    _testes = {"R1": _r1, "R2": _r2, "R5": _r5, "R6": _r6}

    _linhas = [{"Restrição": "H0 original", "Erros encontrados":
                sum(len(v) for v in verificar(dados, aulas_h0).values())}]
    for _nome, _teste in _testes.items():
        _erros = verificar(dados, _teste(aulas_h0))
        _linhas.append({"Restrição": _nome + " (estragada)",
                        "Erros encontrados": len(_erros[_nome])})

    mo.vstack([
        mo.md("O H0 original deve ter **0** erros; cada teste deve ter **mais de 0**."),
        mo.ui.table(_linhas, selection=None),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 6. Construção incremental (R9)

    Os dados mudaram (`dados_v2/`) e precisamos de um horário novo H1.
    Comparamos dois métodos:

    - **Do zero:** o mesmo modelo do H0, sem olhar para o H0.
    - **Incremental:** o mesmo modelo, mas com o objetivo de **manter
      o máximo de sessões no mesmo dia e tempo do H0**. Também damos as
      posições do H0 como sugestão inicial (`AddHint`) ao solver.

    Uma sessão conta como **alterada** se o seu `(turma, disciplina, dia,
    tempo de início)` não existia no H0. Medimos o tempo do solver, as
    aulas alteradas, os buracos e os erros da `verificar`.
    """)
    return


@app.cell
def _(carregar_dados):
    PASTA_DADOS_V2 = "dados_v2"
    dados_v2 = carregar_dados(PASTA_DADOS_V2)
    return (dados_v2,)


@app.cell
def _(mo):
    mo.md(r"""
    **Passo 2 — método 1, do zero.** Igual ao H0: modelo, objetivo O1,
    resolver, atribuir salas.
    """)
    return


@app.cell
def _(adicionar_buracos, atribuir_salas, construir_modelo, dados_v2, resolver):
    _modelo, _x, _sessoes, _ocupacao = construir_modelo(dados_v2)
    adicionar_buracos(_modelo, _ocupacao, _sessoes, dados_v2)
    aulas_zero, estado_zero, tempo_zero = resolver(_modelo, _x, _sessoes)
    aulas_zero = atribuir_salas(aulas_zero, dados_v2)
    return aulas_zero, estado_zero, tempo_zero


@app.cell
def _(mo):
    mo.md(r"""
    **Passo 3 — método 2, incremental.**

    `slots` reduz um horário ao conjunto de `(turma, disciplina, dia,
    início)` das sessões, para podermos comparar horários diferentes.

    Depois, para cada variável do novo modelo cuja sessão existia no H0
    (mesmo `(turma, disciplina, dia, início)`):

    - entra na lista `mantidas`, e o objetivo passa a ser
      **maximizar** o tamanho dessa lista;
    - recebe `AddHint(var, 1)` (uma vez por sessão do H0), para o solver
      arrancar já perto do horário antigo.
    """)
    return


@app.function
def slots(aulas):
    """Conjunto de (turma, disciplina, dia, início) das sessões."""
    primeiras = {}
    for a in aulas:
        s = a["sessao"]
        if s not in primeiras or a["periodo"] < primeiras[s]["periodo"]:
            primeiras[s] = a
    return {(a["turma"], a["disciplina"], a["dia"], a["periodo"])
            for a in primeiras.values()}


@app.cell
def _(atribuir_salas, aulas_h0, construir_modelo, dados_v2, resolver):
    _modelo, _x, _sessoes, _ocupacao = construir_modelo(dados_v2)
    _antigos = slots(aulas_h0)
 
    _mantidas = []
    _usados = set()
    for (_i, _dia, _inicio), _var in _x.items():
        _s = _sessoes[_i]
        _chave = (_s["turma"], _s["disciplina"], _dia, _inicio)
        if _chave in _antigos:
            _mantidas.append(_var)
            if _chave not in _usados:
                _modelo.AddHint(_var, 1)
                _usados.add(_chave)
    _modelo.Maximize(sum(_mantidas))
 
    aulas_inc, estado_inc, tempo_inc = resolver(_modelo, _x, _sessoes)
    aulas_inc = atribuir_salas(aulas_inc, dados_v2)
    return aulas_inc, estado_inc, tempo_inc


@app.cell
def _(mo):
    mo.md(r"""
    **Passo 4 — comparar.** O método incremental deve ter **menos
    sessões alteradas** (horário mais estável) e, idealmente, menos tempo.
    """)
    return


@app.cell
def _(
    aulas_h0,
    aulas_inc,
    aulas_zero,
    contar_buracos,
    dados_v2,
    estado_inc,
    estado_zero,
    mo,
    tempo_inc,
    tempo_zero,
    verificar,
):
    _linhas = []
    for _nome, _aulas, _estado, _tempo in [
        ("Do zero", aulas_zero, estado_zero, tempo_zero),
        ("Incremental", aulas_inc, estado_inc, tempo_inc),
    ]:
        _linhas.append({
            "Método": _nome,
            "Estado": _estado,
            "Tempo (s)": round(_tempo, 3),
            "Sessões alteradas vs H0": len(slots(_aulas) - slots(aulas_h0)),
            "Buracos": contar_buracos(_aulas, dados_v2),
            "Erros (R1–R8)": sum(len(v) for v in verificar(dados_v2, _aulas).values()),
        })
 
    mo.vstack([
        mo.md("### Comparação H1: do zero vs incremental"),
        mo.ui.table(_linhas, selection=None),
    ])
    return


if __name__ == "__main__":
    app.run()
