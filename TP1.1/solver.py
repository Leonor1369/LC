from collections import defaultdict
from typing import Any, Dict, List

from ortools.sat.python import cp_model

from read_data import carregar_dados, construir_sessoes, salas_compativeis

DIAS = ("Seg", "Ter", "Qua", "Qui", "Sex")


def _criar_variaveis(model, dados, sessoes):
    variaveis = {}
    capacidades = defaultdict(int)
    nomes_sala = {}

    for sala in dados["salas"]:
        recurso = "normal" if sala["tipo"] == "normal" else sala["sala"]
        capacidades[recurso] += sala["quantidade"]
        nomes_sala[recurso] = sala["sala"] if recurso != "normal" else "Sala normal"

    indisponiveis = {
        (item["professor"], item["dia"], item["periodo"])
        for item in dados["disponibilidade_excecoes"]
    }

    for indice, sessao in enumerate(sessoes):
        disciplina = next(
            item for item in dados["disciplinas"]
            if item["disciplina"] == sessao["disciplina"]
        )
        salas_validas = salas_compativeis(disciplina, dados["salas"])
        recursos_validos = {
            "normal" if sala["tipo"] == "normal" else sala["sala"]
            for sala in salas_validas
        }

        for dia in DIAS:
            ultimo_inicio = 5 - sessao["duracao"] + 1
            for inicio in range(1, ultimo_inicio + 1):
                periodos_ocupados = range(inicio, inicio + sessao["duracao"])
                if any(
                    (sessao["professor"], dia, periodo) in indisponiveis
                    for periodo in periodos_ocupados
                ):
                    continue

                for recurso in recursos_validos:
                    chave = (indice, dia, inicio, recurso)
                    variaveis[chave] = model.NewBoolVar(
                        f"sessao_{indice}_{dia}_{inicio}_{recurso}"
                    )

    return variaveis, capacidades, nomes_sala


def _adicionar_uma_colocacao_por_sessao(model, sessoes, variaveis):
    for indice, sessao in enumerate(sessoes):
        escolhas = [
            variavel for (sessao_id, _, _, _), variavel in variaveis.items()
            if sessao_id == indice
        ]
        if not escolhas:
            raise ValueError(f"Não há horários possíveis para a sessão: {sessao}")
        model.AddExactlyOne(escolhas)


def _adicionar_sem_sobreposicoes(model, sessoes, variaveis, campo):
    ocupacao = defaultdict(list)
    for (indice, dia, inicio, _), variavel in variaveis.items():
        sessao = sessoes[indice]
        for periodo in range(inicio, inicio + sessao["duracao"]):
            ocupacao[(sessao[campo], dia, periodo)].append(variavel)

    for escolhas in ocupacao.values():
        model.Add(sum(escolhas) <= 1)


def _adicionar_limite_diario_disciplina(model, sessoes, variaveis):
    por_turma_disciplina_dia = defaultdict(list)
    for (indice, dia, _, _), variavel in variaveis.items():
        sessao = sessoes[indice]
        chave = (sessao["turma"], sessao["disciplina"], dia)
        por_turma_disciplina_dia[chave].append(variavel)

    for escolhas in por_turma_disciplina_dia.values():
        model.Add(sum(escolhas) <= 1)


def _adicionar_capacidade_salas(model, sessoes, variaveis, capacidades):
    ocupacao = defaultdict(list)
    for (indice, dia, inicio, recurso), variavel in variaveis.items():
        sessao = sessoes[indice]
        for periodo in range(inicio, inicio + sessao["duracao"]):
            ocupacao[(recurso, dia, periodo)].append(variavel)

    for (recurso, _, _), escolhas in ocupacao.items():
        model.Add(sum(escolhas) <= capacidades[recurso])


def gerar_horarios(dados: Dict[str, Any]) -> List[Dict[str, Any]]:
    sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])
    model = cp_model.CpModel()
    variaveis, capacidades, nomes_sala = _criar_variaveis(model, dados, sessoes)

    _adicionar_uma_colocacao_por_sessao(model, sessoes, variaveis)
    _adicionar_sem_sobreposicoes(model, sessoes, variaveis, "turma")
    _adicionar_sem_sobreposicoes(model, sessoes, variaveis, "professor")
    _adicionar_limite_diario_disciplina(model, sessoes, variaveis)
    _adicionar_capacidade_salas(model, sessoes, variaveis, capacidades)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Não foi encontrado horário: {solver.StatusName(status)}")

    horarios = []
    for (indice, dia, inicio, recurso), variavel in variaveis.items():
        if solver.Value(variavel):
            sessao = sessoes[indice]
            horarios.append({
                **sessao,
                "dia": dia,
                "periodo_inicio": inicio,
                "periodo_fim": inicio + sessao["duracao"] - 1,
                "sala": nomes_sala[recurso],
            })

    return sorted(
        horarios,
        key=lambda aula: (
            DIAS.index(aula["dia"]), aula["periodo_inicio"], aula["turma"]
        ),
    )


if __name__ == "__main__":
    horario = gerar_horarios(carregar_dados())
    for aula in horario:
        print(
            f"{aula['dia']} P{aula['periodo_inicio']}-P{aula['periodo_fim']}: "
            f"{aula['turma']} - {aula['disciplina']} ({aula['sala']})"
        )




