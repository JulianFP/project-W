(final: prev: {
  python3 = prev.python3.override {
    packageOverrides = pyfinal: pyprev: {
      sphinx-mdinclude = pyprev.sphinx-mdinclude.overrideAttrs(old: {
        meta = old.meta // { broken = false; };
      });
      mistune = pyprev.mistune.overrideAttrs (old: rec {
        version = "2.0.5";
        src = final.fetchPypi {
          inherit version;
          pname = "mistune";
          hash = "sha256-AkYRPLJJLbh1xr5Wl0p8iTMzvybNkokchfYxUc7gnTQ=";
        };
      });
      sphinx-jsonschema = prev.callPackage ./pkgs/sphinx-jsonschema.nix { };
      pyaml-env = prev.callPackage ./pkgs/pyaml-env.nix { };
      project-W = prev.callPackage ./pkgs/project-W.nix { };
    };
  };
  python3Packages = final.python3.pkgs;
})
