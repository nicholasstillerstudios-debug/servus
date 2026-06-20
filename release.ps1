# Pipeline de release do SERVUS.
#
# Uso:
#   .\release.ps1                  -> build + instalador na versao atual
#   .\release.ps1 -BumpPatch       -> incrementa patch (0.1.0 -> 0.1.1)
#   .\release.ps1 -BumpMinor       -> incrementa minor (0.1.0 -> 0.2.0)
#   .\release.ps1 -SetVersion 1.0.0
#   .\release.ps1 -Publish         -> faz push da release no GitHub (precisa gh CLI)
#
# Saida:
#   dist\Servus\             - app empacotado (--onedir)
#   release\SetupServus-X.Y.Z.exe
#   release\latest.json

param(
    [switch]$BumpPatch,
    [switch]$BumpMinor,
    [string]$SetVersion,
    [switch]$Publish,
    [string]$Notes = "Atualizacao do SERVUS"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# --- 1. resolve versao ---------------------------------------------------
$verFile = "$root\app\version.py"
$verContent = Get-Content $verFile -Raw
$current = if ($verContent -match '__version__\s*=\s*"([\d.]+)"') { $Matches[1] } else { "0.1.0" }

function Bump($v, $part) {
    $p = $v.Split(".") | ForEach-Object { [int]$_ }
    switch ($part) {
        "patch" { $p[2] += 1 }
        "minor" { $p[1] += 1; $p[2] = 0 }
    }
    return "$($p[0]).$($p[1]).$($p[2])"
}

$new = $current
if     ($SetVersion) { $new = $SetVersion }
elseif ($BumpMinor)  { $new = Bump $current "minor" }
elseif ($BumpPatch)  { $new = Bump $current "patch" }

if ($new -ne $current) {
    (Get-Content $verFile -Raw) -replace '__version__\s*=\s*"[\d.]+"', "__version__ = `"$new`"" | Set-Content $verFile -NoNewline
    Write-Host "Versao: $current -> $new" -ForegroundColor Cyan
} else {
    Write-Host "Versao mantida: $current" -ForegroundColor Cyan
}

# --- 2. build PyInstaller -----------------------------------------------
Write-Host "`n[1/3] PyInstaller build..." -ForegroundColor Yellow
$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& "$root\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean Servus.spec 2>&1 | ForEach-Object { "$_" }
$piExit = $LASTEXITCODE
$ErrorActionPreference = $prev
if ($piExit -ne 0) { throw "PyInstaller falhou (exit $piExit)" }

# --- 3. Inno Setup -------------------------------------------------------
Write-Host "`n[2/3] Inno Setup..." -ForegroundColor Yellow
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    Write-Warning "Inno Setup nao encontrado em $iscc"
    Write-Warning "Instale em https://jrsoftware.org/isdl.php e rode de novo"
    exit 1
}
New-Item -ItemType Directory -Path "$root\release" -Force | Out-Null
$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $iscc "/DAppVersion=$new" "$root\installer\Servus.iss" 2>&1 | ForEach-Object { "$_" }
$isExit = $LASTEXITCODE
$ErrorActionPreference = $prev
if ($isExit -ne 0) { throw "Inno Setup falhou (exit $isExit)" }

$setupExe = "$root\release\SetupServus-$new.exe"
if (-not (Test-Path $setupExe)) { throw "Setup nao gerado: $setupExe" }
$size = (Get-Item $setupExe).Length / 1MB
Write-Host ("  -> {0} ({1:N1} MB)" -f $setupExe, $size) -ForegroundColor Green

# --- 4. manifest latest.json --------------------------------------------
Write-Host "`n[3/3] Gerando latest.json..." -ForegroundColor Yellow
$hash = (Get-FileHash -Algorithm SHA256 $setupExe).Hash.ToLower()
$manifest = @{
    version = $new
    url     = "https://github.com/nicholasstillerstudios-debug/servus-updates/releases/download/v$new/SetupServus-$new.exe"
    sha256  = $hash
    notes   = $Notes
} | ConvertTo-Json -Depth 3
$manifestPath = "$root\release\latest.json"
$manifest | Out-File -FilePath $manifestPath -Encoding utf8
Write-Host "  -> $manifestPath" -ForegroundColor Green

# --- 5. publish opcional -------------------------------------------------
if ($Publish) {
    Write-Host "`nPublicando release v$new no GitHub..." -ForegroundColor Yellow
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) { Write-Warning "gh CLI nao instalado - pulando publish"; exit 0 }
    gh release create "v$new" $setupExe $manifestPath --title "SERVUS v$new" --notes $Notes
}

Write-Host "`nPronto!" -ForegroundColor Green
Write-Host "  Instalador: $setupExe"
Write-Host "  Manifest:   $manifestPath"
Write-Host "`nPara publicar manualmente:"
Write-Host "  1. Crie repo 'servus-updates' no GitHub (se ainda nao existe)"
Write-Host "  2. Crie release 'v$new' e suba SetupServus-$new.exe + latest.json"
