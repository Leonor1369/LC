from csv import DictReader
from pathlib import Path
from typing import List, Dict, Any


def _ler_csv(caminho: str, colunas_obrigatorias: set[str]) -> List[Dict[str, str]]:
    with open(caminho, newline="", encoding="utf8") as ficheiro:
        reader = DictReader(ficheiro)
        colunas = set(reader.fieldnames or [])
        em_falta = colunas_obrigatorias - colunas
        if em_falta:
            raise ValueError(f"{caminho}: faltam as colunas {sorted(em_falta)}")
        return list(reader)


def ler_turmas(pasta_dados: str = "dados") -> List[str]:
    caminho = str(Path(pasta_dados) / "turmas.csv")
    linhas = _ler_csv(caminho, {"turma"})
    return [(linha["turma"] or "").strip() for linha in linhas]


def ler_salas(pasta_dados: str = "dados") -> List[Dict[str, Any]]:
    caminho = str(Path(pasta_dados) / "salas.csv")
    linhas = _ler_csv(caminho, {"sala", "tipo", "quantidade"})
    return [{
        "sala": (linha["sala"] or "").strip(),
        "tipo": (linha["tipo"] or "").strip().lower(),
        "quantidade": int(linha["quantidade"]),
    } for linha in linhas]


def ler_disciplinas(pasta_dados: str = "dados") -> List[Dict[str, Any]]:
    caminho = str(Path(pasta_dados) / "disciplinas.csv")
    linhas = _ler_csv(caminho, {
        "disciplina", "professor", "carga_semanal", "duplo_periodo", "sala_especial"
    })
    disciplinas = []
    for linha in linhas:
        duplo = (linha["duplo_periodo"] or "").strip().lower()
        if duplo not in {"sim", "nao"}:
            raise ValueError(
                f"{caminho}: duplo_periodo deve ser 'sim' ou 'nao'; valor recebido: {duplo!r}"
            )
        disciplinas.append({
            "disciplina": (linha["disciplina"] or "").strip(),
            "professor": (linha["professor"] or "").strip(),
            "carga_semanal": int(linha["carga_semanal"]),
            "duplo_periodo": duplo == "sim",
            "sala_especial": (linha["sala_especial"] or "").strip(),
        })
    return disciplinas


def ler_dispo_exc(pasta_dados: str = "dados") -> List[Dict[str, Any]]:
    caminho = str(Path(pasta_dados) / "disponibilidade_excecoes.csv")
    linhas = _ler_csv(caminho, {"professor", "dia", "periodo"})
    return [{
        "professor": (linha["professor"] or "").strip(),
        "dia": (linha["dia"] or "").strip(),
        "periodo": int(linha["periodo"]),
    } for linha in linhas]


def validar_dados(dados: Dict[str, Any]) -> None:
    turmas = dados["turmas"]
    salas = dados["salas"]
    disciplinas = dados["disciplinas"]
    excecoes = dados["disponibilidade_excecoes"]

    if not turmas or any(not turma for turma in turmas):
        raise ValueError("A lista de turmas não pode estar vazia nem conter nomes vazios.")
    if len(turmas) != len(set(turmas)):
        raise ValueError("Existem turmas repetidas em turmas.csv.")
    if not salas or not disciplinas:
        raise ValueError("É necessário definir pelo menos uma sala e uma disciplina.")

    tipos_sala = {"normal", "especial"}
    for sala in salas:
        if not sala["sala"] or sala["tipo"] not in tipos_sala:
            raise ValueError(f"Sala com nome vazio ou tipo inválido: {sala}")
        if sala["quantidade"] <= 0:
            raise ValueError(f"A quantidade da sala tem de ser positiva: {sala}")

    nomes_especiais = {
        sala["sala"] for sala in salas if sala["tipo"] == "especial"
    }
    professores = {disciplina["professor"] for disciplina in disciplinas}
    for disciplina in disciplinas:
        if not disciplina["disciplina"] or not disciplina["professor"]:
            raise ValueError(f"Disciplina ou professor vazio: {disciplina}")
        if disciplina["carga_semanal"] <= 0:
            raise ValueError(f"A carga semanal tem de ser positiva: {disciplina}")
        if disciplina["duplo_periodo"] and disciplina["carga_semanal"] % 2 != 0:
            raise ValueError(
                f"A carga de uma disciplina de duplo período tem de ser par: {disciplina}"
            )
        sala_especial = disciplina["sala_especial"]
        if sala_especial and sala_especial not in nomes_especiais:
            raise ValueError(
                f"A sala especial {sala_especial!r} de {disciplina['disciplina']} "
                "não existe como sala do tipo 'especial'."
            )
        if not sala_especial and not any(sala["tipo"] == "normal" for sala in salas):
            raise ValueError(
                f"{disciplina['disciplina']} precisa de sala normal, mas não há salas normais."
            )

    dias = {"Seg", "Ter", "Qua", "Qui", "Sex"}
    vistos = set()
    for excecao in excecoes:
        chave = (excecao["professor"], excecao["dia"], excecao["periodo"])
        if excecao["professor"] not in professores:
            raise ValueError(f"Professor desconhecido na disponibilidade: {excecao}")
        if excecao["dia"] not in dias or not 1 <= excecao["periodo"] <= 5:
            raise ValueError(f"Dia ou período inválido na disponibilidade: {excecao}")
        if chave in vistos:
            raise ValueError(f"Exceção de disponibilidade repetida: {excecao}")
        vistos.add(chave)


def construir_sessoes(
    turmas: List[str], disciplinas: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    sessoes = []
    for turma in turmas:
        for disciplina in disciplinas:
            duracao = 2 if disciplina["duplo_periodo"] else 1
            numero_sessoes = disciplina["carga_semanal"] // duracao
            for numero in range(numero_sessoes):
                sessoes.append({
                    "turma": turma,
                    "disciplina": disciplina["disciplina"],
                    "professor": disciplina["professor"],
                    "duracao": duracao,
                    "sala_especial": disciplina["sala_especial"],
                    "ocorrencia": numero + 1,
                })
    return sessoes


def salas_compativeis(
    disciplina: Dict[str, Any], salas: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if disciplina["sala_especial"]:
        return [
            sala for sala in salas
            if sala["tipo"] == "especial" and sala["sala"] == disciplina["sala_especial"]
        ]
    return [sala for sala in salas if sala["tipo"] == "normal"]


def carregar_dados(pasta_dados: str = "dados") -> Dict[str, Any]:
    """Carrega e valida os quatro CSVs da pasta indicada."""
    dados = {
        "turmas": ler_turmas(pasta_dados),
        "salas": ler_salas(pasta_dados),
        "disciplinas": ler_disciplinas(pasta_dados),
        "disponibilidade_excecoes": ler_dispo_exc(pasta_dados),
    }
    validar_dados(dados)
    return dados


if __name__ == "__main__":
    dados = carregar_dados()
    print(dados["turmas"])
    print(dados["salas"])
    print(dados["disciplinas"])
    print(dados["disponibilidade_excecoes"])
