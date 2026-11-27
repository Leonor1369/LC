
## Exercício 2

Raiz quadrada inteira.

Considere o seguinte programa
```
    INPUT  n
    assume 0 <= n < B
    r, s, t = 0, 1, 1
    while s <= n:
        r, t = r + 1, t + 2
        s = s + t
    OUTPUT r
    assert r^2 <= n < (r+1)^2
```

As variáveis são inteiros sem sinal de w bits (com w par). Considera-se estado de erro o “overflow” na soma $$\,s+t\,$$.

Pretende-se:

1. Identificar o CFA que representa o programa: os locais, as guardas, o transformador de predicados “weakest pre-condition” de cada local e os locais `error` e `stop`.
2. Escrever os dois sistemas de CHCs , o orientado às pré-condições e o orientado às pós-condições. Tentar resolvê-los com o Spacer em `BitVec`, para $$\,w\,$$ pequeno, e em `Int`; documentar os limites encontrados.
3. Determinar o maior $$\,\mathsf{B}\,$$, em função de $$\,w\,$$, para o qual o local `error` é inacessível. Provar que o programa é seguro para esse $$\,\mathsf{B}\,$$ e inseguro para $$\,\mathsf{B}+1$$.
4. Provar que o programa termina sempre, usando uma função de “ranking” codificada em CHCs ou a metodologia dos “look-aheads”.

## Entrega

A resolução deste exercício deve ser implementada num **notebook Marimo** nesta pasta.

```text
TP3.2/
├── README.md
└── notebook.py
```

Para editar/executar o notebook:

```bash
marimo edit TP3.2/notebook.py
```

### Estrutura recomendada

- [ ] Representar explicitamente os locais do CFA e as respetivas transições.
- [ ] Apresentar as guardas e o transformador de estado de cada local.
- [ ] Construir o sistema de CHCs orientado às pré-condições.
- [ ] Construir o sistema de CHCs orientado às pós-condições.
- [ ] Experimentar Spacer em `BitVec` para valores pequenos de $w$.
- [ ] Experimentar Spacer em `Int` e documentar eventuais limitações.
- [ ] Calcular o maior $\mathsf{B}$ seguro em função de $w$.
- [ ] Demonstrar por resolução independente que $\mathsf{B}$ é seguro e que $\mathsf{B}+1$ é inseguro.
- [ ] Implementar uma função de ranking em CHCs ou os look-aheads.
- [ ] Demonstrar a terminação em `stop` e a inacessibilidade de `error` no domínio seguro.
- [ ] Executar o notebook até ao fim e verificar os resultados apresentados pelo solver.


# LLM
claude a explicar o que envolve o problema o CHC e o spacer https://claude.ai/share/fc243a5b-d02a-4e10-86f4-7e9ca4f854e9