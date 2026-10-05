# publicar_dockerhub.ps1 - Construye las 6 imágenes del tema 11 y las sube a Docker Hub.
#
# Qué es cada cosa (más en el README, "Qué es Docker Hub"):
#   - Docker Hub es un "GitHub de imágenes": un registro público donde se guardan imágenes para que
#     cualquiera las baje con `docker pull` sin tener que construirlas.
#   - Una imagen se nombra <usuario>/<repositorio>:<etiqueta>. Aquí: dathinel/zonas-esp32-router:1.0.
#     La etiqueta 1.0 es la versión fija (la que cita el README); `latest` apunta a la última.
#   - `docker push` sube solo las capas que Docker Hub todavía no tiene (las capas de python:3.11-slim
#     o alpine:3.20 ya están allá), así que la primera vez tarda y las siguientes mucho menos.
#
# Antes de correrlo, UNA vez, inicie sesión usted mismo (este script NO pide ni guarda contraseñas):
#     docker login            (usuario de Docker Hub + contraseña o, mejor, un "access token")
#
# Uso:
#     powershell -ExecutionPolicy Bypass -File publicar_dockerhub.ps1
#     $env:DOCKERHUB_USUARIO = "otro_usuario"; powershell -ExecutionPolicy Bypass -File publicar_dockerhub.ps1
#     powershell -ExecutionPolicy Bypass -File publicar_dockerhub.ps1 -SinConstruir   (ya están construidas)

param(
    [string]$Version = "1.0",
    [switch]$SinConstruir
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot   # la carpeta del tema: ahí está docker-compose.yml

# Usuario de Docker Hub: el de la variable de entorno o, por defecto, dathinel (la cuenta del repo).
$Usuario = if ($env:DOCKERHUB_USUARIO) { $env:DOCKERHUB_USUARIO } else { "dathinel" }
# docker-compose.yml nombra las imágenes ${DOCKERHUB_USUARIO:-dathinel}/zonas-esp32-<servicio>:1.0;
# se exporta la variable para que `docker compose build` les ponga exactamente el mismo nombre.
$env:DOCKERHUB_USUARIO = $Usuario
# La imagen "robot" que se publica va SIN las mallas de NAO y Pepper: su licencia (SoftBank, CC BY-NC-ND)
# prohíbe redistribuirlas, y subirlas a Docker Hub sería redistribuirlas. Se fuerza "no" aunque en esta
# consola se haya puesto "si" para verlas en local. Por lo mismo, no usar -SinConstruir si la imagen
# local "robot" se construyó con ACEPTO_LICENCIA_SOFTBANK=si.
$env:ACEPTO_LICENCIA_SOFTBANK = "no"

# Una imagen por tipo de servicio (los 3 players comparten "jugador", los 3 robots comparten "robot",
# y todos los ESP32 emulados comparten "emulador").
$Imagenes = @("router", "admin", "servidor-pista", "jugador", "robot", "emulador")

Write-Host "Usuario de Docker Hub: $Usuario   versión: $Version" -ForegroundColor Cyan

# ---- 0. ¿Hay Docker y hay sesión? ----
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker no responde. Abra Docker Desktop y vuelva a intentar." -ForegroundColor Red
    exit 2
}
# Docker no tiene un comando oficial "¿con quién estoy logueado?". Lo que sí hay es el archivo de
# configuración del cliente: si no menciona Docker Hub (index.docker.io) ni un almacén de credenciales,
# casi seguro no hay sesión. Es solo un aviso: la prueba real es el primer push (más abajo).
$Config = Join-Path $env:USERPROFILE ".docker\config.json"
$TextoConfig = if (Test-Path $Config) { Get-Content -Raw $Config } else { "" }
if ($TextoConfig -notmatch "index\.docker\.io" -and $TextoConfig -notmatch "credsStore") {
    Write-Host "AVISO: no veo una sesión de Docker Hub en $Config." -ForegroundColor Yellow
    Write-Host "       Si el push falla, corra primero:  docker login" -ForegroundColor Yellow
}

# ---- 1. Construir ----
if (-not $SinConstruir) {
    Write-Host "`n== docker compose build (con el perfil 'emulado' para incluir la imagen del emulador) ==" -ForegroundColor Cyan
    docker compose --profile emulado build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Falló la construcción; no se sube nada." -ForegroundColor Red
        exit 1
    }
}

# ---- 2. Etiquetar y subir cada imagen (:1.0 y :latest) ----
$Subidas = @()
foreach ($nombre in $Imagenes) {
    $repo = "$Usuario/zonas-esp32-$nombre"
    docker image inspect "${repo}:$Version" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "No existe la imagen local ${repo}:$Version (¿el compose la nombra distinto?). Se salta." -ForegroundColor Yellow
        continue
    }
    docker tag "${repo}:$Version" "${repo}:latest"
    foreach ($etiqueta in @($Version, "latest")) {
        Write-Host "`n== docker push ${repo}:$etiqueta ==" -ForegroundColor Cyan
        # Se captura la salida (además de mostrarla) para reconocer el error de permisos.
        $salida = docker push "${repo}:$etiqueta" 2>&1 | ForEach-Object { "$_" }
        $salida | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) {
            $texto = ($salida -join "`n")
            if ($texto -match "unauthorized|denied|authentication required|requested access to the resource is denied") {
                Write-Host "`nDocker Hub rechazó el push (sin sesión o sin permiso sobre '$Usuario')." -ForegroundColor Red
                Write-Host "Inicie sesión con:  docker login   (y, si el usuario no es '$Usuario', ponga `$env:DOCKERHUB_USUARIO)." -ForegroundColor Red
                Write-Host "Se detiene aquí: no tiene sentido intentar las demás imágenes." -ForegroundColor Red
                exit 3
            }
            Write-Host "El push de ${repo}:$etiqueta falló por otro motivo (ver arriba). Se sigue con las demás." -ForegroundColor Yellow
            continue
        }
        $Subidas += "${repo}:$etiqueta"
    }
}

# ---- 3. Enlaces ----
Write-Host "`n== Listo ==" -ForegroundColor Green
Write-Host "Imágenes subidas: $($Subidas.Count)"
foreach ($nombre in $Imagenes) {
    Write-Host ("  https://hub.docker.com/r/{0}/zonas-esp32-{1}" -f $Usuario, $nombre)
}
Write-Host "`nPara usarlas en otro PC sin construir nada:  docker compose --profile emulado pull; docker compose --profile emulado up -d"
