{
  description = "This is the frontend for Project-W, a service that converts uploaded audio files into downloadable text transcripts using OpenAIs whisper AI model, hosted on a backend server and dedicated runners.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";
    pnpm2nix-nzbr = {
      url = "github:nzbr/pnpm2nix-nzbr";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs@{ nixpkgs, systems, pnpm2nix-nzbr, ...}: 
  let
    eachSystem = nixpkgs.lib.genAttrs (import systems);
    pkgsFor = eachSystem (system: 
      import nixpkgs { inherit system; }
    );
  in {
    packages = eachSystem (system: rec {
      default = project-W_frontend;
      project-W_frontend = pkgsFor.${system}.callPackage ./nix/derivation-frontendFiles.nix { 
        mkPnpmPackage=pnpm2nix-nzbr.packages.${system}.mkPnpmPackage;
      };
    });
    devShells = eachSystem (system: {
      default = import ./nix/shell.nix { pkgs=pkgsFor.${system}; };
    });
    nixosModules.default = import ./nix/module.nix inputs;
  };
}
