{
  description = "Application packaged using poetry2nix";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    {
      # Nixpkgs overlay providing the application
      overlay = nixpkgs.lib.composeManyExtensions [
        poetry2nix.overlay
        (final: prev: {
          # The application
          magint-calc = prev.poetry2nix.mkPoetryApplication {
            projectDir = ./.;
            python = prev.python310;
          };
          magint-calc-env = prev.poetry2nix.mkPoetryEnv {
            projectDir = ./.;
            python = prev.python310;
          };
        })
      ];
    } // (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlay ];
        };
      in
      {
        apps = {
          magint-calc = pkgs.magint-calc;
        };
        defaultApp = pkgs.magint-calc;
      devShell = pkgs.mkShell {
        nativeBuildInputs = [
          pkgs.python310Packages.poetry
          pkgs.python310Packages.uvicorn
          pkgs.magint-calc-env
          pkgs.redis
        ];
      };
      }));
}
