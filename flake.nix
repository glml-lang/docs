{
  description = "GLML Documentation";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    glml.url = "github:glml-lang/glml";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      glml,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        glml-bin = glml.packages.${system}.default;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            mdbook
            nodejs
            glml-bin
            (python3.withPackages (ps: [ ps.markdown-it-py ]))
          ];
        };
      }
    );
}
