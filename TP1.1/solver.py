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
    



