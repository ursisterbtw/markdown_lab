#!/bin/bash
# 
# Markdown Lab One-Command Installer
# Simplifies installation with automatic dependency management
# 

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Installation configuration
PYTHON_MIN_VERSION="3.12"
INSTALL_LOCATION="$HOME/.local/markdown-lab"
BIN_LOCATION="$HOME/.local/bin"

# Banner
echo -e "${BLUE}${BOLD}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                    🔬 Markdown Lab Installer                 ║
║              One-Command Installation Script                 ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Helper functions
print_step() {
    echo -e "\n${BLUE}▶${NC} ${BOLD}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC}  $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Version comparison function
version_ge() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

# Check Python version
check_python() {
    print_step "Checking Python installation..."
    
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python ${PYTHON_MIN_VERSION}+ first."
        echo "Visit: https://www.python.org/downloads/"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    print_info "Found Python $PYTHON_VERSION"
    
    if version_ge "$PYTHON_VERSION" "$PYTHON_MIN_VERSION"; then
        print_success "Python version is compatible (>= $PYTHON_MIN_VERSION)"
    else
        print_error "Python $PYTHON_MIN_VERSION or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi
}

# Check Rust installation
check_rust() {
    print_step "Checking Rust installation..."
    
    if command_exists rustc && command_exists cargo; then
        RUST_VERSION=$(rustc --version | cut -d' ' -f2)
        print_success "Found Rust $RUST_VERSION"
    else
        print_warning "Rust not found. Installing Rust..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
        print_success "Rust installed successfully"
    fi
}

# Install UV package manager
install_uv() {
    print_step "Installing UV package manager..."
    
    if command_exists uv; then
        print_success "UV already installed"
    else
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
        print_success "UV installed successfully"
    fi
}

# Setup installation directory
setup_directories() {
    print_step "Setting up installation directories..."
    
    mkdir -p "$INSTALL_LOCATION"
    mkdir -p "$BIN_LOCATION"
    print_success "Directories created"
}

# Clone or download source
get_source() {
    print_step "Getting Markdown Lab source..."
    
    if [ -d "$INSTALL_LOCATION/.git" ]; then
        print_info "Updating existing installation..."
        cd "$INSTALL_LOCATION"
        git pull origin main
    else
        if command_exists git; then
            print_info "Cloning from GitHub..."
            git clone https://github.com/ursisterbtw/markdown_lab.git "$INSTALL_LOCATION"
        else
            print_info "Downloading source archive..."
            curl -L https://github.com/ursisterbtw/markdown_lab/archive/main.tar.gz | tar xz --strip-components=1 -C "$INSTALL_LOCATION"
        fi
    fi
    
    cd "$INSTALL_LOCATION"
    print_success "Source code obtained"
}

# Build and install
build_install() {
    print_step "Building and installing Markdown Lab..."
    
    cd "$INSTALL_LOCATION"
    
    # Setup Python environment
    print_info "Setting up Python environment..."
    uv sync
    
    # Build Rust components  
    print_info "Building Rust components..."
    uv run maturin develop --release
    
    print_success "Build completed"
}

# Create wrapper scripts
create_wrappers() {
    print_step "Creating command line scripts..."
    
    # Create mlab wrapper
    cat > "$BIN_LOCATION/mlab" << EOF
#!/bin/bash
export UV_PROJECT_ENVIRONMENT="$INSTALL_LOCATION/.venv"
exec "$INSTALL_LOCATION/.venv/bin/python" -m markdown_lab.cli "\$@"
EOF
    chmod +x "$BIN_LOCATION/mlab"
    
    # Create legacy wrapper
    cat > "$BIN_LOCATION/mlab-legacy" << EOF
#!/bin/bash
export UV_PROJECT_ENVIRONMENT="$INSTALL_LOCATION/.venv"
exec "$INSTALL_LOCATION/.venv/bin/python" -m markdown_lab.core.scraper "\$@"
EOF
    chmod +x "$BIN_LOCATION/mlab-legacy"
    
    # Create TUI wrapper
    cat > "$BIN_LOCATION/mlab-tui" << EOF
#!/bin/bash
export UV_PROJECT_ENVIRONMENT="$INSTALL_LOCATION/.venv"
exec "$INSTALL_LOCATION/.venv/bin/python" -m markdown_lab.tui "\$@"
EOF
    chmod +x "$BIN_LOCATION/mlab-tui"
    
    print_success "Command line scripts created"
}

# Setup PATH
setup_path() {
    print_step "Setting up PATH..."
    
    # Add to bashrc if not already present
    if ! grep -q "$BIN_LOCATION" "$HOME/.bashrc" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        print_info "Added to ~/.bashrc"
    fi
    
    # Add to zshrc if it exists
    if [ -f "$HOME/.zshrc" ] && ! grep -q "$BIN_LOCATION" "$HOME/.zshrc"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        print_info "Added to ~/.zshrc"
    fi
    
    # Add to current session
    export PATH="$BIN_LOCATION:$PATH"
    
    print_success "PATH configured"
}

# Test installation
test_installation() {
    print_step "Testing installation..."
    
    if command_exists mlab; then
        print_info "Testing mlab command..."
        mlab --version >/dev/null 2>&1 && print_success "mlab command working"
        
        print_info "Testing profiles..."
        mlab profiles >/dev/null 2>&1 && print_success "Profiles working"
        
        print_success "Installation test passed"
    else
        print_warning "mlab command not found in PATH. You may need to restart your shell."
    fi
}

# Print completion message
print_completion() {
    echo -e "\n${GREEN}${BOLD}🎉 Installation Complete!${NC}\n"
    
    echo -e "${BOLD}Available Commands:${NC}"
    echo -e "  ${GREEN}mlab${NC}         - Main CLI (with profiles, modern interface)"
    echo -e "  ${GREEN}mlab-tui${NC}     - Terminal User Interface"
    echo -e "  ${GREEN}mlab-legacy${NC}  - Legacy CLI interface"
    
    echo -e "\n${BOLD}Quick Start:${NC}"
    echo -e "  ${BLUE}mlab profiles${NC}                    # See available configuration profiles"
    echo -e "  ${BLUE}mlab convert <url>${NC}              # Convert a webpage to markdown"
    echo -e "  ${BLUE}mlab convert <url> --profile dev${NC} # Use development profile"
    echo -e "  ${BLUE}mlab-tui${NC}                        # Launch interactive interface"
    
    echo -e "\n${BOLD}Configuration Profiles:${NC}"
    echo -e "  ${YELLOW}dev${NC}          - Development (slow, safe, debugging)"
    echo -e "  ${YELLOW}prod${NC}         - Production (balanced performance)"
    echo -e "  ${YELLOW}fast${NC}         - Fast processing (maximum speed)"
    echo -e "  ${YELLOW}conservative${NC} - Very safe and respectful"
    
    if ! command_exists mlab; then
        echo -e "\n${YELLOW}${BOLD}Note:${NC} Restart your shell or run:"
        echo -e "  ${BLUE}source ~/.bashrc${NC}  (or ~/.zshrc)"
        echo -e "  ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    fi
    
    echo -e "\n${BOLD}Documentation:${NC}"
    echo -e "  ${BLUE}https://github.com/ursisterbtw/markdown_lab${NC}"
    echo -e "\n${BOLD}Get Help:${NC}"
    echo -e "  ${BLUE}mlab --help${NC}"
    echo -e "  ${BLUE}mlab convert --help${NC}"
}

# Main installation flow
main() {
    echo "Starting Markdown Lab installation..."
    echo "This will install Markdown Lab to: $INSTALL_LOCATION"
    echo "Commands will be available at: $BIN_LOCATION"
    echo
    
    # Check if user wants to continue
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    # Run installation steps
    check_python
    check_rust
    install_uv
    setup_directories
    get_source
    build_install
    create_wrappers
    setup_path
    test_installation
    print_completion
}

# Handle errors
trap 'echo -e "\n${RED}❌ Installation failed!${NC}"; exit 1' ERR

# Run installer
main "$@"