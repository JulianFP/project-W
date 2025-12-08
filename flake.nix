{
  description = "Project-W is a service that converts uploaded audio files into downloadable text transcripts using OpenAIs whisper AI model, hosted on a backend server and dedicated runners.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
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
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;
      pkgsFor = forAllSystems (
        system:
        import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
            cudaSupport = true;
          };
        }
      );
      devShellAttrs = (
        import ./nix/make_dev_shells.nix {
          inherit forAllSystems pkgsFor inputs;
          desiredDevEnvs = {
            "project_W-env" = {
              workspaceRoot = "/backend";
              pythonPkg = (pkgs: pkgs.python313);
              extraPackages = (pkgs: [ ]);
            };
            "project_W_runner-env" = {
              workspaceRoot = "/runner";
              pythonPkg = (pkgs: pkgs.python313);
              extraPackages = (pkgs: [ pkgs.ffmpeg ]);
            };
            "project_W_lib-env" = {
              workspaceRoot = "/lib";
              pythonPkg = (pkgs: pkgs.python313);
              extraPackages = (pkgs: [ ]);
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
      # Run the hooks in a sandbox with `nix flake check`.
      # Read-only filesystem and no internet access.
      checks = forAllSystems (system: {
        pre-commit-check = inputs.pre-commit-hooks.lib.${system}.run {
          src = ./.;
          hooks = {
            end-of-file-fixer.enable = true;
            trim-trailing-whitespace.enable = true;
            check-added-large-files.enable = true;
            check-merge-conflicts.enable = true;
            check-symlinks.enable = true;
            check-docstring-first.enable = true;
            check-builtin-literals.enable = true;
            check-python.enable = true;
            python-debug-statements.enable = true;
            biome = {
              enable = true;
              files = "^frontend/";
              types_or = [ ];
            };
            ruff = {
              enable = true;
              files = "^backend/|^runner/";
            };
            ruff-format = {
              enable = true;
              files = "^backend/|^runner/";
            };
            codespell = {
              enable = true;
              name = "codespell";
              entry = "${pkgsFor.${system}.codespell}/bin/codespell -w --ignore-words-list=delet --skip=frontend/src/lib/utils/schema.d.ts,frontend/pnpm-lock.yaml,frontend/package.json";
            };
            nixfmt-rfc-style.enable = true;
          };
        };
      });

      # Run the hooks with `nix fmt`.
      formatter = forAllSystems (
        system:
        let
          config = self.checks.${system}.pre-commit-check.config;
          inherit (config) package configFile;
          script = ''
            ${pkgsFor.${system}.lib.getExe package} run --all-files --config ${configFile}
          '';
        in
        pkgsFor.${system}.writeShellScriptBin "pre-commit-run" script
      );

      # Enter a development shell with `nix develop`
      devShells = devShellAttrs.devShells;

      #build a production package with `nix build`
      packages = forAllSystems (
        system:
        let
          backendPythonSet = devShellAttrs.pythonSetsSets."project_W-env".${system};
          runnerPythonSet = devShellAttrs.pythonSetsSets."project_W_runner-env".${system};
          inherit (pkgsFor.${system}.callPackages pyproject-nix.build.util { }) mkApplication;
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
          project_W_frontend = pkgsFor.${system}.callPackage ./nix/derivation_frontend_files.nix {
            inherit self;
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
