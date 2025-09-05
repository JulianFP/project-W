(final: prev: {
  python3 = prev.python3.override {
    packageOverrides = pyfinal: pyprev: {
      project-W-runner = prev.callPackage ./pkgs/project-W-runner.nix { };
    };
  };
  python3Packages = final.python3.pkgs;
})
