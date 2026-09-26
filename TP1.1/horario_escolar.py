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
def _():
    from read_data import carregar_dados, construir_sessoes

    dados = carregar_dados()
    sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])
    return dados, sessoes


@app.cell
def _(dados, mo, sessoes):
    mo.md(f"""
    ## Dados carregados

    A validação terminou sem erros.

    - Turmas: **{len(dados['turmas'])}**
    - Disciplinas: **{len(dados['disciplinas'])}**
    - Salas (tipos/registos): **{len(dados['salas'])}**
    - Exceções de disponibilidade: **{len(dados['disponibilidade_excecoes'])}**
    - Sessões a agendar: **{len(sessoes)}**
    """)
    return


@app.cell
def _(dados):
    from solver import gerar_horarios

    horario = gerar_horarios(dados)
    return (horario,)


@app.cell
def _(horario, mo):
    linhas_horario = "\n".join(
        f"| {aula['dia']} | {aula['periodo_inicio']}-"
        f"{aula['periodo_fim']} | {aula['turma']} | {aula['disciplina']} | "
        f"{aula['professor']} | {aula['sala']} |"
        for aula in horario
    )

    mo.md(f"""
    ## Horário gerado

    O solver encontrou **{len(horario)} sessões**.

    | Dia | Períodos | Turma | Disciplina | Professor | Sala |
    |---|---:|---|---|---|---|
    {linhas_horario}
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


if __name__ == "__main__":
    app.run()
