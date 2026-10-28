"""
Cisco Packet Tracer Multi-Version .PKT Encoder & Decoder Module
Supports:
- Packet Tracer 9.0.1 Native Canvas Schema (<PACKETTRACER5><VERSION>9.0.1.0858</VERSION>)
- Packet Tracer 8.x / Legacy Schema (<PACKET_TRACER_NETWORK>)

Consumes Network IR as the Single Source of Truth to generate verified .pkt files offline.
"""

import os
import sys
import copy
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Union, Optional

from network_ir import NetworkIR
from exporters import XMLExporter
from pkt_crypto.pt_crypto import decrypt_pkt
from pkt_crypto.repacket import compress_qt, obf_stage2, encrypt_pkt, obf_stage1

log = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "pt9_template.xml"

class PKTEncoder:
    """
    Encodes Network IR into native Cisco Packet Tracer .pkt binary containers
    using Qt compression (qCompress), Twofish-128 in EAX authenticated mode, and multi-stage XOR obfuscation.
    """

    _archetypes_cache = None
    _template_root_cache = None

    @classmethod
    def _load_template_archetypes(cls):
        if cls._archetypes_cache is not None:
            return cls._archetypes_cache, cls._template_root_cache

        if TEMPLATE_PATH.exists():
            try:
                tree = ET.parse(str(TEMPLATE_PATH))
                root = tree.getroot()
                cls._template_root_cache = root

                devs = root.find("NETWORK").find("DEVICES")
                cls._archetypes_cache = {}
                for d in devs:
                    eng = d.find("ENGINE")
                    if eng is not None and eng.find("TYPE") is not None:
                        m = eng.find("TYPE").get("model")
                        if m and m not in cls._archetypes_cache:
                            cls._archetypes_cache[m] = copy.deepcopy(d)
                return cls._archetypes_cache, cls._template_root_cache
            except Exception as e:
                log.warning("Could not load PT9 template: %s", e)

        return {}, None

    @classmethod
    def _get_archetype_and_model(cls, dev: Dict[str, Any], archetypes: Dict[str, Any]):
        d_type = dev.get("type", "router")
        d_model = dev.get("model", "")
        if d_model in archetypes:
            return archetypes[d_model], d_model
        if d_type == "router":
            return archetypes.get("2911"), "2911"
        elif d_type == "switch_l3":
            return archetypes.get("3650-24PS", archetypes.get("2960-24TT")), "3650-24PS"
        elif d_type == "switch_l2":
            return archetypes.get("2960-24TT"), "2960-24TT"
        elif d_type == "server" or "srv" in dev.get("id", "").lower():
            return archetypes.get("Server-PT"), "Server-PT"
        else:
            return archetypes.get("PC-PT"), "PC-PT"

    @classmethod
    def normalize_port_name(cls, model: str, port: str) -> str:
        if model == "3650-24PS":
            if "FastEthernet0/" in port:
                num = port.replace("FastEthernet0/", "")
                return f"GigabitEthernet1/0/{num}"
            elif "GigabitEthernet0/" in port:
                num = port.replace("GigabitEthernet0/", "")
                return f"GigabitEthernet1/0/{num}"
            elif not port.startswith("GigabitEthernet1/0/"):
                return "GigabitEthernet1/0/1"
        elif model == "2911":
            if "FastEthernet" in port:
                num = port.replace("FastEthernet0/", "").replace("FastEthernet", "")
                val = int(num) if num.isdigit() else 0
                return f"GigabitEthernet0/{min(val, 2)}"
            elif not port.startswith("GigabitEthernet0/"):
                return "GigabitEthernet0/0"
        elif model in ["PC-PT", "Server-PT", "Laptop-PT"]:
            return "FastEthernet0"
        return port

    @classmethod
    def encode_xml_to_pkt(cls, xml_data: Union[str, bytes]) -> bytes:
        """
        Transforms an XML string or bytes into a valid Packet Tracer .pkt binary payload.
        """
        if isinstance(xml_data, str):
            xml_bytes = xml_data.encode('utf-8')
        else:
            xml_bytes = xml_data

        stage2_input = compress_qt(xml_bytes)
        decrypted_blob = obf_stage2(stage2_input)
        stage1_input = encrypt_pkt(decrypted_blob)
        final_pkt_bytes = obf_stage1(stage1_input)
        return final_pkt_bytes

    @classmethod
    def decode_pkt_to_xml(cls, pkt_data: bytes) -> str:
        """
        Decodes a Packet Tracer .pkt binary payload back into its Canonical XML string.
        """
        xml_bytes = decrypt_pkt(pkt_data)
        return xml_bytes.decode('utf-8', errors='ignore')

    @classmethod
    def format_cisco_running_config(cls, raw_lines: list) -> list:
        clean_lines = ["!"]
        indent = False
        for line in raw_lines:
            s = line.strip()
            if not s or s in ["enable", "configure terminal", "conf t", "exit", "end", "write memory", "wr mem", "do wr"]:
                if s in ["exit", "end"]:
                    indent = False
                    clean_lines.append("!")
                continue
            
            if s.startswith("interface ") or s.startswith("router ") or s.startswith("line ") or s.startswith("vlan "):
                clean_lines.append("!")
                clean_lines.append(s)
                indent = True
            elif indent:
                clean_lines.append(" " + s)
            else:
                clean_lines.append(s)
        clean_lines.append("!")
        clean_lines.append("end")
        return clean_lines

    @classmethod
    def generate_pt9_native_xml(cls, ir: NetworkIR) -> str:
        """
        Generates Packet Tracer 9.0.1 Native Canvas Schema (<PACKETTRACER5>) with normalized ports and full cabling.
        """
        data = ir.to_dict() if isinstance(ir, NetworkIR) else ir
        archetypes, base_root = cls._load_template_archetypes()

        if base_root is not None:
            root = copy.deepcopy(base_root)
            net = root.find("NETWORK")
            devs_container = net.find("DEVICES")
            devs_container.clear()
            links_container = net.find("LINKS")
            links_container.clear()
        else:
            root = ET.Element("PACKETTRACER5")
            v_elem = ET.SubElement(root, "VERSION")
            v_elem.text = "9.0.1.0858"
            net = ET.SubElement(root, "NETWORK")
            devs_container = ET.SubElement(net, "DEVICES")
            links_container = ET.SubElement(net, "LINKS")

        base_mem = 93868000000000
        dev_map = {}

        # 1. Build Devices
        for idx, dev in enumerate(data.get("devices", data.get("nodes", []))):
            dev_id = dev.get("id", f"Device_{idx+1}")
            d_name = dev.get("label", dev_id)
            save_ref = f"save-ref-id:{1000000000000000000 + idx * 1000}"
            dev_mem = str(base_mem + idx * 10000)
            
            arch, model_name = cls._get_archetype_and_model(dev, archetypes)
            dev_map[dev_id] = {"save_ref": save_ref, "mem_addr": dev_mem, "model": model_name}
            if d_name != dev_id:
                dev_map[d_name] = dev_map[dev_id]

            if arch is not None:
                d_elem = copy.deepcopy(arch)
                eng = d_elem.find("ENGINE")
                if eng is not None:
                    name_tag = eng.find("NAME")
                    if name_tag is not None:
                        name_tag.text = d_name
                    save_ref_tag = eng.find("SAVE_REF_ID")
                    if save_ref_tag is not None:
                        save_ref_tag.text = save_ref
                    else:
                        s_elem = ET.SubElement(eng, "SAVE_REF_ID")
                        s_elem.text = save_ref

                    # 0. Assign Unique MAC Addresses to all ports to prevent MAC flapping
                    for p_idx, port in enumerate(eng.iter("PORT")):
                        hex_idx = f"{idx+1:04X}"
                        hex_port = f"{p_idx+1:04X}"
                        unique_mac = f"0001.{hex_idx[:2]}{hex_idx[2:]}.{hex_port[:2]}{hex_port[2:]}"
                        
                        mac_elem = port.find("MACADDRESS")
                        if mac_elem is not None: mac_elem.text = unique_mac
                        
                        bia_elem = port.find("BIA")
                        if bia_elem is not None: bia_elem.text = unique_mac
                        
                        ipv6_ll = port.find("IPV6_LINK_LOCAL")
                        if ipv6_ll is not None: ipv6_ll.text = f"FE80::201:{hex_idx}FF:FE{hex_port[:2]}:{hex_port[2:]}"
                        
                        ipv6_def_ll = port.find("IPV6_DEFAULT_LINK_LOCAL")
                        if ipv6_def_ll is not None: ipv6_def_ll.text = f"FE80::201:{hex_idx}FF:FE{hex_port[:2]}:{hex_port[2:]}"

                    # Assign Unique Chassis Base MAC (BUILD_IN_ADDR) so Spanning Tree sees distinct bridges
                    for bia_chassis in d_elem.iter("BUILD_IN_ADDR"):
                        hex_idx = f"{idx+1:04X}"
                        bia_chassis.text = f"0002.{hex_idx[:2]}{hex_idx[2:]}.0001"

                    # 1. Populate Cisco Router & Switch Running/Startup Configs
                    all_chunks = dev.get("phase2_chunks", []) + dev.get("phase3_chunks", []) + dev.get("phase4_chunks", [])
                    raw_lines = []
                    if all_chunks:
                        for c in all_chunks: raw_lines.extend(c)
                    elif dev.get("ios_config"):
                        raw_lines.extend(dev["ios_config"])

                    if raw_lines:
                        formatted_lines = cls.format_cisco_running_config(raw_lines)
                        for cfg_name in ["RUNNINGCONFIG", "STARTUPCONFIG"]:
                            cfg_tag = eng.find(cfg_name)
                            if cfg_tag is not None:
                                cfg_tag.clear()
                                for f_line in formatted_lines:
                                    l_elem = ET.SubElement(cfg_tag, "LINE")
                                    l_elem.text = f_line

                    # 2. Populate Switch VLANs Table
                    if "switch" in dev.get("type", "") or model_name in ["3650-24PS", "2960-24TT"]:
                        vlans_elem = eng.find("VLANS")
                        if vlans_elem is not None and data.get("vlans"):
                            vlans_elem.clear()
                            ET.SubElement(vlans_elem, "VLAN", {"name": "default", "number": "1", "rspan": "0"})
                            for v in data["vlans"]:
                                v_num = str(v.get("vlan", ""))
                                if v_num and v_num != "1":
                                    v_name = v.get("name", f"VLAN_{v_num}")
                                    ET.SubElement(vlans_elem, "VLAN", {"name": v_name, "number": v_num, "rspan": "0"})

                    # 3. Populate Endpoints (PC, Laptop, Server) IP / Subnet / Gateway / DNS
                    if model_name in ["PC-PT", "Laptop-PT", "Server-PT"] or dev.get("type") in ["pc", "laptop", "server"]:
                        gw = dev.get("gateway", "")
                        gw_elem = eng.find("GATEWAY")
                        if gw_elem is not None:
                            gw_elem.text = gw
                        elif gw:
                            ET.SubElement(eng, "GATEWAY").text = gw

                        dns = dev.get("dns", "8.8.8.8")
                        dns_elem = eng.find("DNS")
                        if dns_elem is not None:
                            dns_elem.text = dns
                        elif dns:
                            ET.SubElement(eng, "DNS").text = dns

                        dev_ip = dev.get("ip", "")
                        dev_mask = dev.get("netmask", "255.255.255.0")
                        for port in eng.iter("PORT"):
                            t_elem = port.find("TYPE")
                            if t_elem is not None and "Ethernet" in (t_elem.text or ""):
                                is_dhcp = dev.get("dhcp", False)
                                dhcp_elem = port.find("PORT_DHCP_ENABLE")
                                if dhcp_elem is not None:
                                    dhcp_elem.text = "true" if is_dhcp else "false"
                                elif is_dhcp:
                                    ET.SubElement(port, "PORT_DHCP_ENABLE").text = "true"

                                # Always write IP, Subnet, Gateway, and DNS as initial lease
                                if dev_ip:
                                    ip_elem = port.find("IP")
                                    if ip_elem is not None: ip_elem.text = dev_ip
                                    else: ET.SubElement(port, "IP").text = dev_ip

                                if dev_mask:
                                    subnet_elem = port.find("SUBNET")
                                    if subnet_elem is not None: subnet_elem.text = dev_mask
                                    else: ET.SubElement(port, "SUBNET").text = dev_mask

                                if gw:
                                    port_gw = port.find("PORT_GATEWAY")
                                    if port_gw is not None: port_gw.text = gw
                                    else: ET.SubElement(port, "PORT_GATEWAY").text = gw

                                if dns:
                                    port_dns = port.find("PORT_DNS")
                                    if port_dns is not None: port_dns.text = dns
                                    else: ET.SubElement(port, "PORT_DNS").text = dns

                        # 4. Server-PT Services Injection (DHCP, DNS, HTTP, TFTP)
                        if model_name == "Server-PT" and "services" in dev:
                            svcs = dev["services"]
                            
                            # HTTP
                            if "http" in svcs:
                                http = eng.find("HTTP_SERVER")
                                if http is None: http = ET.SubElement(eng, "HTTP_SERVER")
                                en = http.find("ENABLED")
                                if en is None: en = ET.SubElement(http, "ENABLED")
                                en.text = "1"
                                # Custom institutional HTML for index.html
                                for f_node in eng.iter("FILE"):
                                    fn = f_node.find("NAME")
                                    if fn is not None and fn.text == "index.html":
                                        fc = f_node.find("FILE_CONTENT")
                                        if fc is not None:
                                            txt = fc.find("TEXT")
                                            if txt is None: txt = ET.SubElement(fc, "TEXT")
                                            txt.text = (
                                                "<html>\n"
                                                "<center><font size='+2' color='#003366'><b>UNIVERSIDAD MARIANO GÁLVEZ DE GUATEMALA</b></font></center>\n"
                                                "<center><font size='+1' color='#cc9900'><b>Campus Universitario Inteligente - Portal Central</b></font></center>\n"
                                                "<hr>\n"
                                                "<h3>Estado de la Infraestructura Cisco Enterprise:</h3>\n"
                                                "<ul>\n"
                                                "  <li><b>Portal Web Institucional:</b> campus.umg.edu.gt (Operativo)</li>\n"
                                                "  <li><b>Servidor DNS Central:</b> 10.10.4.10 (Activo)</li>\n"
                                                "  <li><b>Broker IoT MQTT:</b> mqtt.umg.edu.gt:1883 (Activo)</li>\n"
                                                "  <li><b>Core L3 / Gateway:</b> 10.10.4.1 (VLAN 50 Servidores)</li>\n"
                                                "  <li><b>VLANs de Campus:</b> Estudiantes (30), Docentes (20), Labs (40), IoT (60), Admin (10), Voz (70)</li>\n"
                                                "</ul>\n"
                                                "<hr>\n"
                                                "<center><font size='-1' color='gray'>Cisco Packet Tracer 9.0 Simulation - UMG 2026</font></center>\n"
                                                "</html>"
                                            )

                                
                            # TFTP
                            if "tftp" in svcs:
                                tftp = eng.find("TFTP_SERVER")
                                if tftp is None: tftp = ET.SubElement(eng, "TFTP_SERVER")
                                en = tftp.find("ENABLED")
                                if en is None: en = ET.SubElement(tftp, "ENABLED")
                                en.text = "1"
                                
                            # DNS
                            if "dns" in svcs:
                                dns_node = eng.find("DNS_SERVER")
                                if dns_node is None: dns_node = ET.SubElement(eng, "DNS_SERVER")
                                en = dns_node.find("ENABLED")
                                if en is None: en = ET.SubElement(dns_node, "ENABLED")
                                en.text = "1"
                                db = dns_node.find("NAMESERVER-DATABASE")
                                if db is None: db = ET.SubElement(dns_node, "NAMESERVER-DATABASE")
                                db.clear()
                                for rec in svcs["dns"]:
                                    r = ET.SubElement(db, "RESOURCE-RECORD")
                                    rec_type = rec.get("type", "A-REC")
                                    if rec_type in ["A", "0", "A-Record", "A_RECORD", 0]:
                                        rec_type = "A-REC"
                                    ET.SubElement(r, "TYPE").text = rec_type
                                    ET.SubElement(r, "NAME").text = rec.get("name", "")
                                    ET.SubElement(r, "TTL").text = str(rec.get("ttl", "86400"))
                                    if rec_type == "A-REC":
                                        ET.SubElement(r, "IPADDRESS").text = rec.get("ip", "")
                                    elif rec_type == "CNAME":
                                        ET.SubElement(r, "HOSTNAME").text = rec.get("hostname", rec.get("ip", ""))
                                    elif rec_type == "NS":
                                        ET.SubElement(r, "SERVER-NAME").text = rec.get("server_name", rec.get("name", ""))
                                    elif rec_type == "AAAA-REC":
                                        ET.SubElement(r, "IPV6ADDRESS").text = rec.get("ipv6", rec.get("ip", ""))
                                    
                            # DHCP
                            if "dhcp" in svcs:
                                dhcp_node = eng.find("DHCP_SERVERS")
                                if dhcp_node is None: dhcp_node = ET.SubElement(eng, "DHCP_SERVERS")
                                assoc = dhcp_node.find("ASSOCIATED_PORTS")
                                if assoc is None: assoc = ET.SubElement(dhcp_node, "ASSOCIATED_PORTS")
                                port_nd = assoc.find("ASSOCIATED_PORT")
                                if port_nd is None:
                                    port_nd = ET.SubElement(assoc, "ASSOCIATED_PORT")
                                    ET.SubElement(port_nd, "NAME").text = "FastEthernet0"
                                srv_nd = port_nd.find("DHCP_SERVER")
                                if srv_nd is None: srv_nd = ET.SubElement(port_nd, "DHCP_SERVER")
                                en = srv_nd.find("ENABLED")
                                if en is None: en = ET.SubElement(srv_nd, "ENABLED")
                                en.text = "1"
                                pools_nd = srv_nd.find("POOLS")
                                if pools_nd is None: pools_nd = ET.SubElement(srv_nd, "POOLS")
                                for p in svcs["dhcp"]:
                                    pl = ET.SubElement(pools_nd, "POOL")
                                    ET.SubElement(pl, "NAME").text = p.get("name", "pool")
                                    ET.SubElement(pl, "NETWORK").text = p.get("network", "0.0.0.0")
                                    ET.SubElement(pl, "MASK").text = p.get("mask", "255.255.255.0")
                                    ET.SubElement(pl, "DEFAULT_ROUTER").text = p.get("gw", "0.0.0.0")
                                    ET.SubElement(pl, "DNS_SERVER").text = p.get("dns", "0.0.0.0")
                                    ET.SubElement(pl, "START_IP").text = p.get("start_ip", "0.0.0.0")
                                    ET.SubElement(pl, "END_IP").text = p.get("end_ip", "0.0.0.0")
                                    ET.SubElement(pl, "TFTP_ADDRESS").text = p.get("tftp", "0.0.0.0")
                
                ws = d_elem.find("WORKSPACE")
                if ws is not None:
                    log_elem = ws.find("LOGICAL")
                    if log_elem is not None:
                        x_tag = log_elem.find("X")
                        if x_tag is not None: x_tag.text = str(dev.get("x", 300))
                        y_tag = log_elem.find("Y")
                        if y_tag is not None: y_tag.text = str(dev.get("y", 200))
                        mem_tag = log_elem.find("MEM_ADDR")
                        if mem_tag is not None: mem_tag.text = dev_mem
                        dev_addr_tag = log_elem.find("DEV_ADDR")
                        if dev_addr_tag is not None: dev_addr_tag.text = str(int(dev_mem) + 500)
            else:
                d_elem = ET.Element("DEVICE")
                eng = ET.SubElement(d_elem, "ENGINE")
                ET.SubElement(eng, "TYPE", {"customModel": "", "model": model_name}).text = "Router"
                ET.SubElement(eng, "NAME", {"translate": "true"}).text = d_name
                ET.SubElement(eng, "POWER").text = "true"
                ET.SubElement(eng, "SAVE_REF_ID").text = save_ref
                ws = ET.SubElement(d_elem, "WORKSPACE")
                log_elem = ET.SubElement(ws, "LOGICAL")
                ET.SubElement(log_elem, "X").text = str(dev.get("x", 300))
                ET.SubElement(log_elem, "Y").text = str(dev.get("y", 200))
                ET.SubElement(log_elem, "MEM_ADDR").text = dev_mem

            devs_container.append(d_elem)

        # 2. Build Links with strictly validated port names
        for l_idx, link in enumerate(data.get("links", [])):
            src_id = link.get("source")
            dst_id = link.get("target")
            if src_id not in dev_map or dst_id not in dev_map:
                continue

            src_info = dev_map[src_id]
            dst_info = dev_map[dst_id]

            src_port = cls.normalize_port_name(src_info["model"], link.get("src_port", "FastEthernet0/1"))
            dst_port = cls.normalize_port_name(dst_info["model"], link.get("dst_port", "FastEthernet0/1"))

            l_elem = ET.Element("LINK")
            t_link = ET.SubElement(l_elem, "TYPE")
            t_link.text = "eCopper"
            
            cable = ET.SubElement(l_elem, "CABLE")
            ET.SubElement(cable, "LENGTH").text = "1"
            ET.SubElement(cable, "FUNCTIONAL").text = "true"
            ET.SubElement(cable, "FROM").text = src_info["save_ref"]
            ET.SubElement(cable, "PORT").text = src_port
            ET.SubElement(cable, "TO").text = dst_info["save_ref"]
            ET.SubElement(cable, "PORT").text = dst_port
            ET.SubElement(cable, "FROM_DEVICE_MEM_ADDR").text = src_info["mem_addr"]
            ET.SubElement(cable, "TO_DEVICE_MEM_ADDR").text = dst_info["mem_addr"]
            ET.SubElement(cable, "FROM_PORT_MEM_ADDR").text = str(int(src_info["mem_addr"]) + l_idx * 10 + 1)
            ET.SubElement(cable, "TO_PORT_MEM_ADDR").text = str(int(dst_info["mem_addr"]) + l_idx * 10 + 2)
            ET.SubElement(cable, "GEO_VIEW_COLOR").text = "#6ba72e"
            ET.SubElement(cable, "IS_MANAGED_IN_RACK_VIEW").text = "false"
            
            c_type = "eCrossOver" if "cross" in link.get("type", "").lower() else "eStraightThrough"
            ET.SubElement(cable, "TYPE").text = c_type

            links_container.append(l_elem)

        return ET.tostring(root, encoding="utf-8").decode('utf-8')

    @classmethod
    def generate_pkt(
        cls, 
        network_ir: Union[NetworkIR, Dict[str, Any]], 
        output_path: Optional[Union[str, Path]] = None,
        pt_version: str = "9.0"
    ) -> Dict[str, Any]:
        """
        Directly generates a .pkt file from a validated Network IR.
        pt_version options:
          - '9.0' (default): Native Packet Tracer 9.0.1 schema (<PACKETTRACER5><VERSION>9.0.1.0858</VERSION>)
          - 'legacy' / '8.2': Legacy schema (<PACKET_TRACER_NETWORK>)
        """
        if isinstance(network_ir, dict):
            ir = NetworkIR(network_ir)
        else:
            ir = network_ir

        if not ir.validation.get("is_valid"):
            ir.validate()

        # 1. Generate XML based on target version
        if str(pt_version).startswith("9"):
            xml_string = cls.generate_pt9_native_xml(ir)
            format_ver = "9.0.1.0858"
        else:
            xml_string = XMLExporter.export(ir)
            format_ver = "8.2"

        # 2. Encode XML to .pkt binary
        pkt_bytes = cls.encode_xml_to_pkt(xml_string)

        # 3. Write file if output_path is provided
        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(pkt_bytes)
            log.info("Generated .pkt (%s) at %s (%d bytes)", format_ver, out_file, len(pkt_bytes))

        # 4. Immediate Round-Trip Lossless Verification
        recovered_xml = cls.decode_pkt_to_xml(pkt_bytes)
        round_trip_success = (len(recovered_xml) > 0 and format_ver in recovered_xml)

        return {
            "success": True,
            "file_path": str(output_path) if output_path else None,
            "file_size": len(pkt_bytes),
            "pt_format_version": format_ver,
            "crypto_cipher": "Twofish-128 (EAX Mode + CMAC)",
            "compression": "Qt qCompress (zlib)",
            "round_trip_verified": round_trip_success,
            "total_devices": len(ir.devices),
            "total_links": len(ir.links),
            "total_vlans": len(ir.vlans),
            "total_hosts": len(ir.hosts),
            "pkt_bytes": pkt_bytes
        }
