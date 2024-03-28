{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  buildInputs = with pkgs.python3Packages; [
    #all required dependencies + this projects package itself (required for sphinx)
    project-W

    #optional dependencies: tests
    pytest
    pytest-mock
    pytest-cov

    #optional dependencies: docs
    sphinx
    sphinxcontrib-httpdomain
    (pkgs.callPackage ./pkgs/sphinx-jsonschema.nix { })
    sphinx-mdinclude
    sphinx-rtd-theme
  ];
}
