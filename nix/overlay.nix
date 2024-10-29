(final: prev: {
  python3 = prev.python3.override {
    packageOverrides = pyfinal: pyprev: {
      sphinx-jsonschema = prev.callPackage ./pkgs/sphinx-jsonschema.nix { };
      project-W = prev.callPackage ./pkgs/project-W.nix { };
    };
  };
  python3Packages = final.python3.pkgs;
})
