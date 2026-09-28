"""Gera horários escolares com o solver de restrições CP-SAT do OR-Tools.

O modelo cria uma variável booleana para cada colocação possível de uma sessão:
turma, disciplina, professor, dia, período de início e recurso de sala. O valor
1 significa que essa colocação foi escolhida. As funções auxiliares adicionam
as restrições que tornam a solução válida.

Este modelo procura uma solução viável; 

ainda não define uma função objetivo para minimizar os buracos dos professores.
"""

from collections import defaultdict
from typing import Any, Dict, List

from ortools.sat.python import cp_model

from read_data import carregar_dados, construir_sessoes, salas_compativeis

DIAS = ("Seg", "Ter", "Qua", "Qui", "Sex")
"""Dias letivos aceites pelo modelo, na ordem usada para ordenar a saída."""


def _criar_variaveis(model, dados, sessoes):
    """Cria as colocações possíveis e prepara capacidades e indisponibilidades.

    Uma sessão dupla só pode começar até ao período 4 para caber no dia de
    cinco períodos. 
    Colocações que coincidam com a indisponibilidade do professor são omitidas, 
    assim como recursos de sala incompatíveis.

    Args:
        model: Modelo CP-SAT ao qual as variáveis booleanas serão adicionadas.
        dados: Dicionário com salas, disciplinas e exceções de disponibilidade.
        sessoes: Sessões letivas produzidas por ``construir_sessoes``.

    Returns:
        Tuplo com as variáveis indexadas por (sessão, dia, início, recurso),
        capacidades de cada recurso de sala e nomes usados na apresentação.
    """
    variaveis = {}
    capacidades = defaultdict(int)
    nomes_sala = {}

    # Transformação dos registos de salas em recursos do modelo:
    # - salas normais usam a chave comum "normal", somando a capacidade;
    # - salas especiais usam o próprio nome, mantendo capacidades separadas.
    for sala in dados["salas"]:
        recurso = "normal" if sala["tipo"] == "normal" else sala["sala"]
        capacidades[recurso] += sala["quantidade"]
        # Guarda um nome legível para converter depois a chave do modelo na saída.
        nomes_sala[recurso] = sala["sala"] if recurso != "normal" else "Sala normal"

    # Transforma cada linha CSV numa chave (professor, dia, período).
    # O set permite testar pertença diretamente ao criar horários candidatos.
    indisponiveis = {
        (item["professor"], item["dia"], item["periodo"])
        for item in dados["disponibilidade_excecoes"]
    }

    for indice, sessao in enumerate(sessoes):
        # Cada sessão herda a exigência de sala da respetiva disciplina.
        disciplina = next(
            item for item in dados["disciplinas"]
            if item["disciplina"] == sessao["disciplina"]
        )
        salas_validas = salas_compativeis(disciplina, dados["salas"])
        # Converte as salas compatíveis nas mesmas chaves de recurso usadas
        # em capacidades: "normal" ou o nome concreto da sala especial.
        recursos_validos = {
            "normal" if sala["tipo"] == "normal" else sala["sala"]
            for sala in salas_validas
        }

        for dia in DIAS:
            # O período de início tem de deixar espaço para toda a duração.
            # O range é inclusivo, por isso soma-se 1 ao último período.
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
                    # Cria a variável booleana que indica se a sessão é colocada nesse horário e sala.
                    variaveis[chave] = model.NewBoolVar(
                        f"sessao_{indice}_{dia}_{inicio}_{recurso}"
                    )

    return variaveis, capacidades, nomes_sala


def _adicionar_uma_colocacao_por_sessao(model, sessoes, variaveis):
    """Exige que cada sessão tenha exatamente uma colocação no horário.

    Se nenhuma colocação puder ser criada (por exemplo, devido à
    indisponibilidade do professor), lança ``ValueError`` antes de resolver.
    """
    for indice, sessao in enumerate(sessoes):
        escolhas = [
            variavel for (sessao_id, _, _, _), variavel in variaveis.items()
            if sessao_id == indice
        ]
        if not escolhas:
            raise ValueError(f"Não há horários possíveis para a sessão: {sessao}")
        # Adiciona a restrição de que exatamente uma dessas colocações deve ser escolhida.
        model.AddExactlyOne(escolhas)


def _adicionar_sem_sobreposicoes(model, sessoes, variaveis, campo):
    """Impede que o mesmo recurso indicado por ``campo`` tenha dois eventos.

    É chamada com ``campo="turma"`` e ``campo="professor"``. Uma sessão
    ocupa todos os períodos entre o início e o fim, incluindo ambos os
    períodos de uma aula dupla.
    """
    # Cria um dicionário que agrupa as variáveis por (campo, dia, período).
    ocupacao = defaultdict(list)
    for (indice, dia, inicio, _), variavel in variaveis.items():
        sessao = sessoes[indice]
        for periodo in range(inicio, inicio + sessao["duracao"]):
            # Adiciona a variável à lista de ocupação do recurso (turma ou professor) nesse dia e período.
            ocupacao[(sessao[campo], dia, periodo)].append(variavel)

    for escolhas in ocupacao.values():
        # Adiciona a restrição de que no máximo uma dessas colocações pode ser escolhida.
        model.Add(sum(escolhas) <= 1)


def _adicionar_limite_disciplina_por_dia(model, sessoes, variaveis):
    """Limita a uma sessão por disciplina, turma e dia.

    Um bloco duplo conta como uma sessão nesse dia, embora ocupe dois períodos.
    """
    # Cria um dicionário que agrupa as variáveis por (turma, disciplina, dia).
    por_turma_disciplina_dia = defaultdict(list)
    for (indice, dia, _, _), variavel in variaveis.items():
        sessao = sessoes[indice]
        chave = (sessao["turma"], sessao["disciplina"], dia)
        por_turma_disciplina_dia[chave].append(variavel)

    for escolhas in por_turma_disciplina_dia.values():
        model.Add(sum(escolhas) <= 1)


def _adicionar_capacidade_salas(model, sessoes, variaveis, capacidades):
    """Impõe a capacidade de cada recurso de sala em cada período.

    Salas normais são tratadas como um recurso agregado; cada sala especial é
    um recurso próprio. As sessões duplas consomem capacidade nos dois períodos.
    """
    # Cria um dicionário que agrupa as variáveis por (recurso, dia, período).
    ocupacao = defaultdict(list)
    for (indice, dia, inicio, recurso), variavel in variaveis.items():
        sessao = sessoes[indice]
        for periodo in range(inicio, inicio + sessao["duracao"]):
            ocupacao[(recurso, dia, periodo)].append(variavel)

    for (recurso, _, _), escolhas in ocupacao.items():
        model.Add(sum(escolhas) <= capacidades[recurso])


def gerar_horarios(dados: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Constrói e resolve o modelo de horário para os dados recebidos.

    Args:
        dados: Dicionário devolvido por ``read_data.carregar_dados()``, com as
            chaves ``turmas``, ``disciplinas``, ``salas`` e
            ``disponibilidade_excecoes``.

    Returns:
        Lista de aulas escolhidas, ordenada por dia, período inicial e turma.
        Cada item contém os dados da sessão mais ``dia``, ``periodo_inicio``,
        ``periodo_fim`` e ``sala``.

    Raises:
        ValueError: Se alguma sessão não tiver colocações possíveis.
        RuntimeError: Se o CP-SAT não encontrar uma solução viável.
    """
    sessoes = construir_sessoes(dados["turmas"], dados["disciplinas"])
    model = cp_model.CpModel()
    variaveis, capacidades, nomes_sala = _criar_variaveis(model, dados, sessoes)

    # Cada chamada adiciona uma família independente de restrições ao modelo.
    _adicionar_uma_colocacao_por_sessao(model, sessoes, variaveis)
    _adicionar_sem_sobreposicoes(model, sessoes, variaveis, "turma")
    _adicionar_sem_sobreposicoes(model, sessoes, variaveis, "professor")
    _adicionar_limite_disciplina_por_dia(model, sessoes, variaveis)
    _adicionar_capacidade_salas(model, sessoes, variaveis, capacidades)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    # FEASIBLE basta: nesta versão não há objetivo de otimização definido.
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Não foi encontrado horário: {solver.StatusName(status)}")

    horarios = []
    # Só as variáveis escolhidas pelo solver (valor 1) entram no resultado.
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
    # Permite executar este módulo diretamente para imprimir o horário gerado.
    horario = gerar_horarios(carregar_dados())
    for aula in horario:
        print(
            f"{aula['dia']} P{aula['periodo_inicio']}-P{aula['periodo_fim']}: "
            f"{aula['turma']} - {aula['disciplina']} ({aula['sala']})"
        )

