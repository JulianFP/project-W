{
  pkgs ? import <nixpkgs> { },
  system,
  inputs,
}:
let
  dontCheckPythonPkg =
    drv:
    drv.overridePythonAttrs (old: {
      doCheck = false;
    });
  myPythonPackages =
    ps: with ps; [
      #all required dependencies + this projects package itself (required for sphinx)
      (dontCheckPythonPkg project-W)

      #optional dependencies: tests
      pytest
      pytest-mock
      pytest-cov

      #optional dependencies: docs
      sphinx
      sphinxcontrib-httpdomain
      sphinx-jsonschema
      sphinx-mdinclude
      sphinx-rtd-theme
    ];
  pre-commit-check = inputs.pre-commit-hooks.lib.${system}.run {
    src = ./.;
    hooks = {
      check-yaml.enable = true;
      end-of-file-fixer.enable = true;
      trim-trailing-whitespace.enable = true;
      check-added-large-files.enable = true;
      check-merge-conflicts.enable = true;
      check-symlinks.enable = true;
      check-docstring-first.enable = true;
      check-builtin-literals.enable = true;
      check-python.enable = true;
      black = {
        enable = true;
        settings.flags = "--line-length 100";
      };
      isort = {
        enable = true;
        settings.profile = "black";
      };
      nixfmt-rfc-style.enable = true;
    };
  };
in
pkgs.mkShell {
  buildInputs =
    with pkgs;
    [
      (python3.withPackages myPythonPackages)
      sqlite
    ]
    ++ pre-commit-check.enabledPackages;

  shellHook =
    ''
      localOverwriteFile=".pre-commit-config.yaml"
      git update-index --skip-worktree "$localOverwriteFile"
      rm "$localOverwriteFile"
    ''
    + pre-commit-check.shellHook;
}
