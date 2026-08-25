import sys
from pathlib import Path
sys.path.append('/home/joshuaiamv/Desarrollo/Packet_XML/backend')

from network_ir import NetworkIR
from pkt_encoder import PKTEncoder
from exporters import JSExporter, CLIExporter

# We will build the Network IR directly since this is a highly customized CCNA topology
# that network_engine's generic hierarchical generator doesn't specifically model natively yet.

topology = {
    "name": "CCNA Synthetic Test - TECNOSOLUCIONES",
    "devices": [],
    "links": [],
    "vlans": [
        {"id": 10, "name": "ADMINISTRACION", "is_l3": True, "network": "192.168.10.0", "mask": "255.255.255.0", "gateway": "192.168.10.1"},
        {"id": 20, "name": "DESARROLLO", "is_l3": True, "network": "192.168.20.0", "mask": "255.255.255.0", "gateway": "192.168.20.1"},
        {"id": 30, "name": "SOPORTE", "is_l3": True, "network": "192.168.30.0", "mask": "255.255.255.0", "gateway": "192.168.30.1"},
        {"id": 40, "name": "RRHH", "is_l3": True, "network": "192.168.40.0", "mask": "255.255.255.0", "gateway": "192.168.40.1"},
        {"id": 50, "name": "SERVIDORES", "is_l3": True, "network": "192.168.50.0", "mask": "255.255.255.0", "gateway": "192.168.50.1"}
    ]
}

# R1 Configuration (Router-on-a-Stick + DHCP Helpers)
r1_config = [
    "interface GigabitEthernet0/0",
    " no shutdown",
    " no ip address"
]
for v in [10, 20, 30, 40, 50]:
    r1_config.extend([
        f"interface GigabitEthernet0/0.{v}",
        f" encapsulation dot1Q {v}",
        f" ip address 192.168.{v}.1 255.255.255.0",
    ])
    if v != 50:
        r1_config.append(" ip helper-address 192.168.50.10")

topology["devices"].append({
    "id": "R1", "name": "R1", "type": "router", "x": 500, "y": 100,
    "ios_config": r1_config
})

# SW1 Configuration (VTP Server, Trunks)
topology["devices"].append({
    "id": "SW1", "name": "SW1", "type": "switch_l2", "x": 500, "y": 250,
    "ios_config": [
        "vtp mode server",
        "vtp domain TECNOSOLUCIONES",
        "vtp password cisco",
        "interface GigabitEthernet0/1", " switchport mode trunk", # To R1
        "interface GigabitEthernet0/2", " switchport mode trunk", # To SW2
        "interface GigabitEthernet0/3", " switchport mode trunk", # To SW3
        "interface FastEthernet0/1", " switchport mode access", " switchport access vlan 50" # To SRV1
    ]
})

# SW2 & SW3 (VTP Clients, Trunks)
for i, sw_id in enumerate(["SW2", "SW3"]):
    topology["devices"].append({
        "id": sw_id, "name": sw_id, "type": "switch_l2", "x": 300 + (i*400), "y": 400,
        "ios_config": [
            "vtp mode client",
            "vtp domain TECNOSOLUCIONES",
            "vtp password cisco",
            "interface GigabitEthernet0/1", " switchport mode trunk"
        ]
    })

# Server SRV1
dhcp_pools = []
for v in [10, 20, 30, 40]:
    dhcp_pools.append({
        "name": f"VLAN{v}_POOL",
        "network": f"192.168.{v}.0",
        "mask": "255.255.255.0",
        "gw": f"192.168.{v}.1",
        "dns": "192.168.50.10",
        "start_ip": f"192.168.{v}.100",
        "end_ip": f"192.168.{v}.200",
        "tftp": "192.168.50.10"
    })

topology["devices"].append({
    "id": "SRV1", "name": "SRV1", "type": "server", "x": 700, "y": 250,
    "ip": "192.168.50.10", "netmask": "255.255.255.0", "gateway": "192.168.50.1", "dns": "192.168.50.10",
    "services": {
        "http": True,
        "tftp": True,
        "dns": [
            {"name": "www.tecnosoluciones.local", "ip": "192.168.50.10"},
            {"name": "dns.tecnosoluciones.local", "ip": "192.168.50.10"}
        ],
        "dhcp": dhcp_pools
    }
})

# PCs
vlan_assignment = [10, 20, 30, 40, 10, 20, 30, 40, 10, 20] # 10 PCs
for idx, v in enumerate(vlan_assignment):
    pc_id = f"PC{idx+1}"
    sw_id = "SW2" if idx < 5 else "SW3"
    topology["devices"].append({
        "id": pc_id, "name": pc_id, "type": "pc",
        "x": 200 + (idx * 60), "y": 550,
        "dhcp": True, # Ensure it uses DHCP instead of static
    })
    # Add link to switch
    fe_port = f"FastEthernet0/{idx+1}"
    topology["links"].append({"source": pc_id, "target": sw_id, "s_port": "FastEthernet0", "t_port": fe_port})
    # Configure switchport
    sw_dev = next(d for d in topology["devices"] if d["id"] == sw_id)
    sw_dev["ios_config"].extend([f"interface {fe_port}", " switchport mode access", f" switchport access vlan {v}"])

# Trunks and Server Links
topology["links"].extend([
    {"source": "R1", "target": "SW1", "s_port": "GigabitEthernet0/0", "t_port": "GigabitEthernet0/1"},
    {"source": "SW1", "target": "SW2", "s_port": "GigabitEthernet0/2", "t_port": "GigabitEthernet0/1"},
    {"source": "SW1", "target": "SW3", "s_port": "GigabitEthernet0/3", "t_port": "GigabitEthernet0/1"},
    {"source": "SRV1", "target": "SW1", "s_port": "FastEthernet0", "t_port": "FastEthernet0/1"}
])

ir = NetworkIR(topology)
out_pkt = Path('/home/joshuaiamv/Desarrollo/Packet_XML/output/tecnosoluciones.pkt')
PKTEncoder.generate_pkt(ir, output_path=out_pkt, pt_version='9.0')
print(f"✅ Generated {out_pkt}")
