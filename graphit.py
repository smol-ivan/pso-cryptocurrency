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

    results_dir = Path("./results/")
    output_dir = "./graficas"

    # Limpiar carpeta de salida
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Iterar sobre CSV generados por PSO
    for res_file in results_dir.iterdir():
        if res_file.suffix != ".csv":
            continue

        df_pso = pd.read_csv(res_file)

        # Ordenar por riesgo para que se vea como frontera
        df_pso = df_pso.sort_values(by="risk")

        graph_generator(df_pso, res_file.stem, output_dir)

    print(f"Gráficas generadas en carpeta: {output_dir}")


if __name__ == "__main__":
    main()
