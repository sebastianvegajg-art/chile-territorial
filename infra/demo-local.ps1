param(
    [ValidateSet("oficial", "demo")]
    [string]$Modo = "oficial",
    [string]$LoteOficial = $env:CT_LOTE_OFICIAL
)

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

$Python = if ($env:CT_PYTHON) { $env:CT_PYTHON } elseif (Test-Path "$Raiz\.venv\Scripts\python.exe") { "$Raiz\.venv\Scripts\python.exe" } else { "python" }
$Node = if (Test-Path "C:\Program Files\nodejs\node.exe") { "C:\Program Files\nodejs\node.exe" } else { "node" }

if ($Modo -eq "oficial") {
    if (-not $env:DATABASE_URL -and -not $LoteOficial) {
        if (Test-Path "$Raiz\data\published\pib-bde-api.json") {
            $LoteOficial = "$Raiz\data\published\pib-bde-api.json"
        } elseif (Test-Path "$Raiz\data\published\pib-bde-publico.json") {
            $LoteOficial = "$Raiz\data\published\pib-bde-publico.json"
        } else {
            throw "Configura DATABASE_URL o CT_LOTE_OFICIAL, o ejecuta primero python -m pipelines.economia.bde_publico."
        }
    }
    $Etiqueta = "Comparador con datos oficiales"
} else {
    $Etiqueta = "Comparador de prueba (sintético)"
}

$env:CT_MODO = $Modo
if ($Modo -eq "oficial" -and $LoteOficial) {
    $env:CT_LOTE_OFICIAL = $LoteOficial
} else {
    Remove-Item Env:CT_LOTE_OFICIAL -ErrorAction SilentlyContinue
}

$ApiProc = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $Raiz -PassThru -NoNewWindow
$WebProc = Start-Process -FilePath $Node -ArgumentList "node_modules/vite/bin/vite.js", "--mode", $Modo, "--host", "127.0.0.1", "--port", "5173", "--strictPort" -WorkingDirectory "$Raiz\apps\web" -PassThru -NoNewWindow

Write-Host "$Etiqueta en http://127.0.0.1:5173 (API en http://127.0.0.1:8000/api/v1)"
Write-Host "Presiona Ctrl+C para detener ambos servicios."

try {
    Wait-Process -Id @($ApiProc.Id, $WebProc.Id) -Any
} finally {
    if (-not $WebProc.HasExited) { Stop-Process -Id $WebProc.Id -Force -ErrorAction SilentlyContinue }
    if (-not $ApiProc.HasExited) { Stop-Process -Id $ApiProc.Id -Force -ErrorAction SilentlyContinue }
}
