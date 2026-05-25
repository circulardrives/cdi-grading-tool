#!/usr/bin/env bash
# Install or upgrade CDI Health host tooling on Debian/Ubuntu grading hosts.
#
# The cdi-health .deb declares Depends on smartmontools and nvme-cli and
# Recommends openseachest; `sudo apt install ./cdi-health_*.deb` pulls those in
# when the packages exist in configured apt sources. Run this script when you
# need extras or versions apt does not provide:
#   - OpenSeaChest on Ubuntu 22.04 / Debian Bookworm (not in default repos)
#   - Latest Seagate OpenSeaChest release (apt may lag GitHub)
#   - nvme-cli 2.10+ with OCP plugin when distro nvme-cli is older
#   - sg3-utils for SCSI/SAS benches
#   - WeasyPrint system libraries for PDF reports
#
# Usage:
#   sudo ./scripts/install-host-dependencies.sh
#   sudo ./scripts/install-host-dependencies.sh --with-sas --with-pdf
#   sudo ./scripts/install-host-dependencies.sh --latest-openseachest

set -euo pipefail

OPENSEACHEST_VERSION="${OPENSEACHEST_VERSION:-26.03.1}"
NVME_CLI_MIN_VERSION="${NVME_CLI_MIN_VERSION:-2.10}"
NVME_CLI_SOURCE_TAG="${NVME_CLI_SOURCE_TAG:-v2.16}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
WITH_SAS=0
WITH_PDF=0
FORCE_LATEST_OPENSEACHEST=0
FORCE_NVME_BUILD=0
FROM_POSTINST=0

log() { printf '==> %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: install-host-dependencies.sh [options]

Optional extras for CDI Health grading hosts (Debian/Ubuntu). Core tools
(smartmontools, nvme-cli) are normally installed automatically when you run:
  sudo apt install ./cdi-health_*.deb

Options:
  --with-sas                 Install sg3-utils for SCSI/SAS discovery
  --with-pdf                 Install WeasyPrint OS libraries (PDF reports)
  --latest-openseachest      Install OpenSeaChest from Seagate GitHub even if apt has it
  --build-nvme-cli           Build nvme-cli from source (needs OCP plugin, apt too old)
  --from-postinst            Non-interactive mode for package post-install hooks
  -h, --help                 Show this help

Environment:
  OPENSEACHEST_VERSION       Seagate release tag without leading v (default: 26.03.1)
  NVME_CLI_SOURCE_TAG        nvme-cli git tag when building from source (default: v2.16)
EOF
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "Run as root (sudo $0 ...)"
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --with-sas) WITH_SAS=1 ;;
    --with-pdf) WITH_PDF=1 ;;
    --latest-openseachest) FORCE_LATEST_OPENSEACHEST=1 ;;
    --build-nvme-cli) FORCE_NVME_BUILD=1 ;;
    --from-postinst) FROM_POSTINST=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) die "Unknown option: $1 (try --help)" ;;
    esac
    shift
  done
}

apt_update() {
  log "Refreshing apt package lists"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
}

version_ge() {
  local a="${1#v}" b="${2#v}"
  dpkg --compare-versions "$a" ge "$b"
}

install_apt_packages() {
  local pkgs=("$@")
  [[ ${#pkgs[@]} -eq 0 ]] && return 0
  log "Installing apt packages: ${pkgs[*]}"
  apt-get install -y --no-install-recommends "${pkgs[@]}"
}

install_core_apt_tools() {
  install_apt_packages smartmontools nvme-cli
}

nvme_cli_version() {
  if ! command -v nvme >/dev/null 2>&1; then
    echo "0"
    return
  fi
  nvme --version 2>/dev/null | awk '/^nvme version/ {print $3; exit} /^nvme / {print $2; exit} {print $NF; exit}' | head -1
}

install_nvme_cli_from_source() {
  log "Building nvme-cli ${NVME_CLI_SOURCE_TAG} from source (OCP plugin enabled)"
  local build_root
  build_root="$(mktemp -d /tmp/cdi-nvme-cli.XXXXXX)"
  trap 'rm -rf "$build_root"' RETURN

  install_apt_packages \
    build-essential meson ninja-build pkg-config git \
    libjson-c-dev libssl-dev libkeyutils-dev libkmod-dev

  git clone --depth 1 --branch "${NVME_CLI_SOURCE_TAG}" \
    https://github.com/linux-nvme/nvme-cli.git "${build_root}/nvme-cli"
  meson setup "${build_root}/nvme-cli/.build" "${build_root}/nvme-cli" -Dplugins=all
  meson compile -C "${build_root}/nvme-cli/.build"
  meson install -C "${build_root}/nvme-cli/.build"
  ldconfig || true
}

ensure_nvme_cli() {
  local current
  current="$(nvme_cli_version || true)"
  if [[ -n "$current" ]] && version_ge "$current" "$NVME_CLI_MIN_VERSION" && [[ "$FORCE_NVME_BUILD" -eq 0 ]]; then
    log "nvme-cli ${current} already satisfies minimum ${NVME_CLI_MIN_VERSION}"
    return
  fi

  install_core_apt_tools
  current="$(nvme_cli_version || true)"
  if [[ -n "$current" ]] && version_ge "$current" "$NVME_CLI_MIN_VERSION" && [[ "$FORCE_NVME_BUILD" -eq 0 ]]; then
    log "nvme-cli ${current} from apt satisfies minimum ${NVME_CLI_MIN_VERSION}"
    return
  fi

  warn "nvme-cli ${current:-missing} is below ${NVME_CLI_MIN_VERSION} (OCP plugin needs 2.10+)"
  install_nvme_cli_from_source
  log "Installed nvme-cli $(nvme_cli_version)"
}

detect_arch_portable() {
  local machine
  machine="$(uname -m)"
  case "$machine" in
  x86_64 | amd64) echo "linux-x86_64-portable" ;;
  aarch64 | arm64) echo "linux-aarch64-portable" ;;
  armv7l | armhf) echo "linux-armv7l-portable" ;;
  i686 | i386) echo "linux-i686-portable" ;;
  ppc64le) echo "linux-powerpc64le-portable" ;;
  *) die "Unsupported architecture for Seagate portable OpenSeaChest: ${machine}" ;;
  esac
}

detect_arch_deb() {
  dpkg --print-architecture 2>/dev/null || uname -m
}

openseachest_installed_version() {
  if command -v openSeaChest_Basics >/dev/null 2>&1; then
    openSeaChest_Basics --version 2>/dev/null | awk '/openSeaChest_Basics Version:/ {print $4; exit}' || echo "unknown"
  else
    echo ""
  fi
}

install_openseachest_from_apt() {
  if apt-cache show openseachest >/dev/null 2>&1; then
    log "Installing openseachest from apt (package provides openSeaChest_* in /usr/bin)"
    apt-get install -y openseachest
    return 0
  fi
  return 1
}

install_openseachest_from_seagate() {
  local tag="v${OPENSEACHEST_VERSION#v}"
  local arch_deb arch_portable tmpdir deb_file asset_base url
  arch_deb="$(detect_arch_deb)"
  arch_portable="$(detect_arch_portable)"
  tmpdir="$(mktemp -d /tmp/cdi-openseachest.XXXXXX)"
  trap 'rm -rf "$tmpdir"' RETURN

  install_apt_packages curl ca-certificates xz-utils unzip

  deb_file="openseachest_${OPENSEACHEST_VERSION}_${arch_deb}.deb"
  url="https://github.com/Seagate/openSeaChest/releases/download/${tag}/${deb_file}"

  log "Fetching Seagate OpenSeaChest ${tag} (${deb_file})"
  if curl -fsSL -o "${tmpdir}/${deb_file}" "$url"; then
    dpkg -i "${tmpdir}/${deb_file}" || apt-get install -f -y
    log "Installed OpenSeaChest ${tag} from Seagate .deb"
    return
  fi

  warn "Seagate .deb not found for this release/arch; using portable archive"
  asset_base="https://github.com/Seagate/openSeaChest/releases/download/${tag}"
  if curl -fsSL -o "${tmpdir}/osc.zip" "${asset_base}/${arch_portable}.zip"; then
    :
  elif curl -fsSL -o "${tmpdir}/osc.tar.xz" "${asset_base}/openSeaChest-${tag}-${arch_portable}.tar.xz"; then
    mkdir -p "${tmpdir}/extract"
    tar -xJf "${tmpdir}/osc.tar.xz" -C "${tmpdir}/extract"
    install -d "${INSTALL_DIR}"
    find "${tmpdir}/extract" -maxdepth 3 -type f -name 'openSeaChest_*' -executable -print0 |
      while IFS= read -r -d '' bin; do install -m 0755 "$bin" "${INSTALL_DIR}/$(basename "$bin")"; done
    log "Installed OpenSeaChest ${tag} portable binaries to ${INSTALL_DIR}"
    return
  else
    die "Could not download OpenSeaChest ${tag} for ${arch_portable}"
  fi

  unzip -q "${tmpdir}/osc.zip" -d "${tmpdir}/extract"
  install -d "${INSTALL_DIR}"
  find "${tmpdir}/extract" -maxdepth 3 -type f -name 'openSeaChest_*' -print0 |
    while IFS= read -r -d '' bin; do
      [[ -x "$bin" || -f "$bin" ]] || continue
      install -m 0755 "$bin" "${INSTALL_DIR}/$(basename "$bin")"
    done
  log "Installed OpenSeaChest ${tag} portable binaries to ${INSTALL_DIR}"
}

ensure_openseachest() {
  if [[ "$FORCE_LATEST_OPENSEACHEST" -eq 1 ]]; then
    install_openseachest_from_seagate
    return
  fi

  if command -v openSeaChest_Basics >/dev/null 2>&1 && command -v openSeaChest_SMART >/dev/null 2>&1; then
    log "OpenSeaChest already present ($(openseachest_installed_version || echo version unknown))"
    return
  fi

  if install_openseachest_from_apt; then
    return
  fi

  warn "openseachest is not in configured apt sources (common on Ubuntu 22.04 / Debian Bookworm)"
  install_openseachest_from_seagate
}

install_optional_extras() {
  if [[ "$WITH_SAS" -eq 1 ]]; then
    install_apt_packages sg3-utils
  fi

  if [[ "$WITH_PDF" -eq 1 ]]; then
    log "Installing WeasyPrint OS dependencies for PDF reports"
    install_apt_packages \
      python3-cffi python3-cairocffi python3-cairosvg \
      libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
      shared-mime-info fonts-dejavu-core || true
    if apt-cache show python3-weasyprint >/dev/null 2>&1; then
      install_apt_packages python3-weasyprint || true
    else
      warn "python3-weasyprint not in apt; install with: pip install weasyprint"
    fi
  fi
}

verify_tools() {
  log "Verifying tools"
  local missing=0
  for cmd in smartctl nvme openSeaChest_Basics openSeaChest_SMART; do
    if command -v "$cmd" >/dev/null 2>&1; then
      printf '  OK  %s -> %s\n' "$cmd" "$(command -v "$cmd")"
    else
      printf '  --  %s (missing)\n' "$cmd"
      missing=$((missing + 1))
    fi
  done

  if command -v nvme >/dev/null 2>&1; then
    printf '      nvme version: %s\n' "$(nvme_cli_version)"
    if nvme ocp help >/dev/null 2>&1; then
      printf '      nvme OCP plugin: available\n'
    else
      warn "nvme OCP plugin not available (need nvme-cli ${NVME_CLI_MIN_VERSION}+; try --build-nvme-cli)"
    fi
  fi

  if [[ "$missing" -gt 0 ]] && [[ "$FROM_POSTINST" -eq 0 ]]; then
    warn "${missing} expected tool(s) missing — see messages above"
  fi
}

main() {
  parse_args "$@"
  require_root
  apt_update
  install_core_apt_tools
  ensure_nvme_cli
  ensure_openseachest
  install_optional_extras
  verify_tools
  log "Done. Install CDI Health with: sudo apt install ./cdi-health_*.deb"
}

main "$@"
