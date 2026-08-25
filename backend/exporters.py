"""
Network IR Exporters Module
Consumes Network IR as the Single Source of Truth to generate:
- PTBuilder JavaScript (.js)
- Cisco Packet Tracer XML (.xml)
- Cisco IOS CLI Bundle (.txt)
- Live Deployment Commands
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, List, Optional
from network_ir import NetworkIR

class JSExporter:
    """Exports Network IR to PTBuilder JavaScript script with 5-phase safe chunking."""

    @classmethod
    def export(cls, ir: NetworkIR) -> str:
        data = ir.to_dict() if isinstance(ir, NetworkIR) else ir
        lines = []

        # Map node id to clean label
        id_to_label = {}
        for dev in data.get("devices", data.get("nodes", [])):
            label = dev.get("label", dev["id"]).replace(" ", "_").replace("-", "_")
            id_to_label[dev["id"]] = label

        # =========================================================================
        # FASE 1: TOPOLOGÍA FÍSICA (Dispositivos y Enlaces)
        # =========================================================================
        for dev in data.get("devices", data.get("nodes", [])):
            label = id_to_label[dev["id"]]
            model = dev.get("model", "2911")
            x = int(dev.get("x", 200))
            y = int(dev.get("y", 200))
            lines.append(f'addDevice("{label}", "{model}", {x}, {y});')

        for link in data.get("links", []):
            src_name = id_to_label.get(link["source"], link["source"])
            dst_name = id_to_label.get(link["target"], link["target"])
            src_port = link.get("src_port", "GigabitEthernet0/1")
            dst_port = link.get("dst_port", "GigabitEthernet0/1")
            c_type = "cross" if "cross" in link.get("type", "").lower() else "straight"
            lines.append(f'addLink("{src_name}", "{src_port}", "{dst_name}", "{dst_port}", "{c_type}");')

        # =========================================================================
        # FASE 2: SWITCHES - VLANs Y SVIs
        # =========================================================================
        for dev in data.get("devices", data.get("nodes", [])):
            label = id_to_label[dev["id"]]
            for chunk in dev.get("phase2_chunks", []):
                cmds_joined = "\\n".join(chunk).replace('"', '\\"')
                lines.append(f'configureIosDevice("{label}", "{cmds_joined}");')

        # =========================================================================
        # FASE 3: SWITCHES Y ROUTERS - PUERTOS FÍSICOS
        # =========================================================================
        for dev in data.get("devices", data.get("nodes", [])):
            label = id_to_label[dev["id"]]
            for chunk in dev.get("phase3_chunks", []):
                cmds_joined = "\\n".join(chunk).replace('"', '\\"')
                lines.append(f'configureIosDevice("{label}", "{cmds_joined}");')

        # =========================================================================
        # FASE 4: ENRUTAMIENTO OSPF Y RUTAS POR DEFECTO
        # =========================================================================
        for dev in data.get("devices", data.get("nodes", [])):
            label = id_to_label[dev["id"]]
            for chunk in dev.get("phase4_chunks", []):
                cmds_joined = "\\n".join(chunk).replace('"', '\\"')
                lines.append(f'configureIosDevice("{label}", "{cmds_joined}");')

        # =========================================================================
        # FASE 5: EQUIPOS FINALES (PCs, Servidores y Laptops)
        # =========================================================================
        for h in data.get("hosts", []):
            label = id_to_label.get(h["id"], h["id"])
            if h.get("ip"):
                ip = h["ip"]
                mask = h.get("netmask", "255.255.255.0")
                gw = h.get("gateway", "")
                dns = h.get("dns", "127.0.0.1" if h.get("type") == "server" else "8.8.8.8")
                lines.append(f'configurePcIp("{label}", false, "{ip}", "{mask}", "{gw}", "{dns}");')

        return "\n".join(lines)


class CLIExporter:
    """Exports Network IR to a plain text Cisco IOS configuration bundle."""

    @classmethod
    def export(cls, ir: NetworkIR) -> str:
        data = ir.to_dict() if isinstance(ir, NetworkIR) else ir
        lines = [
            "! ===========================================",
            f"! Cisco IOS Configuration Bundle: {data.get('name', 'Network')}",
            "! Generated from Network IR (Intermediate Representation)",
            "! ===========================================\n"
        ]

        for dev in data.get("devices", data.get("nodes", [])):
            dev_id = dev.get("label", dev["id"])
            dev_type = dev.get("type")
            all_chunks = dev.get("phase2_chunks", []) + dev.get("phase3_chunks", []) + dev.get("phase4_chunks", [])
            
            if all_chunks:
                lines.append(f"! --- Device: {dev_id} ({dev_type}) ---")
                for chunk in all_chunks:
                    lines.extend(chunk)
                lines.append("\n")
            elif dev.get("ios_config"):
                lines.append(f"! --- Device: {dev_id} ({dev_type}) ---")
                lines.extend(dev["ios_config"])
                lines.append("\n")

        return "\n".join(lines)


class XMLExporter:
    """Exports Network IR to Cisco Packet Tracer XML schema."""

    @classmethod
    def export(cls, ir: NetworkIR) -> str:
        data = ir.to_dict() if isinstance(ir, NetworkIR) else ir
        root = ET.Element("PACKET_TRACER_NETWORK", {
            "version": "8.2",
            "name": data.get("name", "Network Topology"),
            "generator": "Packet_XML Network IR Engine"
        })

        # 1. Metadata Section
        meta = ET.SubElement(root, "METADATA")
        ET.SubElement(meta, "TOTAL_DEVICES").text = str(len(data.get("devices", data.get("nodes", []))))
        ET.SubElement(meta, "TOTAL_LINKS").text = str(len(data.get("links", [])))
        ET.SubElement(meta, "ROUTING_PROTOCOL").text = str(data.get("routing_protocol", "OSPF"))
        ET.SubElement(meta, "BASE_NETWORK").text = str(data.get("base_network", "10.0.0.0/16"))

        # 2. VLANS Section
        vlans_elem = ET.SubElement(root, "VLANS")
        for vlan in data.get("vlans", []):
            v_id = str(vlan.get("vlan", vlan.get("id", 1)))
            v_elem = ET.SubElement(vlans_elem, "VLAN", {"id": v_id})
            ET.SubElement(v_elem, "NAME").text = str(vlan.get("name", ""))
            ET.SubElement(v_elem, "NETWORK").text = str(vlan.get("network", "N/A"))
            ET.SubElement(v_elem, "PREFIX").text = str(vlan.get("prefix", "N/A"))
            ET.SubElement(v_elem, "NETMASK").text = str(vlan.get("netmask", "N/A"))
            ET.SubElement(v_elem, "GATEWAY").text = str(vlan.get("gateway", "N/A"))
            ET.SubElement(v_elem, "LAYER3").text = str(vlan.get("layer3", v_id != "99"))

        # 3. Devices Section
        devices_elem = ET.SubElement(root, "DEVICES")
        for dev in data.get("devices", data.get("nodes", [])):
            d_elem = ET.SubElement(devices_elem, "DEVICE", {
                "id": str(dev.get("id")),
                "type": str(dev.get("type")),
                "model": str(dev.get("model", "")),
                "layer": str(dev.get("layer", ""))
            })
            ET.SubElement(d_elem, "LABEL").text = str(dev.get("label", dev.get("id")))
            ET.SubElement(d_elem, "POSITION_X").text = str(int(dev.get("x", 0)))
            ET.SubElement(d_elem, "POSITION_Y").text = str(int(dev.get("y", 0)))

            if dev.get("ip"):
                ip_cfg = ET.SubElement(d_elem, "IP_CONFIG")
                ET.SubElement(ip_cfg, "IP_ADDRESS").text = str(dev.get("ip"))
                ET.SubElement(ip_cfg, "NETMASK").text = str(dev.get("netmask", ""))
                ET.SubElement(ip_cfg, "GATEWAY").text = str(dev.get("gateway", ""))
                ET.SubElement(ip_cfg, "DNS").text = str(dev.get("dns", "8.8.8.8"))
                if dev.get("vlan"):
                    ET.SubElement(ip_cfg, "VLAN").text = str(dev.get("vlan"))

        # 4. Links Section
        links_elem = ET.SubElement(root, "LINKS")
        for link in data.get("links", []):
            l_elem = ET.SubElement(links_elem, "LINK", {
                "id": str(link.get("id")),
                "type": str(link.get("type", "Copper_Straight")),
                "mode": str(link.get("mode", "access"))
            })
            ET.SubElement(l_elem, "SOURCE", {"port": str(link.get("src_port", ""))}).text = str(link.get("source"))
            ET.SubElement(l_elem, "TARGET", {"port": str(link.get("dst_port", ""))}).text = str(link.get("target"))
            if link.get("vlan"):
                ET.SubElement(l_elem, "VLAN").text = str(link.get("vlan"))
            if link.get("native_vlan"):
                ET.SubElement(l_elem, "NATIVE_VLAN").text = str(link.get("native_vlan"))

        # Pretty Print XML
        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(raw_xml)
        return parsed.toprettyxml(indent="  ")


class PKTExporter:
    """Exports Network IR directly to a binary Cisco Packet Tracer .pkt container without opening the application."""

    @classmethod
    def export(cls, ir: NetworkIR, output_path: Optional[str] = None) -> bytes:
        from pkt_encoder import PKTEncoder
        res = PKTEncoder.generate_pkt(ir, output_path=output_path)
        return res["pkt_bytes"]

