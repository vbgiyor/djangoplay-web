# Bash (macOS + Debian/Ubuntu + Fedora/Arch-ish)

#!/usr/bin/env bash
set -euo pipefail

# Output folder for certs (project-local)
OUT_DIR="./.certs"
CERT_NAME="dev"
CERT_FILE="$OUT_DIR/${CERT_NAME}.pem"
KEY_FILE="$OUT_DIR/${CERT_NAME}-key.pem"

mkdir -p "$OUT_DIR"

echo "Detecting OS..."
OS="$(uname -s)"
echo "OS: $OS"

install_mkcert_mac() {
  if ! command -v mkcert >/dev/null 2>&1; then
    echo "Installing mkcert via Homebrew..."
    if ! command -v brew >/dev/null 2>&1; then
      echo "Homebrew not found — please install Homebrew first: https://brew.sh"
      exit 1
    fi
    brew install mkcert nss || true
  fi
}

install_mkcert_debian() {
  if ! command -v mkcert >/dev/null 2>&1; then
    echo "Installing mkcert for Debian/Ubuntu..."
    sudo apt update
    sudo apt install -y libnss3-tools curl
    curl -sL -o /tmp/mkcert-v2 https://dl.filippo.io/mkcert/latest?for=linux/amd64
    sudo install /tmp/mkcert-v2 /usr/local/bin/mkcert
    rm -f /tmp/mkcert-v2
  fi
}

install_mkcert_fedora() {
  if ! command -v mkcert >/dev/null 2>&1; then
    echo "Installing mkcert for Fedora/RHEL..."
    sudo dnf install -y nss-tools curl
    curl -sL -o /tmp/mkcert-v2 https://dl.filippo.io/mkcert/latest?for=linux/amd64
    sudo install /tmp/mkcert-v2 /usr/local/bin/mkcert
    rm -f /tmp/mkcert-v2
  fi
}

case "$OS" in
  Darwin)
    install_mkcert_mac
    ;;
  Linux)
    # attempt to detect distro a little (not exhaustive)
    if command -v apt >/dev/null 2>&1; then
      install_mkcert_debian
    elif command -v dnf >/dev/null 2>&1; then
      install_mkcert_fedora
    else
      echo "Unknown Linux distro: please install mkcert manually: https://github.com/FiloSottile/mkcert"
      exit 1
    fi
    ;;
  *)
    echo "Unsupported OS: $OS. Please run mkcert manually: https://github.com/FiloSottile/mkcert"
    exit 1
    ;;
esac

echo "Installing mkcert local CA (may require sudo / admin privileges)..."
mkcert -install

# Domains/IPs to include in cert (add more if needed)
HOSTS=(127.0.0.1 localhost ::1 $(hostname).local)

echo "Generating certificate for: ${HOSTS[*]}"
mkcert -key-file "$KEY_FILE" -cert-file "$CERT_FILE" "${HOSTS[@]}"

echo "Certificates written to: $CERT_FILE and $KEY_FILE"
echo "Tip: add $OUT_DIR to .gitignore to avoid committing certs."
