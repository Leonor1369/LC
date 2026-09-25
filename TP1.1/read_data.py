from csv import DictReader
from typing import List, Dict

def ler_turmas(caminho: str = "dados/turmas.csv") -> List[Dict[str, str]]:
    with open(caminho, newline="", encoding="utf8") as turma_data:
        reader_turma = DictReader(turma_data)
        return list(reader_turma)


def ler_salas(caminho: str = "dados/salas.csv") -> List[Dict[str, object]]:
    with open(caminho, newline="", encoding="utf8") as sala_data:
        reader_sala = DictReader(sala_data)
        salas = []
        for linha in reader_sala:
            linha["quantidade"] = int(linha["quantidade"])
            salas.append(linha)
        return salas

def ler_disciplinas(caminho: str = "dados/disciplinas.csv") -> List[Dict[str, object]]:
    with open(caminho, newline="", encoding="utf8") as disciplinas_data:
            reader_dis = DictReader(disciplinas_data)
            dis = []
            for linha in reader_dis:
                linha["carga_semanal"] = int(linha["carga_semanal"])
                dis.append(linha)
            return dis


def ler_dispo_exc(caminho: str = "dados/disponibilidade_excecoes.csv") -> List[Dict[str, object]]:
    with open(caminho, newline="", encoding="utf8") as dispo_exc:
                reader_dispo = DictReader(dispo_exc)
                dispo = []
                for linha in reader_dispo:
                    linha["periodo"] = int(linha["periodo"])
                    dispo.append(linha)
                return dispo

if __name__ == "__main__":
    turmas = ler_turmas()
    salas = ler_salas()
    disciplinas = ler_disciplinas()
    dispo_exce = ler_dispo_exc()
    # Aqui podes chamar estas funções mais tarde no teu main
    print(turmas)
    print(salas)
    print(disciplinas)
    print(dispo_exce)


# video that i watch to learn https://www.youtube.com/watch?v=5CEsJkKhS78
