{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          # herramientas que corren en tu máquina durante el build
          nativeBuildInputs = with pkgs; [
            pkg-config
          ];

          # librerías contra las que se enlaza
          buildInputs = with pkgs; [
            openssl
            openblas
            gfortran.cc.lib # libgfortran, que openblas suele necesitar
          ];

          packages = with pkgs; [
            cargo
            rustc
            rustfmt
            clippy
            rust-analyzer
            postgresql
            sqlx-cli
            docker-compose
            just
            lazydocker
          ];
        };
      }
    );
}
