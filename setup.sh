#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-shot dev environment setup for documents-rag
#
# Apps covered:
#   • documents app  (api_gateway + workers + rag_service + postgres + kafka + minio + es)
#   • search app     (search_ui)
#   • agents app     (agent_service + agent_ui)
#
# Usage:
#   ./setup.sh              # full setup (all apps)
#   ./setup.sh --app docs   # documents app only
#   ./setup.sh --app search # search app only
#   ./setup.sh --app agents # agents app only
#   ./setup.sh --local      # install Python venvs locally (no Docker)
#   ./setup.sh --help       # show this help
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

log()     { echo -e "${CYAN}▶ $*${RESET}"; }
success() { echo -e "${GREEN}✓ $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $*${RESET}"; }
error()   { echo -e "${RED}✗ $*${RESET}" >&2; exit 1; }
header()  { echo -e "\n${BOLD}════════════════════════════════════════${RESET}"; \
            echo -e "${BOLD}  $*${RESET}"; \
            echo -e "${BOLD}════════════════════════════════════════${RESET}"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Defaults ─────────────────────────────────────────────────────────────────
APP="all"       # all | docs | search | agents
LOCAL=false     # install local Python venvs instead of just Docker

# ── Arg parsing ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --app)    APP="${2:-all}"; shift 2 ;;
    --local)  LOCAL=true; shift ;;
    --help|-h)
      sed -n '/^# Usage/,/^# ====/p' "$0" | grep -v "^# ====" | sed 's/^# //'
      exit 0 ;;
    *) error "Unknown argument: $1. Run ./setup.sh --help for usage." ;;
  esac
done

# ── Prerequisite checks ───────────────────────────────────────────────────────
header "Checking prerequisites"

check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    error "'$1' is required but not installed. $2"
  fi
  success "$1 found ($(command -v "$1"))"
}

check_cmd docker  "Install from https://docs.docker.com/get-docker/"
check_cmd docker  # also verify compose plugin
if ! docker compose version &>/dev/null; then
  error "Docker Compose v2 plugin is required. Run: docker compose version"
fi
success "docker compose v2 found"

if [[ "$LOCAL" == true ]]; then
  check_cmd python3 "Install Python 3.11+ from https://python.org"
  PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
  PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
  if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 11 ) ]]; then
    error "Python 3.11+ required, found $PY_VERSION"
  fi
  success "python3 $PY_VERSION"
fi

# ── .env setup ───────────────────────────────────────────────────────────────
header "Environment file"

ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ ! -f "$ENV_EXAMPLE" ]]; then
    error ".env.example not found in repo root."
  fi
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  success "Created .env from .env.example"
  warn "Review $ENV_FILE and fill in secrets before starting services."
  warn "  Required for AWS Bedrock: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
  warn "  For local Ollama instead: set LLM_PROVIDER=ollama, COMPOSE_PROFILES=ollama"
else
  success ".env already exists — skipping copy"
fi

# Helper: check a key has a non-empty value in .env
check_env_key() {
  local key="$1"
  local val
  val=$(grep -E "^${key}=" "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d "'")
  if [[ -z "$val" ]]; then
    warn "$key is not set in .env"
    return 1
  fi
  return 0
}

# Validate provider-specific required keys
LLM_PROVIDER=$(grep -E "^LLM_PROVIDER=" "$ENV_FILE" | cut -d= -f2 | tr -d '"' || echo "bedrock")
if [[ "$LLM_PROVIDER" == "bedrock" ]]; then
  check_env_key "AWS_ACCESS_KEY_ID"  || warn "  → Bedrock calls will fail without AWS credentials."
  check_env_key "AWS_SECRET_ACCESS_KEY" || true
else
  success "LLM_PROVIDER=$LLM_PROVIDER — skipping AWS credential check"
fi

check_env_key "JWT_SECRET_KEY" || warn "  → Using default JWT secret — change before deploying!"

# ── Local venv setup (optional --local mode) ─────────────────────────────────
setup_venv() {
  local name="$1"
  local dir="$2"
  log "Setting up venv for $name ($dir)"
  if [[ ! -d "$dir/.venv" ]]; then
    python3 -m venv "$dir/.venv"
  fi
  # shellcheck disable=SC1091
  source "$dir/.venv/bin/activate"
  pip install --quiet --upgrade pip
  pip install --quiet -r "$dir/requirements.txt"
  deactivate
  success "$name venv ready → $dir/.venv"
}

if [[ "$LOCAL" == true ]]; then
  header "Installing local Python environments"

  [[ "$APP" == "all" || "$APP" == "docs" ]] && {
    setup_venv "api_gateway"  "$REPO_ROOT/backend/api_gateway"
    setup_venv "rag_service"  "$REPO_ROOT/backend/rag_service"
    setup_venv "workers"      "$REPO_ROOT/backend/workers"
  }
  [[ "$APP" == "all" || "$APP" == "search" ]] && {
    setup_venv "search_ui"    "$REPO_ROOT/backend/search_ui"
  }
  [[ "$APP" == "all" || "$APP" == "agents" ]] && {
    setup_venv "agent_service" "$REPO_ROOT/backend/agent_service"
    setup_venv "agent_ui"      "$REPO_ROOT/backend/agent_ui"
  }
fi

# ── Docker images ─────────────────────────────────────────────────────────────
header "Building Docker images"

# Determine which services to build per app selection
SERVICES=()
case "$APP" in
  docs)
    SERVICES=(api_gateway worker_text_extraction worker_chunking worker_embedding worker_summarization rag_service frontend)
    ;;
  search)
    SERVICES=(search_ui)
    ;;
  agents)
    SERVICES=(agent_service agent_ui)
    ;;
  all)
    SERVICES=()  # build everything
    ;;
esac

cd "$REPO_ROOT"
if [[ ${#SERVICES[@]} -eq 0 ]]; then
  log "Building all services..."
  docker compose build
else
  log "Building: ${SERVICES[*]}"
  docker compose build "${SERVICES[@]}"
fi
success "Images built"

# ── Start infrastructure ───────────────────────────────────────────────────────
header "Starting services"

# Infrastructure is always needed
INFRA_SERVICES=(postgres zookeeper kafka kafka-init minio minio-init elasticsearch)

# App-specific services
APP_SERVICES=()
case "$APP" in
  docs)
    APP_SERVICES=(api_gateway worker_text_extraction worker_chunking worker_embedding worker_summarization worker_compliance rag_service frontend nginx)
    ;;
  search)
    APP_SERVICES=(api_gateway rag_service search_ui nginx)
    ;;
  agents)
    APP_SERVICES=(api_gateway rag_service agent_service agent_ui nginx)
    ;;
  all)
    APP_SERVICES=()  # docker compose up with no args starts everything
    ;;
esac

# Check if Ollama profile is needed
COMPOSE_PROFILES=$(grep -E "^COMPOSE_PROFILES=" "$ENV_FILE" | cut -d= -f2 | tr -d '"' || echo "")
COMPOSE_ARGS=()
[[ -n "$COMPOSE_PROFILES" ]] && COMPOSE_ARGS+=(--profile "$COMPOSE_PROFILES")

if [[ ${#APP_SERVICES[@]} -eq 0 ]]; then
  log "Starting all services..."
  docker compose ${COMPOSE_ARGS[@]+"${COMPOSE_ARGS[@]}"} up -d
else
  log "Starting: ${INFRA_SERVICES[*]} ${APP_SERVICES[*]}"
  docker compose ${COMPOSE_ARGS[@]+"${COMPOSE_ARGS[@]}"} up -d "${INFRA_SERVICES[@]}" "${APP_SERVICES[@]}"
fi

# ── Wait for core services to be healthy ─────────────────────────────────────
header "Waiting for health checks"

wait_healthy() {
  local service="$1"
  local max_wait="${2:-60}"
  local elapsed=0
  local interval=5

  # Check if the service is actually running (some may not be selected)
  if ! docker compose ps --services --status running 2>/dev/null | grep -q "^${service}$"; then
    return 0
  fi

  log "Waiting for $service to be healthy..."
  while [[ $elapsed -lt $max_wait ]]; do
    status=$(docker compose ps "$service" --format json 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
    if [[ "$status" == "healthy" ]]; then
      success "$service is healthy"
      return 0
    fi
    sleep $interval
    elapsed=$((elapsed + interval))
  done
  warn "$service did not become healthy within ${max_wait}s — check: docker compose logs $service"
}

wait_healthy postgres         60
wait_healthy kafka            90
wait_healthy minio            60
wait_healthy elasticsearch    120

[[ "$APP" == "all" || "$APP" == "docs" || "$APP" == "search" || "$APP" == "agents" ]] && \
  wait_healthy api_gateway    60

[[ "$APP" == "all" || "$APP" == "search" || "$APP" == "agents" ]] && \
  wait_healthy rag_service    60

[[ "$APP" == "all" || "$APP" == "agents" ]] && \
  wait_healthy agent_service  60

# ── Seed default users & compliance rules ─────────────────────────────────────
# Only needed when api_gateway is part of the selected app set.
# The seed script is idempotent — safe to run on every setup.
if [[ "$APP" == "all" || "$APP" == "docs" || "$APP" == "search" || "$APP" == "agents" ]]; then
  header "Seeding default users & compliance rules"

  # Wait until api_gateway has finished its own startup (migrations + MinIO init)
  log "Running api_gateway seed (admin users + compliance rules)..."
  if docker compose exec -T api_gateway python seed.py; then
    success "Default users ready"
    echo -e "  ${GREEN}admin@example.com${RESET}  / changeme  (primary user)"
    echo -e "  ${GREEN}admin1@example.com${RESET} / changeme  (service account)"
  else
    warn "api_gateway seed failed — run manually: docker compose exec api_gateway python seed.py"
  fi

  # Seed synthetic Forge SaaS documents (idempotent — skips existing [seed] docs)
  log "Seeding synthetic Forge SaaS documents (scenarios A + B)..."
  if docker compose exec -T api_gateway python /scripts/seed_data.py \
      --base-url http://nginx:80 --wait; then
    success "Forge seed documents ready"
  else
    warn "Document seed failed — run manually: make seed-data"
  fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
header "Setup complete 🎉"

echo ""
echo -e "${BOLD}Services running:${RESET}"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps

echo ""
echo -e "${BOLD}Access points:${RESET}"
echo -e "  ${GREEN}Search UI${RESET}    →  http://localhost:8081/search"
echo -e "  ${GREEN}Ingest UI${RESET}    →  http://localhost:8081/ingest"
echo -e "  ${GREEN}Agent UI${RESET}     →  http://localhost:8081/agents"
echo -e "  ${GREEN}API${RESET}          →  http://localhost:8081/api"
echo -e "  ${GREEN}MinIO Console${RESET}→  http://localhost:9091"
echo -e "  ${GREEN}Kafka UI${RESET}     →  http://localhost:8082"

echo ""
echo -e "${BOLD}Useful commands:${RESET}"
echo -e "  make sanity                 # run end-to-end sanity check"
echo -e "  make seed-data              # re-seed Forge test documents"
echo -e "  make logs svc=api_gateway   # tail logs for a service"
echo -e "  make shell-api              # shell into api_gateway"
echo -e "  make shell-db               # psql into postgres"
echo -e "  make down                   # stop everything"
echo -e "  make clean                  # nuke containers + volumes"

echo ""
if [[ "$LLM_PROVIDER" == "bedrock" ]]; then
  warn "LLM_PROVIDER=bedrock — make sure AWS credentials are set in .env before running agents"
fi
