{ pkgs ? import <nixpkgs> { } }:
let
  dontCheckPythonPkg = drv: drv.overridePythonAttrs (old: { doCheck = false; });
  myPythonPackages = ps: with ps; [
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
  wrappedPreCommit = (pkgs.buildFHSEnv {
    pname = "pre-commit";
    targetPkgs = pkgs: [
      pkgs.pre-commit
    ];
    runScript = "pre-commit";
  });
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages myPythonPackages)
    sqlite
    wrappedPreCommit
  ];
}
