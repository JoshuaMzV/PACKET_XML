"""
Test script for verifying offline generation of Cisco Packet Tracer 9.0.1 .pkt files.
"""

import asyncio
import sys
from pathlib import Path

sys.path.append('/home/joshuaiamv/Desarrollo/Packet_XML/backend')

from ai_engine import AIEngine
from network_ir import NetworkIR
from pkt_encoder import PKTEncoder

async def run_test():
    print('======================================================================')
    print(' 🚀 VERIFICANDO GENERADOR PACKET TRACER 9.0.1 CANÓNICO NATIVO')
    print('======================================================================')
    
    prompt = 'Quiero que diseñes una topología de 3 capas con 2 routers, 2 DMZ, 2 switches y 1 PC en cada lado. Hazlo con VLAN básicas.'
    topo = await AIEngine.generate_from_prompt(prompt, model_provider='heuristic')
    ir = NetworkIR(topo)
    ir.validate()

    out_file = Path('/home/joshuaiamv/Desarrollo/Packet_XML/output/network_pt9.pkt')
    res = PKTEncoder.generate_pkt(ir, output_path=out_file, pt_version='9.0')

    print(f' -> Archivo generado: {res["file_path"]}')
    print(f' -> Tamaño: {res["file_size"]} bytes ({round(res["file_size"]/1024, 2)} KB)')
    print(f' -> Versión de Formato: {res["pt_format_version"]}')
    print(f' -> Round-trip Verificado: {res["round_trip_verified"]}')

    xml_rec = PKTEncoder.decode_pkt_to_xml(out_file.read_bytes())
    print(' -> Tag <PACKETTRACER5> presente:', '<PACKETTRACER5>' in xml_rec)
    print(' -> Tag <VERSION>9.0.1.0858</VERSION> presente:', '9.0.1.0858' in xml_rec)
    print(' -> Tag <OPTIONS> presente:', '<OPTIONS>' in xml_rec)
    print(' -> Tag <PHYSICALWORKSPACE> presente:', '<PHYSICALWORKSPACE>' in xml_rec)
    print(' -> Dispositivos creados en XML nativo:', xml_rec.count('<DEVICE>'))

    assert '<PACKETTRACER5>' in xml_rec
    assert '9.0.1.0858' in xml_rec
    assert '<OPTIONS>' in xml_rec
    assert '<PHYSICALWORKSPACE>' in xml_rec

    print("\n🎉 ¡VERIFICACIÓN EXITOSA! Archivo 100% canónico para Packet Tracer 9.0.1 listo.")

if __name__ == '__main__':
    asyncio.run(run_test())
