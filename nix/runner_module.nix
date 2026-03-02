{
  inputs,
  config,
  lib,
  pkgs,
  ...
}:
let
  inherit (pkgs.stdenv.hostPlatform) system;
  yamlFormat = pkgs.formats.yaml { };
  cfg = config.services.project-W.runner;
  cfg_str = "services.project-W.runner";
in
{
  options = {
    services.project-W.runner = {
      enable = lib.mkEnableOption "Runner of Project-W";
      package = lib.mkOption {
        type = lib.types.package;
        default = inputs.self.packages.${system}.project_W_runner;
        description = ''
          Project-W runner python package to use.
        '';
      };
      user = lib.mkOption {
        type = lib.types.singleLineStr;
        default = "project-W-runner";
        description = ''
          User account under which the runner runs.
        '';
      };
      group = lib.mkOption {
        type = lib.types.singleLineStr;
        default = "project-W-runner";
        description = ''
          User group under which the runner runs.
        '';
      };
      settings = lib.mkOption {
        type = yamlFormat.type;
        description = ''
          The contents of the runner config as a Nix expression. Will be formatted into Yaml. Please don't put any sensitive information in here as it will be world-readable in the Nix store! Use the !ENV notation as described in the Project-W documentation (inside a string in Nix).
        '';
      };
      envFile = lib.mkOption {
        type = lib.types.nullOr lib.types.singleLineStr;
        default = null;
        example = "/run/secrets/secretFile";
        description = ''
          Path to file to load secrets from. All secrets should be written as environment variables (in NAME=VALUE declarations, one per line). Per default, RUNNER_TOKEN sets the runner token. The content of the file most likely should look like this:
          ```
          RUNNER_TOKEN=<your runners token>
          HF_TOKEN=<your huggingface token>
          ```
          This file should be accessible by the user [user](${cfg_str}.user) and by this user only!
        '';
      };
    };
  };

  config =
    let
      fileWithoutEnvs = yamlFormat.generate "project-W-runner-untreaded-config.yaml" cfg.settings;
      configFile = pkgs.writeTextDir "config.yml" (
        builtins.replaceStrings [ "'!ENV " ] [ "!ENV '" ] (builtins.readFile fileWithoutEnvs)
      );
    in
    lib.mkIf cfg.enable {
      #setup systemd service for runner
      systemd.services.project-W-runner = {
        description = "Project-W runner, responsible for the actual transcription.";
        after = [
          "network-online.target"
        ]
        ++ lib.optional config.services.project-W.server.enable "project-W.service";
        wants = [
          "network-online.target"
        ]
        ++ lib.optional config.services.project-W.server.enable "project-W.service";
        wantedBy = [ "multi-user.target" ];
        environment = {
          TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD = "true";
        };
        serviceConfig = {
          Type = "simple";
          User = cfg.user;
          Group = cfg.group;
          UMask = "0077";
          ExecStart = lib.escapeShellArgs [
            "${lib.getExe cfg.package}"
            "--custom_config_path"
            "${configFile}"
          ];
          PrivateTmp = true;
          EnvironmentFile = lib.mkIf (cfg.envFile != null) cfg.envFile;
        };
        path = [ pkgs.ffmpeg ];
      };

      #setup user/group under which systemd service is run
      users.users = lib.mkIf (cfg.user == "project-W-runner") {
        project-W-runner = {
          inherit (cfg) group;
          isSystemUser = true;
          home = "/var/lib/project-W-runner";
          createHome = true;
        };
      };
      users.groups = lib.mkIf (cfg.group == "project-W-runner") {
        project-W-runner = { };
      };
    };
}
