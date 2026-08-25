"""
Packet Tracer Live Bridge Server
Manages the real-time Socket.IO communication (port 7531) and queue with Cisco Packet Tracer.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional

try:
    from mcp_server.bridge import PTBridge
except ImportError:
    PTBridge = None

log = logging.getLogger(__name__)

class PTBridgeServer:
    """
    Real-time Socket.IO and Queue Manager for Live Deployment into Cisco Packet Tracer.
    """
    
    _bridge: Optional[Any] = None
    _queue: List[Dict[str, Any]] = []
    _history: List[Dict[str, Any]] = []
    _current_status: str = "IDLE"
    _deployed_stats: Dict[str, int] = {"devices": 0, "links": 0, "configs": 0}

    @classmethod
    async def start_bridge(cls, host: str = "127.0.0.1", port: int = 7531):
        """Starts the background Socket.IO server on port 7531."""
        if PTBridge is None:
            log.warning("mcp_server package not available, bridge socket disabled.")
            return

        if cls._bridge is None:
            try:
                cls._bridge = PTBridge(host=host, port=port)
                await cls._bridge.start()
                log.info("PT Socket.IO Bridge started successfully on %s:%d", host, port)
            except Exception as e:
                log.error("Failed to start PT Socket.IO Bridge: %s", e)

    @classmethod
    async def stop_bridge(cls):
        """Stops the Socket.IO bridge server."""
        if cls._bridge is not None:
            try:
                await cls._bridge.stop()
                log.info("PT Socket.IO Bridge stopped.")
            except Exception as e:
                log.error("Error stopping PT Socket.IO Bridge: %s", e)
            finally:
                cls._bridge = None

    @classmethod
    def is_pt_connected(cls) -> bool:
        """Returns True if Packet Tracer is currently connected via Socket.IO."""
        if cls._bridge is not None:
            return bool(cls._bridge.is_connected)
        return False

    @classmethod
    def map_device_model(cls, dev_type: str, model: str = "") -> str:
        """Maps internal device types to Cisco Packet Tracer model strings."""
        if dev_type == "router":
            return "2911"
        elif dev_type == "switch_l3":
            return "3560-24PS"
        elif dev_type == "switch_l2":
            return "2960-24TT"
        elif dev_type == "server":
            return "Server-PT"
        elif dev_type == "pc":
            return "PC-PT"
        elif dev_type == "laptop":
            return "Laptop-PT"
        return model or "2911"

    @classmethod
    async def deploy_live(cls, topology: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploys a complete network topology directly into Packet Tracer in real-time over Socket.IO.
        """
        if not cls.is_pt_connected():
            return {
                "success": False,
                "error": "Packet Tracer no está conectado al puente en 127.0.0.1:7531.",
                "instruction": "En Packet Tracer: Ve a 'Extensions' -> 'Packet Tracer MCP' para abrir la ventana del puente. Debe mostrar 'connected'."
            }

        bridge = cls._bridge
        nodes = topology.get("nodes", [])
        links = topology.get("links", [])
        logs = []
        dev_count = 0
        link_count = 0
        cfg_count = 0

        try:
            # 1. FASE 1: Crear Dispositivos
            logs.append(f"Creando {len(nodes)} dispositivos en el espacio de trabajo...")
            for node in nodes:
                pt_model = cls.map_device_model(node["type"], node.get("model", ""))
                res = await bridge.call_tool("addDevice", {
                    "deviceName": node["id"],
                    "deviceModel": pt_model,
                    "x": int(node.get("x", 200)),
                    "y": int(node.get("y", 200))
                })
                dev_count += 1
                logs.append(f" -> Dispositivo '{node['id']}' ({pt_model}) añadido.")

            # 2. FASE 1: Conectar Enlaces (Cables)
            logs.append(f"Conectando {len(links)} enlaces físicos...")
            for link in links:
                cable_type = "cross" if "cross" in link.get("type", "").lower() else "straight"
                await bridge.call_tool("addLink", {
                    "device1Name": link["source"],
                    "device1Interface": link["src_port"],
                    "device2Name": link["target"],
                    "device2Interface": link["dst_port"],
                    "linkType": cable_type
                })
                link_count += 1
                logs.append(f" -> Enlace {link['source']}:{link['src_port']} <-> {link['target']}:{link['dst_port']} conectado.")

            # 3. FASES 2, 3, 4: Configuraciones Cisco IOS (en bloques seguros < 600 chars)
            logs.append("Aplicando configuraciones Cisco IOS por fases secuenciales...")
            for node in nodes:
                node_id = node["id"]
                node_type = node.get("type")
                if node_type in ["router", "switch_l3", "switch_l2"]:
                    # Fase 2: VLANs & SVIs
                    for chunk in node.get("phase2_chunks", []):
                        cmd_text = "\n".join(chunk)
                        await bridge.call_tool("configureIosDevice", {
                            "deviceName": node_id,
                            "commands": cmd_text
                        })
                        cfg_count += 1

                    # Fase 3: Puertos Físicos
                    for chunk in node.get("phase3_chunks", []):
                        cmd_text = "\n".join(chunk)
                        await bridge.call_tool("configureIosDevice", {
                            "deviceName": node_id,
                            "commands": cmd_text
                        })
                        cfg_count += 1

                    # Fase 4: Enrutamiento OSPF / Rutas
                    for chunk in node.get("phase4_chunks", []):
                        cmd_text = "\n".join(chunk)
                        await bridge.call_tool("configureIosDevice", {
                            "deviceName": node_id,
                            "commands": cmd_text
                        })
                        cfg_count += 1

                    logs.append(f" -> Cisco IOS configurado en '{node_id}'.")

            # 4. FASE 5: Equipos Finales (PCs y Servidores)
            logs.append("Asignando direccionamiento IP a clientes y servidores...")
            for node in nodes:
                if node.get("ip"):
                    await bridge.call_tool("configurePcIp", {
                        "deviceName": node["id"],
                        "dhcpEnabled": False,
                        "ipaddress": node["ip"],
                        "subnetMask": node.get("netmask", "255.255.255.0"),
                        "defaultGateway": node.get("gateway", ""),
                        "dnsServer": node.get("dns", "8.8.8.8")
                    })
                    logs.append(f" -> IP {node['ip']} asignada a '{node['id']}'.")

            cls._deployed_stats = {"devices": dev_count, "links": link_count, "configs": cfg_count}
            cls._current_status = "COMPLETED"

            return {
                "success": True,
                "message": f"¡Topología '{topology.get('name')}' desplegada en vivo con éxito!",
                "stats": cls._deployed_stats,
                "logs": logs
            }

        except Exception as e:
            log.error("Error durante el despliegue en vivo: %s", e)
            return {
                "success": False,
                "error": str(e),
                "logs": logs
            }

    @classmethod
    def queue_topology(cls, topology: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback queue for manual / polling operation."""
        task_id = f"task_{int(time.time())}"
        item = {
            "task_id": task_id,
            "name": topology.get("name", "Deployment"),
            "status": "QUEUED",
            "created_at": time.time()
        }
        cls._queue.append(item)
        return {"task_id": task_id, "status": "QUEUED"}

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns overall live bridge status."""
        return {
            "status": cls._current_status,
            "pt_connected": cls.is_pt_connected(),
            "port": 7531,
            "active_queue_count": len(cls._queue),
            "history_count": len(cls._history),
            "last_stats": cls._deployed_stats
        }

