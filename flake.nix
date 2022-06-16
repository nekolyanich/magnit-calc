{
  description = "Application packaged using poetry2nix";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, flake-utils, poetry2nix }: {
    overlay = nixpkgs.lib.composeManyExtensions [
      poetry2nix.overlay
      (final: prev: {
        magnit-calc = prev.poetry2nix.mkPoetryApplication {
          projectDir = ./.;
          python = prev.python310;
        };
        magnit-calc-env = prev.poetry2nix.mkPoetryEnv {
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
        magnit-calc = pkgs.magnit-calc;
      };
      defaultApp = pkgs.magnit-calc;
      devShell = pkgs.mkShell {
        nativeBuildInputs = [
          pkgs.python310Packages.poetry
          pkgs.magnit-calc-env
          pkgs.redis
        ];
      };
    }
  ));
}
