# 🌐 PACKET_XML v1.0
**AI Network Orchestrator for Cisco Packet Tracer**

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Cisco](https://img.shields.io/badge/Cisco-Packet%20Tracer%209.0-success)
![AI](https://img.shields.io/badge/AI-Ollama%20%7C%20Qwen%20%7C%20OpenAI-orange)

**PACKET_XML** is an open-source, AI-driven networking platform that transforms natural language prompts into fully functional, production-ready Cisco Packet Tracer (`.pkt`) files. 

Whether you need to generate a massive 150-node enterprise campus network or a highly specific CCNA laboratory (with Router-on-a-Stick, VTP, and Centralized DHCP), this engine parses your intent, calculates the VLSM subnets, and compiles the Cisco IOS configurations directly into the Packet Tracer XML binary format.

---

## ✨ Key Features

* 🧠 **AI-Powered Network Design**: Connects natively to local LLMs (via Ollama) or Cloud APIs to translate natural language into a strict `NetworkIR` (Intermediate Representation).
* 🏗️ **Massive Hierarchical Topologies**: Automatically scaffolds Core, Distribution, and Access layers, wiring up to hundreds of nodes instantly.
* 🎓 **CCNA Lab Generator (Custom Mode)**: Perfectly orchestrates complex routing concepts natively:
  * **Router-on-a-Stick (RoaS)** with `.1Q` encapsulation.
  * **VLAN Trunking Protocol (VTP)** Server/Client domains.
  * **Centralized DHCP** with `ip helper-address` forwarding.
  * **Server-PT Services**: Injects DNS records, DHCP Pools, TFTP, and HTTP services directly into the simulation.
* ⚙️ **Automatic IOS Scripting**: Generates and chunks complete Cisco IOS startup/running configs for 2911 Routers, 3650 L3 Switches, and 2960 L2 Switches.
* 🔌 **Hardware Level Fidelity**: Overcomes Packet Tracer clone limitations by assigning unique MAC addresses to every interface and injecting correct `<PORT_GATEWAY>` tags for flawless L2/L3 simulation.

---

## 🚀 Quick Start

### Prerequisites
* Python 3.10+
* FastAPI & Uvicorn
* Ollama (Optional, for local AI generation)
* Cisco Packet Tracer 9.0+

### Installation & Execution
```bash
# Clone the repository
git clone https://github.com/JoshuaMzV/PACKET_XML.git
cd PACKET_XML

# Run the FastAPI Backend and Dashboard
./run.sh
```
Open your browser at `http://127.0.0.1:8000` to access the Visual Dashboard and AI Generator.

---

## 🛠️ Architecture

1. **AI Engine (`ai_engine.py`)**: Intercepts the prompt. Uses heuristic fallbacks or LLMs to deduce the topology (Generic Hierarchical vs Custom CCNA Lab).
2. **Network Engine (`network_engine.py`)**: The brain that handles VLSM math, IP allocation, and Cisco IOS text generation.
3. **Custom Topology Parser (`custom_topology_parser.py`)**: Processes complex constraint mapping (VTP, Services, RoaS) for advanced scenarios.
4. **NetworkIR (`network_ir.py`)**: The Single Source of Truth dictionary that connects the frontend graph UI with the backend compilers.
5. **PKT Encoder (`pkt_encoder.py`)**: Reads the template, clones the XML devices, injects the IOS scripts and unique MACs, encrypts the file, and outputs a valid `.pkt` file.

---

## 📜 License
Developed for the networking and open-source community. Let's automate network engineering!
