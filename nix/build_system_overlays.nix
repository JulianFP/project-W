{ self, pkgs }:
final: prev:
let
  version_string = "0.4.2";
  inherit (final) resolveBuildSystem;
  inherit (builtins) mapAttrs;

  # Build system dependencies specified in the shape expected by resolveBuildSystem
  # The empty lists below are lists of optional dependencies.
  #
  # A package `foo` with specification written as:
  # `setuptools-scm[toml]` in pyproject.toml would be written as
  # `foo.setuptools-scm = [ "toml" ]` in Nix
  buildSystemOverrides = {
    #for project_W_runner
    julius.setuptools = [ ];
    docopt.setuptools = [ ];
    antlr4-python3-runtime.setuptools = [ ];

    attrs = {
      hatchling = [ ];
      hatch-vcs = [ ];
      hatch-fancy-pypi-readme = [ ];
    };
    hatchling = {
      pathspec = [ ];
      pluggy = [ ];
      packaging = [ ];
      trove-classifiers = [ ];
    };
    pathspec = {
      flit-core = [ ];
    };
    pluggy = {
      setuptools = [ ];
    };
    trove-classifiers = {
      setuptools = [ ];
    };
    tomli.flit-core = [ ];
    coverage.setuptools = [ ];
    blinker.setuptools = [ ];
    certifi.setuptools = [ ];
    charset-normalizer.setuptools = [ ];
    idna.flit-core = [ ];
    urllib3 = {
      hatchling = [ ];
      hatch-vcs = [ ];
    };
    pip = {
      setuptools = [ ];
      wheel = [ ];
    };
    packaging.flit-core = [ ];
    requests.setuptools = [ ];
    pysocks.setuptools = [ ];
    pytest-cov.setuptools = [ ];
    tqdm.setuptools = [ ];
  };
in
mapAttrs (
  name: spec:
  prev.${name}.overrideAttrs (old: {
    nativeBuildInputs = old.nativeBuildInputs ++ resolveBuildSystem spec;
  })
) buildSystemOverrides
// {
  #for project_W
  bonsai = prev.bonsai.overrideAttrs (old: {
    buildInputs = (old.buildInputs or [ ]) ++ [
      pkgs.cyrus_sasl
      pkgs.openldap
    ];
    nativeBuildInputs = old.nativeBuildInputs ++ [
      (resolveBuildSystem {
        setuptools = [ ];
      })
    ];
  });
  project-w = prev.project-w.overrideAttrs (old: {
    SETUPTOOLS_SCM_PRETEND_VERSION = version_string;
    postFixup = ''
      version_file_glob="$out/lib/*/site-packages/project_W/_version.py"
      for file in $version_file_glob; do
        if [ -f "$file" ]; then
          substituteInPlace "$file" --replace "__commit_id__ = commit_id = None" "__commit_id__ = commit_id = '${
            self.shortRev or self.dirtyShortRev
          }'"
        fi
      done
    '';
  });
  #for project_W_runner
  torch = prev.torch.overrideAttrs (old: {
    #cuda buildInputs for torch copied from nixpkgs
    buildInputs =
      with pkgs.cudaPackages;
      (old.buildInputs or [ ])
      ++ [
        cuda_cccl # <thrust/*>
        cuda_cudart # cuda_runtime.h and libraries
        cuda_cupti # For kineto
        cuda_nvcc # crt/host_config.h; even though we include this in nativeBuildInputs, it's needed here too
        cuda_nvml_dev # <nvml.h>
        cuda_nvrtc
        cuda_nvtx # -llibNVToolsExt
        cusparselt
        libcublas
        libcufft
        libcufile
        libcurand
        libcusolver
        libcusparse
        cudnn
        nccl
      ];
  });
  torchaudio =
    (prev.torchaudio.override {
      sourcePreference = "sdist";
    }).overrideAttrs
      (old: {
        nativeBuildInputs = old.nativeBuildInputs ++ [
          (final.resolveBuildSystem {
            setuptools = [ ];
          })
        ];
        buildInputs = (old.buildInputs or [ ]) ++ [
          pkgs.ffmpeg_6-full
          pkgs.sox
        ];
        FFMPEG_ROOT = pkgs.symlinkJoin {
          name = "ffmpeg";
          paths = [
            pkgs.ffmpeg_6-full.bin
            pkgs.ffmpeg_6-full.dev
            pkgs.ffmpeg_6-full.lib
          ];
        };
        autoPatchelfIgnoreMissingDeps = [
          #this should be fine since we don't use the built-in ffmpeg anyway but set the FFMPEG_ROOT env var
          "libav*"
        ];
        postFixup = ''
          addAutoPatchelfSearchPath "${final.torch}"
        '';
      });
  nvidia-cufile-cu12 = prev.nvidia-cufile-cu12.overrideAttrs (old: {
    buildInputs = (old.buildInputs or [ ]) ++ [
      pkgs.cudaPackages.libcufile
    ];
  });
  nvidia-cusolver-cu12 = prev.nvidia-cusolver-cu12.overrideAttrs (old: {
    buildInputs = (old.buildInputs or [ ]) ++ [
      pkgs.cudaPackages.libcusolver
    ];
  });
  nvidia-cusparse-cu12 = prev.nvidia-cusparse-cu12.overrideAttrs (old: {
    buildInputs = (old.buildInputs or [ ]) ++ [
      pkgs.cudaPackages.libcusparse
    ];
  });
  soundfile =
    (prev.soundfile.override {
      sourcePreference = "sdist";
    }).overrideAttrs
      (old: {
        #this is copied from nixpkgs
        postPatch = ''
          substituteInPlace soundfile.py --replace "_find_library('sndfile')" "'${pkgs.libsndfile.out}/lib/libsndfile${pkgs.stdenv.hostPlatform.extensions.sharedLibrary}'"
        '';
        nativeBuildInputs = old.nativeBuildInputs ++ [
          (final.resolveBuildSystem {
            setuptools = [ ];
            cffi = [ ];
          })
        ];
      });
  project-w-runner = prev.project-w-runner.overrideAttrs (old: {
    SETUPTOOLS_SCM_PRETEND_VERSION = version_string;
    postFixup = ''
      version_file_glob="$out/lib/*/site-packages/project_W_runner/_version.py"
      for file in $version_file_glob; do
        if [ -f "$file" ]; then
          substituteInPlace "$file" --replace "__commit_id__ = commit_id = None" "__commit_id__ = commit_id = '${
            self.shortRev or self.dirtyShortRev
          }'"
        fi
      done
    '';
  });
}
