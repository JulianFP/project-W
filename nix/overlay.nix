(final: prev: {
  python313 = prev.python313.override {
    packageOverrides = pyfinal: pyprev: {
      sphinx-jsonschema = prev.callPackage ./pkgs/sphinx-jsonschema.nix { };
      project-W = prev.callPackage ./pkgs/project-W.nix { };
    };
  };
  python313Packages = final.python313.pkgs;
})
