<#
.SYNOPSIS
    Pharos (FeedFlow V2) Installation Script
.DESCRIPTION
    This script automates the installation of Pharos-News-Feed on a Windows machine.
    It clones the repository, creates a Python virtual environment, installs dependencies,
    creates a default .env file, and provides a startup script.
#>

$RepoUrl = "https://github.com/christoskataxenos/Pharos-News-Feed.git"
$InstallDir = Join-Path $HOME "Pharos-News-Feed"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Pharos (FeedFlow V2) Windows Installer" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check for Git
Write-Host "Checking for Git..." -ForegroundColor Yellow
if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed or not in PATH. Please install Git and try again."
    exit 1
}
Write-Host "Git found." -ForegroundColor Green

# 2. Check for Python
Write-Host "Checking for Python..." -ForegroundColor Yellow
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.11+ and try again."
    exit 1
}
Write-Host "Python found." -ForegroundColor Green

# 3. Clone Repository
if (Test-Path $InstallDir) {
    Write-Host "Directory $InstallDir already exists. Pulling latest changes..." -ForegroundColor Yellow
    Set-Location $InstallDir
    git pull
} else {
    Write-Host "Cloning Pharos-News-Feed to $InstallDir..." -ForegroundColor Yellow
    git clone $RepoUrl $InstallDir
    Set-Location $InstallDir
}

# 4. Setup Virtual Environment
$VenvDir = Join-Path $InstallDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating Python Virtual Environment..." -ForegroundColor Yellow
    python -m venv venv
}

# 5. Install Dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
# Activate venv for the current process to install reqs
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
& $ActivateScript
pip install -r requirements.txt

# 6. Create .env file
$EnvFile = Join-Path $InstallDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "Creating default .env file..." -ForegroundColor Yellow
    $EnvContent = @"
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin_password_change_me
"@
    Set-Content -Path $EnvFile -Value $EnvContent
    Write-Host "Created .env file. Please remember to change the default password!" -ForegroundColor Magenta
}

# 7. Create a convenient Start script on the Desktop
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Start Pharos.bat"
if (-not (Test-Path $ShortcutPath)) {
    Write-Host "Creating startup shortcut on Desktop..." -ForegroundColor Yellow
    $BatContent = @"
@echo off
echo Starting Pharos News Feed...
cd /d "$InstallDir"
call venv\Scripts\activate.bat
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
"@
    Set-Content -Path $ShortcutPath -Value $BatContent
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Installation Complete!" -ForegroundColor Green
Write-Host " Pharos is installed at: $InstallDir"
Write-Host " You can start it using the 'Start Pharos.bat' on your Desktop."
Write-Host " Alternatively, run the following commands:"
Write-Host "   cd ~/Pharos-News-Feed"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "   uvicorn main:app --reload"
Write-Host "=========================================" -ForegroundColor Cyan

# Ask to start immediately
$StartNow = Read-Host "Do you want to start Pharos now? (Y/n)"
if ($StartNow -notmatch "^[nN]") {
    Write-Host "Starting Pharos..." -ForegroundColor Yellow
    uvicorn main:app --reload
}
