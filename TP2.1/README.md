# TP2 — Exercício 1: *Game of Life* finito como máquina de estados finita

Lógica Computacional 2026/27 · Universidade do Minho

Modelação de uma variante finita do *Game of Life* (regra B3/S23) como uma
máquina de estados finita (FSM) em Z3 e verificação de duas propriedades:

- **P1:** nunca se alcança o estado de erro (todas as células normais mortas);
- **P2:** nenhuma célula normal está permanentemente morta ou permanentemente viva.

## Ficheiros

| ficheiro | conteúdo |
|---|---|
| `game_of_life_enunciado.ipynb` | notebook fornecido pelo professor (não alterado) |
| `game_of_life.py` | resolução, em notebook Marimo |
| `resultados/` | exportações HTML do notebook já executado (N = 4 e N = 6) |

## Como correr

```bash
pip install z3-solver marimo
marimo edit game_of_life.py
```

Todos os parâmetros estão na célula **Parâmetros**:

| parâmetro | significado | valor por omissão |
|---|---|---|
| `N` | dimensão da grelha de células normais (N > 3) | 6 |
| `MODO` | `"sync"`: todas as células mudam; `"async"`: uma e só uma muda | `"sync"` |
| `P_VIVA` | probabilidade de uma célula inicial estar viva | 0.5 |
| `SEED` | semente do sorteio das células iniciais | 2026 |
| `NASCE`, `SOBREVIVE` | regra B/S | {3}, {2, 3} |
| `K_MAX` | limite para BMC / k-indução | 30 |

Para exportar os resultados sem abrir o editor:

```bash
marimo export html game_of_life.py -o resultados/game_of_life_N6.html
```

## Modelo

- **Células:** grelha de índices 0..N+1. Há N² células normais, 2N+3 iniciais
  (i = 0 ou j = 0) e 2N+1 finais (i = N+1 ou j = N+1, não iniciais).
- **Estado:** um booleano por célula normal. As células iniciais e finais são
  constantes. As iniciais podem ser sorteadas ou simbólicas; no caso
  simbólico, uma só verificação cobre todas as configurações.
- **Transição `sync`:** todas as células aplicam a regra em simultâneo.
- **Transição `async`:** muda exatamente uma das células que podem mudar. Se
  nenhuma pode mudar, o estado repete-se (*stuttering*).

## Métodos

- **BMC** para encontrar contra-exemplos.
- **k-indução com caminhos simples + diâmetro de recorrência**, completa
  para sistemas finitos.
- **Laços** (*lassos*) para refutar propriedades de animação (leitura LTL da P2).
- **Enumeração explícita por BFS**, sem Z3, para validar os resultados
  de forma independente.

## Resultados (N = 4, SEED = 2026)

| | `sync` | `async` |
|---|---|---|
| P1, células sorteadas | **verdadeira**: k-indução (diâmetro de recorrência) | **falsa**: erro em 9 transições |
| P1, todas as configurações | **falsa**: 10,1 % das configurações levam ao erro, no mínimo em 3 transições | **falsa** |
| P2, leitura LTL | **falsa**: ponto fixo em t = 11 | **falsa**: estado estável em 5 transições |
| P2, leitura "desde o início" | **falsa**: (4,1) e (4,4) nunca nascem | **verdadeira**: confirmada nos 65 144 estados alcançáveis |

Os resultados do Z3 coincidem com os da enumeração explícita.

## Autoras

- Diana Mota
- Leonor Sousa 