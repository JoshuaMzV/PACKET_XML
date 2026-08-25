"""
End-to-End Test and Verification Script:
Network IR -> JSExporter -> Live Bridge / Socket.IO -> Packet Tracer -> Save -> network.pkt
"""

import asyncio
import os
import sys
from pathlib import Path
import json

sys.path.append('/home/joshuaiamv/Desarrollo/Packet_XML/backend')

from ai_engine import AIEngine
from network_ir import NetworkIR
from exporters import XMLExporter, JSExporter, CLIExporter
from bridge_server import PTBridgeServer

OUTPUT_DIR = Path('/home/joshuaiamv/Desarrollo/Packet_XML/output')

async def run_end_to_end(prompt: str):
    print('======================================================================')
    print(' 🌐 INICIANDO PRUEBA END-TO-END: IR -> JS -> PT -> SAVE -> .PKT')
    print('======================================================================')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # ETAPA 1: Network IR y Pre-Flight Validation
    # -------------------------------------------------------------------------
    print("\n[ETAPA 1] Generando y Validando Network IR...")
    topology = await AIEngine.generate_from_prompt(prompt, model_provider='heuristic')
    ir = NetworkIR(topology)
    is_valid = ir.validate()

    print(f' -> Estado de Validación: {ir.validation.get("status")} (is_valid={is_valid})')
    print(f' -> Total Dispositivos: {len(ir.devices)}')
    print(f' -> Total Enlaces: {len(ir.links)}')
    print(f' -> VLANs y Subredes VLSM:')
    for v in ir.vlans:
        print(f'    * VLAN {v.get("vlan", v.get("id"))}: {v.get("name")} -> Net: {v.get("network")} | GW: {v.get("gateway")}')

    if not is_valid:
        print('❌ Error: Network IR no es válida:', ir.validation.get('errors'))
        return False

    # -------------------------------------------------------------------------
    # ETAPA 2: Exportar los 3 artefactos de texto desde la MISMA Network IR
    # -------------------------------------------------------------------------
    print("\n[ETAPA 2] Exportando artefactos unificados desde Network IR...")
    
    xml_path = OUTPUT_DIR / 'network.xml'
    js_path = OUTPUT_DIR / 'network.js'
    cli_path = OUTPUT_DIR / 'network.txt'

    xml_content = XMLExporter.export(ir)
    js_content = JSExporter.export(ir)
    cli_content = CLIExporter.export(ir)

    xml_path.write_text(xml_content, encoding='utf-8')
    js_path.write_text(js_content, encoding='utf-8')
    cli_path.write_text(cli_content, encoding='utf-8')

    print(f' -> network.xml guardado en {xml_path} ({len(xml_content)} bytes)')
    print(f' -> network.js guardado en {js_path} ({len(js_content)} bytes)')
    print(f' -> network.txt guardado en {cli_path} ({len(cli_content)} bytes)')

    # -------------------------------------------------------------------------
    # ETAPA 3: Despliegue en Vivo en Cisco Packet Tracer vía Socket.IO
    # -------------------------------------------------------------------------
    print("\n[ETAPA 3] Verificando conexión de Packet Tracer en 127.0.0.1:7531...")
    
    if PTBridgeServer._bridge is None:
        print(' -> Iniciando servidor Socket.IO en puerto 7531...')
        await PTBridgeServer.start_bridge()
        await asyncio.sleep(0.5)

    pt_connected = PTBridgeServer.is_pt_connected()
    print(f' -> Estado de Packet Tracer en Socket: {"CONECTADO" if pt_connected else "ESPERANDO EXTENSIÓN"}')

    if pt_connected:
        print(' -> Inyectando topología en tiempo real en Packet Tracer...')
        deploy_res = await PTBridgeServer.deploy_live(ir.to_dict())
        print(f' -> Resultado del despliegue: {deploy_res.get("success")}')
        print(f' -> Dispositivos creados: {deploy_res.get("stats", {}).get("devices")}')
        print(f' -> Enlaces conectados: {deploy_res.get("stats", {}).get("links")}')
        print(f' -> Configuraciones IOS aplicadas: {deploy_res.get("stats", {}).get("configs")}')
    else:
        print(' -> ℹ️ Packet Tracer no está conectado en este momento al Socket.IO.')
        print('      (Abre en Packet Tracer: Extensions -> Packet Tracer MCP para conectar)')

    # -------------------------------------------------------------------------
    # ETAPA 4: Verificación del archivo network.pkt
    # -------------------------------------------------------------------------
    pkt_path = OUTPUT_DIR / 'network.pkt'
    print(f"\n[ETAPA 4] Verificando archivo .pkt en: {pkt_path}")

    if pkt_path.exists():
        size = pkt_path.stat().st_size
        print(f' -> ✅ Archivo network.pkt encontrado: {size} bytes ({round(size/1024, 2)} KB)')
        with open(pkt_path, 'rb') as f:
            header = f.read(16)
        print(f' -> Cabecera binaria del contenedor: {header}')
    else:
        print(f' -> ℹ️ El archivo {pkt_path} aún no ha sido guardado desde Packet Tracer.')
        print(f'      Para completar el guardado en Packet Tracer: Haz clic en File -> Save As... y guárdalo como {pkt_path}')

    print("\n======================================================================")
    print(' RESUMEN DE LA ARQUITECTURA DE 4 ARTEFACTOS UNIFICADOS')
    print('======================================================================')
    print(f' 1. XML : {xml_path} ({xml_path.stat().st_size if xml_path.exists() else 0} bytes)')
    print(f' 2. JS  : {js_path} ({js_path.stat().st_size if js_path.exists() else 0} bytes)')
    print(f' 3. TXT : {cli_path} ({cli_path.stat().st_size if cli_path.exists() else 0} bytes)')
    print(f' 4. PKT : {pkt_path} ({"EXISTE: " + str(pkt_path.stat().st_size) + " bytes" if pkt_path.exists() else "Pendiente de guardar"})')
    print("======================================================================\n")

if __name__ == '__main__':
    test_prompt = 'Quiero que diseñes una topología de 3 capas con 2 routers, 2 DMZ, 2 switches y 1 PC en cada lado. Hazlo con VLAN básicas.'
    asyncio.run(run_end_to_end(test_prompt))
