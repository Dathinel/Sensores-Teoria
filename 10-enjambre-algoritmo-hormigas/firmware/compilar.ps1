# compilar.ps1 - Compila el firmware del enjambre para los tres nodos (NODO_ID 1, 2 y 3).
#
# Uso (desde PowerShell, en cualquier carpeta):
#   .\compilar.ps1                  compila los tres
#   .\compilar.ps1 -Nodos 2         compila solo el nodo 2
#   .\compilar.ps1 -Nodos 2 -Puerto COM5 -Subir    compila el nodo 2 y lo sube por COM5
#   .\compilar.ps1 -SinMotores      compila con MOVER_CARRITO=0 (probar sin el driver)
#
# Cada nodo se compila en su propia carpeta de salida (build_n1, build_n2, build_n3 dentro de
# la carpeta temporal del sistema) para no ensuciar la carpeta del sketch con binarios.
param(
    [int[]]$Nodos = @(1, 2, 3),
    [string]$Puerto = "",
    [switch]$Subir,
    [switch]$SinMotores
)

$cli = "C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
$sketch = Join-Path $PSScriptRoot "esp32_aco_nodo"
$placa = "esp32:esp32:esp32"   # "ESP32 Dev Module" (nucleo esp32 3.x)

foreach ($n in $Nodos) {
    $salida = Join-Path $env:TEMP "enjambre_aco_build_n$n"
    $flags = "-DNODO_ID=$n"
    if ($SinMotores) { $flags += " -DMOVER_CARRITO=0" }
    Write-Host "=== Nodo $n ($flags) ==="
    & $cli compile -b $placa --warnings all --build-property "compiler.cpp.extra_flags=$flags" --output-dir $salida $sketch
    if ($LASTEXITCODE -ne 0) { Write-Host "Fallo la compilacion del nodo $n"; exit 1 }
    if ($Subir) {
        if (-not $Puerto) { Write-Host "Falta -Puerto COMx para subir"; exit 1 }
        & $cli upload -b $placa -p $Puerto --input-dir $salida $sketch
        if ($LASTEXITCODE -ne 0) { Write-Host "Fallo la subida del nodo $n"; exit 1 }
    }
}
