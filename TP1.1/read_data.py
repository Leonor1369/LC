from csv import DictReader
from typing import List, Dict, Any


def ler_turmas(caminho: str = "dados/turmas.csv") -> List[str]:
    with open(caminho, newline="", encoding="utf8") as turma_data:
        reader_turma = DictReader(turma_data)
        return [linha["turma"].strip() for linha in reader_turma if linha.get("turma")]


def ler_salas(caminho: str = "dados/salas.csv") -> List[Dict[str, Any]]:
    with open(caminho, newline="", encoding="utf8") as sala_data:
        reader_sala = DictReader(sala_data)
        salas = []
        for linha in reader_sala:
            salas.append({
                "sala": linha["sala"].strip(),
                "tipo": linha["tipo"].strip(),
                "quantidade": int(linha["quantidade"]),
            })
        return salas


def ler_disciplinas(caminho: str = "dados/disciplinas.csv") -> List[Dict[str, Any]]:
    with open(caminho, newline="", encoding="utf8") as disciplinas_data:
        reader_dis = DictReader(disciplinas_data)
        disciplinas = []
        for linha in reader_dis:
            disciplinas.append({
                "disciplina": linha["disciplina"].strip(),
                "professor": linha["professor"].strip(),
                "carga_semanal": int(linha["carga_semanal"]),
                "duplo_periodo": linha["duplo_periodo"].strip().lower() == "sim",
                "sala_especial": (linha.get("sala_especial") or "").strip(),
            })
        return disciplinas


def ler_dispo_exc(caminho: str = "dados/disponibilidade_excecoes.csv") -> List[Dict[str, Any]]:
    with open(caminho, newline="", encoding="utf8") as dispo_exc:
        reader_dispo = DictReader(dispo_exc)
        indisponibilidades = []
        for linha in reader_dispo:
            indisponibilidades.append({
                "professor": linha["professor"].strip(),
                "dia": linha["dia"].strip(),
                "periodo": int(linha["periodo"]),
            })
        return indisponibilidades


def carregar_dados():
    return {
        "turmas": ler_turmas(),
        "salas": ler_salas(),
        "disciplinas": ler_disciplinas(),
        "disponibilidade_excecoes": ler_dispo_exc(),
    }


if __name__ == "__main__":
    dados = carregar_dados()
    print(dados["turmas"])
    print(dados["salas"])
    print(dados["disciplinas"])
    print(dados["disponibilidade_excecoes"])
