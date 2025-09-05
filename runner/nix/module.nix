inputs:
{
  config,
  lib,
  pkgs,
  ...
}:
let
  inherit (pkgs.stdenv.hostPlatform) system;
  inherit (lib)
    mdDoc
    mkIf
    mkOption
    mkEnableOption
    types
    getExe
    escapeShellArgs
    ;
  cfg = config.services.project-W-runner;
  cfg_str = "services.project-W-runner";
in
{
  options = {
    services.project-W-runner = {
      enable = mkEnableOption (mdDoc "Runner of Project-W");
      package = mkOption {
        type = types.package;
        default = inputs.self.packages.${system}.project-W-runner;
        description = mdDoc ''
          Project-W runner python package to use.
        '';
      };
      user = mkOption {
        type = types.singleLineStr;
        default = "project-W-runner";
        description = mdDoc ''
          User account under which the runner runs.
        '';
      };
      group = mkOption {
        type = types.singleLineStr;
        default = "project-W-runner";
        description = mdDoc ''
          User group under which the runner runs.
        '';
      };
      settings = {
        runnerToken = mkOption {
          type = types.singleLineStr;
          default = "\${RUNNER_TOKEN}";
          description = mdDoc ''
            Token that the runner uses to authenticate with the backend. Warning: This will be public in the /nix/store! For production systems please use [envFile](${cfg_str}.envFile) combined with a secret management tool like sops-nix instead!!!
          '';
        };
        backendURL = mkOption {
          type = types.strMatching "^(http|https):\/\/(([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost)(:[0-9]+)?((\/[a-zA-Z0-9\-]+)+)?$$";
          example = "https://example.com";
          description = mdDoc ''
            URL under which the backend is hosted (including http/https, port, shouldn't end with /).
          '';
        };
        modelCacheDir = mkOption {
          type = types.singleLineStr;
          default = "/var/cache/project-W-runner_whisperCache";
          description = mdDoc ''
            Directory used to cache whisper AI models.
          '';
        };
        torchDevice = mkOption {
          type = types.nullOr types.singleLineStr;
          default = null;
          example = "cuda:1";
          description = mdDoc ''
            The PyTorch device used by Whisper. If set to null then pytorches default device will be used.
          '';
        };
      };
      envOptions = mkOption {
        type = types.listOf types.singleLineStr;
        default = [ "runnerToken" ];
        description = mdDoc ''
          Attributes that require loading of environment variables. An !ENV will be added to the yaml config for these. Just add the name of the attribute itself, not the name of the attribute set(s) it is in.
        '';
      };
      envFile = mkOption {
        type = types.nullOr types.singleLineStr;
        default = null;
        example = "/run/secrets/secretFile";
        description = mdDoc ''
          Path to file to load secrets from. All secrets should be written as environment variables (in NAME=VALUE declarations, one per line). Per default, RUNNER_TOKEN sets the runner token. The content of the file most likely should look like this:
          ```
          RUNNER_TOKEN=<your runners token>
          ```
          This file should be accessible by the user [user](${cfg_str}.user) and by this user only!
        '';
      };
    };
  };

  config =
    let
      stringsToReplace = builtins.map (x: x + ":") cfg.envOptions;
      newStrings = builtins.map (x: x + " !ENV") stringsToReplace;
      filteredSettings = pkgs.lib.filterAttrsRecursive (name: value: value != null) cfg.settings;
      fileWithoutEnvs =
        (pkgs.formats.yaml { }).generate "project-W-runner-config-without-env.yaml"
          filteredSettings;
      configFile = pkgs.writeTextDir "config.yml" (
        builtins.replaceStrings stringsToReplace newStrings (builtins.readFile fileWithoutEnvs)
      );
      #function that checks if we have attributes in cfg.envOptions that are not strings
      invalidEnvOption = (
        attrSet:
        let
          v = builtins.attrValues attrSet;
          boolFunc = (
            element:
            if (builtins.isAttrs element) then
              (invalidEnvOption element)
            else if (builtins.elem element cfg.envOptions && !(builtins.isString element)) then
              true
            else
              false
          );
          iterateV = (
            i:
            if (i >= (builtins.length v)) then
              false
            else if (boolFunc (builtins.elemAt v i)) then
              true
            else
              iterateV (i + 1)
          );
        in
        iterateV 0
      );
    in
    mkIf cfg.enable {
      assertions = [
        {
          assertion = !(invalidEnvOption cfg.settings);
          message = "The ${cfg_str}.envOptions option cannot contain attributes that are not some kind of string in ${cfg_str}.settings";
        }
        {
          assertion = cfg.envOptions == [ ] || cfg.envFile != null;
          message = "The ${cfg_str}.envFile option can't be null if ${cfg_str}.envOptions contains elements. Per default the runner token ${cfg_str}.settings.runnerToken has to be set in envFile.";
        }
      ];

      systemd = {
        #create directories for persistent stuff
        tmpfiles.settings.project-W-runner-dirs = {
          "${cfg.settings.modelCacheDir}"."d" = {
            mode = "700";
            inherit (cfg) user group;
          };
        };

        #setup systemd service for runner
        services.project-W-runner = {
          description = "Project-W runner";
          after = [ "network-online.target" ];
          wants = [ "network-online.target" ];
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            Type = "simple";
            User = cfg.user;
            Group = cfg.group;
            UMask = "0077";
            ExecStart = escapeShellArgs [
              "${getExe cfg.package}"
              "--customConfigPath"
              "${configFile}"
            ];
            PrivateTmp = true;
            EnvironmentFile = mkIf (cfg.envFile != null) cfg.envFile;
          };
        };
      };

      #setup user/group under which systemd service is run
      users.users = mkIf (cfg.user == "project-W-runner") {
        project-W-runner = {
          inherit (cfg) group;
          isSystemUser = true;
        };
      };
      users.groups = mkIf (cfg.group == "project-W-runner") {
        project-W-runner = { };
      };
    };
}
