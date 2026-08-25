"""
Main FastAPI Server for Packet_XML
Provides REST APIs for AI Topology Generation, VLSM calculation,
Packet Tracer Live Bridge, and File Exports.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from network_engine import NetworkEngine
from ai_engine import AIEngine
from pkt_builder import PKTBuilder
from bridge_server import PTBridgeServer
from exporters import XMLExporter, JSExporter, CLIExporter
from network_ir import NetworkIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Socket.IO bridge on 127.0.0.1:7531
    await PTBridgeServer.start_bridge()
    yield
    # Shutdown: Stop Socket.IO bridge
    await PTBridgeServer.stop_bridge()

app = FastAPI(
    title="Packet_XML AI Orchestrator",
    description="AI-driven Network Architecture & Cisco Packet Tracer Bridge",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class PromptRequest(BaseModel):
    prompt: str
    model_provider: str = "ollama"
    model_name: str = "qwen3:8b"
    api_key: Optional[str] = None

class ScaleRequest(BaseModel):
    preset: str = "enterprise_150"  # small_10, medium_50, enterprise_150, massive_300
    routing_protocol: str = "ospf"
    base_network: str = "10.0.0.0/16"

class TopologyPayload(BaseModel):
    topology: Dict[str, Any]

class AckPayload(BaseModel):
    task_id: str
    success: bool = True
    stats: Optional[Dict[str, int]] = None

# --- API Endpoints ---

@app.get("/api/models")
async def get_models():
    """List available Ollama models and cloud providers."""
    return await AIEngine.list_available_models()

@app.post("/api/generate")
async def generate_topology(req: PromptRequest):
    """Generate a full network topology based on user prompt and AI model."""
    try:
        topology = await AIEngine.generate_from_prompt(
            prompt=req.prompt,
            model_provider=req.model_provider,
            model_name=req.model_name,
            api_key=req.api_key
        )
        return {"success": True, "topology": topology}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scale")
async def generate_scale_preset(req: ScaleRequest):
    """Generates instant scalable topologies from 10 to 300+ devices."""
    preset = req.preset.lower()
    
    if preset == "massive_300":
        # 3 Cores, 6 Distribution Switches, 18 Access Switches, 252 Endpoints + 4 Servers = ~280-300 Devices
        core_routers = 3
        dist_switches = 2
        access_switches = 3
        pcs_per_access = 14
        name = "Massive Enterprise Campus (300 Devices)"
    elif preset == "enterprise_150":
        # 2 Cores, 4 Distribution, 8 Access, 128 Endpoints + 4 Servers = ~146 Devices
        core_routers = 2
        dist_switches = 2
        access_switches = 2
        pcs_per_access = 16
        name = "Enterprise Multi-Floor Network (150 Devices)"
    elif preset == "medium_50":
        # 2 Cores, 2 Distribution, 4 Access, 40 Endpoints + 4 Servers = ~52 Devices
        core_routers = 2
        dist_switches = 1
        access_switches = 2
        pcs_per_access = 10
        name = "Medium Business Network (50 Devices)"
    else:  # small_10
        core_routers = 1
        dist_switches = 1
        access_switches = 1
        pcs_per_access = 6
        name = "Small Lab Network (10 Devices)"

    topology = NetworkEngine.generate_hierarchical_topology(
        name=name,
        core_routers=core_routers,
        dist_switches_per_core=dist_switches,
        access_switches_per_dist=access_switches,
        pcs_per_access=pcs_per_access,
        include_servers=True,
        routing_protocol=req.routing_protocol,
        base_network=req.base_network
    )
    topology["ptbuilder_script"] = NetworkEngine.to_ptbuilder_js(topology)
    return {"success": True, "topology": topology}

@app.post("/api/e2e/workflow")
async def run_e2e_workflow(req: PromptRequest):
    """Executes full pipeline: Prompt -> Network IR -> Validation -> Exporters (XML, JS, CLI) -> Live Bridge -> Save."""
    topology = await AIEngine.generate_from_prompt(
        prompt=req.prompt,
        model_provider=req.model_provider,
        model_name=req.model_name,
        api_key=req.api_key
    )
    ir = NetworkIR(topology)
    is_valid = ir.validate()

    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    xml_str = XMLExporter.export(ir)
    js_str = JSExporter.export(ir)
    cli_str = CLIExporter.export(ir)

    (out_dir / "network.xml").write_text(xml_str, encoding="utf-8")
    (out_dir / "network.js").write_text(js_str, encoding="utf-8")
    (out_dir / "network.txt").write_text(cli_str, encoding="utf-8")

    live_res = None
    if PTBridgeServer.is_pt_connected():
        live_res = await PTBridgeServer.deploy_live(ir.to_dict())

    pkt_exists = (out_dir / "network.pkt").exists()
    pkt_size = (out_dir / "network.pkt").stat().st_size if pkt_exists else 0

    return {
        "success": is_valid,
        "validation": ir.validation,
        "live_deployment": live_res,
        "artifacts": {
            "xml": {"path": str(out_dir / "network.xml"), "size": len(xml_str)},
            "js": {"path": str(out_dir / "network.js"), "size": len(js_str)},
            "txt": {"path": str(out_dir / "network.txt"), "size": len(cli_str)},
            "pkt": {"path": str(out_dir / "network.pkt"), "exists": pkt_exists, "size": pkt_size}
        },
        "topology": ir.to_dict()
    }

@app.post("/api/export/xml")
async def export_xml(req: TopologyPayload):
    """Export topology as Cisco Packet Tracer compatible XML from Network IR."""
    xml_str = XMLExporter.export(req.topology)
    return Response(
        content=xml_str,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={req.topology.get('name', 'network').replace(' ', '_')}.xml"}
    )

@app.post("/api/export/ptbuilder")
async def export_ptbuilder(req: TopologyPayload):
    """Export JavaScript code for PTBuilder Packet Tracer Extension from Network IR."""
    js_code = JSExporter.export(req.topology)
    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Content-Disposition": "attachment; filename=ptbuilder_topology.js"}
    )

@app.post("/api/export/ios")
async def export_ios(req: TopologyPayload):
    """Export all Cisco IOS device configurations in a single bundle from Network IR."""
    cli_bundle = CLIExporter.export(req.topology)
    return Response(
        content=cli_bundle,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=cisco_ios_configs.txt"}
    )

@app.post("/api/export/pkt")
async def export_pkt(req: TopologyPayload):
    """Directly encode and export Network IR to binary Cisco Packet Tracer .pkt file."""
    from pkt_encoder import PKTEncoder
    out_dir = Path(__file__).resolve().parent.parent / "output"
    pkt_res = PKTEncoder.generate_pkt(req.topology, output_path=out_dir / "network.pkt")
    return Response(
        content=pkt_res["pkt_bytes"],
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={req.topology.get('name', 'network').replace(' ', '_')}.pkt"}
    )

@app.get("/api/download/pkt")
async def download_pkt():
    """Download the saved Cisco Packet Tracer .pkt file from the output directory."""
    from fastapi.responses import FileResponse
    pkt_file = Path(__file__).resolve().parent.parent / "output" / "network.pkt"
    if not pkt_file.exists():
        raise HTTPException(
            status_code=404,
            detail="El archivo network.pkt no existe todavía en el servidor."
        )
    return FileResponse(
        path=str(pkt_file),
        filename="network.pkt",
        media_type="application/octet-stream"
    )

# --- Live Bridge Endpoints ---

@app.post("/api/bridge/deploy_live")
async def deploy_live(req: TopologyPayload):
    """Deploy topology directly in real time over Socket.IO (port 7531) into Packet Tracer."""
    res = await PTBridgeServer.deploy_live(req.topology)
    return res

@app.post("/api/bridge/queue")
async def queue_bridge_deployment(req: TopologyPayload):
    """Queue topology or deploy live directly if Socket.IO bridge is connected."""
    if PTBridgeServer.is_pt_connected():
        res = await PTBridgeServer.deploy_live(req.topology)
        return {
            "success": res.get("success", True),
            "queue_info": {"task_id": "socket_live"},
            "message": res.get("message", "Desplegado en vivo vía Socket.IO"),
            "logs": res.get("logs", []),
            "stats": res.get("stats", {})
        }
    res = PTBridgeServer.queue_topology(req.topology)
    return {"success": True, "queue_info": res}

@app.get("/api/bridge/poll")
async def poll_bridge(client_id: str = "pt_client"):
    """Called by Packet Tracer .pts script to retrieve pending actions."""
    batch = PTBridgeServer.get_next_batch(client_id)
    return {"has_task": batch is not None, "task": batch}

@app.post("/api/bridge/ack")
async def ack_bridge(payload: AckPayload):
    """Packet Tracer acknowledges task completion."""
    PTBridgeServer.acknowledge_task(payload.task_id, payload.success, payload.stats)
    return {"success": True}

@app.get("/api/bridge/status")
async def get_bridge_status():
    """Get live bridge connection and queue status."""
    return PTBridgeServer.get_status()

# Mount Static Frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
