import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    from read_data import carregar_dados

    dados = carregar_dados()
    dados
    return


if __name__ == "__main__":
    app.run()
