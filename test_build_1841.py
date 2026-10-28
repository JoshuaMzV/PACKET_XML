import os
import sys
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.append("/home/joshuaiamv/Desarrollo/Packet_XML/backend")
from pkt_encoder import PKTEncoder

# 1. Load 1841_real.xml
r1841_tree = ET.parse("/home/joshuaiamv/Desarrollo/Packet_XML/backend/templates/1841_real.xml")
r1841_elem = r1841_tree.getroot()

# 2. Load base template
archetypes, base_root = PKTEncoder._load_template_archetypes()
root = copy.deepcopy(base_root)
net = root.find("NETWORK")
devs_container = net.find("DEVICES")
devs_container.clear()
links_container = net.find("LINKS")
links_container.clear()

base_mem = 93868000000000

# Create 2 1841 routers
routers = [
    {"id": "Router0", "x": 300, "y": 200, "config": ["hostname Router0", "interface Serial0/0/0", " ip address 172.16.13.17 255.255.255.252", " clock rate 64000", " no shutdown"]},
    {"id": "Router1", "x": 600, "y": 200, "config": ["hostname Router1", "interface Serial0/0/0", " ip address 172.16.13.18 255.255.255.252", " no shutdown"]}
]

dev_map = {}

for idx, r in enumerate(routers):
    r_id = r["id"]
    save_ref = f"save-ref-id:{1000000000000000000 + idx * 1000}"
    dev_mem = str(base_mem + idx * 10000)
    dev_map[r_id] = {"save_ref": save_ref, "mem_addr": dev_mem}
    
    d_elem = copy.deepcopy(r1841_elem)
    eng = d_elem.find("ENGINE")
    if eng is not None:
        name_tag = eng.find("NAME")
        if name_tag is not None: name_tag.text = r_id
        save_ref_tag = eng.find("SAVE_REF_ID")
        if save_ref_tag is not None: save_ref_tag.text = save_ref
        else: ET.SubElement(eng, "SAVE_REF_ID").text = save_ref
        
        # MAC Addresses
        for p_idx, port in enumerate(eng.iter("PORT")):
            hex_idx = f"{idx+1:04X}"
            hex_port = f"{p_idx+1:04X}"
            unique_mac = f"0001.{hex_idx[:2]}{hex_idx[2:]}.{hex_port[:2]}{hex_port[2:]}"
            mac_elem = port.find("MACADDRESS")
            if mac_elem is not None: mac_elem.text = unique_mac
            bia_elem = port.find("BIA")
            if bia_elem is not None: bia_elem.text = unique_mac
            
        for bia_chassis in d_elem.iter("BUILD_IN_ADDR"):
            hex_idx = f"{idx+1:04X}"
            bia_chassis.text = f"0002.{hex_idx[:2]}{hex_idx[2:]}.0001"
            
        formatted_lines = PKTEncoder.format_cisco_running_config(r["config"])
        for cfg_name in ["RUNNINGCONFIG", "STARTUPCONFIG"]:
            cfg_tag = eng.find(cfg_name)
            if cfg_tag is not None:
                cfg_tag.clear()
                for f_line in formatted_lines:
                    ET.SubElement(cfg_tag, "LINE").text = f_line

    ws = d_elem.find("WORKSPACE")
    if ws is not None:
        log_elem = ws.find("LOGICAL")
        if log_elem is not None:
            x_tag = log_elem.find("X")
            if x_tag is not None: x_tag.text = str(r["x"])
            y_tag = log_elem.find("Y")
            if y_tag is not None: y_tag.text = str(r["y"])
            mem_tag = log_elem.find("MEM_ADDR")
            if mem_tag is not None: mem_tag.text = dev_mem
            dev_addr_tag = log_elem.find("DEV_ADDR")
            if dev_addr_tag is not None: dev_addr_tag.text = str(int(dev_mem) + 500)

    devs_container.append(d_elem)

# Add Serial Link
l_elem = ET.Element("LINK")
ET.SubElement(l_elem, "TYPE").text = "eSerial"
cable = ET.SubElement(l_elem, "CABLE")
ET.SubElement(cable, "LENGTH").text = "1"
ET.SubElement(cable, "FUNCTIONAL").text = "true"
ET.SubElement(cable, "FROM").text = dev_map["Router0"]["save_ref"]
ET.SubElement(cable, "PORT").text = "Serial0/0/0"
ET.SubElement(cable, "TO").text = dev_map["Router1"]["save_ref"]
ET.SubElement(cable, "PORT").text = "Serial0/0/0"
ET.SubElement(cable, "FROM_DEVICE_MEM_ADDR").text = dev_map["Router0"]["mem_addr"]
ET.SubElement(cable, "TO_DEVICE_MEM_ADDR").text = dev_map["Router1"]["mem_addr"]
ET.SubElement(cable, "FROM_PORT_MEM_ADDR").text = str(int(dev_map["Router0"]["mem_addr"]) + 1)
ET.SubElement(cable, "TO_PORT_MEM_ADDR").text = str(int(dev_map["Router1"]["mem_addr"]) + 2)
ET.SubElement(cable, "GEO_VIEW_COLOR").text = "#ff0000"
ET.SubElement(cable, "IS_MANAGED_IN_RACK_VIEW").text = "false"
ET.SubElement(cable, "TYPE").text = "eSerial"

links_container.append(l_elem)

# Generate XML and PKT
xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
pkt_bytes = PKTEncoder.encode_xml_to_pkt(xml_str)
out_path = Path("/tmp/test_1841_serial.pkt")
out_path.write_bytes(pkt_bytes)
print(f"Generated {out_path} ({len(pkt_bytes)} bytes)")
