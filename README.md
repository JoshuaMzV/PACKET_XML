# 🌐 PACKET_XML v2.0
**AI Network Orchestrator & Native Cisco Packet Tracer Compiler**

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Cisco](https://img.shields.io/badge/Cisco-Packet%20Tracer%208.x%20%7C%209.0%2B-success)
![AI](https://img.shields.io/badge/AI-Ollama%20%7C%20Qwen%20%7C%20OpenAI-orange)
![License](https://img.shields.io/badge/license-MIT-green)

**PACKET_XML** is an open-source, AI-driven networking platform and compiler that transforms natural language prompts or structured network specifications into fully functional, production-ready Cisco Packet Tracer (`.pkt`) files.

Whether you need to generate a massive 150-node enterprise campus network or a complex multi-site CCNA/CCNP laboratory (with Cisco 1841 modular routers, WIC-2T serial WAN links, OSPF Area 0, Router-on-a-Stick, VTP, and institutional HTTP/DNS server portals), this engine parses your intent, calculates VLSM subnets, and compiles configurations directly into encrypted Packet Tracer binary files.

---

## ✨ Key Features (v2.0)

* 🧠 **AI-Powered Network Design**: Connects natively to local LLMs (via Ollama) or Cloud APIs to translate natural language into a strict `NetworkIR` (Intermediate Representation).
* ⚡ **Native Cisco 1841 & WIC-2T Serial Support**: Generates Cisco 1841 routers equipped with high-speed serial WAN interface cards (`WIC-2T`) in Slot 0 (`Serial0/0/0` and `Serial0/0/1`).
* 🔌 **Cisco Packet Tracer 9.0+ Serial Binary Compatibility**: Fully reverse-engineered and compatible with `Link::CSerial::deserialize` schema (mandatory `<DCEDEV>` and `<DCEPORT>` clock tags, accurate DCE/DTE auto-assignment).
* 🌐 **Dynamic Routing Protocols**: Native orchestration and configuration of **OSPF Area 0**, static routing, and subnets across multi-campus topologies.
* 🎓 **CCNA/Enterprise Services Orchestration**:
  * **Router-on-a-Stick (RoaS)** with 802.1Q sub-interfaces and encapsulation.
  * **VLAN Trunking Protocol (VTP)** Server/Client domains.
  * **Centralized DHCP** with `ip helper-address` forwarding.
  * **Server-PT Services**: Injects custom HTTP web portals (HTML/CSS), DNS domain records, TFTP, and DHCP scopes directly into the simulation.
* 🔒 **Pure Python Twofish + EAX Crypto Engine**: Autonomous decryption (`unpacket.py`) and recompilation (`pkt_encoder.py`) without requiring third-party C++ libraries or legacy tools.
* 🖥️ **Full Multi-layer Switching**: Native archetypes for **Catalyst 2960-24TT** (24 FastEthernet + 2 GigabitEthernet) and **Catalyst 3650** Layer 3 switches.

---

## 💻 Instalación y Ejecución en Windows (Windows Setup)

### 1. Prerrequisitos en Windows
* **Python 3.10 o superior**: Descárgalo desde [python.org](https://www.python.org/downloads/).
  > ⚠️ **Importante**: Durante la instalación, marca la casilla **"Add Python to PATH"** (Agregar Python al PATH).
* **Cisco Packet Tracer 8.x / 9.0 o superior**.
* **Git para Windows**: Descárgalo desde [git-scm.com](https://git-scm.com/).

---

### 2. Clonar el Repositorio
Abre tu terminal (**Símbolo del sistema / CMD** o **PowerShell**) y clona el proyecto:

```cmd
git clone https://github.com/JoshuaMzV/PACKET_XML.git
cd PACKET_XML
```

---

### 3. Crear y Activar un Entorno Virtual (Recomendado)

* **En Símbolo del sistema (CMD):**
  ```cmd
  python -m venv venv
  venv\Scripts\activate
  ```

* **En PowerShell:**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(Si PowerShell bloquea scripts, ejecuta una vez como Administrador: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

---

### 4. Instalar Librerías de Python Requeridas

Instala todas las dependencias necesarias mediante `requirements.txt`:

```cmd
pip install -r requirements.txt
```

O si prefieres instalar las librerías individualmente:

```cmd
pip install fastapi uvicorn pydantic httpx
```

| Librería | Propósito |
| :--- | :--- |
| **`fastapi`** | Framework web moderno para el backend y las APIs de generación |
| **`uvicorn`** | Servidor ASGI de alto rendimiento para servir la aplicación |
| **`pydantic`** | Validación de esquemas y modelos de datos de la red (`NetworkIR`) |
| **`httpx`** | Cliente HTTP asíncrono para comunicarse con Ollama y APIs de IA |

---

### 5. Iniciar la Aplicación y Dashboard Web en Windows

#### Opción A: Mediante el ejecutable rápido (Recomendado)
Haz doble clic sobre el archivo **`run.bat`** en la carpeta principal del proyecto.

#### Opción B: Por línea de comandos
1. Navega a la carpeta `backend`:
   ```cmd
   cd backend
   ```
2. Ejecuta el servidor con Uvicorn:
   ```cmd
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *(También puedes ejecutar simplemente: `python main.py`)*

3. Abre tu navegador web en:
   👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🐧 Instalación y Ejecución en Linux / macOS

```bash
# 1. Clonar el repositorio
git clone https://github.com/JoshuaMzV/PACKET_XML.git
cd PACKET_XML

# 2. Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar librerías
pip install -r requirements.txt

# 4. Iniciar con el script automatizado
chmod +x run.sh
./run.sh
```

Abre tu navegador en **`http://127.0.0.1:8000`**.

---

## ⚡ Generación Directa de Laboratorios (CLI Scripts)

Si deseas compilar laboratorios completos directamente por línea de comandos sin abrir el navegador:

### Generar Laboratorio Segundo Parcial (4 Routers 1841 + Seriales + OSPF + UMG Portal)
```bash
# En Windows:
python generate_segundo_parcial.py

# En Linux:
python3 generate_segundo_parcial.py
```
El archivo `.pkt` listo para Cisco Packet Tracer 9.0+ se generará automáticamente en:
📁 **`output/Segundo_Parcial_Redes_2.pkt`**

### Desencriptar cualquier archivo `.pkt` a XML legible
```bash
python backend/pkt_crypto/unpacket.py output/Segundo_Parcial_Redes_2.pkt -o output/inspeccion.xml
```

### Verificar integridad de un archivo `.pkt`
```bash
python verify_pkt.py
```

---

## 🛠️ Arquitectura del Sistema

```
PACKET_XML/
├── backend/
│   ├── main.py                     # API FastAPI y montaje del Dashboard
│   ├── ai_engine.py                # Parser de IA (Ollama / Cloud / Heurístico)
│   ├── network_engine.py           # Cálculo VLSM e inyección de comandos Cisco IOS
│   ├── custom_topology_parser.py   # Mapeo de topologías avanzadas (OSPF, VTP, RoaS)
│   ├── network_ir.py               # Representación Intermedia (Single Source of Truth)
│   ├── pkt_encoder.py              # Compilador binario y clonador XML para PT 9.0+
│   ├── pkt_crypto/                 # Motor criptográfico Twofish + EAX puro en Python
│   │   ├── pt_crypto.py            # Funciones decrypt_pkt / encrypt_pkt
│   │   ├── unpacket.py             # Herramienta CLI para desencriptar .pkt a XML
│   │   └── twofish.py / eax.py     # Algoritmos de cifrado simétrico
│   └── templates/                  # Arquetipos XML de dispositivos (1841 WIC-2T, 2960, 3650)
├── frontend/                       # Dashboard visual interactivo (HTML5 / Canvas / JS)
├── output/                         # Archivos .pkt y topologías compiladas
├── generate_segundo_parcial.py     # Generador del examen práctico UMG (4 sedes, WAN OSPF)
├── requirements.txt                # Dependencias oficiales de Python
├── run.sh                          # Launcher para Linux / macOS
└── run.bat                         # Launcher para Windows
```

---

## 📜 Licencia & Créditos
Desarrollado para la comunidad de ingeniería en redes, estudiantes y profesionales Cisco CCNA/CCNP.
¡Automatizando la simulación de redes a escala!
