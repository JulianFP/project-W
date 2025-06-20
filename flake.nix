{
  description = "This is the frontend for Project-W, a service that converts uploaded audio files into downloadable text transcripts using OpenAIs whisper AI model, hosted on a backend server and dedicated runners.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";
    pnpm2nix-nzbr = {
      #use this instead of main repo nzbr/pnpm2nix-nzbr because this pr fixes compatibility with lockfile v9
      #see https://github.com/nzbr/pnpm2nix-nzbr/pull/40
      url = "github:wrvsrx/pnpm2nix-nzbr/adapt-to-v9";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pre-commit-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      nixpkgs,
      systems,
      pnpm2nix-nzbr,
      ...
    }:
    let
      eachSystem = nixpkgs.lib.genAttrs (import systems);
      pkgsFor = eachSystem (system: import nixpkgs { inherit system; });
    in
    {
      packages = eachSystem (system: rec {
        default = project-W_frontend;
        project-W_frontend = pkgsFor.${system}.callPackage ./nix/derivation-frontendFiles.nix {
          mkPnpmPackage = pnpm2nix-nzbr.packages.${system}.mkPnpmPackage;
        };
      });
      devShells = eachSystem (system: {
        default = import ./nix/shell.nix {
          inherit inputs system;
          pkgs = pkgsFor.${system};
        };
      });
    };
}
