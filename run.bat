@echo off
REM ==============================================================================
REM  PACKET_XML: Windows Launcher Script
REM ==============================================================================

title PACKET_XML: AI Network Orchestrator
cd /d "%~dp0backend"

echo ======================================================================
echo  PACKET_XML v2.0: AI Network Orchestrator for Cisco Packet Tracer
echo ======================================================================
echo  -^> Iniciando Servidor FastAPI en http://127.0.0.1:8000
echo  -^> Abre tu navegador en: http://127.0.0.1:8000
echo ======================================================================

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] No se pudo iniciar el servidor. Asegurate de haber instalado las dependencias:
    echo pip install -r ..\requirements.txt
    pause
)
