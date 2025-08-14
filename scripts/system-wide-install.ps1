# Markdown Lab One-Command Installer for Windows
# PowerShell script for simplified installation

param(
    [string]$InstallPath = "$env:USERPROFILE\.local\markdown-lab",
    [string]$BinPath = "$env:USERPROFILE\.local\bin"
)

# Colors for output (if supported)
function Write-Step([string]$Message) {
    Write-Host "▶ " -ForegroundColor Blue -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Success([string]$Message) {
    Write-Host "✅ " -ForegroundColor Green -NoNewline  
    Write-Host $Message
}

function Write-Warning([string]$Message) {
    Write-Host "⚠️ " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error([string]$Message) {
    Write-Host "❌ " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Info([string]$Message) {
    Write-Host "ℹ️  " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

# Banner
Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║                    🔬 Markdown Lab Installer                 ║
║              One-Command Installation Script                 ║
║                         Windows Version                      ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Blue

Write-Host ""
Write-Host "Starting Markdown Lab installation..." -ForegroundColor White
Write-Host "This will install Markdown Lab to: $InstallPath"
Write-Host "Commands will be available at: $BinPath"
Write-Host ""

# Check if user wants to continue
$continue = Read-Host "Continue? (y/N)"
if ($continue -notmatch '^[Yy]$') {
    Write-Host "Installation cancelled."
    exit 0
}

try {
    # Check Python
    Write-Step "Checking Python installation..."
    $pythonCmd = $null
    
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3" 
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCmd = "py"
    } else {
        Write-Error "Python not found. Please install Python 3.12+ first."
        Write-Host "Visit: https://www.python.org/downloads/"
        exit 1
    }
    
    $pythonVersion = & $pythonCmd --version 2>&1 | ForEach-Object { $_.Split(' ')[1] }
    Write-Info "Found Python $pythonVersion"
    
    # Simple version check (assumes 3.12+ format)
    $versionParts = $pythonVersion.Split('.')
    $major = [int]$versionParts[0]
    $minor = [int]$versionParts[1]
    
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 12)) {
        Write-Error "Python 3.12 or higher is required (found $pythonVersion)"
        exit 1
    }
    Write-Success "Python version is compatible (>= 3.12)"

    # Check Rust
    Write-Step "Checking Rust installation..."
    if ((Get-Command rustc -ErrorAction SilentlyContinue) -and (Get-Command cargo -ErrorAction SilentlyContinue)) {
        $rustVersion = rustc --version | ForEach-Object { $_.Split(' ')[1] }
        Write-Success "Found Rust $rustVersion"
    } else {
        Write-Warning "Rust not found. Please install Rust from https://rustup.rs/"
        Write-Host "After installing Rust, restart PowerShell and run this installer again."
        exit 1
    }

    # Install UV
    Write-Step "Installing UV package manager..."
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Success "UV already installed"
    } else {
        Write-Info "Installing UV..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        # Add UV to PATH for current session
        $env:PATH += ";$env:USERPROFILE\.cargo\bin"
        Write-Success "UV installed successfully"
    }

    # Setup directories
    Write-Step "Setting up installation directories..."
    New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null
    New-Item -ItemType Directory -Force -Path $BinPath | Out-Null
    Write-Success "Directories created"

    # Get source
    Write-Step "Getting Markdown Lab source..."
    
    if (Test-Path "$InstallPath\.git") {
        Write-Info "Updating existing installation..."
        Set-Location $InstallPath
        git pull origin main
    } else {
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Write-Info "Cloning from GitHub..."
            git clone https://github.com/ursisterbtw/markdown_lab.git $InstallPath
        } else {
            Write-Info "Downloading source archive..."
            $zipUrl = "https://github.com/ursisterbtw/markdown_lab/archive/main.zip"
            $zipPath = "$env:TEMP\markdown_lab.zip"
            Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
            
            # Extract zip
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $env:TEMP)
            
            # Move extracted content
            Move-Item "$env:TEMP\markdown_lab-main\*" $InstallPath -Force
            Remove-Item "$env:TEMP\markdown_lab-main" -Recurse -Force
            Remove-Item $zipPath -Force
        }
    }
    
    Set-Location $InstallPath
    Write-Success "Source code obtained"

    # Build and install
    Write-Step "Building and installing Markdown Lab..."
    
    Write-Info "Setting up Python environment..."
    uv sync
    
    Write-Info "Building Rust components..."
    uv run maturin develop --release
    
    Write-Success "Build completed"

    # Create wrapper scripts  
    Write-Step "Creating command line scripts..."
    
    # Create mlab wrapper
    @"
@echo off
set UV_PROJECT_ENVIRONMENT=$InstallPath\.venv
"$InstallPath\.venv\Scripts\python.exe" -m markdown_lab.cli %*
"@ | Out-File -FilePath "$BinPath\mlab.bat" -Encoding ASCII
    
    # Create legacy wrapper
    @"
@echo off
set UV_PROJECT_ENVIRONMENT=$InstallPath\.venv  
"$InstallPath\.venv\Scripts\python.exe" -m markdown_lab.core.scraper %*
"@ | Out-File -FilePath "$BinPath\mlab-legacy.bat" -Encoding ASCII
    
    # Create TUI wrapper
    @"
@echo off
set UV_PROJECT_ENVIRONMENT=$InstallPath\.venv
"$InstallPath\.venv\Scripts\python.exe" -m markdown_lab.tui %*
"@ | Out-File -FilePath "$BinPath\mlab-tui.bat" -Encoding ASCII
    
    Write-Success "Command line scripts created"

    # Setup PATH
    Write-Step "Setting up PATH..."
    
    # Get current user PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    
    if ($currentPath -notlike "*$BinPath*") {
        $newPath = $currentPath + ";$BinPath"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        $env:PATH += ";$BinPath"  # Add to current session
        Write-Success "PATH configured (restart PowerShell to take effect)"
    } else {
        Write-Success "PATH already configured"
    }

    # Test installation
    Write-Step "Testing installation..."
    
    # Add current session PATH for testing
    $env:PATH += ";$BinPath"
    
    if (Test-Path "$BinPath\mlab.bat") {
        Write-Success "Installation completed successfully"
    } else {
        Write-Warning "Installation may have issues. Check the scripts in $BinPath"
    }

    # Print completion
    Write-Host ""
    Write-Host "Installation Complete!" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "Available Commands:" -ForegroundColor White
    Write-Host "  mlab         - Main CLI (with profiles, modern interface)" -ForegroundColor Green
    Write-Host "  mlab-tui     - Terminal User Interface" -ForegroundColor Green  
    Write-Host "  mlab-legacy  - Legacy CLI interface" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor White
    Write-Host "  mlab profiles                    # See available configuration profiles" -ForegroundColor Blue
    Write-Host "  mlab convert <url>              # Convert a webpage to markdown" -ForegroundColor Blue
    Write-Host "  mlab convert <url> --profile dev # Use development profile" -ForegroundColor Blue
    Write-Host "  mlab-tui                        # Launch interactive interface" -ForegroundColor Blue
    
    Write-Host ""
    Write-Host "Note: Restart PowerShell to use the commands from anywhere" -ForegroundColor Yellow
    
    Write-Host ""
    Write-Host "Documentation: https://github.com/ursisterbtw/markdown_lab" -ForegroundColor Blue
    Write-Host "Get Help: mlab --help" -ForegroundColor Blue

} catch {
    Write-Error "Installation failed: $($_.Exception.Message)"
    exit 1
}