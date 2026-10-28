import os
import sys
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

# Add backend to path
sys.path.append("/home/joshuaiamv/Desarrollo/Packet_XML/backend")
from pkt_encoder import PKTEncoder

def build_perfect_pkt():
    print("Iniciando construcción perfecta con Cisco 1841 y Catalyst 2950...")
    
    # 1. Load base template & archetypes
    archetypes, base_root = PKTEncoder._load_template_archetypes()
    
    # Load native 1841 archetype from 1841_real.xml
    tree_1841 = ET.parse("/home/joshuaiamv/Desarrollo/Packet_XML/backend/templates/1841_real.xml")
    arch_1841 = tree_1841.getroot()
    
    # Switch archetype: use 2960 archetype but customize model attribute to 2950-24
    arch_2950 = copy.deepcopy(archetypes["2960-24TT"])
    eng_2950 = arch_2950.find("ENGINE")
    if eng_2950 is not None and eng_2950.find("TYPE") is not None:
        eng_2950.find("TYPE").set("model", "2950-24")
    
    root = copy.deepcopy(base_root)
    net = root.find("NETWORK")
    devs_container = net.find("DEVICES")
    devs_container.clear()
    links_container = net.find("LINKS")
    links_container.clear()
    
    banner_text = (
        "*****************************************************\\n"
        "* ACCESO NO AUTORIZADO ESTA ESTRICTAMENTE PROHIBIDO *\\n"
        "* SISTEMA MONITOREADO Y REGISTRADO - UMG 2026       *\\n"
        "*****************************************************"
    )
    
    # Router configurations
    # Note: Cisco 1841 has FastEthernet0/0, FastEthernet0/1, Serial0/0/0, Serial0/0/1
    r0_config = [
        "hostname Router0",
        "service password-encryption",
        "enable secret cisco",
        f"banner motd #{banner_text}#",
        "username admin privilege 15 secret cisco",
        "ip domain-name umg.edu.gt",
        "crypto key generate rsa modulus 2048",
        # LAN Interfaces
        "interface FastEthernet0/0",
        " description LAN_Subred_G",
        " ip address 172.16.12.225 255.255.255.224",
        " no shutdown",
        "interface FastEthernet0/1",
        " description LAN_Subred_H",
        " ip address 172.16.10.1 255.255.254.0",
        " no shutdown",
        # WAN Interfaces (Serial)
        "interface Serial0/0/0",
        " description WAN_Subred_A_to_R1",
        " ip address 172.16.13.17 255.255.255.252",
        " clock rate 64000",
        " no shutdown",
        "interface Serial0/0/1",
        " description WAN_Subred_C_to_R2",
        " ip address 172.16.13.25 255.255.255.252",
        " clock rate 64000",
        " no shutdown",
        # DHCP
        "ip dhcp excluded-address 172.16.12.225 172.16.12.235",
        "ip dhcp excluded-address 172.16.10.1 172.16.10.10",
        "ip dhcp pool POOL_SUBRED_G",
        " network 172.16.12.224 255.255.255.224",
        " default-router 172.16.12.225",
        " dns-server 172.16.12.226",
        "ip dhcp pool POOL_SUBRED_H",
        " network 172.16.10.0 255.255.254.0",
        " default-router 172.16.10.1",
        " dns-server 172.16.12.226",
        # OSPF
        "router ospf 10",
        " router-id 1.1.1.1",
        " network 172.16.0.0 0.0.255.255 area 0",
        # Access security
        "line con 0",
        " password cisco",
        " login",
        "line vty 0 4",
        " login local",
        " transport input ssh"
    ]
    
    r1_config = [
        "hostname Router1",
        "service password-encryption",
        "enable secret cisco",
        f"banner motd #{banner_text}#",
        "username admin privilege 15 secret cisco",
        "ip domain-name umg.edu.gt",
        "crypto key generate rsa modulus 2048",
        # LAN Interfaces
        "interface FastEthernet0/0",
        " description LAN_Subred_E",
        " ip address 172.16.12.129 255.255.255.192",
        " no shutdown",
        "interface FastEthernet0/1",
        " description LAN_Subred_F",
        " ip address 172.16.12.1 255.255.255.128",
        " no shutdown",
        # WAN Interfaces (Serial)
        "interface Serial0/0/0",
        " description WAN_Subred_A_to_R0",
        " ip address 172.16.13.18 255.255.255.252",
        " no shutdown",
        "interface Serial0/0/1",
        " description WAN_Subred_B_to_R3",
        " ip address 172.16.13.21 255.255.255.252",
        " clock rate 64000",
        " no shutdown",
        # DHCP
        "ip dhcp excluded-address 172.16.12.129 172.16.12.135",
        "ip dhcp excluded-address 172.16.12.1 172.16.12.10",
        "ip dhcp pool POOL_SUBRED_E",
        " network 172.16.12.128 255.255.255.192",
        " default-router 172.16.12.129",
        " dns-server 172.16.12.226",
        "ip dhcp pool POOL_SUBRED_F",
        " network 172.16.12.0 255.255.255.128",
        " default-router 172.16.12.1",
        " dns-server 172.16.12.226",
        # OSPF
        "router ospf 10",
        " router-id 2.2.2.2",
        " network 172.16.0.0 0.0.255.255 area 0",
        # Access security
        "line con 0",
        " password cisco",
        " login",
        "line vty 0 4",
        " login local",
        " transport input ssh"
    ]
    
    r2_config = [
        "hostname Router2",
        "service password-encryption",
        "enable secret cisco",
        f"banner motd #{banner_text}#",
        "username admin privilege 15 secret cisco",
        "ip domain-name umg.edu.gt",
        "crypto key generate rsa modulus 2048",
        # LAN Interfaces
        "interface FastEthernet0/0",
        " description LAN_Subred_K",
        " ip address 172.16.12.193 255.255.255.224",
        " no shutdown",
        "interface FastEthernet0/1",
        " description LAN_Subred_L",
        " ip address 172.16.0.1 255.255.248.0",
        " no shutdown",
        # WAN Interfaces (Serial)
        "interface Serial0/0/0",
        " description WAN_Subred_C_to_R0",
        " ip address 172.16.13.26 255.255.255.252",
        " no shutdown",
        "interface Serial0/0/1",
        " description WAN_Subred_D_to_R3",
        " ip address 172.16.13.29 255.255.255.252",
        " clock rate 64000",
        " no shutdown",
        # DHCP
        "ip dhcp excluded-address 172.16.12.193 172.16.12.200",
        "ip dhcp excluded-address 172.16.0.1 172.16.0.20",
        "ip dhcp pool POOL_SUBRED_K",
        " network 172.16.12.192 255.255.255.224",
        " default-router 172.16.12.193",
        " dns-server 172.16.12.226",
        "ip dhcp pool POOL_SUBRED_L",
        " network 172.16.0.0 255.255.248.0",
        " default-router 172.16.0.1",
        " dns-server 172.16.12.226",
        # OSPF + Default route propagation
        "router ospf 10",
        " router-id 3.3.3.3",
        " network 172.16.0.0 0.0.255.255 area 0",
        " default-information originate",
        # Floating route & static
        "ip route 0.0.0.0 0.0.0.0 200.100.50.2",
        "ip route 172.16.0.0 255.255.240.0 Null0 250",
        # Access security
        "line con 0",
        " password cisco",
        " login",
        "line vty 0 4",
        " login local",
        " transport input ssh"
    ]
    
    r3_config = [
        "hostname Router3",
        "service password-encryption",
        "enable secret cisco",
        f"banner motd #{banner_text}#",
        "username admin privilege 15 secret cisco",
        "ip domain-name umg.edu.gt",
        "crypto key generate rsa modulus 2048",
        # LAN Interfaces
        "interface FastEthernet0/0",
        " description LAN_Subred_I",
        " ip address 172.16.13.1 255.255.255.240",
        " no shutdown",
        "interface FastEthernet0/1",
        " description LAN_Subred_J",
        " ip address 172.16.8.1 255.255.254.0",
        " no shutdown",
        # WAN Interfaces (Serial)
        "interface Serial0/0/0",
        " description WAN_Subred_B_to_R1",
        " ip address 172.16.13.22 255.255.255.252",
        " no shutdown",
        "interface Serial0/0/1",
        " description WAN_Subred_D_to_R2",
        " ip address 172.16.13.30 255.255.255.252",
        " no shutdown",
        # DHCP
        "ip dhcp excluded-address 172.16.13.1 172.16.13.5",
        "ip dhcp excluded-address 172.16.8.1 172.16.8.10",
        "ip dhcp pool POOL_SUBRED_I",
        " network 172.16.13.0 255.255.255.240",
        " default-router 172.16.13.1",
        " dns-server 172.16.12.226",
        "ip dhcp pool POOL_SUBRED_J",
        " network 172.16.8.0 255.255.254.0",
        " default-router 172.16.8.1",
        " dns-server 172.16.12.226",
        # OSPF
        "router ospf 10",
        " router-id 4.4.4.4",
        " network 172.16.0.0 0.0.255.255 area 0",
        # Access security
        "line con 0",
        " password cisco",
        " login",
        "line vty 0 4",
        " login local",
        " transport input ssh"
    ]
    
    def switch_config(name):
        return [
            f"hostname {name}",
            "service password-encryption",
            "enable secret cisco",
            f"banner motd #{banner_text}#",
            "line con 0",
            " password cisco",
            " login",
            "line vty 0 15",
            " password cisco",
            " login"
        ]

    # Device definitions
    devices_def = [
        # Routers (Cisco 1841)
        {"id": "Router0", "label": "Router0", "type": "router_1841", "x": 500, "y": 280, "config": r0_config},
        {"id": "Router1", "label": "Router1", "type": "router_1841", "x": 500, "y": 550, "config": r1_config},
        {"id": "Router2", "label": "Router2", "type": "router_1841", "x": 900, "y": 280, "config": r2_config},
        {"id": "Router3", "label": "Router3", "type": "router_1841", "x": 900, "y": 550, "config": r3_config},
        
        # Switches (Catalyst 2950-24)
        {"id": "Switch0", "label": "Switch0", "type": "switch_2950", "x": 300, "y": 520, "config": switch_config("Switch0")},
        {"id": "Switch1", "label": "Switch1", "type": "switch_2950", "x": 500, "y": 720, "config": switch_config("Switch1")},
        {"id": "Switch2", "label": "Switch2", "type": "switch_2950", "x": 900, "y": 700, "config": switch_config("Switch2")},
        {"id": "Switch3", "label": "Switch3", "type": "switch_2950", "x": 1050, "y": 600, "config": switch_config("Switch3")},
        {"id": "Switch4", "label": "Switch4", "type": "switch_2950", "x": 1100, "y": 200, "config": switch_config("Switch4")},
        {"id": "Switch5", "label": "Switch5", "type": "switch_2950", "x": 1100, "y": 400, "config": switch_config("Switch5")},
        {"id": "Switch6", "label": "Switch6", "type": "switch_2950", "x": 250, "y": 340, "config": switch_config("Switch6")},
        {"id": "Switch7", "label": "Switch7", "type": "switch_2950", "x": 500, "y": 100, "config": switch_config("Switch7")},
        
        # PCs
        {"id": "PC0", "label": "PC0", "type": "pc", "x": 150, "y": 600, "ip": "172.16.12.130", "netmask": "255.255.255.192", "gateway": "172.16.12.129", "dns": "172.16.12.226"},
        {"id": "PC1", "label": "PC1", "type": "pc", "x": 350, "y": 780, "ip": "172.16.12.10", "netmask": "255.255.255.128", "gateway": "172.16.12.1", "dns": "172.16.12.226"},
        {"id": "PC2", "label": "PC2", "type": "pc", "x": 1050, "y": 800, "ip": "172.16.13.2", "netmask": "255.255.255.240", "gateway": "172.16.13.1", "dns": "172.16.12.226"},
        {"id": "PC3", "label": "PC3", "type": "pc", "x": 1200, "y": 680, "ip": "172.16.8.10", "netmask": "255.255.254.0", "gateway": "172.16.8.1", "dns": "172.16.12.226"},
        {"id": "PC4", "label": "PC4", "type": "pc", "x": 1300, "y": 400, "ip": "172.16.0.10", "netmask": "255.255.248.0", "gateway": "172.16.0.1", "dns": "172.16.12.226"},
        {"id": "PC5", "label": "PC5", "type": "pc", "x": 1300, "y": 200, "ip": "172.16.12.194", "netmask": "255.255.255.224", "gateway": "172.16.12.193", "dns": "172.16.12.226"},
        
        # Servers
        {
            "id": "Server-PT HTTP", "label": "Server-PT HTTP", "type": "server", "x": 100, "y": 200,
            "ip": "172.16.12.226", "netmask": "255.255.255.224", "gateway": "172.16.12.225", "dns": "172.16.12.226",
            "services": {
                "http": True,
                "dns": [
                    {"name": "www.umg.edu.gt", "ip": "172.16.12.226", "type": "A-REC"},
                    {"name": "campus.umg.edu.gt", "ip": "172.16.12.226", "type": "A-REC"},
                    {"name": "ftp.umg.edu.gt", "ip": "172.16.12.227", "type": "A-REC"},
                    {"name": "dhcp.umg.edu.gt", "ip": "172.16.10.2", "type": "A-REC"},
                    {"name": "tftp.umg.edu.gt", "ip": "172.16.12.2", "type": "A-REC"}
                ]
            }
        },
        {
            "id": "Server-PT FTP", "label": "Server-PT FTP", "type": "server", "x": 200, "y": 150,
            "ip": "172.16.12.227", "netmask": "255.255.255.224", "gateway": "172.16.12.225", "dns": "172.16.12.226",
            "services": {"ftp": True}
        },
        {
            "id": "Server-PT DHCP", "label": "Server-PT DHCP", "type": "server", "x": 650, "y": 100,
            "ip": "172.16.10.2", "netmask": "255.255.254.0", "gateway": "172.16.10.1", "dns": "172.16.12.226",
            "services": {
                "dhcp": [
                    {
                        "name": "POOL_SUBRED_H",
                        "network": "172.16.10.0",
                        "mask": "255.255.254.0",
                        "gw": "172.16.10.1",
                        "dns": "172.16.12.226",
                        "start_ip": "172.16.10.15",
                        "end_ip": "172.16.11.254"
                    }
                ]
            }
        },
        {
            "id": "Server-PT TFTP", "label": "Server-PT TFTP", "type": "server", "x": 650, "y": 720,
            "ip": "172.16.12.2", "netmask": "255.255.255.128", "gateway": "172.16.12.1", "dns": "172.16.12.226",
            "services": {"tftp": True}
        }
    ]

    # Perfect Links definition strictly matching image3.png and hardware specs
    links_def = [
        # WAN Serial links between 1841 routers
        # Subred A: R0 (Serial0/0/0) <---> R1 (Serial0/0/0)
        {"src": "Router0", "src_port": "Serial0/0/0", "dst": "Router1", "dst_port": "Serial0/0/0", "type": "serial", "dce": "Router0"},
        # Subred B: R1 (Serial0/0/1) <---> R3 (Serial0/0/0)
        {"src": "Router1", "src_port": "Serial0/0/1", "dst": "Router3", "dst_port": "Serial0/0/0", "type": "serial", "dce": "Router1"},
        # Subred C: R0 (Serial0/0/1) <---> R2 (Serial0/0/0)
        {"src": "Router0", "src_port": "Serial0/0/1", "dst": "Router2", "dst_port": "Serial0/0/0", "type": "serial", "dce": "Router0"},
        # Subred D: R2 (Serial0/0/1) <---> R3 (Serial0/0/1)
        {"src": "Router2", "src_port": "Serial0/0/1", "dst": "Router3", "dst_port": "Serial0/0/1", "type": "serial", "dce": "Router2"},
        
        # Router to Switch links (LAN gateways via FastEthernet)
        # R0 to SW6 (Subred G: Fa0/0 -> Fa0/1)
        {"src": "Router0", "src_port": "FastEthernet0/0", "dst": "Switch6", "dst_port": "FastEthernet0/1", "type": "copper"},
        # R0 to SW7 (Subred H: Fa0/1 -> Fa0/1)
        {"src": "Router0", "src_port": "FastEthernet0/1", "dst": "Switch7", "dst_port": "FastEthernet0/1", "type": "copper"},
        # R1 to SW0 (Subred E: Fa0/0 -> Fa0/1)
        {"src": "Router1", "src_port": "FastEthernet0/0", "dst": "Switch0", "dst_port": "FastEthernet0/1", "type": "copper"},
        # R1 to SW1 (Subred F: Fa0/1 -> Fa0/1)
        {"src": "Router1", "src_port": "FastEthernet0/1", "dst": "Switch1", "dst_port": "FastEthernet0/1", "type": "copper"},
        # R2 to SW4 (Subred K: Fa0/0 -> Fa0/1)
        {"src": "Router2", "src_port": "FastEthernet0/0", "dst": "Switch4", "dst_port": "FastEthernet0/1", "type": "copper"},
        # R2 to SW5 (Subred L: Fa0/1 -> Fa0/1)
        {"src": "Router2", "src_port": "FastEthernet0/1", "dst": "Switch5", "dst_port": "FastEthernet0/1", "type": "copper"},
        # R3 to SW2 (Subred I: Fa0/0 -> Fa0/1)
        {"src": "Router3", "src_port": "FastEthernet0/0", "dst": "Switch2", "dst_port": "FastEthernet0/1", "type": "copper"},
        # R3 to SW3 (Subred J: Fa0/1 -> Fa0/1)
        {"src": "Router3", "src_port": "FastEthernet0/1", "dst": "Switch3", "dst_port": "FastEthernet0/1", "type": "copper"},
        
        # Switch to End Device links (Fa0/2, Fa0/3 -> FastEthernet0)
        # SW0 to PC0 (Subred E)
        {"src": "Switch0", "src_port": "FastEthernet0/2", "dst": "PC0", "dst_port": "FastEthernet0", "type": "copper"},
        # SW1 to PC1, TFTP (Subred F)
        {"src": "Switch1", "src_port": "FastEthernet0/2", "dst": "PC1", "dst_port": "FastEthernet0", "type": "copper"},
        {"src": "Switch1", "src_port": "FastEthernet0/3", "dst": "Server-PT TFTP", "dst_port": "FastEthernet0", "type": "copper"},
        # SW2 to PC2 (Subred I)
        {"src": "Switch2", "src_port": "FastEthernet0/2", "dst": "PC2", "dst_port": "FastEthernet0", "type": "copper"},
        # SW3 to PC3 (Subred J)
        {"src": "Switch3", "src_port": "FastEthernet0/2", "dst": "PC3", "dst_port": "FastEthernet0", "type": "copper"},
        # SW4 to PC5 (Subred K)
        {"src": "Switch4", "src_port": "FastEthernet0/2", "dst": "PC5", "dst_port": "FastEthernet0", "type": "copper"},
        # SW5 to PC4 (Subred L)
        {"src": "Switch5", "src_port": "FastEthernet0/2", "dst": "PC4", "dst_port": "FastEthernet0", "type": "copper"},
        # SW6 to HTTP, FTP (Subred G)
        {"src": "Switch6", "src_port": "FastEthernet0/2", "dst": "Server-PT HTTP", "dst_port": "FastEthernet0", "type": "copper"},
        {"src": "Switch6", "src_port": "FastEthernet0/3", "dst": "Server-PT FTP", "dst_port": "FastEthernet0", "type": "copper"},
        # SW7 to DHCP (Subred H)
        {"src": "Switch7", "src_port": "FastEthernet0/2", "dst": "Server-PT DHCP", "dst_port": "FastEthernet0", "type": "copper"}
    ]

    base_mem = 93868000000000
    dev_map = {}

    for idx, dev in enumerate(devices_def):
        dev_id = dev["id"]
        d_name = dev.get("label", dev_id)
        save_ref = f"save-ref-id:{1000000000000000000 + idx * 1000}"
        dev_mem = str(base_mem + idx * 10000)
        
        dev_map[dev_id] = {"save_ref": save_ref, "mem_addr": dev_mem}
        
        if dev["type"] == "router_1841":
            d_elem = copy.deepcopy(arch_1841)
        elif dev["type"] == "switch_2950":
            d_elem = copy.deepcopy(arch_2950)
        elif dev["type"] == "server":
            d_elem = copy.deepcopy(archetypes["Server-PT"])
        else:
            d_elem = copy.deepcopy(archetypes["PC-PT"])
            
        eng = d_elem.find("ENGINE")
        if eng is not None:
            name_tag = eng.find("NAME")
            if name_tag is not None: name_tag.text = d_name
            save_ref_tag = eng.find("SAVE_REF_ID")
            if save_ref_tag is not None: save_ref_tag.text = save_ref
            else: ET.SubElement(eng, "SAVE_REF_ID").text = save_ref

            # Assign Unique MAC Addresses
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

            # Populate IOS configs
            if dev.get("config"):
                formatted_lines = PKTEncoder.format_cisco_running_config(dev["config"])
                for cfg_name in ["RUNNINGCONFIG", "STARTUPCONFIG"]:
                    cfg_tag = eng.find(cfg_name)
                    if cfg_tag is not None:
                        cfg_tag.clear()
                        for f_line in formatted_lines:
                            ET.SubElement(cfg_tag, "LINE").text = f_line

            # Populate Endpoints
            if dev["type"] in ["pc", "server"]:
                gw = dev.get("gateway", "")
                gw_elem = eng.find("GATEWAY")
                if gw_elem is not None: gw_elem.text = gw
                elif gw: ET.SubElement(eng, "GATEWAY").text = gw

                dns = dev.get("dns", "172.16.12.226")
                dns_elem = eng.find("DNS")
                if dns_elem is not None: dns_elem.text = dns
                elif dns: ET.SubElement(eng, "DNS").text = dns

                dev_ip = dev.get("ip", "")
                dev_mask = dev.get("netmask", "255.255.255.0")
                for port in eng.iter("PORT"):
                    t_elem = port.find("TYPE")
                    if t_elem is not None and "Ethernet" in (t_elem.text or ""):
                        ip_elem = port.find("IP")
                        if ip_elem is not None: ip_elem.text = dev_ip
                        else: ET.SubElement(port, "IP").text = dev_ip

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

                # Server-PT Services Injection
                if dev["type"] == "server" and "services" in dev:
                    svcs = dev["services"]
                    if "http" in svcs:
                        http = eng.find("HTTP_SERVER")
                        if http is None: http = ET.SubElement(eng, "HTTP_SERVER")
                        en = http.find("ENABLED")
                        if en is None: en = ET.SubElement(http, "ENABLED")
                        en.text = "1"
                        for f_node in eng.iter("FILE"):
                            fn = f_node.find("NAME")
                            if fn is not None and fn.text == "index.html":
                                fc = f_node.find("FILE_CONTENT")
                                if fc is not None:
                                    txt = fc.find("TEXT")
                                    if txt is None: txt = ET.SubElement(fc, "TEXT")
                                    txt.text = (
                                        "<html>\\n"
                                        "<center><font size='+2' color='#003366'><b>UNIVERSIDAD MARIANO GÁLVEZ DE GUATEMALA</b></font></center>\\n"
                                        "<center><font size='+1' color='#cc9900'><b>Segundo Parcial Redes 2 - Topología Multi-Router OSPF</b></font></center>\\n"
                                        "<hr>\\n"
                                        "<h3>Servicios Centrales Activos:</h3>\\n"
                                        "<ul>\\n"
                                        "  <li><b>Subred G (Servidores):</b> Web & FTP Operativos (172.16.12.226 / 227)</li>\\n"
                                        "  <li><b>Subred H (DHCP):</b> Servidor DHCP Central (172.16.10.2)</li>\\n"
                                        "  <li><b>Subred F (TFTP):</b> Servidor TFTP de Respaldos (172.16.12.2)</li>\\n"
                                        "  <li><b>Enrutamiento Dinámico:</b> OSPF Área 0, Proceso 10</li>\\n"
                                        "  <li><b>Seguridad:</b> SSH v2 RSA 2048-bit en Routers / Telnet en Switches</li>\\n"
                                        "</ul>\\n"
                                        "<hr>\\n"
                                        "<center><font size='-1' color='gray'>Cisco Packet Tracer 9.0 - UMG 2026</font></center>\\n"
                                        "</html>"
                                    )

                    if "tftp" in svcs:
                        tftp = eng.find("TFTP_SERVER")
                        if tftp is None: tftp = ET.SubElement(eng, "TFTP_SERVER")
                        en = tftp.find("ENABLED")
                        if en is None: en = ET.SubElement(tftp, "ENABLED")
                        en.text = "1"

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
                            ET.SubElement(r, "TYPE").text = rec.get("type", "A-REC")
                            ET.SubElement(r, "NAME").text = rec.get("name", "")
                            ET.SubElement(r, "TTL").text = "86400"
                            ET.SubElement(r, "IPADDRESS").text = rec.get("ip", "")

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
                            ET.SubElement(pl, "TFTP_ADDRESS").text = "172.16.12.2"

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

        devs_container.append(d_elem)

    # 2. Build Links (Serial & Copper)
    for l_idx, link in enumerate(links_def):
        src_id = link["src"]
        dst_id = link["dst"]
        src_info = dev_map[src_id]
        dst_info = dev_map[dst_id]

        l_elem = ET.Element("LINK")
        cable = ET.SubElement(l_elem, "CABLE")
        ET.SubElement(cable, "LENGTH").text = "1"
        ET.SubElement(cable, "FUNCTIONAL").text = "true"
        ET.SubElement(cable, "FROM").text = src_info["save_ref"]
        ET.SubElement(cable, "PORT").text = link["src_port"]
        ET.SubElement(cable, "TO").text = dst_info["save_ref"]
        ET.SubElement(cable, "PORT").text = link["dst_port"]
        ET.SubElement(cable, "FROM_DEVICE_MEM_ADDR").text = src_info["mem_addr"]
        ET.SubElement(cable, "TO_DEVICE_MEM_ADDR").text = dst_info["mem_addr"]
        ET.SubElement(cable, "FROM_PORT_MEM_ADDR").text = str(int(src_info["mem_addr"]) + l_idx * 10 + 1)
        ET.SubElement(cable, "TO_PORT_MEM_ADDR").text = str(int(dst_info["mem_addr"]) + l_idx * 10 + 2)
        ET.SubElement(cable, "GEO_VIEW_COLOR").text = "#000000" if link["type"] == "serial" else "#6ba72e"
        
        if link["type"] == "serial":
            ET.SubElement(l_elem, "TYPE").text = "eSerial"
            # Set DCE side
            dce_id = link.get("dce", src_id)
            dce_info = dev_map[dce_id]
            dce_port = link["src_port"] if dce_id == src_id else link["dst_port"]
            ET.SubElement(cable, "DCEDEV").text = dce_info["save_ref"]
            ET.SubElement(cable, "DCEPORT").text = dce_port
        else:
            ET.SubElement(l_elem, "TYPE").text = "eCopper"
            ET.SubElement(cable, "IS_MANAGED_IN_RACK_VIEW").text = "false"
            ET.SubElement(cable, "TYPE").text = "eStraightThrough"

        links_container.append(l_elem)

    # Generate XML and PKT
    xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
    pkt_bytes = PKTEncoder.encode_xml_to_pkt(xml_str)
    
    out_path = Path("/home/joshuaiamv/Descargas/Segundo_Parcial_Redes_2.pkt")
    out_path.write_bytes(pkt_bytes)
    print(f"✅ Archivo .pkt generado exitosamente en: {out_path} ({len(pkt_bytes)} bytes)")
    
    # Verify round-trip
    rec_xml = PKTEncoder.decode_pkt_to_xml(pkt_bytes)
    print(f"✅ Round-trip decodificación validado: {len(rec_xml)} caracteres XML.")
    assert "Router0" in rec_xml
    assert "Switch7" in rec_xml
    assert "Server-PT HTTP" in rec_xml
    assert "172.16.12.226" in rec_xml
    assert "Serial0/0/0" in rec_xml
    assert "eSerial" in rec_xml
    print("🎉 ¡Verificación 100% completada con éxito!")

if __name__ == "__main__":
    build_perfect_pkt()
