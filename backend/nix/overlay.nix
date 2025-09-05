(final: prev: {
  python3 = prev.python3.override {
    packageOverrides = pyfinal: pyprev: {
      sphinx-jsonschema = prev.callPackage ./pkgs/sphinx-jsonschema.nix { };
      autodoc-pydantic = prev.callPackage ./pkgs/autodoc-pydantic.nix { };
      project-W = prev.callPackage ./pkgs/project-W.nix { };
    };
  };
  python313 = prev.python313.override {
    packageOverrides = pyfinal: pyprev: {
      sphinx-jsonschema = prev.callPackage ./pkgs/sphinx-jsonschema.nix {
        python3Packages = prev.python313Packages;
      };
      autodoc-pydantic = prev.callPackage ./pkgs/autodoc-pydantic.nix {
        python3Packages = prev.python313Packages;
      };
      project-W = prev.callPackage ./pkgs/project-W.nix { python3Packages = prev.python313Packages; };
    };
  };
  python313Packages = final.python313.pkgs;
})
