/**
 * Packet_XML Frontend Application Engine
 * Interactive Graph Visualizer, AI Prompt Handler, and Live Bridge Orchestrator.
 */

// State
let cy = null;
let currentTopology = null;
let selectedNodeData = null;

// DOM Elements
const cyContainer = document.getElementById('cy');
const statDevices = document.getElementById('statDevices');
const statLinks = document.getElementById('statLinks');
const statProtocol = document.getElementById('statProtocol');
const promptInput = document.getElementById('promptInput');
const btnSendPrompt = document.getElementById('btnSendPrompt');
const modelSelect = document.getElementById('modelSelect');
const scaleSelect = document.getElementById('scaleSelect');
const btnLoadScale = document.getElementById('btnLoadScale');
const layoutSelect = document.getElementById('layoutSelect');
const btnZoomIn = document.getElementById('btnZoomIn');
const btnZoomOut = document.getElementById('btnZoomOut');
const btnFit = document.getElementById('btnFit');
const chatHistory = document.getElementById('chatHistory');
const nodeLabel = document.getElementById('nodeLabel');
const nodeModel = document.getElementById('nodeModel');
const nodeLayer = document.getElementById('nodeLayer');
const nodeIp = document.getElementById('nodeIp');
const selectedNodeType = document.getElementById('selectedNodeType');
const iosCodeBlock = document.getElementById('iosCodeBlock');
const btnCopyIos = document.getElementById('btnCopyIos');
const vlsmList = document.getElementById('vlsmList');
const bridgeLog = document.getElementById('bridgeLog');
const bridgeBadge = document.getElementById('bridgeBadge');
const bridgeText = document.getElementById('bridgeText');
const btnLiveDeploy = document.getElementById('btnLiveDeploy');
const btnExportMenu = document.getElementById('btnExportMenu');
const exportDropdown = document.getElementById('exportDropdown');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toastMsg');

// Tabs
const tabIos = document.getElementById('tabIos');
const tabVlsm = document.getElementById('tabVlsm');
const tabBridge = document.getElementById('tabBridge');
const contentIos = document.getElementById('contentIos');
const contentVlsm = document.getElementById('contentVlsm');
const contentBridge = document.getElementById('contentBridge');

// Initialize Cytoscape
function initCytoscape() {
  cy = cytoscape({
    container: cyContainer,
    boxSelectionEnabled: false,
    autounselectify: false,
    style: [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'color': '#e2e8f0',
          'font-size': '10px',
          'font-family': 'monospace',
          'text-valign': 'bottom',
          'text-margin-y': 5,
          'background-color': '#475569',
          'border-width': 2,
          'border-color': '#64748b',
          'width': 26,
          'height': 26,
          'transition-property': 'background-color, border-color, width, height',
          'transition-duration': '0.2s'
        }
      },
      // Core Layer (Routers)
      {
        selector: 'node[layer = "core"]',
        style: {
          'background-color': '#dc2626',
          'border-color': '#f87171',
          'shape': 'diamond',
          'width': 38,
          'height': 38,
          'font-size': '11px',
          'font-weight': 'bold'
        }
      },
      // Distribution Layer (L3 Switches)
      {
        selector: 'node[layer = "distribution"]',
        style: {
          'background-color': '#2563eb',
          'border-color': '#60a5fa',
          'shape': 'round-rectangle',
          'width': 32,
          'height': 32,
          'font-size': '11px'
        }
      },
      // Access Layer (L2 Switches)
      {
        selector: 'node[layer = "access"]',
        style: {
          'background-color': '#059669',
          'border-color': '#34d399',
          'shape': 'round-rectangle',
          'width': 26,
          'height': 26
        }
      },
      // Endpoints (Servers)
      {
        selector: 'node[type = "server"]',
        style: {
          'background-color': '#d97706',
          'border-color': '#fbbf24',
          'shape': 'cut-rectangle',
          'width': 28,
          'height': 28
        }
      },
      // Endpoints (PCs / Laptops)
      {
        selector: 'node[layer = "endpoint"][type != "server"]',
        style: {
          'background-color': '#475569',
          'border-color': '#94a3b8',
          'shape': 'ellipse',
          'width': 18,
          'height': 18,
          'font-size': '9px'
        }
      },
      // Selected Node
      {
        selector: 'node:selected',
        style: {
          'border-color': '#38bdf8',
          'border-width': 4,
          'shadow-blur': 15,
          'shadow-color': '#38bdf8',
          'shadow-opacity': 0.8
        }
      },
      // Edge styling
      {
        selector: 'edge',
        style: {
          'width': 1.5,
          'line-color': '#334155',
          'curve-style': 'bezier',
          'opacity': 0.8
        }
      },
      {
        selector: 'edge[layer = "core"]',
        style: {
          'width': 2.5,
          'line-color': '#ef4444',
          'line-style': 'dashed'
        }
      },
      {
        selector: 'edge[layer = "distribution"]',
        style: {
          'width': 2,
          'line-color': '#3b82f6'
        }
      },
      {
        selector: 'edge[is_trunk = "true"]',
        style: {
          'width': 2,
          'line-color': '#10b981'
        }
      }
    ]
  });

  // Node Selection Event
  cy.on('tap', 'node', function (evt) {
    const node = evt.target;
    selectNode(node.data());
  });

  // Background Click
  cy.on('tap', function (evt) {
    if (evt.target === cy) {
      // deselected
    }
  });
}

// Render Topology onto Cytoscape Canvas
function renderTopology(topology) {
  currentTopology = topology;

  // Update Top Stats
  statDevices.textContent = topology.total_devices || (topology.nodes ? topology.nodes.length : 0);
  statLinks.textContent = topology.total_links || (topology.links ? topology.links.length : 0);
  statProtocol.textContent = topology.routing_protocol || 'OSPF';

  // Build Elements
  const elements = [];

  // Add Nodes
  (topology.nodes || []).forEach(node => {
    elements.push({
      group: 'nodes',
      data: {
        id: node.id,
        label: node.label || node.id,
        type: node.type,
        layer: node.layer,
        model: node.model,
        ip: node.ip || (node.gateway ? `${node.gateway} (GW)` : 'DHCP / Dynamic'),
        netmask: node.netmask || '',
        gateway: node.gateway || '',
        vlan: node.vlan || '',
        ios_config: node.ios_config || []
      },
      position: { x: node.x || 200, y: node.y || 200 }
    });
  });

  // Add Links
  (topology.links || []).forEach(link => {
    elements.push({
      group: 'edges',
      data: {
        id: link.id,
        source: link.source,
        target: link.target,
        layer: link.layer || 'access',
        is_trunk: link.is_trunk ? "true" : "false"
      }
    });
  });

  cy.elements().remove();
  cy.add(elements);

  applyLayout(layoutSelect.value);

  // Auto select first core router
  const firstCore = (topology.nodes || []).find(n => n.layer === 'core') || (topology.nodes || [])[0];
  if (firstCore) {
    selectNode(firstCore);
  }

  // Populate VLSM Table
  renderVlsmTable(topology.vlans || []);
}

// Apply Cytoscape Layout
function applyLayout(layoutName) {
  if (!cy) return;

  let options = {};
  if (layoutName === 'dagre') {
    options = {
      name: 'dagre',
      rankDir: 'TB',
      nodeSep: 40,
      rankSep: 80,
      animate: true,
      animationDuration: 400
    };
  } else if (layoutName === 'concentric') {
    options = {
      name: 'concentric',
      concentric: function (node) {
        const layer = node.data('layer');
        if (layer === 'core') return 4;
        if (layer === 'distribution') return 3;
        if (layer === 'access') return 2;
        return 1;
      },
      levelWidth: () => 1,
      animate: true
    };
  } else {
    options = {
      name: 'cose',
      animate: true,
      randomize: false,
      componentSpacing: 100,
      nodeOverlap: 20
    };
  }

  const layout = cy.layout(options);
  layout.run();
}

// Select and Inspect Node
function selectNode(data) {
  selectedNodeData = data;
  nodeLabel.textContent = data.label || data.id;
  nodeModel.textContent = `Modelo: Cisco ${data.model || 'Device'}`;
  nodeLayer.textContent = `Capa: ${data.layer ? data.layer.toUpperCase() : 'N/A'}`;
  nodeIp.textContent = data.ip || 'DHCP Client';
  selectedNodeType.textContent = (data.type || 'DEVICE').toUpperCase();

  // Populate IOS Config block
  if (data.ios_config && data.ios_config.length > 0) {
    iosCodeBlock.textContent = data.ios_config.join('\n');
  } else if (data.type === 'pc' || data.type === 'laptop' || data.type === 'server') {
    iosCodeBlock.textContent = `! --- Configuración IP Endpoint ---\nIP Address : ${data.ip || 'Auto'}\nSubnet Mask: ${data.netmask || '255.255.255.0'}\nGateway    : ${data.gateway || 'None'}\nVLAN       : ${data.vlan || '1'}\nDNS Server : 8.8.8.8`;
  } else {
    iosCodeBlock.textContent = `! No hay configuración específica para este nodo.`;
  }
}

// Render VLSM Subnets
function renderVlsmTable(vlans) {
  vlsmList.innerHTML = '';
  if (!vlans || vlans.length === 0) {
    vlsmList.innerHTML = '<p class="text-gray-500 text-xs">No hay VLANs calculadas.</p>';
    return;
  }

  vlans.forEach(v => {
    const card = document.createElement('div');
    card.className = 'bg-[#161f30] border border-gray-800 p-2.5 rounded-lg space-y-1';
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-bold text-cyan-400">VLAN ${v.vlan}: ${v.name}</span>
        <span class="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-1.5 py-0.5 rounded">/${v.prefix}</span>
      </div>
      <div class="grid grid-cols-2 gap-1 text-[10px] text-gray-400 font-mono">
        <div>Red: <span class="text-white">${v.network}</span></div>
        <div>Máscara: <span class="text-white">${v.netmask}</span></div>
        <div>Gateway: <span class="text-emerald-400">${v.gateway}</span></div>
        <div>Usables: <span class="text-white">${v.total_usable || v.requested_hosts} hosts</span></div>
      </div>
    `;
    vlsmList.appendChild(card);
  });
}

// Fetch Pre-Scaled Topology
async function loadScalePreset(presetName) {
  showToast(`Generando topología escalada (${presetName})...`);
  try {
    const res = await fetch('/api/scale', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset: presetName, routing_protocol: 'ospf', base_network: '10.0.0.0/16' })
    });
    const data = await res.json();
    if (data.success && data.topology) {
      renderTopology(data.topology);
      showToast(`¡Topología de ${data.topology.total_devices} nodos cargada exitosamente!`);
      appendChatMessage('Asistente', `He generado la red jerárquica con **${data.topology.total_devices} dispositivos** y **${data.topology.total_links} enlaces** con protocolo **${data.topology.routing_protocol}**.`);
    }
  } catch (err) {
    showToast('Error cargando topología: ' + err.message);
  }
}

// Send AI Prompt
async function sendPrompt(promptText) {
  if (!promptText.trim()) return;
  appendChatMessage('Usuario', promptText);
  promptInput.value = '';

  const modelVal = modelSelect.value;
  const isCloud = modelVal === 'gemini' || modelVal === 'openai';
  const provider = isCloud ? modelVal : 'ollama';

  showToast('La IA está diseñando la red y calculando VLSM...');
  appendChatMessage('Asistente', `🧠 Diseñando topología con modelo **${modelVal}**...`);

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: promptText,
        model_provider: provider,
        model_name: modelVal
      })
    });
    const data = await res.json();
    if (data.success && data.topology) {
      renderTopology(data.topology);
      showToast(`¡Red diseñada con ${data.topology.total_devices} dispositivos!`);
      appendChatMessage('Asistente', `✅ **${data.topology.name}** generada con éxito.\n- **Dispositivos:** ${data.topology.total_devices}\n- **Protocolo:** ${data.topology.routing_protocol}\n- **VLANs:** ${data.topology.vlans ? data.topology.vlans.length : 0}`);
    }
  } catch (err) {
    showToast('Error en generación: ' + err.message);
    appendChatMessage('Asistente', '❌ Ocurrió un error al procesar el prompt: ' + err.message);
  }
}

// Append Chat Message
function appendChatMessage(sender, text) {
  const msgDiv = document.createElement('div');
  const isUser = sender === 'Usuario';
  msgDiv.className = `p-2.5 rounded-lg text-xs leading-relaxed ${isUser ? 'bg-cyan-950/60 border border-cyan-800 text-cyan-100 ml-4' : 'bg-[#161f30] border border-gray-800 text-gray-300'}`;
  msgDiv.innerHTML = `
    <div class="font-bold mb-1 flex items-center space-x-1.5 ${isUser ? 'text-cyan-400' : 'text-emerald-400'}">
      <i class="fa-solid ${isUser ? 'fa-user' : 'fa-robot'}"></i>
      <span>${sender}</span>
    </div>
    <div class="whitespace-pre-line">${text}</div>
  `;
  chatHistory.appendChild(msgDiv);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Show Toast Notification
function showToast(msg) {
  toastMsg.textContent = msg;
  toast.classList.remove('opacity-0', 'translate-y-2', 'pointer-events-none');
  toast.classList.add('opacity-100', 'translate-y-0');
  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2', 'pointer-events-none');
    toast.classList.remove('opacity-100', 'translate-y-0');
  }, 3500);
}

// Live Deploy to Packet Tracer Bridge (Socket.IO Real-Time)
async function liveDeploy() {
  if (!currentTopology) {
    showToast('No hay ninguna topología activa para desplegar.');
    return;
  }

  showToast('Desplegando topología en vivo en Cisco Packet Tracer...');
  tabBridge.click();
  appendBridgeLog(`[LIVE BRIDGE] Iniciando despliegue de: ${currentTopology.name || 'Red'}...`);

  try {
    const res = await fetch('/api/bridge/deploy_live', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topology: currentTopology })
    });
    const data = await res.json();
    
    if (data.success) {
      showToast('¡Topología desplegada en vivo en Packet Tracer! 🎉');
      if (data.logs && data.logs.length) {
        data.logs.forEach(l => appendBridgeLog(`[LIVE] ${l}`));
      }
      appendBridgeLog(`[STATUS] Despliegue completado: ${data.stats?.devices || 0} dispositivos, ${data.stats?.links || 0} enlaces, ${data.stats?.configs || 0} configs.`);
    } else {
      showToast(data.error || 'Packet Tracer no conectado.');
      appendBridgeLog(`[AVISO] ${data.error}`);
      if (data.instruction) {
        appendBridgeLog(`[INSTRUCCIÓN] ${data.instruction}`);
      }
    }
  } catch (err) {
    showToast('Error en conexión: ' + err.message);
    appendBridgeLog(`[ERROR] ${err.message}`);
  }
}

// Append Bridge Log
function appendBridgeLog(msg) {
  const p = document.createElement('p');
  p.textContent = msg;
  bridgeLog.appendChild(p);
  bridgeLog.scrollTop = bridgeLog.scrollHeight;
}

// Poll Bridge Status
async function pollBridgeStatus() {
  try {
    const res = await fetch('/api/bridge/status');
    const data = await res.json();
    if (data.pt_connected) {
      bridgeText.textContent = 'PT: CONECTADO';
      bridgeBadge.classList.add('border-emerald-500', 'bridge-active');
    } else {
      bridgeText.textContent = data.active_queue_count > 0 ? `En Cola (${data.active_queue_count})` : 'Bridge: Esperando PT';
      bridgeBadge.classList.remove('border-emerald-500', 'bridge-active');
    }
  } catch (e) {
    // offline
  }
}

// Generic File Downloader
function downloadFile(url, bodyData, filename) {
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bodyData)
  })
  .then(res => res.blob())
  .then(blob => {
    const a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast(`Archivo ${filename} descargado.`);
  })
  .catch(err => showToast('Error descargando: ' + err.message));
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  initCytoscape();

  // Load Models
  fetch('/api/models')
    .then(r => r.json())
    .then(d => {
      if (d.ollama_models && d.ollama_models.length > 0) {
        modelSelect.innerHTML = '';
        d.ollama_models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m;
          opt.textContent = `Ollama: ${m} (Local)`;
          modelSelect.appendChild(opt);
        });
        const cloudOpts = ['gemini: Google Gemini API', 'openai: OpenAI GPT-4o'];
        cloudOpts.forEach(c => {
          const [val, label] = c.split(': ');
          const opt = document.createElement('option');
          opt.value = val;
          opt.textContent = label;
          modelSelect.appendChild(opt);
        });
      }
    })
    .catch(() => {});

  // Initial Scale Preset
  loadScalePreset('enterprise_150');

  // Poll Bridge every 4s
  setInterval(pollBridgeStatus, 4000);

  // Load Scale Preset button
  btnLoadScale.addEventListener('click', () => {
    loadScalePreset(scaleSelect.value);
  });

  // Prompt Send
  btnSendPrompt.addEventListener('click', () => {
    sendPrompt(promptInput.value);
  });
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendPrompt(promptInput.value);
    }
  });

  // Chips
  document.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      promptInput.value = chip.textContent.trim();
      sendPrompt(promptInput.value);
    });
  });

  // Layout switcher
  layoutSelect.addEventListener('change', () => {
    applyLayout(layoutSelect.value);
  });

  // Canvas Zoom / Pan buttons
  btnZoomIn.addEventListener('click', () => cy && cy.zoom(cy.zoom() * 1.25));
  btnZoomOut.addEventListener('click', () => cy && cy.zoom(cy.zoom() * 0.8));
  btnFit.addEventListener('click', () => cy && cy.fit(50));

  // Live Deploy Button
  btnLiveDeploy.addEventListener('click', liveDeploy);

  // Copy IOS
  btnCopyIos.addEventListener('click', () => {
    navigator.clipboard.writeText(iosCodeBlock.textContent);
    showToast('Configuraciones copiadas al portapapeles.');
  });

  // Export Menu
  btnExportMenu.addEventListener('click', (e) => {
    e.stopPropagation();
    exportDropdown.classList.toggle('hidden');
  });
  document.addEventListener('click', () => exportDropdown.classList.add('hidden'));

  document.getElementById('exportPkt').addEventListener('click', (e) => {
    e.preventDefault();
    if (!currentTopology) return;
    showToast('Generando archivo binario .pkt nativo...');
    downloadFile('/api/export/pkt', { topology: currentTopology }, `${currentTopology.name.replace(/ /g, '_')}.pkt`);
  });

  document.getElementById('exportXml').addEventListener('click', (e) => {
    e.preventDefault();
    if (!currentTopology) return;
    downloadFile('/api/export/xml', { topology: currentTopology }, `${currentTopology.name.replace(/ /g, '_')}.xml`);
  });

  document.getElementById('exportPtBuilder').addEventListener('click', (e) => {
    e.preventDefault();
    if (!currentTopology) return;
    downloadFile('/api/export/ptbuilder', { topology: currentTopology }, 'ptbuilder_topology.js');
  });

  document.getElementById('exportIos').addEventListener('click', (e) => {
    e.preventDefault();
    if (!currentTopology) return;
    downloadFile('/api/export/ios', { topology: currentTopology }, 'cisco_ios_configs.txt');
  });

  // Tab switching
  tabIos.addEventListener('click', () => {
    tabIos.className = 'flex-1 py-2 text-center font-medium text-cyan-400 border-b-2 border-cyan-400 transition';
    tabVlsm.className = 'flex-1 py-2 text-center font-medium text-gray-400 hover:text-gray-200 transition';
    tabBridge.className = 'flex-1 py-2 text-center font-medium text-gray-400 hover:text-gray-200 transition';
    contentIos.classList.remove('hidden');
    contentVlsm.classList.add('hidden');
    contentBridge.classList.add('hidden');
  });

  tabVlsm.addEventListener('click', () => {
    tabVlsm.className = 'flex-1 py-2 text-center font-medium text-cyan-400 border-b-2 border-cyan-400 transition';
    tabIos.className = 'flex-1 py-2 text-center font-medium text-gray-400 hover:text-gray-200 transition';
    tabBridge.className = 'flex-1 py-2 text-center font-medium text-gray-400 hover:text-gray-200 transition';
    contentVlsm.classList.remove('hidden');
    contentIos.classList.add('hidden');
    contentBridge.classList.add('hidden');
  });

  tabBridge.addEventListener('click', () => {
    tabBridge.className = 'flex-1 py-2 text-center font-medium text-cyan-400 border-b-2 border-cyan-400 transition';
    tabIos.className = 'flex-1 py-2 text-center font-medium text-gray-400 hover:text-gray-200 transition';
    tabVlsm.className = 'flex-1 py-2 text-center font-medium text-gray-400 hover:text-gray-200 transition';
    contentBridge.classList.remove('hidden');
    contentIos.classList.add('hidden');
    contentVlsm.classList.add('hidden');
  });

  // Filters
  const updateFilters = () => {
    if (!cy) return;
    const showCore = document.getElementById('filterCore').checked;
    const showDist = document.getElementById('filterDist').checked;
    const showAccess = document.getElementById('filterAccess').checked;
    const showEnd = document.getElementById('filterEndpoints').checked;

    cy.nodes().forEach(node => {
      const layer = node.data('layer');
      if (layer === 'core') node.style('display', showCore ? 'element' : 'none');
      else if (layer === 'distribution') node.style('display', showDist ? 'element' : 'none');
      else if (layer === 'access') node.style('display', showAccess ? 'element' : 'none');
      else node.style('display', showEnd ? 'element' : 'none');
    });
  };

  document.getElementById('filterCore').addEventListener('change', updateFilters);
  document.getElementById('filterDist').addEventListener('change', updateFilters);
  document.getElementById('filterAccess').addEventListener('change', updateFilters);
  document.getElementById('filterEndpoints').addEventListener('change', updateFilters);
});
