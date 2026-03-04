#!/usr/bin/env bash
# ============================================================
# Kinfolk — Developer Install Script
# ============================================================
# Sets up Kinfolk on Ubuntu 24.04 (ARM64 or x86-64).
#
# Usage:
#   bash install.sh                  # Interactive — asks Docker vs bare-metal
#   bash install.sh --docker         # Docker mode (backend in containers)
#   bash install.sh --bare-metal     # Bare-metal mode (everything native)
#   bash install.sh --check          # Verify dependencies without installing
#
# Both Docker and bare-metal are first-class install paths.
# Flutter always runs natively (not containerised).
# ============================================================

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Globals ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE=""
CHECK_ONLY=false
ERRORS=0

# ── Helpers ──────────────────────────────────────────────────

info() { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail() {
	echo -e "${RED}[FAIL]${NC}  $*"
	ERRORS=$((ERRORS + 1))
}

check_cmd() {
	if command -v "$1" &>/dev/null; then
		ok "$1 found: $(command -v "$1")"
		return 0
	else
		fail "$1 not found"
		return 1
	fi
}

check_python_version() {
	local py_cmd="${1:-python3}"
	if ! command -v "$py_cmd" &>/dev/null; then
		fail "Python 3 not found"
		return 1
	fi
	local version
	version=$("$py_cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
	local major minor
	major=$(echo "$version" | cut -d. -f1)
	minor=$(echo "$version" | cut -d. -f2)
	if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 11 ]]; then
		ok "Python $version (>= 3.11)"
		return 0
	else
		fail "Python $version found — need >= 3.11"
		return 1
	fi
}

# ── Parse Arguments ──────────────────────────────────────────

while [[ $# -gt 0 ]]; do
	case "$1" in
	--docker)
		MODE="docker"
		shift
		;;
	--bare-metal)
		MODE="bare-metal"
		shift
		;;
	--check)
		CHECK_ONLY=true
		shift
		;;
	-h | --help)
		echo "Usage: bash install.sh [--docker|--bare-metal] [--check]"
		echo ""
		echo "Options:"
		echo "  --docker       Backend services in Docker containers"
		echo "  --bare-metal   Everything installed natively"
		echo "  --check        Verify dependencies without installing"
		echo "  -h, --help     Show this help message"
		exit 0
		;;
	*)
		echo "Unknown option: $1"
		echo "Run 'bash install.sh --help' for usage."
		exit 1
		;;
	esac
done

# ── Banner ───────────────────────────────────────────────────

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║          Kinfolk — Developer Setup               ║${NC}"
echo -e "${BOLD}║   Privacy-first smart display for families       ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Mode Selection ───────────────────────────────────────────

if [[ -z "$MODE" ]] && [[ "$CHECK_ONLY" == false ]]; then
	echo -e "${BOLD}Choose an install mode:${NC}"
	echo ""
	echo "  1) Docker       — Backend services run in containers."
	echo "                    Requires: Docker, Docker Compose"
	echo ""
	echo "  2) Bare-metal   — Everything installed natively."
	echo "                    Requires: Python 3.11+, system packages"
	echo ""
	echo "  Both modes run Flutter natively on the host."
	echo ""
	read -rp "  Enter choice [1/2]: " choice
	case "$choice" in
	1) MODE="docker" ;;
	2) MODE="bare-metal" ;;
	*)
		echo "Invalid choice. Defaulting to Docker."
		MODE="docker"
		;;
	esac
	echo ""
fi

# ── Dependency Check ─────────────────────────────────────────

echo -e "${BOLD}── Checking Dependencies ──────────────────────────${NC}"
echo ""

# Common dependencies (both modes)
check_cmd git
check_cmd curl

# Flutter (always native)
if command -v flutter &>/dev/null; then
	ok "Flutter found: $(flutter --version 2>/dev/null | head -1)"
else
	warn "Flutter not found — needed to run the frontend"
	info "Install: https://docs.flutter.dev/get-started/install/linux"
fi

# Flutter system deps (ninja is 'ninja-build' on Ubuntu, 'ninja' on Arch)
for pkg in cmake clang pkg-config; do
	check_cmd "$pkg" || true
done
if command -v ninja &>/dev/null || command -v ninja-build &>/dev/null; then
	ok "ninja found"
else
	fail "ninja not found (package: ninja-build on Ubuntu)"
fi

if [[ "$MODE" == "docker" ]] || [[ "$CHECK_ONLY" == true ]]; then
	echo ""
	echo -e "${BOLD}── Docker Dependencies ────────────────────────────${NC}"
	echo ""
	check_cmd docker
	if command -v docker &>/dev/null; then
		if docker compose version &>/dev/null; then
			ok "Docker Compose plugin found"
		elif command -v docker-compose &>/dev/null; then
			ok "docker-compose (standalone) found"
		else
			fail "Docker Compose not found"
		fi
	fi
fi

if [[ "$MODE" == "bare-metal" ]] || [[ "$CHECK_ONLY" == true ]]; then
	echo ""
	echo -e "${BOLD}── Bare-Metal Dependencies ────────────────────────${NC}"
	echo ""
	check_python_version
	check_cmd pip3 || check_cmd pip || true

	# System libraries
	info "Checking system libraries..."
	for lib in libsqlcipher-dev portaudio19-dev ffmpeg libgtk-3-dev; do
		if dpkg -s "$lib" &>/dev/null 2>&1; then
			ok "$lib installed"
		else
			warn "$lib not installed"
			info "  Install with: sudo apt install $lib"
		fi
	done
fi

echo ""

# ── Check-Only Exit ──────────────────────────────────────────

if [[ "$CHECK_ONLY" == true ]]; then
	echo -e "${BOLD}── Summary ────────────────────────────────────────${NC}"
	echo ""
	if [[ $ERRORS -gt 0 ]]; then
		fail "$ERRORS required dependency/dependencies missing."
		echo ""
		echo "  Fix the issues above, then re-run:"
		echo "    bash install.sh --check"
	else
		ok "All dependencies satisfied."
		echo ""
		echo "  Ready to install. Run one of:"
		echo "    bash install.sh --docker"
		echo "    bash install.sh --bare-metal"
	fi
	echo ""
	exit $ERRORS
fi

# ── .env Setup ───────────────────────────────────────────────

echo -e "${BOLD}── Environment Configuration ──────────────────────${NC}"
echo ""

if [[ -f "$SCRIPT_DIR/.env" ]]; then
	ok ".env file already exists"
	read -rp "  Overwrite with fresh config? [y/N]: " overwrite
	if [[ "$overwrite" =~ ^[Yy]$ ]]; then
		cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
		info "Copied .env.example → .env"
	fi
else
	cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
	ok "Created .env from .env.example"
fi

# Run first-run wizard
if command -v python3 &>/dev/null; then
	echo ""
	read -rp "  Run the configuration wizard now? [Y/n]: " run_wizard
	if [[ ! "$run_wizard" =~ ^[Nn]$ ]]; then
		python3 "$SCRIPT_DIR/scripts/first_run.py" --env-file .env
	fi
else
	warn "Python 3 not available — skipping configuration wizard."
	info "Run it later: python3 scripts/first_run.py"
fi

# ── Create Data Directories ─────────────────────────────────

echo ""
echo -e "${BOLD}── Data Directories ───────────────────────────────${NC}"
echo ""

mkdir -p "$SCRIPT_DIR/data/photos" "$SCRIPT_DIR/data/music" "$SCRIPT_DIR/data/models"
mkdir -p "$SCRIPT_DIR/docker/rhasspy/models"
ok "Created data/{photos,music,models} and docker/rhasspy/models"

# ══════════════════════════════════════════════════════════════
# Docker Mode
# ══════════════════════════════════════════════════════════════

if [[ "$MODE" == "docker" ]]; then
	echo ""
	echo -e "${BOLD}── Docker Setup ───────────────────────────────────${NC}"
	echo ""

	# Validate compose file
	info "Validating docker-compose.yml..."
	if docker compose -f "$SCRIPT_DIR/docker-compose.yml" config --quiet 2>/dev/null; then
		ok "docker-compose.yml is valid"
	elif docker-compose -f "$SCRIPT_DIR/docker-compose.yml" config --quiet 2>/dev/null; then
		ok "docker-compose.yml is valid (standalone)"
	else
		fail "docker-compose.yml validation failed"
	fi

	# Pull images
	info "Pulling Docker images (this may take a few minutes)..."
	if docker compose -f "$SCRIPT_DIR/docker-compose.yml" pull 2>/dev/null; then
		ok "Images pulled"
	elif docker-compose -f "$SCRIPT_DIR/docker-compose.yml" pull 2>/dev/null; then
		ok "Images pulled (standalone)"
	else
		warn "Could not pull all images — they will be built/pulled on first start"
	fi

	# Build backend image
	info "Building backend image..."
	if docker compose -f "$SCRIPT_DIR/docker-compose.yml" build backend 2>/dev/null; then
		ok "Backend image built"
	elif docker-compose -f "$SCRIPT_DIR/docker-compose.yml" build backend 2>/dev/null; then
		ok "Backend image built (standalone)"
	else
		fail "Backend image build failed"
	fi

	# Start services
	echo ""
	read -rp "  Start services now? [Y/n]: " start_now
	if [[ ! "$start_now" =~ ^[Nn]$ ]]; then
		info "Starting services..."
		if docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d 2>/dev/null; then
			ok "Services started"
		elif docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d 2>/dev/null; then
			ok "Services started (standalone)"
		else
			fail "Failed to start services"
		fi
	fi
fi

# ══════════════════════════════════════════════════════════════
# Bare-Metal Mode
# ══════════════════════════════════════════════════════════════

if [[ "$MODE" == "bare-metal" ]]; then
	echo ""
	echo -e "${BOLD}── System Dependencies ────────────────────────────${NC}"
	echo ""

	info "Installing system packages (may require sudo)..."
	PACKAGES=(
		libsqlcipher-dev
		portaudio19-dev
		ffmpeg
		libgtk-3-dev
		clang
		cmake
		ninja-build
		pkg-config
		python3-venv
		python3-pip
		curl
	)

	if sudo apt-get update -qq && sudo apt-get install -y -qq "${PACKAGES[@]}"; then
		ok "System packages installed"
	else
		fail "Some system packages failed to install"
		info "Try manually: sudo apt install ${PACKAGES[*]}"
	fi

	# ── Python Virtual Environment ───────────────────────────
	echo ""
	echo -e "${BOLD}── Python Backend ─────────────────────────────────${NC}"
	echo ""

	VENV_DIR="$SCRIPT_DIR/backend/.venv"

	if [[ -d "$VENV_DIR" ]]; then
		ok "Virtual environment exists at backend/.venv"
	else
		info "Creating virtual environment..."
		python3 -m venv "$VENV_DIR"
		ok "Created backend/.venv"
	fi

	info "Installing Python dependencies..."
	"$VENV_DIR/bin/pip" install --upgrade pip -q
	"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/backend/requirements.txt" -q
	ok "Python dependencies installed"

	# ── Start Backend ────────────────────────────────────────
	echo ""
	read -rp "  Start the backend server now? [Y/n]: " start_backend
	if [[ ! "$start_backend" =~ ^[Nn]$ ]]; then
		info "Starting backend (uvicorn)..."
		cd "$SCRIPT_DIR/backend"
		"$VENV_DIR/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8080 &
		BACKEND_PID=$!
		cd "$SCRIPT_DIR"
		sleep 3
		ok "Backend started (PID: $BACKEND_PID)"
	fi
fi

# ── Flutter Frontend ─────────────────────────────────────────

echo ""
echo -e "${BOLD}── Flutter Frontend ───────────────────────────────${NC}"
echo ""

if command -v flutter &>/dev/null; then
	info "Installing Flutter dependencies..."
	(cd "$SCRIPT_DIR/frontend" && flutter pub get -q 2>/dev/null) &&
		ok "Flutter dependencies installed" ||
		warn "Flutter pub get had warnings (may still work)"
else
	warn "Flutter not found — install it to run the frontend"
	info "  https://docs.flutter.dev/get-started/install/linux"
fi

# ── Health Check ─────────────────────────────────────────────

echo ""
echo -e "${BOLD}── Health Check ───────────────────────────────────${NC}"
echo ""

info "Waiting for backend to be ready..."
HEALTH_OK=false
for i in $(seq 1 10); do
	if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
		HEALTH_OK=true
		break
	fi
	sleep 2
done

if [[ "$HEALTH_OK" == true ]]; then
	ok "Backend is healthy: http://localhost:8080/health"
else
	warn "Backend health check did not pass (may still be starting)"
	info "  Check manually: curl http://localhost:8080/health"
fi

# ── Summary ──────────────────────────────────────────────────

echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Kinfolk Setup Complete${NC}"
echo -e "${BOLD}══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Mode:     $MODE"
echo "  Config:   .env"
echo "  Backend:  http://localhost:8080"
echo "  API docs: http://localhost:8080/docs"
echo ""

if [[ "$MODE" == "docker" ]]; then
	echo "  Docker commands:"
	echo "    docker compose up -d        # Start services"
	echo "    docker compose logs -f      # View logs"
	echo "    docker compose down         # Stop services"
	echo ""
fi

echo "  Flutter frontend:"
echo "    cd frontend && flutter run -d linux"
echo ""
echo "  Re-run configuration wizard:"
echo "    python3 scripts/first_run.py"
echo ""

if [[ $ERRORS -gt 0 ]]; then
	warn "$ERRORS issue(s) encountered during setup. Review the output above."
	exit 1
fi

ok "All done. Enjoy Kinfolk!"
echo ""
