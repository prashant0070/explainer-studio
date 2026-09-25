#!/usr/bin/env bash
# Idempotent environment bootstrap for Explainer Studio.
# Runs after the repository is checked out; safe to run repeatedly.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || dirname "$(dirname "$0")")"

# System dependencies:
#   - ffmpeg/ffprobe drive the entire edit/master/QC pipeline
#   - python3-venv is required to create the virtualenv (missing from the base image)
sudo apt-get update -qq
sudo apt-get install -y -qq --no-install-recommends ffmpeg python3-venv

# Python virtualenv with pinned dependencies.
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Local config. The free demo pipeline runs end to end without any API keys;
# drop an LLM key into .env to unlock topic research and new scripts.
[ -f .env ] || cp .env.example .env

echo "Explainer Studio environment ready."
