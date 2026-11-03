"""
Testes simples do SFOTS de multiplicação (ficheiro à parte do notebook).

    pip install pytest
    pytest test_mult.py -v

Importa a classe Mult e as funções de verificação diretamente do notebook.py
(declaradas com @app.class_definition / @app.function).
"""
from pysmt.shortcuts import BV, And, Not, BVULT, simplify, substitute

from notebook import (
    LOOP, EVEN, ODD, STOP, ERROR,
    Mult, resolve, unroll, kinducao, invariantes, bmc,
    termina_J, termina_V, decresce, sem_bloqueio,
)

N = 4          # largura usada nos testes (rápida)
# exceto as execuç~oes concretas que usam n = 8


# ---------------------------------------------------------------------------
# auxiliares
# ---------------------------------------------------------------------------

def vale(formula, valores):
    """Substitui os símbolos por constantes e diz se a fórmula fica TRUE.
    Serve para avaliar fórmulas sem chamar o solver."""
    return simplify(substitute(formula, valores)).is_true()


def transicao_ok(M, antes, depois):
    """A transição (pc, x, y, z) -> (pc', x', y', z') é permitida por M.trans? (a=3, b=5 fixos)"""
    s, p = M.declare(0), M.declare(1)
    valores = {}
    for st, (pc, x, y, z) in ((s, antes), (p, depois)):
        valores[st['pc']] = BV(pc, 3)
        valores[st['a']], valores[st['b']] = BV(3, M.n), BV(5, M.n)
        valores[st['x']], valores[st['y']], valores[st['z']] = BV(x, M.n), BV(y, M.n), BV(z, M.n)
    return vale(M.trans(s, p), valores)

def executa(M, a, b, passos):
    """ fixa a e b, desenrola a transição passos vezes e devolve o pc e o z finais."""
    estados, transicoes = unroll(M, passos)
    m = resolve(M.init(estados[0]),
                And(estados[0]['a'].Equals(BV(a, M.n)), estados[0]['b'].Equals(BV(b, M.n))),
                *transicoes)
    final = estados[-1]
    return m.get_py_value(final['pc']), m.get_py_value(final['z'])

# ---------------------------------------------------------------------------
# overflow
# ---------------------------------------------------------------------------

def test_overflow_soma_sem_sinal():
    """para todos os pares (x, z) de 4 bits, ovf_soma é verdadeiro exatamente quando x + z > 15."""
    M = Mult(N, com_sinal=False)
    s = M.declare(0)
    for x in range(16):
        for z in range(16):
            esperado = x + z > 15
            assert vale(M.ovf_soma(s), {s['x']: BV(x, N), s['z']: BV(z, N)}) == esperado


def test_overflow_soma_com_sinal():
    """ o mesmo em complemento para dois: há overflow quando a soma sai de [−8, 7]."""
    M = Mult(N, com_sinal=True)
    s = M.declare(0)
    com_sinal = lambda v: v - 16 if v >= 8 else v
    for x in range(16):
        for z in range(16):
            esperado = not (-8 <= com_sinal(x) + com_sinal(z) <= 7)
            assert vale(M.ovf_soma(s), {s['x']: BV(x, N), s['z']: BV(z, N)}) == esperado


def test_overflow_shift():
    """para todo o x, ovf_shift dá overflow quando 2x > 15 (sem sinal) ou quando 2x sai de [−8, 7] (com sinal)."""
    s_u, s_s = Mult(N, False).declare(0), Mult(N, True).declare(0)
    for x in range(16):
        sem = vale(Mult(N, False).ovf_shift(s_u), {s_u['x']: BV(x, N)})
        com = vale(Mult(N, True).ovf_shift(s_s), {s_s['x']: BV(x, N)})
        assert sem == (2 * x > 15)
        assert com == (not (-8 <= 2 * (x - 16 if x >= 8 else x) <= 7))


# ---------------------------------------------------------------------------
# relação de transição (exemplos concretos)
# ---------------------------------------------------------------------------

def test_transicoes_do_loop():
    """a partir de LOOP, y = 0 vai para STOP, y par vai para EVEN e y ímpar vai para ODD, sem alterar x, y, z."""
    M = Mult(N)
    assert transicao_ok(M, (LOOP, 3, 0, 0), (STOP, 3, 0, 0))     # y = 0
    assert transicao_ok(M, (LOOP, 3, 6, 0), (EVEN, 3, 6, 0))     # y par
    assert transicao_ok(M, (LOOP, 3, 5, 0), (ODD, 3, 5, 0))      # y ímpar


def test_transicao_even_e_odd():
    """EVEN faz x<<1 e y>>1; ODD faz y−1 e z+x; ambos voltam a LOOP."""
    M = Mult(N)
    assert transicao_ok(M, (EVEN, 3, 6, 1), (LOOP, 6, 3, 1))     # x<<1, y>>1
    assert transicao_ok(M, (ODD, 3, 5, 1), (LOOP, 3, 4, 4))      # y-1, z+x


def test_overflow_leva_a_erro():
    """com overflow, EVEN e ODD vão para ERROR e a transição normal para LOOP é rejeitada (precedência do erro)."""
    M = Mult(N)
    assert transicao_ok(M, (EVEN, 8, 2, 0), (ERROR, 8, 2, 0))    # 8<<1 não cabe em 4 bits
    assert not transicao_ok(M, (EVEN, 8, 2, 0), (LOOP, 0, 1, 0))
    assert transicao_ok(M, (ODD, 9, 3, 9), (ERROR, 9, 3, 9))     # 9+9 não cabe


def test_stop_e_error_ficam_parados():
    """STOP e ERROR têm laço em si próprios e não podem sair para LOOP."""
    M = Mult(N)
    assert transicao_ok(M, (STOP, 3, 0, 6), (STOP, 3, 0, 6))
    assert transicao_ok(M, (ERROR, 3, 2, 6), (ERROR, 3, 2, 6))
    assert not transicao_ok(M, (STOP, 3, 0, 6), (LOOP, 3, 0, 6))


# ---------------------------------------------------------------------------
# unroll e execuções
# ---------------------------------------------------------------------------

def test_unroll_tem_k_mais_um_estados():
    # regressão do IndexError: k transições precisam de k+1 estados
    for k in (1, 4, 16):
        estados, transicoes = unroll(Mult(N), k)
        assert len(estados) == k + 1
        assert len(transicoes) == k


def test_execucao_13_vezes_11():
    """com n = 8, a execução termina em STOP com z = 143."""
    assert executa(Mult(8), 13, 11, 32) == (STOP, 143)


def test_execucao_com_overflow():
    """200*3 não cabe em 8 bits sem sinal, logo acaba em ERROR."""
    assert executa(Mult(8), 200, 3, 32)[0] == ERROR


def test_execucao_com_sinal():
    """9*7 dá STOP com z = 63; 100·3 dá ERROR (300 > 127)."""
    assert executa(Mult(8, com_sinal=True), 9, 7, 32) == (STOP, 63)
    assert executa(Mult(8, com_sinal=True), 100, 3, 32)[0] == ERROR


# ---------------------------------------------------------------------------
# k-indução, BMC, segurança
# ---------------------------------------------------------------------------

def test_invariante_provado_com_k_2():
    """x·y+z = a·b é provado com k = 2, nas versões modular e exata."""
    M = Mult(N)
    P_mod, P_exato = invariantes(M)
    assert kinducao(M, P_mod, 6)[0] == "PROVADO com k=2"
    assert kinducao(M, P_exato, 6)[0] == "PROVADO com k=2"


def test_invariante_nao_e_1_indutivo():
    """com K = 1 o resultado é INCONCLUSIVO (estados inalcançáveis quebram o passo)."""
    M = Mult(N)
    P_mod, _ = invariantes(M)
    assert kinducao(M, P_mod, 1)[0].startswith("INCONCLUSIVO")


def test_propriedade_falsa_e_detetada():
    """a propriedade ¬ERROR sem restrições é declarada FALSO, porque ERROR é alcançável."""
    M = Mult(N)
    resultado, _ = kinducao(M, lambda s: Not(M.erro(s)), 6)     # ERROR é alcançável
    assert resultado.startswith("FALSO")


def test_bmc_encontra_erro_sem_restricao():
    """o BMC encontra o erro em k = 2 (LOOP → EVEN → ERROR)."""
    M = Mult(N)
    k, _, _ = bmc(M, M.erro, 4 * N)
    assert k == 2                                               # LOOP -> EVEN -> ERROR


def test_seguranca_com_a_b_pequenos():
    """com a, b < 2^(N/2): o BMC não encontra erro; a propriedade reforçada prova-se com k = 2; a direta só com k = 4N."""
    M = Mult(N)
    _, P_exato = invariantes(M)
    h = BV(2 ** (N // 2), N)
    pequenos = lambda s: And(BVULT(s['a'], h), BVULT(s['b'], h))
    seguro = lambda s: And(Not(M.erro(s)), pequenos(s))
    seguro_r = lambda s: And(seguro(s), P_exato(s))

    assert bmc(M, M.erro, 4 * N, extra=pequenos) is None
    assert kinducao(M, seguro_r, 6, extra=pequenos)[0] == "PROVADO com k=2"
    assert kinducao(M, seguro, 4 * N + 2, extra=pequenos)[0] == f"PROVADO com k={4 * N}"


# ---------------------------------------------------------------------------
# terminação
# ---------------------------------------------------------------------------

def test_terminacao():
    """J é invariante (k-indução), V decresce fora dos estados terminais, e não há bloqueio."""
    M = Mult(N)
    J, V = termina_J(M), termina_V(M)
    assert kinducao(M, J, 3)[0].startswith("PROVADO")           # J é invariante
    assert decresce(M, J, V)                                    # V decresce
    assert sem_bloqueio(M, J)                                   # sempre há sucessor


def test_variante_errada_e_rejeitada():
    """com V = y, decresce devolve falso, porque em LOOP → EVEN/ODD o y não muda. Confirma que a verificação não aceita qualquer variante."""
    M = Mult(N)
    assert not decresce(M, termina_J(M), lambda s: s['y'])      # V = y não decresce em LOOP