#!/usr/bin/env bash
# ==============================================================================
# Packet_XML - Launcher Script
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/backend"

echo "======================================================================"
echo " 🌐 PACKET_XML: AI Network Orchestrator for Cisco Packet Tracer"
echo "======================================================================"
echo " -> Iniciando Servidor FastAPI en http://127.0.0.1:8000"
echo " -> Ollama Local Detectado en http://localhost:11434"
echo " -> Abre tu navegador en: http://127.0.0.1:8000"
echo "======================================================================"

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
