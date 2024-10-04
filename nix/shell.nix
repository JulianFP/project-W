{ pkgs ? import <nixpkgs> { } }:
let
  wrappedPreCommit = (pkgs.buildFHSEnv {
    name = "wrapped pre-commit";
    pname = "pre-commit";
    targetPkgs = pkgs: [
      pkgs.pre-commit
    ];
    runScript = "pre-commit";
  });
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs_20
    corepack_20
    wrappedPreCommit
  ];
}
