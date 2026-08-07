#!/usr/bin/env bash
#
# setup.sh - Initialize development environment
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

cd "${PROJECT_ROOT}"

info "Setting up Climber Agent Engine development environment..."

# Check Python version
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    info "Python version: ${PYTHON_VERSION}"
else
    error "Python 3.11+ is required but not found"
    exit 1
fi

# Check Node.js version
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    info "Node.js version: ${NODE_VERSION}"
else
    warn "Node.js not found. Frontend development will not be available."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    info "Creating Python virtual environment..."
    python3 -m venv venv
    success "Virtual environment created"
else
    info "Virtual environment already exists"
fi

# Activate virtual environment
info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
info "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
info "Installing Python dependencies..."
pip install -r requirements.txt

# Install development dependencies if file exists
if [ -f "requirements-dev.txt" ]; then
    info "Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Setup frontend if Node.js is available
if command -v node &>/dev/null && [ -d "frontend-react" ]; then
    info "Setting up frontend..."
    cd frontend-react
    npm install
    cd ..
    success "Frontend dependencies installed"
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        info "Creating .env from .env.example..."
        cp .env.example .env
        warn "Please edit .env with your API keys and configuration"
    fi
else
    info ".env file already exists"
fi

# Setup pre-commit hooks if pre-commit is available
if command -v pre-commit &>/dev/null; then
    info "Setting up pre-commit hooks..."
    pre-commit install
    success "Pre-commit hooks installed"
fi

# Run database migrations if alembic is available
if command -v alembic &>/dev/null; then
    info "Running database migrations..."
    alembic upgrade head || warn "Migration failed - check your database configuration"
fi

success "Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run ./scripts/dev.sh to start development servers"
echo "  3. Run ./scripts/check.sh to verify everything works"
