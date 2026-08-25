import re

with open('/home/joshuaiamv/Desarrollo/Packet_XML/backend/ai_engine.py', 'r') as f:
    content = f.read()

# 1. Import CustomTopologyParser
if 'from custom_topology_parser import CustomTopologyParser' not in content:
    content = content.replace(
        'from network_engine import NetworkEngine',
        'from network_engine import NetworkEngine\nfrom custom_topology_parser import CustomTopologyParser'
    )

# 2. Update system_instruction
new_instruction = """        system_instruction = (
            "You are a Senior Cisco CCIE Network Architect. Your job is to analyze the user's network requirements "
            "and output a strictly valid JSON object with the design specifications for Cisco Packet Tracer.\\n"
            "If the request is a specific scenario, homework, or requires Router-on-a-Stick, specific IP layouts, or VTP, "
            "you MUST use topology_type: 'custom' and output the FULL layout.\\n"
            "Respond ONLY with a valid JSON object matching ONE of these schemas:\\n"
            "Schema 1 (Generic):\\n"
            "{\\n"
            '  "topology_type": "basic" | "hierarchical",\\n'
            '  "name": "Network Project Name",\\n'
            '  "routers_count": <int>, "switches_count": <int>, "pcs_count": <int>,\\n'
            '  "include_servers": true | false,\\n'
            '  "routing_protocol": "ospf" | "rip" | "static",\\n'
            '  "base_network": "192.168.1.0/24"\\n'
            "}\\n"
            "Schema 2 (Custom/Specific CCNA Task):\\n"
            "{\\n"
            '  "topology_type": "custom",\\n'
            '  "name": "CCNA Lab",\\n'
            '  "vlans": [{"id": 10, "name": "Admin", "network": "192.168.10.0", "mask": "255.255.255.0", "gateway": "192.168.10.1"}],\\n'
            '  "devices": [\\n'
            '    {"id": "R1", "type": "router", "roas": true, "dhcp_helpers": ["192.168.50.10"]},\\n'
            '    {"id": "SW1", "type": "switch_l2", "vtp_mode": "server", "vtp_domain": "LAB"},\\n'
            '    {"id": "SRV1", "type": "server", "vlan": 50, "services": {"dhcp": [{"network": "192.168.10.0", "mask": "255.255.255.0", "gw": "192.168.10.1"}], "dns": [{"name": "www.test.com", "ip": "192.168.50.10"}], "http": true, "tftp": true}},\\n'
            '    {"id": "PC1", "type": "pc", "vlan": 10, "dhcp": true}\\n'
            '  ],\\n'
            '  "links": [{"source": "R1", "target": "SW1", "is_trunk": true}, {"source": "SW1", "target": "PC1"}]\\n'
            "}"
        )"""

content = re.sub(
    r'system_instruction = \([\s\S]*?\)\s*design_params = None',
    new_instruction + '\n\n        design_params = None',
    content
)

# 3. Add 'custom' topology execution logic
custom_logic = """        if topo_type == "custom":
            topology = CustomTopologyParser.build_ir(design_params)
        elif topo_type == "basic":"""

content = content.replace(
    '        if topo_type == "basic":',
    custom_logic
)

with open('/home/joshuaiamv/Desarrollo/Packet_XML/backend/ai_engine.py', 'w') as f:
    f.write(content)

print("ai_engine.py patched successfully!")
