{
  description = "Project-W is a service that converts uploaded audio files into downloadable text transcripts using OpenAIs whisper AI model, hosted on a backend server and dedicated runners.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";
    pre-commit-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    project-W-frontend = {
      url = "github:julianfp/project-W-frontend";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      nixpkgs,
      systems,
      project-W-frontend,
      ...
    }:
    let
      pythonOverlay = import ./nix/overlay.nix;
      eachSystem = nixpkgs.lib.genAttrs (import systems);
      pkgsFor = eachSystem (
        system:
        import nixpkgs {
          inherit system;
          #overlays add all new packages and their dependencies
          overlays = [ pythonOverlay ];
        }
      );
    in
    {
      packages = eachSystem (system: rec {
        default = project-W;
        project-W = pkgsFor.${system}.python3Packages.project-W;
      });
      devShells = eachSystem (system: {
        default = import ./nix/shell.nix {
          inherit inputs system;
          pkgs = pkgsFor.${system};
        };
      });
      nixosModules.default =
        { pkgs, ... }:
        {
          #apply overlay
          nixpkgs.overlays = [
            pythonOverlay
            (final: prev: {
              project-W-frontend = project-W-frontend.packages."${pkgs.system}".project-W_frontend;
            })
          ];

          imports = [ ./nix/module.nix ];
        };
      overlays.default = pythonOverlay;
    };
}
