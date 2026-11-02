from z3 import *

n = 4                                   # nº de bits (começa pequeno!)
LOOP, ODD, EVEN, STOP, ERROR = range(5) # localizações do CFA

# BitVec(nome, n) cria um vetor de bits de largura fixa; a aritmética é módulo 2^n.
# ULT(a, b) verifica se a < b tratando os vetores como números sem sinal.
# Extract(high, low, x) extrai de x os bits entre high e low, inclusive.
# BitVecVal(valor, n) cria uma constante representada por n bits.
# And(c1, ...) combina restrições com conjunção lógica.
# LShR(x, k) desloca x k posições à direita e preenche com zeros à esquerda.
# Or(c1, ...) combina restrições com disjunção lógica.
# Not(c) nega uma restrição lógica.
# ZeroExt(k, x) aumenta a largura de x em k bits, acrescentando zeros à esquerda.

# ---------- 1. ESTADO: um dicionário de variáveis por instante i ----------
def declare(i):
    s = {"pc": BitVec(f"pc{i}", 3)}
    for v in "abxyz":
        s[v] = BitVec(f"{v}{i}", n)
    return s

# ---------- 2. OVERFLOW (sem sinal) ----------
def ovf_add(x, z): return ULT(z + x, z)                 # soma ficou menor que um operando
def ovf_shl(x):    return Extract(n - 1, n - 1, x) == 1 # bit mais significativo = 1

# ---------- 3. ESTADO INICIAL ----------
def init(s, pequenos=False):
    c = [s["pc"] == LOOP, s["x"] == s["a"], s["y"] == s["b"], s["z"] == 0]
    if pequenos:                                        # a, b < 2^(n/2)
        lim = BitVecVal(2 ** (n // 2), n)
        c += [ULT(s["a"], lim), ULT(s["b"], lim)]
    return And(c)

# ---------- 4. TRANSIÇÃO ----------
def trans(s, p):
    x, y, z = s["x"], s["y"], s["z"]
    def vai(pc, nx=None, ny=None, nz=None):             # None = "fica igual"
        return And(p["pc"] == pc,
                   p["x"] == (x if nx is None else nx),
                   p["y"] == (y if ny is None else ny),
                   p["z"] == (z if nz is None else nz))
    return And(p["a"] == s["a"], p["b"] == s["b"],      # a e b nunca mudam
        Or(
        And(s["pc"] == LOOP, y == 0,              vai(STOP)),
        And(s["pc"] == LOOP, y != 0, y & 1 == 1,  vai(ODD)),
        And(s["pc"] == LOOP, y != 0, y & 1 == 0,  vai(EVEN)),
        And(s["pc"] == ODD,  Not(ovf_add(x, z)),  vai(LOOP, ny=y - 1, nz=z + x)),
        And(s["pc"] == ODD,  ovf_add(x, z),       vai(ERROR)),
        And(s["pc"] == EVEN, Not(ovf_shl(x)),     vai(LOOP, nx=x << 1, ny=LShR(y, 1))),
        And(s["pc"] == EVEN, ovf_shl(x),          vai(ERROR)),
        And(s["pc"] == STOP,                      vai(STOP)),    # estados finais ficam parados
        And(s["pc"] == ERROR,                     vai(ERROR))))

# ---------- 5. ERRO ----------
def erro(s): return s["pc"] == ERROR

# ---------- 6. K-INDUÇÃO genérica ----------
def kind(P, K, pequenos=False):
    for k in range(1, K + 1):
        # caso base: de INIT, P vale nos primeiros k estados
        t = [declare(i) for i in range(k)]
        S = Solver()
        S.add(init(t[0], pequenos), *[trans(t[i], t[i+1]) for i in range(k - 1)])
        S.add(Or([Not(P(s)) for s in t]))
        if S.check() == sat:
            return f"FALSO (contraexemplo no caso base, k={k})"
        # passo: P em k estados seguidos => P no seguinte
        t = [declare(i) for i in range(k + 1)]
        S = Solver()
        for i in range(k):
            S.add(trans(t[i], t[i+1]), P(t[i]))
        S.add(Not(P(t[k])))
        if S.check() == unsat:
            return f"PROVADO com k={k}"
    return f"inconclusivo até k={K}"

W = lambda v: ZeroExt(n, v)                              # alarga para 2n bits

# ---------- 7. PROPRIEDADES ----------
inv_mod = lambda s: s["x"]*s["y"] + s["z"] == s["a"]*s["b"]
inv_ex  = lambda s: W(s["x"])*W(s["y"]) + W(s["z"]) == W(s["a"])*W(s["b"])
pequeno = lambda s: And(ULT(s["a"], 2**(n//2)), ULT(s["b"], 2**(n//2)))

print("1.1 invariante (módulo 2^n):", kind(inv_mod, 5))
print("1.1 invariante (exato 2n)  :", kind(inv_ex, 5))
print("1.2 ¬ERROR sozinho         :", kind(lambda s: Not(erro(s)), 5, pequenos=True))
print("1.2 ¬ERROR ∧ pequenos ∧ inv:", kind(lambda s: And(Not(erro(s)), pequeno(s), inv_ex(s)), 5, pequenos=True))

# ---------- 8. TERMINAÇÃO (BMC) ----------
final = lambda s: Or(s["pc"] == STOP, s["pc"] == ERROR)
t = [declare(i) for i in range(4*n + 1)]
S = Solver()
S.add(init(t[0]), *[trans(t[i], t[i+1]) for i in range(4*n)], *[Not(final(s)) for s in t])
print("1.3 caminho de 4n passos sem terminar:", S.check())   # unsat = termina sempre

# ---------- 9. TESTE concreto: a=3, b=3 ----------
S = Solver(); t = [declare(i) for i in range(10)]
S.add(init(t[0]), t[0]["a"] == 3, t[0]["b"] == 3, *[trans(t[i], t[i+1]) for i in range(9)])
S.check(); m = S.model()
print("trace a=3,b=3:", [(m[s["pc"]].as_long(), m[s["x"]].as_long(), m[s["y"]].as_long(), m[s["z"]].as_long()) for s in t][:8])