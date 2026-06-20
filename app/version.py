"""Versao unica do SERVUS - lida pelo app, pelo Inno Setup e pelo release script."""

__version__ = "0.7.2"
APP_NAME = "SERVUS"
APP_ID = "{{C7E84A3F-7E22-4F8A-9A1D-SERVUS00001}}"  # identificador unico do Windows
APP_MUTEX = "Global\\ServusAppRunning"

# Endpoint do manifest de atualizacao.
# Crie um repo "servus-updates" no GitHub e publique releases com SetupServus-X.Y.Z.exe
# + um arquivo latest.json. O updater usa "Releases > latest > assets > latest.json".
UPDATE_MANIFEST_URL = (
    "https://github.com/nicholasstillerstudios-debug/servus-updates/"
    "releases/latest/download/latest.json"
)
