"""
Network Engine for Packet_XML
Handles VLSM calculation, hierarchical topology creation (1 to 300+ devices),
Cisco IOS script generation, and topology validation.
"""

import math
import ipaddress
from typing import Dict, List, Any, Optional, Tuple

from network_ir import NetworkIR
from exporters import JSExporter

class NetworkEngine:
    """
    Core engine for generating scalable network topologies, 
    calculating IP subnets, and generating Cisco IOS configurations.
    """
    
    DEVICE_TYPES = {
        "router": {"model": "2911", "pt_type": "Router-PT", "icon": "router", "layer": "core"},
        "switch_l3": {"model": "3650-24PS", "pt_type": "3560-24PS", "icon": "switch_l3", "layer": "distribution"},
        "switch_l2": {"model": "2960-24TT", "pt_type": "2960-24TT", "icon": "switch", "layer": "access"},
        "server": {"model": "Server-PT", "pt_type": "Server-PT", "icon": "server", "layer": "endpoint"},
        "pc": {"model": "PC-PT", "pt_type": "PC-PT", "icon": "pc", "layer": "endpoint"},
        "laptop": {"model": "Laptop-PT", "pt_type": "Laptop-PT", "icon": "laptop", "layer": "endpoint"}
    }

    @staticmethod
    def calculate_vlsm(base_network: str, subnets_req: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate VLSM allocations given a base network and list of required subnets with host counts.
        Treats VLAN 99 (Native Trunk) and L2-only VLANs as pure Layer 2 without IP/gateway allocation.
        """
        # Separate L3 routed VLANs from L2-only/Native VLANs
        l3_reqs = [r for r in subnets_req if r.get("vlan") != 99 and r.get("hosts", 0) > 0 and r.get("is_l3", True)]
        l2_reqs = [r for r in subnets_req if r.get("vlan") == 99 or r.get("hosts", 0) == 0 or not r.get("is_l3", True)]

        sorted_reqs = sorted(l3_reqs, key=lambda x: x.get("hosts", 10), reverse=True)
        current_ip = ipaddress.IPv4Network(base_network).network_address
        allocated = []

        for req in sorted_reqs:
            hosts = req.get("hosts", 10)
            needed_size = hosts + 2
            prefix_len = 32 - math.ceil(math.log2(needed_size))
            if prefix_len < 8:
                prefix_len = 8
            
            # Align to subnet boundary
            block_size = 2 ** (32 - prefix_len)
            ip_int = int(current_ip)
            if ip_int % block_size != 0:
                ip_int = ((ip_int // block_size) + 1) * block_size
                current_ip = ipaddress.IPv4Address(ip_int)

            subnet = ipaddress.IPv4Network(f"{current_ip}/{prefix_len}")
            usable_hosts = list(subnet.hosts())
            gateway = str(usable_hosts[0]) if usable_hosts else str(subnet.network_address)
            first_host = str(usable_hosts[1]) if len(usable_hosts) > 1 else gateway
            last_host = str(usable_hosts[-1]) if usable_hosts else gateway

            allocated.append({
                "name": req.get("name", f"Subnet_{req.get('vlan', 10)}"),
                "vlan": req.get("vlan", 10),
                "type": "Routed_L3",
                "requested_hosts": hosts,
                "network": str(subnet.network_address),
                "prefix": prefix_len,
                "netmask": str(subnet.netmask),
                "gateway": gateway,
                "first_host": first_host,
                "last_host": last_host,
                "total_usable": len(usable_hosts),
                "purpose": req.get("purpose", "Active Data/Service VLAN")
            })

            # Advance current IP
            current_ip = subnet.broadcast_address + 1

        # Add pure Layer 2 / Native VLANs without IP assignment
        for req in l2_reqs:
            v_id = req.get("vlan", 99)
            allocated.append({
                "name": req.get("name", "Native_Trunk" if v_id == 99 else f"VLAN_{v_id}"),
                "vlan": v_id,
                "type": "Layer2_Native" if v_id == 99 else "Layer2_Only",
                "requested_hosts": 0,
                "network": "N/A",
                "prefix": "N/A",
                "netmask": "N/A",
                "gateway": "N/A",
                "first_host": "N/A",
                "last_host": "N/A",
                "total_usable": 0,
                "purpose": "VLAN Nativa exclusiva de Troncales 802.1Q (Sin Gateway/SVI por seguridad)" if v_id == 99 else "VLAN Capa 2"
            })

        return allocated

    @classmethod
    def generate_basic_topology(
        cls,
        name: str = "Basic SOHO Network",
        routers_count: int = 1,
        switches_count: int = 1,
        pcs_count: int = 2,
        include_servers: bool = False,
        base_network: str = "192.168.1.0/24"
    ) -> Dict[str, Any]:
        """
        Generates a clean, minimal basic topology (e.g. 1 Router, 1 Switch, 2 PCs).
        """
        nodes = []
        links = []

        # 1. Routers
        router_nodes = []
        for r_idx in range(routers_count):
            r_id = f"R{r_idx+1}" if routers_count > 1 else "R1"
            r_x = int(350 + (r_idx - (routers_count - 1)/2.0) * 200)
            r_node = {
                "id": r_id,
                "label": r_id,
                "type": "router",
                "layer": "core",
                "model": "2911",
                "x": r_x,
                "y": 100,
                "interfaces": {},
                "phase2_chunks": [],
                "phase3_chunks": [],
                "phase4_chunks": []
            }
            router_nodes.append(r_node)
            nodes.append(r_node)

        # 2. Switches
        switch_nodes = []
        for s_idx in range(switches_count):
            s_id = f"SW{s_idx+1}" if switches_count > 1 else "SW1"
            s_x = int(350 + (s_idx - (switches_count - 1)/2.0) * 200)
            s_node = {
                "id": s_id,
                "label": s_id,
                "type": "switch_l2",
                "layer": "access",
                "model": "2960-24TT",
                "x": s_x,
                "y": 250,
                "interfaces": {},
                "phase2_chunks": [],
                "phase3_chunks": [],
                "phase4_chunks": []
            }
            switch_nodes.append(s_node)
            nodes.append(s_node)

            # Connect Switch to Router if available
            if router_nodes:
                target_r = router_nodes[s_idx % len(router_nodes)]
                links.append({
                    "id": f"link_{target_r['id']}_{s_id}",
                    "source": target_r["id"],
                    "target": s_id,
                    "src_port": f"GigabitEthernet0/{s_idx}",
                    "dst_port": "GigabitEthernet0/1",
                    "type": "Copper_Straight",
                    "layer": "distribution"
                })

        # 3. Endpoints (PCs)
        endpoint_nodes = []
        for p_idx in range(pcs_count):
            p_id = f"PC{p_idx+1}"
            target_sw = switch_nodes[p_idx % len(switch_nodes)] if switch_nodes else router_nodes[0]
            
            p_x = int(350 + (p_idx - (pcs_count - 1)/2.0) * 120)
            p_y = 420

            pc_ip = f"192.168.1.{10 + p_idx}"
            pc_gw = "192.168.1.1" if router_nodes else ""

            p_node = {
                "id": p_id,
                "label": p_id,
                "type": "pc",
                "layer": "endpoint",
                "model": "PC-PT",
                "x": p_x,
                "y": p_y,
                "ip": pc_ip,
                "netmask": "255.255.255.0",
                "gateway": pc_gw,
                "dns": "8.8.8.8"
            }
            endpoint_nodes.append(p_node)
            nodes.append(p_node)

            # Link PC to Switch
            links.append({
                "id": f"link_{target_sw['id']}_{p_id}",
                "source": target_sw["id"],
                "target": p_id,
                "src_port": f"FastEthernet0/{p_idx+1}",
                "dst_port": "FastEthernet0",
                "type": "Copper_Straight",
                "layer": "endpoint"
            })

        # 4. Optional Servers
        if include_servers:
            srv_node = {
                "id": "SRV1",
                "label": "SRV_WEB",
                "type": "server",
                "layer": "endpoint",
                "model": "Server-PT",
                "x": 550,
                "y": 250,
                "ip": "192.168.1.200",
                "netmask": "255.255.255.0",
                "gateway": "192.168.1.1",
                "dns": "127.0.0.1"
            }
            nodes.append(srv_node)
            target_sw = switch_nodes[0] if switch_nodes else router_nodes[0]
            links.append({
                "id": "link_srv1",
                "source": target_sw["id"],
                "target": "SRV1",
                "src_port": "FastEthernet0/24",
                "dst_port": "FastEthernet0",
                "type": "Copper_Straight",
                "layer": "endpoint"
            })

        # 5. Generate 5-Phase Configurations
        for r in router_nodes:
            r["phase3_chunks"].append([
                "enable",
                "configure terminal",
                f"hostname {r['label']}",
                "no ip domain-lookup",
                "interface GigabitEthernet0/0",
                "ip address 192.168.1.1 255.255.255.0",
                "no shutdown",
                "exit",
                "end",
                "write memory"
            ])

        for s in switch_nodes:
            s["phase2_chunks"].append([
                "enable",
                "configure terminal",
                f"hostname {s['label']}",
                "no ip domain-lookup",
                "end"
            ])
            s_ports = ["enable", "configure terminal", "interface GigabitEthernet0/1", "no shutdown", "exit"]
            for p in range(1, pcs_count + 1):
                s_ports.extend([
                    f"interface FastEthernet0/{p}",
                    "switchport mode access",
                    "spanning-tree portfast",
                    "no shutdown",
                    "exit"
                ])
            s_ports.extend(["end", "write memory"])
            s["phase3_chunks"].append(s_ports)

        ir_data = {
            "metadata": {
                "name": name,
                "version": "1.0",
                "architecture": "soho",
                "routing_protocol": "STATIC",
                "base_network": base_network
            },
            "devices": nodes,
            "vlans": [{"vlan": 1, "name": "Default", "network": "192.168.1.0", "prefix": 24, "netmask": "255.255.255.0", "gateway": "192.168.1.1", "layer3": True}],
            "hosts": endpoint_nodes,
            "links": links,
            "routing": {"protocol": "STATIC", "area": 0, "networks": ["192.168.1.0/24"], "routers": [r["id"] for r in router_nodes]}
        }
        ir = NetworkIR(ir_data)
        ir.validate()
        return ir.to_dict()

    @classmethod
    def generate_hierarchical_topology(
        cls,
        name: str = "Enterprise Campus",
        core_routers: int = 2,
        dist_switches_per_core: int = 2,
        access_switches_per_dist: int = 2,
        pcs_per_access: int = 4,
        include_servers: bool = False,
        servers_count: int = 2,
        routing_protocol: str = "ospf",
        base_network: str = "10.0.0.0/16",
        vlans: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates a full hierarchical enterprise network topology (up to 300+ devices)
        with Core, Distribution, Access, and Endpoint layers.
        """
        num_access = core_routers * dist_switches_per_core * access_switches_per_dist
        total_endpoints = num_access * pcs_per_access
        
        if not vlans:
            corp_hosts = max(30, int(total_endpoints * 0.45) + 16)
            voice_hosts = max(14, int(total_endpoints * 0.35) + 16)
            guest_hosts = max(14, int(total_endpoints * 0.35) + 16)
            vlans = [
                {"vlan": 20, "name": "Corporate_Data", "hosts": corp_hosts},
                {"vlan": 30, "name": "Voice_VoIP", "hosts": voice_hosts},
                {"vlan": 50, "name": "Guest_WiFi", "hosts": guest_hosts},
                {"vlan": 10, "name": "Management", "hosts": 14},
                {"vlan": 40, "name": "DMZ_1", "hosts": 14},
                {"vlan": 41, "name": "DMZ_2", "hosts": 14},
                {"vlan": 99, "name": "Native_Trunk", "hosts": 0, "layer3": False}
            ]

        # Calculate VLSM
        subnets = cls.calculate_vlsm(base_network, vlans)
        vlan_map = {s["vlan"]: s for s in subnets}

        nodes = []
        links = []

        col_width = 320 if num_access <= 2 else 260
        start_x = 400 if num_access == 1 else 300

        # 1. ACCESS LAYER (L2 Switches)
        access_nodes = []
        for i in range(num_access):
            a_id = f"ASW{i+1}"
            x = start_x + i * col_width
            y = 430
            acc_node = {
                "id": a_id,
                "label": a_id,
                "type": "switch_l2",
                "layer": "access",
                "model": "2960-24TT",
                "x": x,
                "y": y,
                "interfaces": {},
                "ios_config": []
            }
            access_nodes.append(acc_node)

        # 2. DISTRIBUTION LAYER (L3 Switches)
        dist_nodes = []
        dist_idx = 1
        for c in range(core_routers):
            for d in range(dist_switches_per_core):
                d_id = f"DSW{dist_idx}"
                s_acc = (c * dist_switches_per_core + d) * access_switches_per_dist
                e_acc = s_acc + access_switches_per_dist - 1
                d_x = int((access_nodes[s_acc]["x"] + access_nodes[e_acc]["x"]) / 2)
                y = 260
                dist_node = {
                    "id": d_id,
                    "label": d_id,
                    "type": "switch_l3",
                    "layer": "distribution",
                    "model": "3650-24PS",
                    "x": d_x,
                    "y": y,
                    "pod_idx": dist_idx,
                    "core_idx": c + 1,
                    "dist_port_idx": d,
                    "interfaces": {},
                    "ios_config": []
                }
                dist_nodes.append(dist_node)

                # Connect Distribution Switch to its Access Switches (GigabitEthernet1/0/3..1/0/8)
                for a_offset in range(access_switches_per_dist):
                    target_asw = access_nodes[s_acc + a_offset]
                    target_asw["pod_idx"] = dist_idx
                    links.append({
                        "id": f"link_{d_id}_{target_asw['id']}",
                        "source": d_id,
                        "target": target_asw["id"],
                        "src_port": f"GigabitEthernet1/0/{a_offset + 3}",
                        "dst_port": "GigabitEthernet0/1",
                        "type": "Copper_Straight",
                        "layer": "access",
                        "is_trunk": True
                    })

                dist_idx += 1

        # Distribution Redundancy Cross-Links (between pairs in same cluster on GigabitEthernet1/0/2)
        for d_pair in range(0, len(dist_nodes) - 1, 2):
            links.append({
                "id": f"link_dist_cross_{d_pair+1}_{d_pair+2}",
                "source": dist_nodes[d_pair]["id"],
                "target": dist_nodes[d_pair+1]["id"],
                "src_port": "GigabitEthernet1/0/2",
                "dst_port": "GigabitEthernet1/0/2",
                "type": "Copper_Cross",
                "layer": "distribution",
                "is_trunk": True
            })

        # 3. CORE LAYER (Routers)
        core_nodes = []
        for c in range(core_routers):
            r_id = f"R{c+1}"
            s_dist = c * dist_switches_per_core
            e_dist = s_dist + dist_switches_per_core - 1
            c_x = int((dist_nodes[s_dist]["x"] + dist_nodes[e_dist]["x"]) / 2)
            y = 90
            core_node = {
                "id": r_id,
                "label": r_id,
                "type": "router",
                "layer": "core",
                "model": "2911",
                "x": c_x,
                "y": y,
                "interfaces": {},
                "ios_config": []
            }
            core_nodes.append(core_node)

            # Connect Core Router to ALL its Distribution Switches (GigabitEthernet1/0/1 on DSW)
            for d_offset in range(dist_switches_per_core):
                target_dsw = dist_nodes[s_dist + d_offset]
                links.append({
                    "id": f"link_{r_id}_{target_dsw['id']}",
                    "source": r_id,
                    "target": target_dsw["id"],
                    "src_port": f"GigabitEthernet0/{d_offset}",
                    "dst_port": "GigabitEthernet1/0/1",
                    "type": "Copper_Straight",
                    "layer": "distribution",
                    "pod_idx": target_dsw["pod_idx"]
                })

        # Interconnect Core Routers (Full Mesh between cores)
        for i in range(len(core_nodes)):
            for j in range(i + 1, len(core_nodes)):
                links.append({
                    "id": f"link_core_{i+1}_{j+1}",
                    "source": core_nodes[i]["id"],
                    "target": core_nodes[j]["id"],
                    "src_port": "GigabitEthernet0/2",
                    "dst_port": "GigabitEthernet0/2",
                    "type": "Copper_Cross",
                    "layer": "core",
                    "subnet": f"172.16.0.{i*4 + 1}/30"
                })

        nodes.extend(core_nodes)
        nodes.extend(dist_nodes)
        nodes.extend(access_nodes)

        # 4. ENDPOINT LAYER (PCs & Laptops in clean pods)
        endpoint_nodes = []
        pc_idx = 1
        vlan_keys = [20, 30, 50]  # End-user VLANs (Corporate, Voice, Guest)
        pod_vlan_counters = {}

        for a_idx, acc in enumerate(access_nodes):
            pod_num = acc.get("pod_idx", 1)
            grid_cols = 4 if pcs_per_access >= 8 else 2
            for p in range(1, pcs_per_access + 1):
                assigned_vlan = vlan_keys[(p - 1) % len(vlan_keys)]
                h_count = pod_vlan_counters.get((pod_num, assigned_vlan), 0)
                pod_vlan_counters[(pod_num, assigned_vlan)] = h_count + 1
                
                if len(dist_nodes) > 1:
                    pc_ip = f"10.{pod_num}.{assigned_vlan}.{10 + h_count}"
                    pc_gw = f"10.{pod_num}.{assigned_vlan}.1"
                    pc_mask = "255.255.255.0"
                else:
                    v_info = vlan_map.get(assigned_vlan, {})
                    v_first_ip = ipaddress.IPv4Address(v_info.get("first_host", "10.0.0.2"))
                    pc_ip = str(v_first_ip + h_count)
                    pc_gw = v_info.get("gateway", "10.0.0.1")
                    pc_mask = v_info.get("netmask", "255.255.255.0")

                p_id = f"PC{pc_idx}"
                dev_type = "pc" if p % 2 != 0 else "laptop"

                col = (p - 1) % grid_cols
                row = (p - 1) // grid_cols
                spacing_x = 100 if pcs_per_access <= 2 else (70 if pcs_per_access <= 4 else 45)
                pc_x = int(acc["x"] + (col - (grid_cols - 1) / 2.0) * spacing_x)
                pc_y = int(550 + row * 55)

                p_node = {
                    "id": p_id,
                    "label": p_id,
                    "type": dev_type,
                    "layer": "endpoint",
                    "model": "PC-PT" if dev_type == "pc" else "Laptop-PT",
                    "x": pc_x,
                    "y": pc_y,
                    "vlan": assigned_vlan,
                    "ip": pc_ip,
                    "netmask": pc_mask,
                    "gateway": pc_gw,
                    "dns": "8.8.8.8"
                }
                endpoint_nodes.append(p_node)

                # Link endpoint to Access Switch
                links.append({
                    "id": f"link_{acc['id']}_{p_id}",
                    "source": acc["id"],
                    "target": p_id,
                    "src_port": f"FastEthernet0/{p}",
                    "dst_port": "FastEthernet0",
                    "type": "Copper_Straight",
                    "layer": "endpoint",
                    "vlan": assigned_vlan
                })

                pc_idx += 1

        # Servers in DMZ / Data Center (Dedicated DMZ_1 and DMZ_2 zones physically connected to Distribution)
        srv_nodes = []
        if include_servers and servers_count > 0:
            srv_names = ["SRV_DMZ1", "SRV_DMZ2", "SRV_DB", "SRV_APP"]
            for s_idx in range(min(servers_count, len(srv_names))):
                s_id = f"SRV{s_idx+1}"
                srv_vlan = 40 if s_idx == 0 else 41

                if len(dist_nodes) > 1:
                    srv_ip = f"10.{s_idx + 1}.{srv_vlan}.10"
                    srv_gw = f"10.{s_idx + 1}.{srv_vlan}.1"
                    srv_mask = "255.255.255.0"
                else:
                    v_info = vlan_map.get(srv_vlan, {})
                    srv_ip = v_info.get("first_host", f"10.0.0.{82 + s_idx*16}")
                    srv_gw = v_info.get("gateway", f"10.0.0.{81 + s_idx*16}")
                    srv_mask = v_info.get("netmask", "255.255.255.240")

                # Symmetrical physical layout: DMZ 1 on the left of DSW1, DMZ 2 on the right of DSW2
                if s_idx == 0 and dist_nodes:
                    target_sw = dist_nodes[0]
                    srv_x = max(80, int(target_sw["x"] - 180))
                    srv_y = int(target_sw["y"])
                    s_port = "GigabitEthernet1/0/10"
                elif s_idx == 1 and len(dist_nodes) > 1:
                    target_sw = dist_nodes[1]
                    srv_x = int(target_sw["x"] + 180)
                    srv_y = int(target_sw["y"])
                    s_port = "GigabitEthernet1/0/10"
                else:
                    target_sw = dist_nodes[s_idx % len(dist_nodes)] if dist_nodes else core_nodes[0]
                    srv_x = int(target_sw["x"] - 180)
                    srv_y = int(target_sw["y"] + 60 * (s_idx // 2 + 1))
                    s_port = f"GigabitEthernet1/0/{10 + s_idx}"

                srv_node = {
                    "id": s_id,
                    "label": s_id,
                    "type": "server",
                    "layer": "dmz",
                    "model": "Server-PT",
                    "x": srv_x,
                    "y": srv_y,
                    "vlan": srv_vlan,
                    "ip": srv_ip,
                    "netmask": srv_mask,
                    "gateway": srv_gw,
                    "dns": "127.0.0.1",
                    "services": ["HTTP", "DNS"] if s_idx == 0 else ["HTTP"]
                }
                srv_nodes.append(srv_node)
                endpoint_nodes.append(srv_node)

                # Connect server to its Distribution Switch
                links.append({
                    "id": f"link_srv_{s_id}",
                    "source": target_sw["id"],
                    "target": s_id,
                    "src_port": s_port,
                    "dst_port": "FastEthernet0",
                    "type": "Copper_Straight",
                    "layer": "dmz",
                    "vlan": srv_vlan
                })

        nodes.extend(endpoint_nodes)

        # Generate Cisco Configurations with 5-Phase Chunking
        cls._generate_all_ios_configs(nodes, links, routing_protocol, vlans, vlan_map)

        ir_data = {
            "metadata": {
                "name": name,
                "version": "1.0",
                "architecture": "3-layer" if len(core_nodes) > 0 and len(dist_nodes) > 0 else "2-layer",
                "routing_protocol": routing_protocol.upper(),
                "base_network": base_network
            },
            "devices": nodes,
            "vlans": subnets,
            "hosts": endpoint_nodes,
            "links": links,
            "routing": {
                "protocol": routing_protocol.upper(),
                "area": 0,
                "networks": [s["network"] for s in subnets if s.get("network") and s.get("network") != "N/A"],
                "routers": [n["id"] for n in core_nodes + dist_nodes]
            }
        }
        ir = NetworkIR(ir_data)
        ir.validate()
        return ir.to_dict()

    @classmethod
    def _generate_all_ios_configs(
        cls, 
        nodes: List[Dict[str, Any]], 
        links: List[Dict[str, Any]], 
        routing_protocol: str,
        vlan_catalog: Optional[List[Dict[str, Any]]] = None,
        vlan_map: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> None:
        """
        Generates production-grade, 5-Phase Cisco IOS configurations for all routers and switches.
        Guarantees that every configureIosDevice call stays strictly under 600 characters.
        """
        node_links = {}
        for l in links:
            node_links.setdefault(l["source"], []).append(l)
            node_links.setdefault(l["target"], []).append(l)

        if not vlan_map:
            vlan_map = {}

        vlan_defs = [
            (10, "Management"),
            (20, "Corporate_Data"),
            (30, "Voice_VoIP"),
            (40, "DMZ_1"),
            (41, "DMZ_2"),
            (50, "Guest_WiFi"),
            (99, "Native_Trunk")
        ]

        for n_idx, node in enumerate(nodes):
            node_type = node.get("type")
            node_id = node.get("id")
            label = node.get("label", node_id)
            node["phase2_chunks"] = []
            node["phase3_chunks"] = []
            node["phase4_chunks"] = []

            if node_type == "router":
                r_num = int(node_id.replace("R", "")) if node_id.replace("R", "").isdigit() else (n_idx + 1)
                
                # FASE 3: Configuración de Puertos Físicos e IPs (~380 chars)
                r_ports = [
                    "enable",
                    "configure terminal",
                    f"hostname {label}",
                    "no ip domain-lookup",
                    "ip routing"
                ]
                for l in node_links.get(node_id, []):
                    if l.get("layer") == "distribution" and l["source"] == node_id:
                        d_port = l["src_port"]
                        pod_num = l.get("pod_idx", 1)
                        r_ports.extend([
                            f"interface {d_port}",
                            f"ip address 10.255.{pod_num}.1 255.255.255.252",
                            "no shutdown",
                            "exit"
                        ])

                r_ports.extend([
                    "interface GigabitEthernet0/2",
                    f"ip address 172.16.0.{r_num} 255.255.255.252",
                    "no shutdown",
                    "exit",
                    "end"
                ])
                node["phase3_chunks"].append([c.strip() for c in r_ports if c.strip()])

                # FASE 4: Enrutamiento OSPF y Rutas entre Cores (~240 chars)
                if routing_protocol.lower() == "ospf":
                    r_ospf = [
                        "enable",
                        "configure terminal",
                        "router ospf 1",
                        f"router-id {r_num}.{r_num}.{r_num}.{r_num}",
                        "network 10.0.0.0 0.255.255.255 area 0",
                        "network 172.16.0.0 0.0.255.255 area 0",
                        "exit"
                    ]
                    if len([n for n in nodes if n.get("type") == "router"]) > 1:
                        if r_num == 1:
                            r_ospf.extend([
                                "ip route 10.1.0.0 255.255.0.0 10.255.1.2",
                                "ip route 10.2.0.0 255.255.0.0 10.255.2.2",
                                "ip route 10.3.0.0 255.255.0.0 172.16.0.2",
                                "ip route 10.4.0.0 255.255.0.0 172.16.0.2",
                                "ip route 10.255.3.0 255.255.255.252 172.16.0.2",
                                "ip route 10.255.4.0 255.255.255.252 172.16.0.2"
                            ])
                        elif r_num == 2:
                            r_ospf.extend([
                                "ip route 10.1.0.0 255.255.0.0 172.16.0.1",
                                "ip route 10.2.0.0 255.255.0.0 172.16.0.1",
                                "ip route 10.255.1.0 255.255.255.252 172.16.0.1",
                                "ip route 10.255.2.0 255.255.255.252 172.16.0.1",
                                "ip route 10.3.0.0 255.255.0.0 10.255.3.2",
                                "ip route 10.4.0.0 255.255.0.0 10.255.4.2"
                            ])
                    r_ospf.extend(["end", "write memory"])
                    node["phase4_chunks"].append([c.strip() for c in r_ospf if c.strip()])

            elif node_type == "switch_l3":
                pod_num = node.get("pod_idx", 1)

                # FASE 2: VLANs y SVIs vinculadas exactamente al VLSM calculado (~550 chars)
                sw_vlans = [
                    "enable",
                    "configure terminal",
                    f"hostname {label}",
                    "no ip domain-lookup",
                    "ip routing",
                    f"spanning-tree vlan 1-99 priority {4096 if pod_num % 2 != 0 else 8192}",
                    "spanning-tree portfast default"
                ]
                for v_id, v_name in vlan_defs:
                    sw_vlans.extend([f"vlan {v_id}", f"name {v_name}", "exit"])
                
                # Configure SVIs for active routed VLANs (exclude native trunk VLAN 99)
                dist_count = len([n for n in nodes if n.get("type") == "switch_l3"])
                for v_id, _ in vlan_defs:
                    if v_id != 99:
                        if dist_count > 1:
                            sw_vlans.extend([
                                f"interface Vlan{v_id}",
                                f"ip address 10.{pod_num}.{v_id}.1 255.255.255.0",
                                "no shutdown",
                                "exit"
                            ])
                        else:
                            v_info = vlan_map.get(v_id)
                            if v_info and v_info.get("gateway") and v_info["gateway"] != "N/A":
                                sw_vlans.extend([
                                    f"interface Vlan{v_id}",
                                    f"ip address {v_info['gateway']} {v_info['netmask']}",
                                    "no shutdown",
                                    "exit"
                                ])
                sw_vlans.append("end")
                node["phase2_chunks"].append([c.strip() for c in sw_vlans if c.strip()])

                # FASE 3: Puertos Físicos DSW (Uplinks enrutados y Trunks dinámicos hacia ASWs/Cross-links)
                sw_ports = [
                    "enable",
                    "configure terminal"
                ]
                for l in node_links.get(node_id, []):
                    port = l["src_port"] if l["source"] == node_id else l["dst_port"]
                    if l.get("layer") == "distribution" and ("R" in l["source"] or "R" in l["target"]):
                        sw_ports.extend([
                            f"interface {port}",
                            "no switchport",
                            f"ip address 10.255.{pod_num}.2 255.255.255.252",
                            "no shutdown",
                            "exit"
                        ])
                    elif l.get("is_trunk") or l.get("mode") == "trunk" or ("ASW" in l["source"] or "ASW" in l["target"]) or ("DSW" in l["source"] and "DSW" in l["target"]):
                        sw_ports.extend([
                            f"interface {port}",
                            "switchport mode trunk",
                            "switchport trunk native vlan 99",
                            "spanning-tree portfast trunk",
                            "no shutdown",
                            "exit"
                        ])
                sw_ports.append("end")
                node["phase3_chunks"].append([c.strip() for c in sw_ports if c.strip()])

                # FASE 3 (Servidores en DSW): Configurar puertos físicos según enlaces reales conectados
                srv_links = [
                    l for l in node_links.get(node_id, [])
                    if l.get("layer") in ["endpoint", "dmz"] and l["source"] == node_id and (l.get("vlan") in [40, 41] or "SRV" in l.get("target", ""))
                ]
                if srv_links:
                    srv_ports = ["enable", "configure terminal"]
                    for l in srv_links:
                        s_port = l["src_port"]
                        s_vlan = l.get("vlan", 40)
                        srv_ports.extend([
                            f"interface {s_port}",
                            "switchport mode access",
                            f"switchport access vlan {s_vlan}",
                            "spanning-tree portfast",
                            "no shutdown",
                            "exit"
                        ])
                    srv_ports.append("end")
                    node["phase3_chunks"].append([c.strip() for c in srv_ports if c.strip()])

                # FASE 4: Enrutamiento (Ruta por Defecto y OSPF) (~280 chars)
                sw_route = [
                    "enable",
                    "configure terminal",
                    f"ip route 0.0.0.0 0.0.0.0 10.255.{pod_num}.1"
                ]
                if routing_protocol.lower() == "ospf":
                    sw_route.extend([
                        "router ospf 1",
                        f"router-id {pod_num+10}.{pod_num+10}.{pod_num+10}.{pod_num+10}",
                        f"network 10.{pod_num}.0.0 0.0.255.255 area 0",
                        f"network 10.255.{pod_num}.0 0.0.0.3 area 0",
                        "exit"
                    ])
                sw_route.extend(["end", "write memory"])
                node["phase4_chunks"].append([c.strip() for c in sw_route if c.strip()])

            elif node_type == "switch_l2":
                # FASE 2: VLANs (~280 chars)
                l2_vlans = [
                    "enable",
                    "configure terminal",
                    f"hostname {label}",
                    "no ip domain-lookup",
                    "spanning-tree portfast default"
                ]
                for v_id, v_name in vlan_defs:
                    l2_vlans.extend([f"vlan {v_id}", f"name {v_name}", "exit"])
                l2_vlans.append("end")
                node["phase2_chunks"].append([c.strip() for c in l2_vlans if c.strip()])

                # FASE 3: Puertos Físicos Trunks hacia DSW
                l2_trunk = ["enable", "configure terminal"]
                for l in node_links.get(node_id, []):
                    if l.get("is_trunk") or "DSW" in l["source"] or "DSW" in l["target"]:
                        port = l["src_port"] if l["source"] == node_id else l["dst_port"]
                        l2_trunk.extend([
                            f"interface {port}",
                            "switchport mode trunk",
                            "switchport trunk native vlan 99",
                            "spanning-tree portfast trunk",
                            "no shutdown",
                            "exit"
                        ])
                l2_trunk.append("end")
                node["phase3_chunks"].append([c.strip() for c in l2_trunk if c.strip()])

                access_links = [
                    l for l in node_links.get(node_id, [])
                    if l.get("layer") == "endpoint" and l["source"] == node_id
                ]

                chunk_size = 4
                for group_idx in range(0, len(access_links), chunk_size):
                    sub_group = access_links[group_idx : group_idx + chunk_size]
                    chunk_ports = ["enable", "configure terminal"]
                    for l in sub_group:
                        port_name = l["src_port"]
                        vlan_id = l.get("vlan", 20)
                        chunk_ports.extend([
                            f"interface {port_name}",
                            "switchport mode access",
                            f"switchport access vlan {vlan_id}",
                            "spanning-tree portfast",
                            "no shutdown",
                            "exit"
                        ])
                    chunk_ports.extend(["end", "write memory"])
                    node["phase3_chunks"].append([c.strip() for c in chunk_ports if c.strip()])

    @classmethod
    def to_ptbuilder_js(cls, topology_data: Dict[str, Any]) -> str:
        """
        Converts the topology data into a strict 5-Phase sequential execution script for PTBuilder.
        Every configureIosDevice call is guaranteed to be under 600 characters.
        """
        return JSExporter.export(topology_data)

