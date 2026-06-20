# SERVUS launcher
# Uso:
#   servus              -> abre o PAINEL desktop (voz + texto + config)
#   servus -Cli         -> modo terminal (Open Interpreter padrao)
#   servus -Local       -> terminal usando Ollama local
#   servus -Claude      -> terminal usando Claude

param(
    [switch]$Cli,
    [switch]$Local,
    [switch]$Claude,
    [string]$Args = ""
)

$python = "C:\Users\nicho\servus\.venv\Scripts\python.exe"
$interp = "C:\Users\nicho\servus\.venv\Scripts\interpreter.exe"
$panel  = "C:\Users\nicho\servus\app\main.py"

if ($Local) {
    & $interp --local $Args.Split(" ")
} elseif ($Claude) {
    & $interp --model claude-sonnet-4-5 $Args.Split(" ")
} elseif ($Cli) {
    & $interp $Args.Split(" ")
} else {
    & $python $panel
}
