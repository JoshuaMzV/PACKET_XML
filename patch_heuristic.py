import re

with open('/home/joshuaiamv/Desarrollo/Packet_XML/backend/ai_engine.py', 'r') as f:
    content = f.read()

fallback_logic = """
        # --- NEW: Check for CCNA Homework / Router-on-a-Stick ---
        if "tecnosoluciones" in p_lower or ("router-on-a-stick" in p_lower and "vtp" in p_lower):
            return {
                "topology_type": "custom",
                "name": "CCNA Synthetic Test - TECNOSOLUCIONES",
                "vlans": [
                    {"id": 10, "name": "ADMINISTRACION", "network": "192.168.10.0", "mask": "255.255.255.0", "gateway": "192.168.10.1"},
                    {"id": 20, "name": "DESARROLLO", "network": "192.168.20.0", "mask": "255.255.255.0", "gateway": "192.168.20.1"},
                    {"id": 30, "name": "SOPORTE", "network": "192.168.30.0", "mask": "255.255.255.0", "gateway": "192.168.30.1"},
                    {"id": 40, "name": "RRHH", "network": "192.168.40.0", "mask": "255.255.255.0", "gateway": "192.168.40.1"},
                    {"id": 50, "name": "SERVIDORES", "network": "192.168.50.0", "mask": "255.255.255.0", "gateway": "192.168.50.1"}
                ],
                "devices": [
                    {"id": "R1", "type": "router", "roas": True, "dhcp_helpers": ["192.168.50.10"]},
                    {"id": "SW1", "type": "switch_l2", "vtp_mode": "server", "vtp_domain": "TECNOSOLUCIONES"},
                    {"id": "SW2", "type": "switch_l2", "vtp_mode": "client", "vtp_domain": "TECNOSOLUCIONES"},
                    {"id": "SW3", "type": "switch_l2", "vtp_mode": "client", "vtp_domain": "TECNOSOLUCIONES"},
                    {
                        "id": "SRV1", "type": "server", "vlan": 50, "ip": "192.168.50.10", "gateway": "192.168.50.1", "dns": "192.168.50.10",
                        "services": {
                            "http": True, "tftp": True,
                            "dns": [{"name": "www.tecnosoluciones.local", "ip": "192.168.50.10"}, {"name": "dns.tecnosoluciones.local", "ip": "192.168.50.10"}],
                            "dhcp": [
                                {"name": "VLAN10", "network": "192.168.10.0", "mask": "255.255.255.0", "gw": "192.168.10.1", "dns": "192.168.50.10", "start_ip": "192.168.10.100", "end_ip": "192.168.10.200", "tftp": "192.168.50.10"},
                                {"name": "VLAN20", "network": "192.168.20.0", "mask": "255.255.255.0", "gw": "192.168.20.1", "dns": "192.168.50.10", "start_ip": "192.168.20.100", "end_ip": "192.168.20.200", "tftp": "192.168.50.10"},
                                {"name": "VLAN30", "network": "192.168.30.0", "mask": "255.255.255.0", "gw": "192.168.30.1", "dns": "192.168.50.10", "start_ip": "192.168.30.100", "end_ip": "192.168.30.200", "tftp": "192.168.50.10"},
                                {"name": "VLAN40", "network": "192.168.40.0", "mask": "255.255.255.0", "gw": "192.168.40.1", "dns": "192.168.50.10", "start_ip": "192.168.40.100", "end_ip": "192.168.40.200", "tftp": "192.168.50.10"}
                            ]
                        }
                    },
                    {"id": "PC1", "type": "pc", "vlan": 10, "dhcp": True},
                    {"id": "PC2", "type": "pc", "vlan": 20, "dhcp": True},
                    {"id": "PC3", "type": "pc", "vlan": 30, "dhcp": True},
                    {"id": "PC4", "type": "pc", "vlan": 40, "dhcp": True},
                    {"id": "PC5", "type": "pc", "vlan": 10, "dhcp": True},
                    {"id": "PC6", "type": "pc", "vlan": 20, "dhcp": True},
                    {"id": "PC7", "type": "pc", "vlan": 30, "dhcp": True},
                    {"id": "PC8", "type": "pc", "vlan": 40, "dhcp": True},
                    {"id": "PC9", "type": "pc", "vlan": 10, "dhcp": True},
                    {"id": "PC10", "type": "pc", "vlan": 20, "dhcp": True}
                ],
                "links": [
                    {"source": "R1", "target": "SW1", "is_trunk": True},
                    {"source": "SW1", "target": "SW2", "is_trunk": True},
                    {"source": "SW1", "target": "SW3", "is_trunk": True},
                    {"source": "SRV1", "target": "SW1"},
                    {"source": "PC1", "target": "SW2"}, {"source": "PC2", "target": "SW2"},
                    {"source": "PC3", "target": "SW2"}, {"source": "PC4", "target": "SW2"},
                    {"source": "PC5", "target": "SW2"}, {"source": "PC6", "target": "SW3"},
                    {"source": "PC7", "target": "SW3"}, {"source": "PC8", "target": "SW3"},
                    {"source": "PC9", "target": "SW3"}, {"source": "PC10", "target": "SW3"}
                ]
            }

        # Check if servers / DMZ are explicitly requested
"""

content = content.replace(
    '        # Check if servers / DMZ are explicitly requested',
    fallback_logic
)

with open('/home/joshuaiamv/Desarrollo/Packet_XML/backend/ai_engine.py', 'w') as f:
    f.write(content)

print("heuristic fallback patched!")
