# Windows PowerShell script 

Param()

$OutDir = ".\.certs"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$CertFile = Join-Path $OutDir "dev.pem"
$KeyFile  = Join-Path $OutDir "dev-key.pem"

function Install-ChocoAndMkcert {
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "Chocolatey not found. Installing Chocolatey..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    }
    choco install -y mkcert nssm || true
}

if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
    Write-Host "mkcert not found. Installing via Chocolatey (requires admin)..."
    Install-ChocoAndMkcert
}

Write-Host "Installing mkcert CA (may prompt)..."
mkcert -install

$hosts = @("127.0.0.1","localhost","::1", ("{0}.local" -f $env:COMPUTERNAME))
Write-Host "Generating certificate for: $hosts"
mkcert -key-file $KeyFile -cert-file $CertFile $hosts

Write-Host "Certificates written to: $CertFile and $KeyFile"
Write-Host "Add $OutDir to .gitignore"
