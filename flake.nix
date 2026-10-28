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
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          uv
        ];

        # Comandos o variables de entorno al entrar a la shell
        shellHook = ''
          echo "⚡ Entorno de desarrollo cargado con éxito"
          alias run="uv run streamlit run app.py"
          echo "Alias cargados: run"
        '';
      };
    };
}
