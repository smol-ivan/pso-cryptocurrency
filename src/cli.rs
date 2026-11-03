use clap::{Parser, Subcommand};

#[derive(Parser, Debug)]
#[command(
    name = "pso-crypto",
    version,
    about = "Optimizador de portafolio con PSO"
)]
pub struct Cli {
    /// Ruta a archivo de configuración alternativo (opcional)
    #[arg(short, long, default_value = "config.toml")]
    pub config: String,

    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Descargar datos de mercado y guardarlos en base de datos
    UpdateDb,

    /// Calcular y mostrar los límites de target return del dataset
    TargetBounds,

    /// Ejecutar la optimización PSO completa
    OptimizeSingleTest {
        /// Sobrescribir el target_return definido en el config (opcional)
        #[arg(short, long)]
        target_return: Option<f64>,
    },
}
