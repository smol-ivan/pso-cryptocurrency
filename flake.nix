{
  description = "Entorno para desarrollo y muestra del proyecto terminal";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      runApp = pkgs.writeShellScriptBin "run" ''
        uv run streamlit run app.py
      '';

      runTests = pkgs.writeShellScriptBin "dev" ''
        uv run streamlit run validation_dashboard.py
      '';
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          uv
          runApp
          runTests
        ];

        shellHook = ''
          echo "Entorno de desarrollo cargado con éxito"
          echo "Comando disponible: [run dev]"
        '';
      };
    };
}
