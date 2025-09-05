(final: prev: {
  python3 = prev.python3.override {
    packageOverrides = pyfinal: pyprev: {
      sphinx-jsonschema = prev.callPackage ./pkgs/sphinx-jsonschema.nix { };
      autodoc-pydantic = prev.callPackage ./pkgs/autodoc-pydantic.nix { };
      project-W = prev.callPackage ./pkgs/project-W.nix { };
      project-W-runner = prev.callPackage ./pkgs/project-W-runner.nix { };
    };
  };
  python312 = prev.python312.override {
    packageOverrides = pyfinal: pyprev: {
      sphinx-jsonschema = prev.callPackage ./pkgs/sphinx-jsonschema.nix {
        python3Packages = prev.python312Packages;
      };
      autodoc-pydantic = prev.callPackage ./pkgs/autodoc-pydantic.nix {
        python3Packages = prev.python312Packages;
      };
      project-W = prev.callPackage ./pkgs/project-W.nix { python3Packages = prev.python312Packages; };
    };
  };
  python3Packages = final.python3.pkgs;
  python312Packages = final.python312.pkgs;
})
