import sys
sys.path.append("/home/joshuaiamv/Desarrollo/Packet_XML/backend")
from pkt_encoder import PKTEncoder
import xml.etree.ElementTree as ET

with open("/home/joshuaiamv/Descargas/Segundo_Parcial_Redes_2.pkt", "rb") as f:
    xml = PKTEncoder.decode_pkt_to_xml(f.read())
root = ET.fromstring(xml)

devs = root.findall(".//DEVICES/DEVICE")
links = root.findall(".//LINKS/LINK")
print(f"Total devices: {len(devs)}")
print(f"Total links: {len(links)}")

routers = [d for d in devs if d.find("ENGINE/TYPE") is not None and d.find("ENGINE/TYPE").get("model") == "1841"]
print(f"Routers 1841 count: {len(routers)}")
for r in routers:
    name = r.find("ENGINE/NAME").text
    has_wic = any(m.find("MODEL") is not None and m.find("MODEL").text == "WIC-2T" for m in r.findall(".//MODULE"))
    cfg = "".join([l.text or "" for l in r.findall(".//RUNNINGCONFIG/LINE")])
    has_ospf = "router ospf" in cfg
    has_ssh = "transport input ssh" in cfg
    print(f" -> Router: {name}, Has WIC-2T: {has_wic}, OSPF: {has_ospf}, SSH: {has_ssh}")

serial_links = [l for l in links if l.find("TYPE").text == "eSerial"]
copper_links = [l for l in links if l.find("TYPE").text == "eCopper"]
print(f"Serial links count: {len(serial_links)} (Expected 4)")
print(f"Copper links count: {len(copper_links)} (Expected 18)")
for sl in serial_links:
    c = sl.find("CABLE")
    p_from = c.find("PORT").text
    p_to = c.findall("PORT")[1].text
    dce_dev = c.find("DCEDEV").text if c.find("DCEDEV") is not None else "NONE"
    dce_port = c.find("DCEPORT").text if c.find("DCEPORT") is not None else "NONE"
    print(f" -> Serial: {p_from} <---> {p_to}, DCE dev: {dce_dev}, DCE port: {dce_port}")

pw_uuids = set()
for n in root.findall(".//PHYSICALWORKSPACE//NODE"):
    u = n.find("UUID_STR")
    if u is not None and u.text:
        pw_uuids.add(u.text.strip())

missing_devs = []
for d in devs:
    name = d.find("ENGINE/NAME").text
    ws = d.find("WORKSPACE")
    phys = ws.find("PHYSICAL").text if ws.find("PHYSICAL") is not None else ""
    u = phys.split(",")[-1].strip()
    if u not in pw_uuids:
        missing_devs.append((name, u))

print(f"Devices missing from PHYSICALWORKSPACE: {len(missing_devs)}")
if not missing_devs:
    print("✅ PERFECT! All devices exist in PHYSICALWORKSPACE!")
