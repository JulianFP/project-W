{
  pkgs ? import <nixpkgs> { },
  system,
  inputs,
}:
let
  pre-commit-check = inputs.pre-commit-hooks.lib.${system}.run {
    src = ./.;
    hooks = {
      check-yaml.enable = true;
      end-of-file-fixer.enable = true;
      trim-trailing-whitespace.enable = true;
      check-added-large-files.enable = true;
      check-merge-conflicts.enable = true;
      check-symlinks.enable = true;
      biome = {
        enable = true;
        entry = "${pkgs.biome}/bin/biome check --write";
        types_or = [
          "javascript"
          "jsx"
          "ts"
          "tsx"
          "json"
          "svelte"
        ];
      };
      nixfmt-rfc-style.enable = true;
    };
  };
in
pkgs.mkShell {
  buildInputs =
    with pkgs;
    [
      nodejs_20
      corepack_20
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
