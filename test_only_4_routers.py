import os
import sys
import copy
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.append("/home/joshuaiamv/Desarrollo/Packet_XML/backend")
from pkt_encoder import PKTEncoder

# 1. Load user-saved mi_1841.pkt
with open("/home/joshuaiamv/Descargas/mi_1841.pkt", "rb") as f:
    xml_user = PKTEncoder.decode_pkt_to_xml(f.read())
    
root = ET.fromstring(xml_user)
r1841_base = copy.deepcopy(root.find(".//DEVICE"))

net = root.find("NETWORK")
devs_container = net.find("DEVICES")
devs_container.clear()
links_container = net.find("LINKS")
links_container.clear()

base_mem = 94568119405680
routers = ["Router0", "Router1", "Router2", "Router3"]
dev_map = {}

for idx, r_name in enumerate(routers):
    save_ref = f"save-ref-id:{1000000000000000000 + idx * 1000}"
    dev_mem = str(base_mem + idx * 100000)
    dev_uuid = str(uuid.uuid4())
    dev_map[r_name] = {"save_ref": save_ref, "mem_addr": dev_mem}
    
    d_elem = copy.deepcopy(r1841_base)
    eng = d_elem.find("ENGINE")
    eng.find("NAME").text = r_name
    sref = eng.find("SAVE_REF_ID")
    if sref is not None: sref.text = save_ref
    else: ET.SubElement(eng, "SAVE_REF_ID").text = save_ref
    
    for p_idx, port in enumerate(eng.iter("PORT")):
        hex_idx = f"{idx+1:04X}"
        hex_port = f"{p_idx+1:04X}"
        mac = f"0001.{hex_idx[:2]}{hex_idx[2:]}.{hex_port[:2]}{hex_port[2:]}"
        me = port.find("MACADDRESS")
        if me is not None: me.text = mac
        be = port.find("BIA")
        if be is not None: be.text = mac
        
    for bia in d_elem.iter("BUILD_IN_ADDR"):
        hex_idx = f"{idx+1:04X}"
        bia.text = f"0002.{hex_idx[:2]}{hex_idx[2:]}.0001"
        
    ws = d_elem.find("WORKSPACE")
    log_elem = ws.find("LOGICAL")
    log_elem.find("X").text = str(300 + (idx % 2) * 300)
    log_elem.find("Y").text = str(200 + (idx // 2) * 200)
    log_elem.find("MEM_ADDR").text = dev_mem
    log_elem.find("DEV_ADDR").text = str(int(dev_mem) + 500)
    
    # In PHYSICAL, keep the exact container hierarchy from mi_1841.pkt, only change the device UUID
    phys = ws.find("PHYSICAL")
    if phys is not None:
        parts = phys.text.split(",")
        parts[-1] = f"{{{dev_uuid}}}"
        phys.text = ",".join(parts)
        
    cpur = ws.find("PHYSICAL_CPUR")
    if cpur is not None:
        orig_u = cpur.find("ORIGINAL_DEVICE_UUID")
        if orig_u is not None: orig_u.text = f"{{{dev_uuid}}}"
        # Set distinct rack slot Y
        y_elem = cpur.find("Y")
        if y_elem is not None: y_elem.text = str(idx * 2)
        
    devs_container.append(d_elem)

# Add 4 serial links
serial_links = [
    ("Router0", "Serial0/1/0", "Router1", "Serial0/1/0"),
    ("Router1", "Serial0/1/1", "Router3", "Serial0/1/0"),
    ("Router0", "Serial0/1/1", "Router2", "Serial0/1/0"),
    ("Router2", "Serial0/1/1", "Router3", "Serial0/1/1")
]

for l_idx, (src, src_p, dst, dst_p) in enumerate(serial_links):
    l_elem = ET.Element("LINK")
    ET.SubElement(l_elem, "TYPE").text = "eSerial"
    cable = ET.SubElement(l_elem, "CABLE")
    ET.SubElement(cable, "LENGTH").text = "1"
    ET.SubElement(cable, "FUNCTIONAL").text = "true"
    ET.SubElement(cable, "FROM").text = dev_map[src]["save_ref"]
    ET.SubElement(cable, "PORT").text = src_p
    ET.SubElement(cable, "TO").text = dev_map[dst]["save_ref"]
    ET.SubElement(cable, "PORT").text = dst_p
    ET.SubElement(cable, "FROM_DEVICE_MEM_ADDR").text = dev_map[src]["mem_addr"]
    ET.SubElement(cable, "TO_DEVICE_MEM_ADDR").text = dev_map[dst]["mem_addr"]
    ET.SubElement(cable, "FROM_PORT_MEM_ADDR").text = str(int(dev_map[src]["mem_addr"]) + l_idx * 10 + 1)
    ET.SubElement(cable, "TO_PORT_MEM_ADDR").text = str(int(dev_map[dst]["mem_addr"]) + l_idx * 10 + 2)
    ET.SubElement(cable, "GEO_VIEW_COLOR").text = "#ff0000"
    ET.SubElement(cable, "IS_MANAGED_IN_RACK_VIEW").text = "false"
    ET.SubElement(cable, "TYPE").text = "eSerial"
    links_container.append(l_elem)

xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
pkt_bytes = PKTEncoder.encode_xml_to_pkt(xml_str)
out_path = Path("/home/joshuaiamv/Descargas/test_4_routers_1841.pkt")
out_path.write_bytes(pkt_bytes)
print(f"Generated {out_path} ({len(pkt_bytes)} bytes)")
