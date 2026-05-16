#!/bin/bash
set -e

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p cache/logos cache/routes

echo ""
echo "Setup complete. Edit config.json, then run:"
echo "  source venv/bin/activate && python main.py"
