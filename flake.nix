{
  inputs = {
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    systems.url = "github:nix-systems/default";
    devenv.url = "github:cachix/devenv";
    devenv.inputs.nixpkgs.follows = "nixpkgs";
    nixpkgs-python.url = "github:cachix/nixpkgs-python";
    nixpkgs-python.inputs = { nixpkgs.follows = "nixpkgs"; };
    unstable.url = "github:nixos/nixpkgs?ref=nixpkgs-unstable";
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs = { self, nixpkgs, devenv, unstable, systems, ... } @ inputs:
    let
      forEachSystem = nixpkgs.lib.genAttrs (import systems);
    in
    {
      packages = forEachSystem (system: {
        devenv-up = self.devShells.${system}.default.config.procfileScript;
        devenv-test = self.devShells.${system}.default.config.test;
      });

      devShells = forEachSystem
        (system:
          let
            pkgs = import nixpkgs {
              inherit system;
              overlays = [
                (final: prev: {
                  unstable = import unstable { inherit system; };
                })
              ];
            };
            python-dependencies = with pkgs; [
              libz
              stdenv.cc.cc.lib
            ];
            core-dependencies = with pkgs; [
              ffmpeg
              sox
              espeak-ng
            ];
          in
          {
            default = devenv.lib.mkShell {
              inherit inputs pkgs;
              modules = [
                {
                  env.LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib64:${pkgs.libz}/lib";
                  packages = python-dependencies ++ core-dependencies;
                  languages.python = {
                    enable = true;
                    version = "3.9";
                    uv.enable = true;
                    uv.package = pkgs.unstable.uv;
                    uv.sync.enable = true;
                    venv.enable = true;
                  };
                }
              ];
            };
          });
    };
}
