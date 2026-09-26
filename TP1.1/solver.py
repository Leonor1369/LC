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
    



