import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Gerador de Horário Escolar

    Nesta primeira etapa, o notebook carrega e valida os CSVs, cria as sessões
    letivas por turma e mostra as salas compatíveis com cada disciplina.
    """)
    return


@app.cell
def _(mo):
    pasta_selecionada = mo.ui.dropdown(
        options=["dados", "dados_v2"],
        value="dados",
        label="Escolhe a pasta de dados",
    )
    pasta_selecionada
    return (pasta_selecionada,)


@app.cell
def _(pasta_selecionada):
    from read_data import carregar_dados, construir_sessoes

    pasta_dados = pasta_selecionada.value
    dados = carregar_dados(pasta_dados)
    sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])
    return dados, pasta_dados, sessoes


@app.cell
def _(dados, mo, pasta_dados, sessoes):
    mo.md(f"""
    ## Dados carregados

    A validação terminou sem erros.

    - Pasta selecionada: **`{pasta_dados}/`**
    - Turmas: **{len(dados['turmas'])}**
    - Disciplinas: **{len(dados['disciplinas'])}**
    - Salas (tipos/registos): **{len(dados['salas'])}**
    - Exceções de disponibilidade: **{len(dados['disponibilidade_excecoes'])}**
    - Sessões a agendar: **{len(sessoes)}**
    """)
    return

@app.cell
def _(dados, mo):
    lista_turmas = "\n".join(f"- {turma}" for turma in dados["turmas"])
    lista_disciplinas = "\n".join(
        f"- **{disciplina['disciplina']}**; professor: {disciplina['professor']}; "
        f"carga: {disciplina['carga_semanal']}; duplo: "
        f"{'sim' if disciplina['duplo_periodo'] else 'não'}; "
        f"sala especial: {disciplina['sala_especial'] or 'não'}"
        for disciplina in dados["disciplinas"]
    )
    lista_salas = "\n".join(
        f"- {sala['sala']} ({sala['tipo']}), quantidade: {sala['quantidade']}"
        for sala in dados["salas"]
    )
    lista_excecoes = "\n".join(
        f"- {item['professor']}: {item['dia']}, período {item['periodo']}"
        for item in dados["disponibilidade_excecoes"]
    )

    mo.md(f"""
    ## Dados de entrada

    ### Turmas
    {lista_turmas}

    ### Disciplinas
    {lista_disciplinas}

    ### Salas
    {lista_salas}

    ### Indisponibilidades
    {lista_excecoes}
    """)
    return


@app.cell
def _(dados, mo, sessoes):
    from read_data import salas_compativeis

    lista_duplos = "\n".join(
        f"- {sessao['turma']}: {sessao['disciplina']} com {sessao['professor']} "
        f"({sessao['duracao']} períodos consecutivos)"
        for sessao in sessoes
        if sessao["duracao"] == 2
    ) or "- Não existem sessões duplas."

    lista_salas_compativeis = []
    for disciplina in dados["disciplinas"]:
        salas_validas = salas_compativeis(disciplina, dados["salas"])
        nomes = ", ".join(
            f"{sala['sala']} (capacidade {sala['quantidade']})"
            for sala in salas_validas
        ) or "nenhuma sala compatível"
        lista_salas_compativeis.append(f"- {disciplina['disciplina']}: {nomes}")
    texto_salas_compativeis = "\n".join(lista_salas_compativeis)

    mo.md(f"""
    ## Preparação para o horário

    ### Sessões de duplo período
    {lista_duplos}

    ### Salas compatíveis por disciplina
    {texto_salas_compativeis}

    As sessões e opções de sala estão preparadas. A célula seguinte chama o solver
    para escolher dia/período, respeitar blocos duplos e aplicar limites de capacidade.
    """)
    return

@app.cell
def _(dados):
    from solver import gerar_horarios

    horario = gerar_horarios(dados)
    return (horario,)

@app.cell
def _(dados, horario, mo):
    dias = ("Seg", "Ter", "Qua", "Qui", "Sex")
    grelhas_turma = []

    for turma in dados["turmas"]:
        grelha = {(periodo, dia): [] for periodo in range(1, 6) for dia in dias}
        for aula in horario:
            if aula["turma"] != turma:
                continue

            periodo_inicio = aula["periodo_inicio"]
            periodo_fim = aula["periodo_fim"]
            descricao = (
                f"**{aula['disciplina']}**"
                f"<br>{aula['professor']}"
                f"<br>{aula['sala']}"
            )
            if periodo_inicio < periodo_fim:
                descricao += f"<br>(duplo: P{periodo_inicio}-P{periodo_fim})"

            grelha[(periodo_inicio, aula["dia"])].append(descricao)
            for periodo in range(periodo_inicio + 1, periodo_fim + 1):
                grelha[(periodo, aula["dia"])].append("↳ continuação do bloco duplo")

        linhas = []
        for periodo in range(1, 6):
            celulas = ["<br>".join(grelha[(periodo, dia)]) or "—" for dia in dias]
            linhas.append(
                f"| **{periodo}** | " + " | ".join(celulas) + " |"
            )

        grelhas_turma.append(f"""
    ### Turma {turma}

    | Período | Seg | Ter | Qua | Qui | Sex |
    |---:|---|---|---|---|---|
    {chr(10).join(linhas)}
    """)

    texto_grelhas = "\n".join(grelhas_turma)
    mo.md(f"""
    ## Horário semanal

    O solver encontrou **{len(horario)} sessões**. Cada grelha mostra os períodos
    nas linhas e os dias da semana nas colunas. As aulas duplas ocupam duas células
    consecutivas.

    {texto_grelhas}
    """)
    return


if __name__ == "__main__":
    app.run()
