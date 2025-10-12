{
  description = "Project-W is a service that converts uploaded audio files into downloadable text transcripts using OpenAIs whisper AI model, hosted on a backend server and dedicated runners.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
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
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  #to avoid long nccl build
  nixConfig = {
    extra-substituters = [
      "https://nix-community.cachix.org"
    ];
    extra-trusted-public-keys = [
      "nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs="
    ];
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      pnpm2nix-nzbr,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;
      devShellAttrs = (
        import ./nix/make_dev_shells.nix {
          inherit forAllSystems inputs;
          desiredDevEnvs = {
            "project_W-env" = {
              workspaceRoot = "/backend";
              pythonPkg = (pkgs: pkgs.python313);
              extraPackages = (pkgs: [ ]);
            };
            "project_W_runner-env" = {
              workspaceRoot = "/runner";
              pythonPkg = (pkgs: pkgs.python312);
              extraPackages = (pkgs: [ pkgs.ffmpeg ]);
            };
            "doc-env" = {
              workspaceRoot = "/doc";
              pythonPkg = (pkgs: pkgs.python313);
              extraPackages = (pkgs: [ ]);
            };
            "tests-env" = {
              workspaceRoot = "/tests";
              pythonPkg = (pkgs: pkgs.python313);
              extraPackages = (pkgs: [ ]);
            };
          };
        }
      );
    in
    {
      devShells = devShellAttrs.devShells;

      packages = forAllSystems (
        system:
        let
          backendPythonSet = devShellAttrs.pythonSetsSets."project_W-env".${system};
          runnerPythonSet = devShellAttrs.pythonSetsSets."project_W_runner-env".${system};
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
          };
          inherit (pkgs.callPackages pyproject-nix.build.util { }) mkApplication;
        in
        {
          project_W = mkApplication {
            venv =
              backendPythonSet.mkVirtualEnv "project_W-env"
                devShellAttrs.workspaces."project_W-env".deps.optionals;
            package = backendPythonSet.project-w;
          };
          project_W_runner = mkApplication {
            venv =
              runnerPythonSet.mkVirtualEnv "project_W_runner-env"
                devShellAttrs.workspaces."project_W_runner-env".deps.optionals;
            package = runnerPythonSet.project-w-runner;
          };
          project_W_frontend = pkgs.callPackage ./nix/derivation_frontend_files.nix {
            inherit self;
            mkPnpmPackage = pnpm2nix-nzbr.packages.${system}.mkPnpmPackage;
          };
          default = self.packages.${system}.project_W;
        }
      );

      nixosModules.default =
        args@{ pkgs, ... }:
        {
          imports = [
            (import ./nix/backend_module.nix (args // { inputs = inputs; }))
            (import ./nix/runner_module.nix (args // { inputs = inputs; }))
          ];
        };
    };
}
