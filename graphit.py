import argparse
import os
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


# ------------------------------------------------------
# Generación de gráfica CVaR vs Return
# ------------------------------------------------------
def graph_generator(df_pso, file_name, output_dir):
    fig, ax = plt.subplots()

    sns.scatterplot(
        data=df_pso,
        x="risk",
        y="return",
        ax=ax,
        color="teal",
        s=60,
        label="PSO (CVaR)",
    )

    ax.set_title("Efficient Frontier using CVaR", pad=15)
    ax.set_xlabel("CVaR (95%)")
    ax.set_ylabel("Expected Return")

    ax.legend()

    save_path = os.path.join(output_dir, f"{file_name}.png")
    plt.savefig(save_path)
    plt.close()


# ------------------------------------------------------
# Main
# ------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="graphit",
        description="Genera gráficas de frontera eficiente desde CSV del PSO",
    )
    parser.add_argument(
        "--returns-source",
        choices=["historical", "garch"],
        default="historical",
        help="Fuente de retornos para ubicar carpeta de resultados",
    )
    args = parser.parse_args()

    sns.set_theme(style="whitegrid")

    plt.rcParams.update(
        {
            "figure.figsize": (7, 5),
            "font.size": 12,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )

    base_dir = Path("outputs") / args.returns_source
    results_dir = base_dir / "results"
    output_dir = base_dir / "graficas"

    if not results_dir.exists():
        print(f"No existe carpeta de resultados: {results_dir}")
        return

    # Limpiar carpeta de salida del modo seleccionado
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Iterar sobre CSV generados por PSO
    for res_file in results_dir.iterdir():
        if res_file.suffix != ".csv":
            continue

        df_pso = pd.read_csv(res_file)

        # Ordenar por riesgo para que se vea como frontera
        df_pso = df_pso.sort_values(by="risk")

        graph_generator(df_pso, res_file.stem, str(output_dir))

    print(f"Gráficas generadas en carpeta: {output_dir}")


if __name__ == "__main__":
    main()
