from read_data import *
from ortools.sat.python import cp_model


# modelo para criar variavel sessao x[(sessao, dia, inicio)]
def gerar_horarios():
    model = cp_model.CpModel()
    sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])

    # 1. Cada sessão é agendada uma vez
    model.AddExactlyOne(variaveis_da_sessao)

    #2. subreposicoes de horario de turma e horario professor

    # 3. No máximo uma aula da mesma disciplina por dia , exceto duplos
    model.Add(sum(variaveis_da_disciplina_nesse_dia) <= 1)

    #4. Disponibilidade dos professores
    indisponiveis = {
        (item["professor"], item["dia"], item["periodo"])
        for item in dados["disponibilidade_excecoes"]
    }

    #5. Salas e capacidade
  
    capacidade = {}
    for linha in dados["salas"]:
        if linha["tipo"] == "normal":
            tipo = "normal"
        else:
            tipo = linha["sala"]
        if tipo not in capacidade:
            capacidade[tipo] = 0
        capacidade[tipo] = capacidade[tipo] + int(linha["quantidade"])

    # Depois, para cada tipo de sala e cada tempo da semana, juntamos todas
    # as sessões que estariam a decorrer nesse tempo e nesse tipo de sala.
    for tipo in capacidade:
        for dia in DIAS:
            for periodo in PERIODOS:
                a_decorrer = []
                for (i, d, inicio) in x:
                    sessao = sessoes[i]

                    # Tipo de sala que esta sessão usa
                    if sessao["sala_especial"] == "":
                        tipo_sessao = "normal"
                    else:
                        tipo_sessao = sessao["sala_especial"]

                    # A sessão ocupa este tempo se começa nele ou se é um bloco
                    # duplo que começou no tempo anterior
                    ocupa = inicio <= periodo < inicio + sessao["duracao"]

                    if d == dia and tipo_sessao == tipo and ocupa:
                        a_decorrer.append(x[(i, d, inicio)])

                # Não pode haver mais aulas do que salas deste tipo
                if len(a_decorrer) > 0:
                    model.Add(sum(a_decorrer) <= capacidade[tipo])
    



