"""
Network IR (Intermediate Representation) Module
Single Source of Truth for Network Topology, Addressing, and Configuration.

Architecture:
  User Prompt / Intent -> AI Parser -> Network IR (Validated Once) -> Exporters (XML, JS, CLI, PKT)
"""

import ipaddress
import logging
from typing import Dict, List, Any, Optional

log = logging.getLogger(__name__)

class NetworkIRValidationError(Exception):
    """Raised when a Network IR violates network architecture, VLSM, or consistency rules."""
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class NetworkIR:
    """
    Formal Intermediate Representation (IR) of a network topology.
    Acts as the Single Source of Truth for all downstream exporters (JS, XML, CLI, Live Bridge, PKT).
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self.metadata: Dict[str, Any] = {
            "name": "Enterprise Network",
            "version": "1.0",
            "architecture": "3-layer",
            "routing_protocol": "OSPF",
            "base_network": "10.0.0.0/16"
        }
        self.devices: List[Dict[str, Any]] = []
        self.vlans: List[Dict[str, Any]] = []
        self.hosts: List[Dict[str, Any]] = []
        self.links: List[Dict[str, Any]] = []
        self.routing: Dict[str, Any] = {
            "protocol": "OSPF",
            "area": 0,
            "networks": [],
            "routers": []
        }
        self.ios_configs: Dict[str, Dict[str, Any]] = {}
        self.validation: Dict[str, Any] = {
            "is_valid": False,
            "status": "UNVALIDATED",
            "errors": [],
            "warnings": [],
            "architecture_notes": [],
            "inferred_infrastructure": []
        }

        if data:
            self.from_dict(data)

    def from_dict(self, data: Dict[str, Any]) -> "NetworkIR":
        """Loads and maps dictionary data into Network IR."""
        self.metadata = data.get("metadata", {
            "name": data.get("name", "Network Topology"),
            "version": "1.0",
            "architecture": data.get("architecture", "3-layer"),
            "routing_protocol": data.get("routing_protocol", "OSPF"),
            "base_network": data.get("base_network", "10.0.0.0/16")
        })
        self.devices = data.get("devices", data.get("nodes", []))
        self.vlans = data.get("vlans", [])
        self.hosts = data.get("hosts", [d for d in self.devices if d.get("type") in ["pc", "laptop", "server"]])
        self.links = data.get("links", [])
        self.routing = data.get("routing", {
            "protocol": self.metadata.get("routing_protocol", "OSPF"),
            "area": 0,
            "networks": [],
            "routers": []
        })
        self.ios_configs = data.get("ios_configs", {})
        self.validation = data.get("validation", data.get("ai_metadata", {}).get("validation", {}))
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Network IR to dictionary maintaining backward compatibility with UI."""
        nodes = self.devices
        for d in nodes:
            d_id = d["id"]
            if d_id in self.ios_configs:
                cfg = self.ios_configs[d_id]
                d["phase2_chunks"] = cfg.get("phase2_chunks", [])
                d["phase3_chunks"] = cfg.get("phase3_chunks", [])
                d["phase4_chunks"] = cfg.get("phase4_chunks", [])
                d["ios_config"] = cfg.get("raw_cli", [])

        return {
            "metadata": self.metadata,
            "name": self.metadata.get("name", "Network Topology"),
            "total_devices": len(self.devices),
            "total_links": len(self.links),
            "layers": self._calculate_layer_counts(),
            "routing_protocol": self.metadata.get("routing_protocol", "OSPF"),
            "base_network": self.metadata.get("base_network", "10.0.0.0/16"),
            "devices": self.devices,
            "nodes": nodes,
            "vlans": self.vlans,
            "hosts": self.hosts,
            "links": self.links,
            "routing": self.routing,
            "ios_configs": self.ios_configs,
            "validation": self.validation,
            "ai_metadata": {"validation": self.validation}
        }

    def _calculate_layer_counts(self) -> Dict[str, int]:
        counts = {"core": 0, "distribution": 0, "access": 0, "dmz": 0, "endpoint": 0}
        for d in self.devices:
            layer = d.get("layer", "endpoint").lower()
            if layer in counts:
                counts[layer] += 1
            else:
                counts["endpoint"] += 1
        return counts

    def validate(self) -> bool:
        """
        Executes strict, comprehensive architectural and logical validation on the Network IR.
        """
        errors = []
        warnings = []
        notes = []

        # 1. Validate Devices
        device_ids = set()
        for d in self.devices:
            d_id = d.get("id")
            if not d_id:
                errors.append("Dispositivo encontrado sin 'id'.")
                continue
            if d_id in device_ids:
                errors.append(f"ID de dispositivo duplicado: '{d_id}'.")
            device_ids.add(d_id)

            if not d.get("type"):
                errors.append(f"Dispositivo '{d_id}' no tiene tipo especificado.")

        # 2. Validate VLANs & Subnets
        vlan_map = {}
        allocated_networks = []

        for v in self.vlans:
            v_id = v.get("vlan", v.get("id"))
            if v_id is None:
                errors.append("VLAN encontrada sin 'id'.")
                continue
            if v_id in vlan_map:
                errors.append(f"ID de VLAN duplicado: {v_id}.")
            vlan_map[v_id] = v

            # VLAN 99 Native special check
            if v_id == 99 or v.get("type") == "Layer2_Native":
                v["layer3"] = False
                if v.get("gateway") and v.get("gateway") != "N/A":
                    warnings.append(f"VLAN {v_id} (Native Trunk) no debe tener Gateway L3 configurado.")
                continue

            # Check L3 subnet
            net_str = v.get("network")
            prefix = v.get("prefix")
            gw_str = v.get("gateway")

            if net_str and net_str != "N/A" and prefix:
                try:
                    net_obj = ipaddress.IPv4Network(f"{net_str}/{prefix}")
                    for prev_net in allocated_networks:
                        if net_obj.overlaps(prev_net):
                            errors.append(f"Solapamiento de subredes detectado entre {net_obj} y {prev_net}.")
                    allocated_networks.append(net_obj)

                    if gw_str and gw_str != "N/A":
                        gw_obj = ipaddress.IPv4Address(gw_str)
                        if gw_obj not in net_obj:
                            errors.append(f"Gateway {gw_str} no pertenece a la subred {net_obj} para VLAN {v_id}.")
                except ValueError as e:
                    errors.append(f"Error de formato IP en VLAN {v_id}: {e}")

        # 3. Validate Hosts
        host_ips = set()
        for h in self.hosts:
            h_id = h.get("id")
            h_vlan = h.get("vlan")
            h_ip = h.get("ip")

            if h_ip:
                if h_ip in host_ips:
                    errors.append(f"IP duplicada detectada: '{h_ip}' en host '{h_id}'.")
                host_ips.add(h_ip)

                h_gw = h.get("gateway")
                h_mask = h.get("netmask", "255.255.255.0")
                if h_gw and h_gw != "N/A" and h_mask:
                    try:
                        h_net = ipaddress.IPv4Network(f"{h_gw}/{h_mask}", strict=False)
                        if ipaddress.IPv4Address(h_ip) not in h_net:
                            errors.append(f"IP del host {h_id} ({h_ip}) no pertenece a la subred de su Gateway {h_gw} ({h_net}).")
                    except ValueError as e:
                        errors.append(f"Error de formato IP en host {h_id}: {e}")

        # 4. Validate Links
        for l in self.links:
            src = l.get("source")
            dst = l.get("target")

            if src not in device_ids:
                errors.append(f"Enlace hace referencia a dispositivo origen inexistente: '{src}'.")
            if dst not in device_ids:
                errors.append(f"Enlace hace referencia a dispositivo destino inexistente: '{dst}'.")

            src_port = l.get("src_port")
            dst_port = l.get("dst_port")
            if not src_port or not dst_port:
                errors.append(f"Enlace {src} <-> {dst} no tiene interfaces origen/destino definidas.")

            # Explicit Link Mode
            if "mode" not in l:
                if l.get("is_trunk") or l.get("layer") == "access":
                    l["mode"] = "trunk"
                    l["native_vlan"] = 99
                elif l.get("layer") == "endpoint":
                    l["mode"] = "access"
                elif l.get("layer") in ["distribution", "core"]:
                    l["mode"] = "routed"

        # 5. DMZ Validation Check
        dmz_servers = [h for h in self.hosts if h.get("layer") == "dmz" or h.get("type") == "server" or "SRV" in h.get("id", "")]
        if len(dmz_servers) >= 2:
            dmz_vlans = {s.get("vlan") for s in dmz_servers}
            if len(dmz_vlans) < 2:
                warnings.append("Se solicitaron 2 DMZ pero comparten la misma VLAN. Se recomienda separar en VLAN 40 y VLAN 41.")
            else:
                notes.append(f"✓ Zonas DMZ separadas lógicamente ({len(dmz_servers)} servidores en VLANs {sorted(list(dmz_vlans))}).")

        cores = sum(1 for d in self.devices if d.get("layer") == "core")
        dists = sum(1 for d in self.devices if d.get("layer") == "distribution")
        accs = sum(1 for d in self.devices if d.get("layer") == "access")

        if cores > 0 and dists > 0 and accs > 0:
            notes.append(f"✓ Arquitectura de 3 Capas verificada: {cores} Core, {dists} Distribución, {accs} Acceso.")
        elif accs > 0:
            notes.append(f"✓ Arquitectura Plana/2 Capas verificada: {accs} Acceso.")

        self.validation = {
            "is_valid": len(errors) == 0,
            "status": "APPROVED" if len(errors) == 0 else "REJECTED",
            "errors": errors,
            "warnings": warnings,
            "architecture_notes": notes,
            "inferred_infrastructure": self.validation.get("inferred_infrastructure", []),
            "total_nodes": len(self.devices),
            "total_links": len(self.links)
        }

        return len(errors) == 0
