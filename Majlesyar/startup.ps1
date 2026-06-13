param(
    [ValidateSet("auto", "docker", "local")]
    [string]$Mode = $(if ($env:STARTUP_MODE) { $env:STARTUP_MODE } else { "auto" }),
    [string]$ImageName = $(if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { "majlesyar:latest" }),
    [string]$ContainerName = $(if ($env:CONTAINER_NAME) { $env:CONTAINER_NAME } else { "majlesyar" }),
    [string]$HostPort = $(if ($env:HOST_PORT) { $env:HOST_PORT } else { "8000" }),
    [string]$FrontendPort = $(if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "8080" }),
    [string]$AppPort = $(if ($env:APP_PORT) { $env:APP_PORT } else { "8000" }),
    [string]$AdminUsername = $(if ($env:ADMIN_USERNAME) { $env:ADMIN_USERNAME } else { "" }),
    [string]$AdminEmail = $(if ($env:ADMIN_EMAIL) { $env:ADMIN_EMAIL } else { "admin@example.com" }),
    [string]$AdminPassword = $(if ($env:ADMIN_PASSWORD) { $env:ADMIN_PASSWORD } else { "" }),
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
$HealthPath = "/api/v1/health/"

function Write-StartupLog {
    param([string]$Message)
    Write-Host "[startup] $Message"
}

function Get-ProjectRoot {
    if ($PSScriptRoot) {
        return $PSScriptRoot
    }
    return (Get-Location).Path
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Start-DockerDesktopIfPresent {
    $dockerDesktop = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LocalAppData\Docker\Docker Desktop.exe"
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

    if (-not $dockerDesktop) {
        return
    }

    $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if (-not $dockerProcess) {
        Write-StartupLog "Starting Docker Desktop..."
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden | Out-Null
    }
}

function Wait-DockerDaemon {
    Start-DockerDesktopIfPresent
    Write-StartupLog "Waiting for Docker daemon..."
    for ($i = 0; $i -lt 60; $i++) {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "Docker daemon is not running. Start Docker Desktop, then run this script again."
}

function New-SecretKey {
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    return (($bytes | ForEach-Object { $_.ToString("x2") }) -join "")
}

function Set-EnvFileValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = Get-Content -LiteralPath $Path
    }

    $updated = $false
    $next = foreach ($line in $lines) {
        if ($line -match "^$([regex]::Escape($Key))=") {
            "$Key=$Value"
            $updated = $true
        } else {
            $line
        }
    }

    if (-not $updated) {
        $next += "$Key=$Value"
    }

    Set-Content -LiteralPath $Path -Value $next -Encoding utf8
}

function Initialize-EnvFile {
    param(
        [string]$DeployDir,
        [string]$EnvFile,
        [string]$MediaDir
    )

    New-Item -ItemType Directory -Force -Path $DeployDir, $MediaDir | Out-Null
    $dbFile = Join-Path $DeployDir "db.sqlite3"
    if (-not (Test-Path -LiteralPath $dbFile)) {
        New-Item -ItemType File -Path $dbFile | Out-Null
    }
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        New-Item -ItemType File -Path $EnvFile | Out-Null
    }

    $secret = $env:DJANGO_SECRET_KEY
    if (-not $secret) {
        $existingSecret = Select-String -LiteralPath $EnvFile -Pattern "^DJANGO_SECRET_KEY=(.*)$" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($existingSecret) {
            $secret = $existingSecret.Matches[0].Groups[1].Value
        }
    }
    if (-not $secret) {
        $secret = New-SecretKey
    }

    Set-EnvFileValue -Path $EnvFile -Key "PORT" -Value $AppPort
    Set-EnvFileValue -Path $EnvFile -Key "DJANGO_DEBUG" -Value "0"
    Set-EnvFileValue -Path $EnvFile -Key "DJANGO_SECRET_KEY" -Value $secret
    Set-EnvFileValue -Path $EnvFile -Key "DJANGO_ALLOWED_HOSTS" -Value "localhost,127.0.0.1"
    Set-EnvFileValue -Path $EnvFile -Key "DJANGO_MEDIA_ROOT" -Value "/app/media"
    Set-EnvFileValue -Path $EnvFile -Key "CORS_ALLOWED_ORIGINS" -Value "http://localhost:$HostPort,http://127.0.0.1:$HostPort"
    Set-EnvFileValue -Path $EnvFile -Key "CSRF_TRUSTED_ORIGINS" -Value "http://localhost:$HostPort,http://127.0.0.1:$HostPort"
}

function Wait-Health {
    param([string]$Url)

    Write-StartupLog "Waiting for application health at $Url ..."
    for ($i = 0; $i -lt 60; $i++) {
        try {
            Invoke-RestMethod -Uri $Url -TimeoutSec 3 | Out-Null
            Write-StartupLog "Application is healthy."
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    docker logs --tail 100 $ContainerName
    throw "Application did not become healthy in time."
}

function Test-TcpPortInUse {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Get-AvailablePort {
    param(
        [int]$PreferredPort,
        [int[]]$FallbackPorts = @(5173, 5174, 8081, 8082, 3000, 3001)
    )

    if (-not (Test-TcpPortInUse -Port $PreferredPort)) {
        return $PreferredPort
    }

    foreach ($port in $FallbackPorts) {
        if (-not (Test-TcpPortInUse -Port $port)) {
            return $port
        }
    }

    for ($port = 8090; $port -lt 8200; $port++) {
        if (-not (Test-TcpPortInUse -Port $port)) {
            return $port
        }
    }
    throw "No free frontend port found."
}

function Get-ListeningProcessId {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($connection) {
        return [int]$connection.OwningProcess
    }
    return $null
}

function Wait-HttpOk {
    param([string]$Url)

    Write-StartupLog "Waiting for HTTP 200 at $Url ..."
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "HTTP server did not become ready: $Url"
}

function Stop-ProcessFromPidFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $pidValue = (Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $pidValue) {
        return
    }
    $processId = [int]$pidValue
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$processId" -ErrorAction SilentlyContinue |
        ForEach-Object {
            $child = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
            if ($child) {
                Write-StartupLog "Stopping child process PID $($child.Id) ..."
                Stop-Process -Id $child.Id -Force
            }
        }

    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Write-StartupLog "Stopping previous process PID $pidValue ..."
        Stop-Process -Id $process.Id -Force
    }
    Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}

function Start-LocalProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$LogPath
    )

    $errPath = [System.IO.Path]::ChangeExtension($LogPath, ".err.log")
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogPath `
        -RedirectStandardError $errPath `
        -PassThru
    Write-StartupLog "$Name started. PID: $($process.Id)"
    return $process
}

function Start-LocalStack {
    param(
        [string]$RootDir,
        [string]$DeployDir
    )

    $backendDir = Join-Path $RootDir "backend"
    $logsDir = Join-Path $DeployDir "logs"
    New-Item -ItemType Directory -Force -Path $DeployDir, $logsDir | Out-Null

    Stop-ProcessFromPidFile -Path (Join-Path $DeployDir "backend.pid")
    Stop-ProcessFromPidFile -Path (Join-Path $DeployDir "frontend.pid")

    $actualFrontendPort = Get-AvailablePort -PreferredPort ([int]$FrontendPort)
    if ($actualFrontendPort -ne [int]$FrontendPort) {
        Write-StartupLog "Frontend port $FrontendPort is busy. Using $actualFrontendPort."
        $FrontendPort = [string]$actualFrontendPort
    }

    if (-not (Test-Command "python")) {
        throw "Python is required but not found in PATH."
    }
    if (-not (Test-Command "npm")) {
        throw "npm is required but not found in PATH."
    }

    if (-not (Test-Path -LiteralPath (Join-Path $RootDir "node_modules"))) {
        Write-StartupLog "Installing frontend packages..."
        Push-Location $RootDir
        try {
            npm install
            if ($LASTEXITCODE -ne 0) {
                throw "npm install failed."
            }
        } finally {
            Pop-Location
        }
    }

    Write-StartupLog "Running Django migrations..."
    Push-Location $backendDir
    try {
        $env:DJANGO_DEBUG = "1"
        $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
        $env:CORS_ALLOWED_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
        $env:CSRF_TRUSTED_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
        python manage.py migrate
        if ($LASTEXITCODE -ne 0) {
            throw "Django migrate failed."
        }
        python manage.py seed_initial_data
        if ($LASTEXITCODE -ne 0) {
            throw "Django seed_initial_data failed."
        }
    } finally {
        Pop-Location
    }

    $env:DJANGO_DEBUG = "1"
    $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
    $env:CORS_ALLOWED_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
    $env:CSRF_TRUSTED_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
    $env:VITE_API_BASE_URL = ""

    $viteScript = Join-Path $RootDir "node_modules\vite\bin\vite.js"
    if (-not (Test-Path -LiteralPath $viteScript)) {
        throw "Vite script not found. Run npm install in $RootDir."
    }

    $backendProcess = Start-LocalProcess `
        -Name "Backend" `
        -FilePath "python" `
        -ArgumentList @("manage.py", "runserver", "127.0.0.1:$HostPort", "--noreload") `
        -WorkingDirectory $backendDir `
        -LogPath (Join-Path $logsDir "backend.log")
    $frontendProcess = Start-LocalProcess `
        -Name "Frontend" `
        -FilePath "node" `
        -ArgumentList @("""$viteScript""", "--host", "127.0.0.1", "--port", $FrontendPort, "--strictPort") `
        -WorkingDirectory $RootDir `
        -LogPath (Join-Path $logsDir "frontend.log")
    Set-Content -LiteralPath (Join-Path $DeployDir "backend.pid") -Value $backendProcess.Id -Encoding ascii
    Set-Content -LiteralPath (Join-Path $DeployDir "frontend.pid") -Value $frontendProcess.Id -Encoding ascii

    Wait-Health -Url "http://127.0.0.1:$HostPort$HealthPath"
    Wait-HttpOk -Url "http://127.0.0.1:$FrontendPort/"

    $backendPid = Get-ListeningProcessId -Port ([int]$HostPort)
    $frontendPid = Get-ListeningProcessId -Port ([int]$FrontendPort)
    if ($backendPid) {
        Set-Content -LiteralPath (Join-Path $DeployDir "backend.pid") -Value $backendPid -Encoding ascii
    }
    if ($frontendPid) {
        Set-Content -LiteralPath (Join-Path $DeployDir "frontend.pid") -Value $frontendPid -Encoding ascii
    }

    Write-StartupLog "Local startup complete."
    Write-StartupLog "Frontend: http://localhost:$FrontendPort"
    Write-StartupLog "Backend: http://localhost:$HostPort"
    Write-StartupLog "Admin: http://localhost:$HostPort/majmanage/"
    Write-StartupLog "Swagger: http://localhost:$HostPort/api/docs/"
    Write-StartupLog "Logs: $logsDir"
}

$rootDir = Get-ProjectRoot
$dockerFile = Join-Path $rootDir "Dockerfile"
$backendDir = Join-Path $rootDir "backend"
if (-not (Test-Path -LiteralPath $dockerFile)) {
    throw "Dockerfile not found in $rootDir."
}
if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "backend/ not found in $rootDir."
}
if (-not (Test-Command "docker")) {
    if ($Mode -eq "docker") {
        throw "Docker is required but not found in PATH."
    }
    $Mode = "local"
}

$deployDir = Join-Path $rootDir ".deploy"
$envFile = Join-Path $deployDir ".env.production"
$dbFile = Join-Path $deployDir "db.sqlite3"
$mediaDir = Join-Path $deployDir "media"

if ($Mode -eq "local") {
    Start-LocalStack -RootDir $rootDir -DeployDir $deployDir
    exit 0
}

Wait-DockerDaemon
Initialize-EnvFile -DeployDir $deployDir -EnvFile $envFile -MediaDir $mediaDir

if (-not $NoBuild) {
    Write-StartupLog "Building image $ImageName ..."
    docker build -t $ImageName $rootDir
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed."
    }
}

Write-StartupLog "Starting container $ContainerName ..."
docker rm -f $ContainerName *> $null
docker run -d `
    --name $ContainerName `
    --restart unless-stopped `
    --env-file $envFile `
    -p "${HostPort}:${AppPort}" `
    -v "${dbFile}:/app/db.sqlite3" `
    -v "${mediaDir}:/app/media" `
    $ImageName | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker run failed."
}

Wait-Health -Url "http://127.0.0.1:$HostPort$HealthPath"

if ($AdminUsername -and $AdminPassword) {
    Write-StartupLog "Creating/updating Django superuser $AdminUsername ..."
    $script = @"
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ['DJANGO_SUPERUSER_USERNAME']
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'is_staff': True, 'is_superuser': True})
changed = False
if user.email != email:
    user.email = email
    changed = True
if not user.is_staff:
    user.is_staff = True
    changed = True
if not user.is_superuser:
    user.is_superuser = True
    changed = True
if created or not user.check_password(password):
    user.set_password(password)
    changed = True
if changed:
    user.save()
print('superuser ready')
"@
    docker exec `
        -e "DJANGO_SUPERUSER_USERNAME=$AdminUsername" `
        -e "DJANGO_SUPERUSER_EMAIL=$AdminEmail" `
        -e "DJANGO_SUPERUSER_PASSWORD=$AdminPassword" `
        $ContainerName `
        python manage.py shell -c $script
}

Write-StartupLog "Deployment complete."
Write-StartupLog "Container: $ContainerName"
Write-StartupLog "URL: http://localhost:$HostPort"
Write-StartupLog "Admin: http://localhost:$HostPort/majmanage/"
Write-StartupLog "Swagger: http://localhost:$HostPort/api/docs/"
Write-StartupLog "Logs: docker logs -f $ContainerName"
