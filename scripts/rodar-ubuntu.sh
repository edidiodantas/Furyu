#!/usr/bin/env bash
# Roda o IPeia Acadêmico no Ubuntu
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    echo "ERRO: ambiente virtual não encontrado."
    echo "Rode primeiro: bash scripts/install-ubuntu.sh"
    exit 1
fi

source .venv/bin/activate

echo "IPeia Acadêmico — Ollama precisa estar rodando (localhost:11434)."
echo "Abrindo http://localhost:8501 ..."
streamlit run app.py
