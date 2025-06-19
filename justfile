# Justfile for Markdown Lab
# Streamlined task runner for development, testing, and deployment

# Default recipe - show available commands
default:
    @just --list

# Helper function to activate virtual environment
_activate_venv:
    #!/usr/bin/env bash
    if [ -f ".venv/bin/activate" ]; then
        . .venv/bin/activate
    else
        echo "Error: Virtual environment not found at .venv/bin/activate" >&2
        exit 1
    fi

# === SETUP & INSTALLATION ===

# Install all dependencies and set up development environment
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Setting up Markdown Lab development environment..."
    
    # Check for required tools
    for cmd in python3 pip curl cargo; do
        if ! command -v "$cmd" &> /dev/null; then
            echo "❌ Error: $cmd is required but not installed"
            exit 1
        fi
    done

    # Install UV if not present
    if ! command -v uv &> /dev/null; then
        echo "📦 Installing UV package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    echo "📦 Installing Python dependencies..."
    uv sync
    
    echo "🦀 Building Rust components..."
    @just _activate_venv && maturin develop
    
    echo "✅ Setup complete! Run 'just test' to verify installation."

# Clean all build artifacts
clean:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🧹 Cleaning build artifacts..."
    
    # Rust artifacts
    cargo clean 2>/dev/null || true
    
    # Python artifacts
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.py[co]" -delete 2>/dev/null || true
    
    # Build and cache directories
    for dir in target build dist .pytest_cache .coverage htmlcov .request_cache examples/demo_output *.egg-info; do
        rm -rf "$dir" 2>/dev/null || true
    done
    
    echo "✅ Clean complete!"

# === DEVELOPMENT ===

# Build Rust components (dev=debug, release=optimized, js=with JavaScript support)
build mode="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{mode}}" in
        "dev")
            echo "🔨 Building Rust components for development..."
            just _activate_venv && maturin develop
            ;;
        "release")
            echo "🚀 Building Rust components with optimizations..."
            just _activate_venv && maturin develop --release
            ;;
        "js")
            echo "🌐 Building with JavaScript rendering support..."
            cargo build --release --features real_rendering
            just _activate_venv && maturin develop --release --features real_rendering
            ;;
        *)
            echo "❌ Invalid mode. Use: dev, release, or js"
            exit 1
            ;;
    esac

# Quick development setup and build
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🔄 Starting development mode..."
    if [ ! -d ".venv" ]; then
        echo "❌ Virtual environment not found. Run 'just setup' first."
        exit 1
    fi
    just build dev
    echo "✅ Development ready! Use 'just build dev' after Rust changes"

# === TESTING ===

# Run tests (all=complete suite, rust=Rust only, python=Python only, bindings=Python bindings, coverage=with coverage)
test type="all":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        "all")
            echo "🧪 Running complete test suite..."
            cargo test --color=always
            just _activate_venv && python -m pytest tests/ -v --color=yes
            echo "✅ All tests completed successfully!"
            ;;
        "rust")
            echo "🦀 Running Rust tests..."
            cargo test --color=always
            ;;
        "rust-verbose")
            echo "🦀 Running Rust tests with verbose output..."
            RUST_LOG=debug cargo test -- --nocapture --color=always
            ;;
        "python")
            echo "🐍 Running Python tests..."
            just _activate_venv && python -m pytest tests/ -v --color=yes
            ;;
        "bindings")
            echo "🔗 Running Python binding tests..."
            just _activate_venv && python -m pytest tests/rust/test_python_bindings.py -v --color=yes
            ;;
        "integration")
            echo "🔧 Running integration tests..."
            just _activate_venv && python -m pytest tests/integration/ -v --color=yes
            ;;
        "coverage")
            echo "📊 Running tests with coverage..."
            just _activate_venv && python -m pytest --cov=markdown_lab --cov-report=html --cov-report=term --cov-fail-under=80 --color=yes
            ;;
        *)
            echo "❌ Invalid type. Use: all, rust, rust-verbose, python, bindings, integration, coverage"
            exit 1
            ;;
    esac

# Run specific test file or pattern
test-file file="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "{{file}}" ]; then
        echo "❌ Usage: just test-file <test_file_or_pattern>"
        exit 1
    fi
    echo "🔍 Running tests matching {{file}}..."
    just _activate_venv && python -m pytest "{{file}}" -v --color=yes

# === BENCHMARKING ===

# Run benchmarks (all=complete suite, html=HTML parsing, chunk=chunking, viz=visualization)
bench type="all":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        "all")
            echo "⚡ Running all benchmarks..."
            cargo bench
            ;;
        "html")
            echo "📄 Running HTML parsing benchmark..."
            cargo bench html_to_markdown
            ;;
        "chunk")
            echo "📝 Running chunking benchmark..."
            cargo bench chunk_markdown
            ;;
        "viz")
            echo "📊 Generating benchmark visualization..."
            just _activate_venv && python scripts/visualize_benchmarks.py
            ;;
        *)
            echo "❌ Invalid type. Use: all, html, chunk, viz"
            exit 1
            ;;
    esac

# === CODE QUALITY ===

# Code quality checks (lint=formatting, typecheck=type checking, security=audit, quality=all)
quality type="lint":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        "lint")
            echo "🔍 Running linting and formatting..."
            just _activate_venv && ruff check . --fix
            just _activate_venv && black .
            just _activate_venv && isort .
            cargo fmt -- --check
            cargo clippy -- -D warnings
            echo "✅ Linting complete!"
            ;;
        "lint-unsafe")
            echo "🔍 Running linting with unsafe fixes..."
            just _activate_venv && ruff check . --fix --unsafe-fixes
            just _activate_venv && black .
            just _activate_venv && isort .
            ;;
        "typecheck")
            echo "🔍 Running type checks..."
            just _activate_venv && mypy markdown_lab/
            ;;
        "security")
            echo "🔒 Running security audit..."
            cargo audit
            just _activate_venv && safety check --full-report
            ;;
        "all")
            echo "🔍 Running full code quality check..."
            just quality lint
            just quality typecheck
            just quality security
            just test all
            echo "✅ Code quality checks passed!"
            ;;
        *)
            echo "❌ Invalid type. Use: lint, lint-unsafe, typecheck, security, all"
            exit 1
            ;;
    esac

# === DEMOS & EXAMPLES ===

# Run examples and demos (demo=format conversion, hello=hello world, cli=CLI test, formats=all formats)
example type="demo":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -d ".venv" ]; then
        echo "❌ Virtual environment not found. Run 'just setup' first."
        exit 1
    fi
    
    case "{{type}}" in
        "demo")
            echo "🎭 Running format conversion demo..."
            just _activate_venv && python examples/demo_formats.py
            ;;
        "hello")
            echo "👋 Running hello world example..."
            just _activate_venv && python examples/hello.py
            ;;
        "cli")
            echo "🖥️  Testing CLI with example URL..."
            just _activate_venv && python -m markdown_lab https://httpbin.org/html -o test_output.md
            echo "✅ Output saved to test_output.md"
            ;;
        "formats")
            echo "📄 Testing all output formats..."
            OUTPUT_DIR="test_output_$(date +%Y%m%d_%H%M%S)"
            mkdir -p "$OUTPUT_DIR"
            
            echo "🔹 Testing Markdown output..."
            just _activate_venv && python -m markdown_lab https://httpbin.org -o "$OUTPUT_DIR/output.md" -f markdown
            
            echo "🔹 Testing JSON output..."
            just _activate_venv && python -m markdown_lab https://httpbin.org -o "$OUTPUT_DIR/output.json" -f json
            
            echo "🔹 Testing XML output..."
            just _activate_venv && python -m markdown_lab https://httpbin.org -o "$OUTPUT_DIR/output.xml" -f xml
            
            echo "✨ All formats tested successfully!"
            echo "📁 Output directory: $OUTPUT_DIR"
            echo "   - output.md (Markdown)"
            echo "   - output.json (JSON)"
            echo "   - output.xml (XML)"
            ;;
        *)
            echo "❌ Invalid type. Use: demo, hello, cli, formats"
            exit 1
            ;;
    esac

# === DOCUMENTATION ===

# Documentation tasks (gen=generate, help=CLI help, api=API docs, serve=start server)
docs type="gen":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        "gen")
            echo "📚 Generating project documentation..."
            just _activate_venv && python scripts/generate_flowchart.py
            echo "✅ Documentation generated!"
            ;;
        "help")
            echo "❓ Showing CLI help..."
            just _activate_venv && python -m markdown_lab --help
            ;;
        "api")
            echo "📚 Generating API documentation..."
            just _activate_venv && pdoc --html --force -o docs/api markdown_lab
            echo "✅ API documentation generated in docs/api/"
            ;;
        "serve")
            echo "🌐 Starting documentation server..."
            just _activate_venv && python -m http.server 8000 --directory docs/
            echo "📚 Documentation available at http://localhost:8000"
            ;;
        *)
            echo "❌ Invalid type. Use: gen, help, api, serve"
            exit 1
            ;;
    esac

# === PROFILING & DEBUGGING ===

# Profiling and debugging tools (memory=memory usage, cpu=CPU usage, debug=debug build, shell=debug shell, leaks=memory leaks, flamegraph=performance)
profile type="memory":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        "memory")
            echo "🧠 Profiling memory usage..."
            just _activate_venv && python -m memory_profiler examples/demo_formats.py
            ;;
        "cpu")
            echo "⏱️  Profiling CPU usage..."
            just _activate_venv && python -m cProfile -o profile.cprof examples/demo_formats.py
            echo "📊 Profile saved to profile.cprof (analyze with: snakeviz profile.cprof)"
            ;;
        "debug")
            echo "🐛 Building in debug mode..."
            just _activate_venv && RUST_LOG=debug maturin develop
            ;;
        "shell")
            echo "🐚 Starting Python debug shell..."
            just _activate_venv && python -m IPython --no-banner
            ;;
        "leaks")
            echo "🔍 Checking for memory leaks..."
            just _activate_venv && python -c "from markdown_lab import markdown_lab_rs; markdown_lab_rs.test_leaks()"
            ;;
        "flamegraph")
            echo "🔥 Generating flamegraph..."
            cargo flamegraph --example demo_formats --features=flamegraph
            echo "📊 Flamegraph saved to flamegraph.svg"
            ;;
        *)
            echo "❌ Invalid type. Use: memory, cpu, debug, shell, leaks, flamegraph"
            exit 1
            ;;
    esac

# === RELEASE & DEPLOYMENT ===

# Build wheels (std=standard, js=with JavaScript support)
wheel type="std":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        "std")
            echo "📦 Building standard wheel..."
            just _activate_venv && maturin build --release
            echo "✅ Wheel built in target/wheels/"
            ;;
        "js")
            echo "📦 Building wheel with JavaScript support..."
            just _activate_venv && maturin build --release --features real_rendering
            echo "✅ JavaScript-enabled wheel built in target/wheels/"
            ;;
        *)
            echo "❌ Invalid type. Use: std, js"
            exit 1
            ;;
    esac

# Prepare for release
release-prep: clean
    @echo "🎯 Preparing for release..."
    @just quality all
    @just bench all
    @echo "✅ All checks passed! Ready for release."

# Create release build
release: clean
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Creating release build..."
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "❌ Error: Uncommitted changes detected. Please commit or stash them first."
        exit 1
    fi
    
    # Get version from Cargo.toml
    VERSION=$(grep -m 1 '^version =' Cargo.toml | cut -d '\"' -f 2)
    echo "📦 Preparing release v$VERSION"
    
    # Run full test suite
    echo "\n🧪 Running test suite..."
    just test
    
    # Run benchmarks
    echo "\n⚡ Running benchmarks..."
    just bench
    
    # Build optimized wheels
    echo "\n🔨 Building wheels..."
    just build-wheel
    just build-wheel-js
    
    # Create release commit and tag
    echo "\n🏷️  Creating release tag v$VERSION..."
    git tag -a "v$VERSION" -m "Release v$VERSION"
    
    echo "\n✅ Release v$VERSION is ready!"
    echo "📦 Wheels are in target/wheels/"
    echo "🏷️  Tag v$VERSION has been created"
    echo "\nNext steps:"
    echo "1. Review changes: git log --oneline -n 5"
    echo "2. Push the tag: git push origin v$VERSION"
    echo "3. Create a release on GitHub"

# === UTILITIES ===

# Show project status
status:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Colors for output
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
    
    echo -e "${YELLOW}📊 Markdown Lab Project Status${NC}"
    echo -e "${YELLOW}==============================${NC}"
    
    # Git status
    echo -e "\n${GREEN}🔀 Git Status:${NC}"
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git status --short
        echo -e "\n${GREEN}📡 Remote Branches:${NC}"
        git branch -r | head -5
        [ $(git branch -r | wc -l) -gt 5 ] && echo "... and more"
    else
        echo "Not a git repository"
    fi
    
    # Python environment
    echo -e "\n${GREEN}🐍 Python Environment:${NC}"
    if [ -d ".venv" ]; then
        source .venv/bin/activate && python --version
        echo -e "\n${GREEN}📦 Installed Packages:${NC}"
        source .venv/bin/activate && pip list | grep -E "(markdown-lab|pytest|requests|beautifulsoup4|pyo3|maturin|ruff|black|isort|mypy)" | sort
    else
        echo -e "${RED}❌ Virtual environment not found. Run 'just setup' first.${NC}"
    fi
    
    # Rust environment
    echo -e "\n${GREEN}🦀 Rust Environment:${NC}"
    if command -v rustc &> /dev/null; then
        rustc --version
        cargo --version
        echo -e "\n${GREEN}🔧 Rust Toolchain:${NC}"
        rustup show active-toolchain
    else
        echo -e "${RED}❌ Rust not found. Please install Rust first.${NC}"
    fi
    
    # Project structure
    echo -e "\n${GREEN}📁 Project Structure:${NC}"
    find . -maxdepth 2 -type d | sort | sed -e 's/[^-][^\/]*\//  |/g' -e 's/| \[/[/g'
    
    # Quick test
    echo -e "\n${GREEN}🧪 Quick Test:${NC}"
    if [ -d ".venv" ]; then
        if source .venv/bin/activate && python -c "import markdown_lab.markdown_lab_rs; print('✅ Rust bindings working')"; then
            echo -e "${GREEN}✅ Basic imports working${NC}"
        else
            echo -e "${RED}❌ Error importing module${NC}"
        fi
    fi
    
    echo -e "\n${GREEN}🚀 Next Steps:${NC}"
    echo "- Run 'just dev' to start development mode"
    echo "- Run 'just test' to run all tests"
    echo "- Run 'just docs-serve' to view documentation"


# === WORKFLOW SHORTCUTS ===

# Quick development cycle: build + test bindings
dev-cycle:
    @just build dev
    @just test bindings

# Full development cycle: build + quality + test
full-cycle:
    @just build dev
    @just quality lint
    @just test all

# CI simulation: complete pipeline
ci: clean setup
    @just quality all
    @just test all
    @echo "✅ CI pipeline simulation complete!"

# Performance check: optimized build + benchmarks
perf:
    @just build release
    @just bench all

# === TROUBLESHOOTING ===

# Fix common issues
fix:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🔧 Fixing common issues..."
    
    # Clear Python cache
    echo "🧹 Clearing Python cache..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.py[co]" -delete 2>/dev/null || true
    
    # Rebuild Rust components
    echo "🔨 Rebuilding Rust components..."
    cargo clean 2>/dev/null || true
    
    if [ -d ".venv" ]; then
        source .venv/bin/activate && maturin develop
    else
        echo "⚠️  Virtual environment not found. Run 'just setup' first."
    fi
    
    # Clear caches
    echo "🧹 Clearing caches..."
    rm -rf .pytest_cache/ .mypy_cache/ .request_cache/ 2>/dev/null || true
    
    # Update dependencies
    echo "⬆️  Updating dependencies..."
    uv sync 2>/dev/null || echo "⚠️  Failed to update dependencies"
    
    echo "✅ Common issues fixed!"
    echo "\nIf you're still experiencing issues, try:"
    echo "1. Delete .venv/ and run 'just setup'"
    echo "2. Run 'cargo clean' and rebuild"
    echo "3. Check for system updates"

# Check environment
check-env:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Colors
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
    
    echo -e "${YELLOW}🔍 Environment Check${NC}"
    echo -e "${YELLOW}==================${NC}"
    
    # Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"
    else
        echo -e "${RED}❌ Python not found${NC}"
    fi
    
    # Rust
    if command -v rustc &> /dev/null; then
        RUST_VERSION=$(rustc --version 2>&1)
        echo -e "${GREEN}✅ Rust: $RUST_VERSION${NC}"
        echo -e "${GREEN}   Cargo: $(cargo --version 2>&1)${NC}"
    else
        echo -e "${RED}❌ Rust not found${NC}"
    fi
    
    # UV
    if command -v uv &> /dev/null; then
        echo -e "${GREEN}✅ UV: $(uv --version)${NC}"
    else
        echo -e "${YELLOW}⚠️  UV not found (optional, but recommended)${NC}"
    fi
    
    # Virtual Environment
    if [ -d ".venv" ]; then
        echo -e "${GREEN}✅ Virtual environment: .venv/ exists${NC}"
        if [ -n "${VIRTUAL_ENV:-}" ]; then
            echo -e "   ${GREEN}Active: $VIRTUAL_ENV${NC}"
        else
            echo -e "   ${YELLOW}Not activated. Run 'source .venv/bin/activate'${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Virtual environment not found. Run 'just setup'${NC}"
    fi
    
    # Check for required tools
    echo -e "\n${YELLOW}🔧 Required Tools:${NC}"
    for cmd in git curl make; do
        if command -v "$cmd" &> /dev/null; then
            echo -e "${GREEN}✅ $cmd: $(which $cmd)${NC}"
        else
            echo -e "${RED}❌ $cmd not found${NC}"
        fi
    done
    
    # Disk space
    echo -e "\n${YELLOW}💾 Disk Space:${NC}"
    df -h . | awk 'NR==1{print $0} NR>1{print $0 | "sort -k5 -h -r"}'
    
    echo -e "\n${YELLOW}🚀 Next Steps:${NC}"
    echo "- Run 'just setup' to set up the development environment"
    echo "- Run 'just status' for project status"
    echo "- Run 'just test' to run tests"

# === ADVANCED WORKFLOWS ===

# End-to-end test with real website
e2e url="https://httpbin.org/html":
    #!/usr/bin/env bash
    echo "🌐 Running end-to-end test with {{url}}"
    just _activate_venv
    python -m markdown_lab "{{url}}" -o e2e_test.md -f markdown
    python -m markdown_lab "{{url}}" -o e2e_test.json -f json
    python -m markdown_lab "{{url}}" -o e2e_test.xml -f xml
    python -m markdown_lab "{{url}}" -o e2e_test_chunked.md --save-chunks --chunk-dir e2e_chunks
    echo "✅ End-to-end test complete! Generated: e2e_test.{md,json,xml} and e2e_chunks/"

# Load test with multiple URLs
load-test:
    #!/usr/bin/env bash
    echo "⚡ Running load test..."
    just _activate_venv
    echo -e 'https://httpbin.org/html\nhttps://httpbin.org/json\nhttps://httpbin.org/xml' > test_urls.txt
    python -m markdown_lab --links-file test_urls.txt -o load_test_output --parallel --max-workers 3
    echo "✅ Load test complete! Check load_test_output/"
    rm test_urls.txt

# === MAINTENANCE ===

# Maintenance tasks (clean-tests=remove test files, archive=create backup, update=update deps, hooks=install pre-commit)
maintain type="clean-tests":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        "clean-tests")
            echo "🧹 Cleaning up test files..."
            rm -f test_output.* e2e_test.* test_urls.txt
            rm -rf e2e_chunks/ load_test_output/
            ;;
        "archive")
            timestamp=$(date +%Y%m%d_%H%M%S)
            echo "📦 Creating project archive: markdown_lab_${timestamp}.tar.gz"
            tar -czf "markdown_lab_${timestamp}.tar.gz" \
                --exclude='target' --exclude='.venv' --exclude='__pycache__' \
                --exclude='.pytest_cache' --exclude='.request_cache' \
                --exclude='*.pyc' --exclude='.git' .
            echo "✅ Archive created: markdown_lab_${timestamp}.tar.gz"
            ;;
        "update")
            echo "📦 Updating dependencies..."
            uv sync --upgrade
            cargo update
            ;;
        "hooks")
            echo "🪝 Installing pre-commit hooks..."
            just _activate_venv && pre-commit install
            ;;
        *)
            echo "❌ Invalid type. Use: clean-tests, archive, update, hooks"
            exit 1
            ;;
    esac