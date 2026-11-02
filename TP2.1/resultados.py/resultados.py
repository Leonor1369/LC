# ---------- testes ----------
def test_contagem_celulas():
        for n in range(4, 8):
            M = GameOfLife(n, "sync")  # ty: ignore[unresolved-reference]
            normais, iniciais, finais = set(M.normais), set(M.iniciais), set(M.finais)
            assert len(normais) == n * n
            assert len(iniciais) == 2 * n + 3
            assert len(finais) == 2 * n + 1
            assert not (normais & iniciais) and not (normais & finais) and not (iniciais & finais)
            assert len(normais | iniciais | finais) == (n + 2) ** 2

def test_vizinhos():
        M = GameOfLife(5, "sync")  # ty: ignore[unresolved-reference]
        todas = set(M.normais) | set(M.iniciais) | set(M.finais)
        for c in M.normais:
            assert len(M.viz[c]) == 8 and len(set(M.viz[c])) == 8
            assert c not in M.viz[c]
            assert all(v in todas for v in M.viz[c])

def test_regra_bloco():
        bloco = {(2, 2), (2, 3), (3, 2), (3, 3)}
        for modo in ("sync", "async"):
            assert _sucessores(_modelo(5, modo, bloco)) == [bloco]  # ty: ignore[unresolved-reference]

def test_regra_blinker():
        horizontal = {(3, 2), (3, 3), (3, 4)}
        vertical = {(2, 3), (3, 3), (4, 3)}
        assert _sucessores(_modelo(5, "sync", horizontal)) == [vertical]  # ty: ignore[unresolved-reference]
        assert _sucessores(_modelo(5, "sync", vertical)) == [horizontal]  # ty: ignore[unresolved-reference]

def test_async_muda_uma_celula():
        vivas = {(1, 1), (1, 2), (2, 1), (3, 3), (4, 2)}
        M = _modelo(4, "async", vivas)  # ty: ignore[unresolved-reference]
        # células que a regra B3/S23 manda mudar (cálculo direto, sem Z3)
        def n_vivos(c):
            return sum(1 for v in M.viz[c] if v in vivas)
        def novo(c):
            n = n_vivos(c)
            return n == 3 or (c in vivas and n == 2)
        podem_mudar = {c for c in M.normais if novo(c) != (c in vivas)}
        sucs = _sucessores(M)  # ty: ignore[unresolved-reference]
        assert len(sucs) == len(podem_mudar) > 0
        for t in sucs:
            dif = t ^ vivas
            assert len(dif) == 1 and dif <= podem_mudar

def test_async_stuttering():
        bloco = {(1, 1), (1, 2), (2, 1), (2, 2)}
        assert _sucessores(_modelo(4, "async", bloco)) == [bloco]  # ty: ignore[unresolved-reference]

def test_z3_igual_explicito():
        for seed in (1, 7, 42, 2026):
            ini = sorteia_iniciais(4, 0.5, seed)  # ty: ignore[unresolved-reference]
            M = GameOfLife(4, "sync", ini)  # ty: ignore[unresolved-reference]
            r = bmc(M, M.erro, 20)  # ty: ignore[unresolved-reference]
            esperado = explicito(4, ini, "sync")["erro"]  # ty: ignore[unresolved-reference]
            assert (r[0] if r else None) == esperado
def test_resultados_enunciado():
        ini = sorteia_iniciais(4, 0.5, 2026)
        Ms = GameOfLife(4, "sync", ini)
        assert bmc(Ms, Ms.erro, 30) is None
        assert kinducao(Ms, lambda s: Not(Ms.erro(s)), 30)[0].startswith("PROVADO")
        Msimb = GameOfLife(4, "sync")
        assert bmc(Msimb, Msimb.erro, 30)[0] == 3
        Ma = GameOfLife(4, "async", ini)
        assert bmc(Ma, Ma.erro, 30)[0] == 9
        assert explicito(4, ini, "async")["erro"] == 9
# ---------- correr os testes dentro do notebook ----------
_testes = [test_contagem_celulas, test_vizinhos, test_regra_bloco, test_regra_blinker,
               test_async_muda_uma_celula, test_async_stuttering, test_z3_igual_explicito,
               test_resultados_enunciado]
_falhas = 0
for _t in _testes:
        try:
            _t()
            print(f"  OK     {_t.__name__}")
        except AssertionError as _e:
            _falhas += 1
            print(f"  FALHOU {_t.__name__} {_e}")
    print(f"\n{len(_testes) - _falhas}/{len(_testes)} testes passaram")
_ = And  # (And importado para uso eventual em novos testes)
return


if __name__ == "__main__":
    app.run()  