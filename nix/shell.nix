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
in
{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages myPythonPackages)
    sqlite
  ];
}
