#!/usr/bin/env bash
# Note: Do not enable set -e here since this script is meant to be sourced.
# Using -e in a sourced script can exit the parent shell on non-zero commands.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="python3"

command -v uv >/dev/null 2>&1 && UV_BIN="$(command -v uv)" || UV_BIN=""

echo "[env] Project root: $PROJECT_ROOT"

# Create venv if missing
if [[ ! -d "$VENV_DIR" ]]; then
  if [[ -n "$UV_BIN" ]]; then
    echo "[env] Creating venv with uv at $VENV_DIR"
    "$UV_BIN" venv "$VENV_DIR"
  else
    echo "[env] Creating venv with $PYTHON_BIN -m venv at $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
else
  echo "[env] Using existing venv at $VENV_DIR"
fi

# Ensure pip is available; uv can install without pip inside venv
if [[ -x "$VENV_DIR/bin/python" ]]; then
  if ! "$VENV_DIR/bin/python" -m pip -V >/dev/null 2>&1; then
    echo "[env] Installing pip into venv"
    "$VENV_DIR/bin/python" -m ensurepip --upgrade || true
  fi
  # Upgrade core tooling when pip is present
  if "$VENV_DIR/bin/python" -m pip -V >/dev/null 2>&1; then
    "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
  fi
fi

# Install requirements
REQ_FILE="$PROJECT_ROOT/requirements.txt"
if [[ -f "$REQ_FILE" ]]; then
  if [[ -n "$UV_BIN" ]]; then
    echo "[env] Installing requirements with uv"
    "$UV_BIN" pip install -r "$REQ_FILE" --python "$VENV_DIR/bin/python"
  else
    echo "[env] Installing requirements with pip"
    "$VENV_DIR/bin/python" -m pip install -r "$REQ_FILE"
  fi
else
  echo "[env] requirements.txt not found at $REQ_FILE"
fi

echo "[env] Activating venv"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[env] Python: $(python -V)"
echo "[env] Which python: $(command -v python)"
echo "[env] Done. Your shell is now using the project venv."


