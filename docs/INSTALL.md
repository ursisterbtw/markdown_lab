# Markdown Lab Installation Guide

## One-Command Installation

### Linux/macOS (Bash)

```bash
curl -fsSL https://raw.githubusercontent.com/ursisterbtw/markdown_lab/main/scripts/install.sh | bash
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/ursisterbtw/markdown_lab/main/scripts/install.ps1 | iex
```

## What the Installer Does

The installation script will:

1. **Check Prerequisites** - Verify Python 3.12+ and Rust are installed
2. **Install UV Package Manager** - Fast Python package manager
3. **Download Source** - Clone from GitHub or download archive
4. **Build Components** - Compile Rust extensions and Python environment
5. **Create CLI Scripts** - Install `mlab`, `mlab-tui`, and `mlab-legacy` commands
6. **Configure PATH** - Add commands to your shell environment

## Installation Locations

- **Installation**: `~/.local/markdown-lab/` (Linux/macOS) or `%USERPROFILE%\.local\markdown-lab\` (Windows)
- **Commands**: `~/.local/bin/` (Linux/macOS) or `%USERPROFILE%\.local\bin\` (Windows)

## Verification

After installation, verify with:

```bash
mlab --version
mlab profiles
```

## Manual Installation

If the one-command installer doesn't work for your setup:

### 1. Prerequisites

- **Python 3.12+**: [python.org/downloads](https://www.python.org/downloads/)
- **Rust**: [rustup.rs](https://rustup.rs/)
- **Git** (optional): For development or latest features

### 2. Install UV Package Manager

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Clone and Build

```bash
git clone https://github.com/ursisterbtw/markdown_lab.git
cd markdown_lab
uv sync
uv run maturin develop --release
```

### 4. Run

```bash
# Use UV to run with proper environment
uv run python -m markdown_lab.cli --help

# Or activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
python -m markdown_lab.cli --help
```

## Development Installation

For development with hot reloading:

```bash
git clone https://github.com/ursisterbtw/markdown_lab.git
cd markdown_lab

# Quick development setup
just setup
just dev

# Or manually
uv sync --dev
uv run maturin develop
```

## Configuration Profiles

After installation, try different profiles:

- **Development**: `mlab convert <url> --profile dev` - Slow, safe, debugging
- **Production**: `mlab convert <url> --profile prod` - Balanced performance  
- **Fast**: `mlab convert <url> --profile fast` - Maximum speed
- **Conservative**: `mlab convert <url> --profile conservative` - Very respectful

See all profiles: `mlab profiles`

## Troubleshooting

### Python Version Issues

The installer requires Python 3.12+. Check your version:

```bash
python --version
# or
python3 --version
```

Install from [python.org](https://www.python.org/downloads/) or use your package manager:

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.12

# macOS with Homebrew  
brew install python@3.12

# Windows with Chocolatey
choco install python
```

### Rust Installation Issues

Install Rust from [rustup.rs](https://rustup.rs/):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Then restart your shell or run:

```bash
source ~/.cargo/env
```

### PATH Issues

If commands aren't found after installation:

```bash
# Linux/macOS - Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Or run directly
source ~/.bashrc
```

Windows: Restart PowerShell after installation.

### Permission Issues

On Linux/macOS, you might need to make scripts executable:

```bash
chmod +x ~/.local/bin/mlab*
```

### UV Installation Issues  

Install UV manually:

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows  
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Building Issues

If Rust compilation fails:

```bash
# Update Rust
rustup update

# Clear caches
cargo clean
rm -rf target/

# Rebuild
uv run maturin develop --release
```

## Uninstallation

To remove Markdown Lab:

```bash
# Remove installation directory
rm -rf ~/.local/markdown-lab/

# Remove commands (Linux/macOS)
rm ~/.local/bin/mlab*

# Windows - Delete folder and remove from PATH
# %USERPROFILE%\.local\markdown-lab\
```

## Getting Help

- **Documentation**: [github.com/ursisterbtw/markdown_lab](https://github.com/ursisterbtw/markdown_lab)
- **Issues**: [github.com/ursisterbtw/markdown_lab/issues](https://github.com/ursisterbtw/markdown_lab/issues)
- **CLI Help**: `mlab --help`, `mlab convert --help`
- **Profiles**: `mlab profiles`
- **System Status**: `mlab status`
