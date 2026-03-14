/**
 * Verificador DUSA - Extension Chrome
 * Popup Script - Lógica principal con soporte paralelo
 */

// Estado de la aplicación
const state = {
  connected: false,
  tabId: null,
  tabIds: [],           // Array de tabs para procesamiento paralelo
  productos: [],
  columnaSeleccionada: null,
  procesando: false,
  detenido: false,
  resultados: [],
  numTabs: 3,           // Número de ventanas paralelas
  tiempoInicio: null,
  tiemposProductos: []  // Para calcular promedio
};

// Elementos del DOM
const elements = {};

// Inicialización
document.addEventListener('DOMContentLoaded', init);

async function init() {
  cacheElements();
  setupEventListeners();
  await checkConnection();
}

function cacheElements() {
  elements.statusDot = document.getElementById('status-dot');
  elements.statusText = document.getElementById('status-text');
  elements.uploadZone = document.getElementById('upload-zone');
  elements.fileInput = document.getElementById('file-input');
  elements.fileInfo = document.getElementById('file-info');
  elements.btnClearFile = document.getElementById('btn-clear-file');
  elements.stepConfig = document.getElementById('step-config');
  elements.columnSelect = document.getElementById('column-select');
  elements.tabsSelect = document.getElementById('tabs-select');
  elements.previewList = document.getElementById('preview-list');
  elements.stepProcess = document.getElementById('step-process');
  elements.btnStart = document.getElementById('btn-start');
  elements.btnStop = document.getElementById('btn-stop');
  elements.progressContainer = document.getElementById('progress-container');
  elements.progressFill = document.getElementById('progress-fill');
  elements.progressText = document.getElementById('progress-text');
  elements.progressPercent = document.getElementById('progress-percent');
  elements.parallelStats = document.getElementById('parallel-stats');
  elements.tabsActive = document.getElementById('tabs-active');
  elements.timeEstimate = document.getElementById('time-estimate');
  elements.currentProduct = document.getElementById('current-product');
  elements.stepResults = document.getElementById('step-results');
  elements.summary = document.getElementById('summary');
  elements.resultsBody = document.getElementById('results-body');
  elements.btnDownload = document.getElementById('btn-download');
  elements.btnNew = document.getElementById('btn-new');
  elements.errorMessage = document.getElementById('error-message');
}

function setupEventListeners() {
  // Upload
  elements.uploadZone.addEventListener('click', () => elements.fileInput.click());
  elements.fileInput.addEventListener('change', handleFileSelect);
  elements.uploadZone.addEventListener('dragover', handleDragOver);
  elements.uploadZone.addEventListener('dragleave', handleDragLeave);
  elements.uploadZone.addEventListener('drop', handleDrop);
  elements.btnClearFile.addEventListener('click', clearFile);
  
  // Config
  elements.columnSelect.addEventListener('change', handleColumnChange);
  
  // Process
  elements.btnStart.addEventListener('click', startVerification);
  elements.btnStop.addEventListener('click', stopVerification);
  
  // Results
  elements.btnDownload.addEventListener('click', downloadResults);
  elements.btnNew.addEventListener('click', resetApp);
}

// ==================== CONEXIÓN ====================

async function checkConnection() {
  try {
    // Buscar pestaña de DUSA abierta
    const tabs = await chrome.tabs.query({ url: 'https://pedidos.dusa.com.uy/*' });
    
    if (tabs.length > 0) {
      state.tabId = tabs[0].id;
      
      // Verificar si está logueado
      const response = await sendToContent({ action: 'checkLogin' });
      
      if (response && response.loggedIn) {
        setConnectionStatus(true, 'Conectado a DUSA');
      } else {
        setConnectionStatus(false, 'Abre DUSA e inicia sesión');
      }
    } else {
      setConnectionStatus(false, 'Abre pedidos.dusa.com.uy primero');
    }
  } catch (error) {
    setConnectionStatus(false, 'Error de conexión');
    console.error('Error checking connection:', error);
  }
}

function setConnectionStatus(connected, message) {
  state.connected = connected;
  elements.statusDot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
  elements.statusText.textContent = message;
  
  // Habilitar/deshabilitar botones según conexión
  if (elements.btnStart) {
    elements.btnStart.disabled = !connected;
  }
}

// ==================== ARCHIVO ====================

function handleDragOver(e) {
  e.preventDefault();
  elements.uploadZone.classList.add('dragover');
}

function handleDragLeave(e) {
  e.preventDefault();
  elements.uploadZone.classList.remove('dragover');
}

function handleDrop(e) {
  e.preventDefault();
  elements.uploadZone.classList.remove('dragover');
  
  const file = e.dataTransfer.files[0];
  if (file) processFile(file);
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) processFile(file);
}

async function processFile(file) {
  if (!file.name.match(/\.(xlsx|xls)$/i)) {
    showError('Solo se permiten archivos Excel (.xlsx, .xls)');
    return;
  }
  
  try {
    const data = await readExcelFile(file);
    
    if (!data || data.length === 0) {
      showError('El archivo está vacío o no se pudo leer');
      return;
    }
    
    // Guardar datos
    state.excelData = data;
    state.columns = Object.keys(data[0]);
    
    // Mostrar info del archivo
    elements.fileInfo.classList.remove('hidden');
    elements.fileInfo.querySelector('.file-name').textContent = file.name;
    elements.fileInfo.querySelector('.file-count').textContent = `${data.length} filas`;
    elements.uploadZone.classList.add('hidden');
    
    // Mostrar paso de configuración
    showConfigStep();
    
  } catch (error) {
    showError('Error leyendo el archivo: ' + error.message);
    console.error(error);
  }
}

function readExcelFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const jsonData = XLSX.utils.sheet_to_json(firstSheet, { defval: '' });
        resolve(jsonData);
      } catch (err) {
        reject(err);
      }
    };
    
    reader.onerror = () => reject(new Error('Error leyendo archivo'));
    reader.readAsArrayBuffer(file);
  });
}

function clearFile() {
  state.excelData = null;
  state.columns = null;
  state.productos = [];
  
  elements.fileInfo.classList.add('hidden');
  elements.uploadZone.classList.remove('hidden');
  elements.stepConfig.classList.add('hidden');
  elements.stepProcess.classList.add('hidden');
  elements.fileInput.value = '';
}

// ==================== CONFIGURACIÓN ====================

function showConfigStep() {
  elements.stepConfig.classList.remove('hidden');
  
  // Llenar selector de columnas
  elements.columnSelect.innerHTML = '<option value="">Selecciona una columna...</option>';
  
  state.columns.forEach(col => {
    const option = document.createElement('option');
    option.value = col;
    option.textContent = col;
    
    // Auto-seleccionar si parece ser código de barras
    if (col.toLowerCase().includes('codigo') || 
        col.toLowerCase().includes('barras') || 
        col.toLowerCase().includes('ean') ||
        col.toLowerCase().includes('sku')) {
      option.selected = true;
      handleColumnChange({ target: { value: col } });
    }
    
    elements.columnSelect.appendChild(option);
  });
}

function handleColumnChange(e) {
  const column = e.target.value;
  if (!column) return;
  
  state.columnaSeleccionada = column;
  
  // Extraer productos (códigos de barras)
  state.productos = state.excelData
    .map(row => String(row[column] || '').trim())
    .filter(code => code.length > 0);
  
  // Mostrar preview
  elements.previewList.innerHTML = '';
  state.productos.slice(0, 5).forEach(code => {
    const li = document.createElement('li');
    li.textContent = code;
    elements.previewList.appendChild(li);
  });
  
  if (state.productos.length > 5) {
    const li = document.createElement('li');
    li.textContent = `... y ${state.productos.length - 5} más`;
    li.style.color = '#999';
    elements.previewList.appendChild(li);
  }
  
  // Mostrar paso de proceso
  elements.stepProcess.classList.remove('hidden');
  elements.btnStart.disabled = !state.connected;
}

// ==================== VERIFICACIÓN ====================

async function startVerification() {
  if (!state.connected) {
    showError('Primero abre DUSA e inicia sesión');
    return;
  }
  
  if (state.productos.length === 0) {
    showError('No hay productos para verificar');
    return;
  }
  
  // Obtener número de tabs seleccionado
  state.numTabs = parseInt(elements.tabsSelect.value) || 1;
  
  state.procesando = true;
  state.detenido = false;
  state.resultados = [];
  state.tiempoInicio = Date.now();
  state.tiemposProductos = [];
  
  // UI
  elements.btnStart.classList.add('hidden');
  elements.btnStop.classList.remove('hidden');
  elements.progressContainer.classList.remove('hidden');
  elements.stepResults.classList.add('hidden');
  elements.resultsBody.innerHTML = '';
  hideError();
  
  const total = state.productos.length;
  
  try {
    if (state.numTabs === 1) {
      // Procesamiento secuencial (una sola ventana)
      await processSequential(total);
    } else {
      // Procesamiento paralelo (múltiples ventanas)
      await processParallel(total);
    }
  } catch (error) {
    console.error('Error en verificación:', error);
    showError('Error durante la verificación: ' + error.message);
  }
  
  // Finalizar
  state.procesando = false;
  finishVerification();
}

/**
 * Procesamiento secuencial - un producto a la vez
 */
async function processSequential(total) {
  updateTabsActive(1);
  
  for (let i = 0; i < total; i++) {
    if (state.detenido) break;
    
    const codigo = state.productos[i];
    const tiempoProductoInicio = Date.now();
    
    updateProgress(i, total, codigo);
    
    try {
      const resultado = await verificarProducto(state.tabId, codigo);
      state.resultados.push(resultado);
      addResultToTable(resultado);
      
      // Registrar tiempo
      state.tiemposProductos.push(Date.now() - tiempoProductoInicio);
      updateTimeEstimate(i + 1, total);
      
    } catch (error) {
      console.error(`Error verificando ${codigo}:`, error);
      state.resultados.push({
        codigo: codigo,
        producto: 'Error',
        stock: '-',
        precio: '-',
        estado: 'error',
        mensaje: error.message
      });
    }
    
    await sleep(300);
  }
}

/**
 * Procesamiento paralelo - múltiples ventanas
 */
async function processParallel(total) {
  // Crear tabs adicionales para procesamiento paralelo
  const tabsNeeded = Math.min(state.numTabs, total);
  state.tabIds = [state.tabId]; // La primera tab ya existe
  
  elements.currentProduct.textContent = 'Abriendo ventanas paralelas...';
  
  // Crear tabs adicionales
  for (let i = 1; i < tabsNeeded; i++) {
    try {
      const newTab = await chrome.tabs.create({
        url: 'https://pedidos.dusa.com.uy/DUSAWebUI',
        active: false
      });
      state.tabIds.push(newTab.id);
      await sleep(1500); // Esperar a que cargue
    } catch (error) {
      console.error('Error creando tab:', error);
    }
  }
  
  updateTabsActive(state.tabIds.length);
  
  // Dividir productos entre las tabs
  let productoIndex = 0;
  const pendientes = [...state.productos];
  const enProceso = new Map(); // tabId -> producto actual
  
  // Función para procesar un producto en una tab específica
  async function procesarEnTab(tabId) {
    while (pendientes.length > 0 && !state.detenido) {
      const codigo = pendientes.shift();
      const indexActual = productoIndex++;
      const tiempoProductoInicio = Date.now();
      
      enProceso.set(tabId, codigo);
      updateProgressParallel(state.resultados.length, total, enProceso);
      
      try {
        const resultado = await verificarProducto(tabId, codigo);
        state.resultados.push(resultado);
        addResultToTable(resultado);
        
        // Registrar tiempo
        state.tiemposProductos.push(Date.now() - tiempoProductoInicio);
        updateTimeEstimate(state.resultados.length, total);
        
      } catch (error) {
        console.error(`Error en tab ${tabId} verificando ${codigo}:`, error);
        state.resultados.push({
          codigo: codigo,
          producto: 'Error',
          stock: '-',
          precio: '-',
          estado: 'error',
          mensaje: error.message
        });
      }
      
      enProceso.delete(tabId);
      await sleep(200);
    }
  }
  
  // Iniciar procesamiento en todas las tabs
  const promesas = state.tabIds.map(tabId => procesarEnTab(tabId));
  await Promise.all(promesas);
  
  // Cerrar tabs adicionales (mantener la primera)
  for (let i = 1; i < state.tabIds.length; i++) {
    try {
      await chrome.tabs.remove(state.tabIds[i]);
    } catch (e) {
      // Tab ya cerrada
    }
  }
  state.tabIds = [state.tabId];
}

async function verificarProducto(tabId, codigo) {
  const response = await sendToTab(tabId, {
    action: 'buscarProducto',
    codigo: codigo
  });
  
  if (!response) {
    throw new Error('Sin respuesta del content script');
  }
  
  return {
    codigo: codigo,
    producto: response.nombre || 'No encontrado',
    stock: response.stock || '-',
    precio: response.precio || '-',
    estado: response.estado || 'no_encontrado',
    mensaje: response.mensaje || ''
  };
}

function stopVerification() {
  state.detenido = true;
  state.procesando = false;
  elements.btnStop.classList.add('hidden');
  elements.btnStart.classList.remove('hidden');
  
  // Cerrar tabs adicionales
  if (state.tabIds && state.tabIds.length > 1) {
    for (let i = 1; i < state.tabIds.length; i++) {
      try {
        chrome.tabs.remove(state.tabIds[i]);
      } catch (e) {
        // Tab ya cerrada
      }
    }
    state.tabIds = [state.tabId];
  }
}

function updateProgress(current, total, producto) {
  const percent = Math.round((current / total) * 100);
  elements.progressFill.style.width = percent + '%';
  elements.progressText.textContent = `${current} / ${total}`;
  elements.progressPercent.textContent = percent + '%';
  elements.currentProduct.textContent = `Verificando: ${producto}`;
}

function updateProgressParallel(completed, total, enProceso) {
  const percent = Math.round((completed / total) * 100);
  elements.progressFill.style.width = percent + '%';
  elements.progressText.textContent = `${completed} / ${total}`;
  elements.progressPercent.textContent = percent + '%';
  
  // Mostrar los productos en proceso
  const procesando = Array.from(enProceso.values()).join(', ');
  elements.currentProduct.textContent = procesando ? `Verificando: ${procesando}` : 'Procesando...';
}

function updateTabsActive(count) {
  if (elements.tabsActive) {
    elements.tabsActive.textContent = `Ventanas activas: ${count}`;
  }
}

function updateTimeEstimate(completed, total) {
  if (state.tiemposProductos.length < 3) return; // Necesitamos al menos 3 para un promedio útil
  
  const promedio = state.tiemposProductos.reduce((a, b) => a + b, 0) / state.tiemposProductos.length;
  const restantes = total - completed;
  const tiempoRestante = (promedio * restantes) / state.numTabs; // Dividir por número de tabs
  
  const minutos = Math.floor(tiempoRestante / 60000);
  const segundos = Math.floor((tiempoRestante % 60000) / 1000);
  
  if (elements.timeEstimate) {
    if (minutos > 0) {
      elements.timeEstimate.textContent = `~${minutos}m ${segundos}s restantes`;
    } else {
      elements.timeEstimate.textContent = `~${segundos}s restantes`;
    }
  }
}

function finishVerification() {
  elements.btnStop.classList.add('hidden');
  elements.btnStart.classList.remove('hidden');
  elements.currentProduct.textContent = 'Verificación completada';
  
  // Mostrar resumen
  showResults();
}

// ==================== RESULTADOS ====================

function showResults() {
  elements.stepResults.classList.remove('hidden');
  
  // Calcular estadísticas
  const total = state.resultados.length;
  const disponibles = state.resultados.filter(r => r.estado === 'disponible').length;
  const agotados = state.resultados.filter(r => r.estado === 'agotado').length;
  const noEncontrados = state.resultados.filter(r => r.estado === 'no_encontrado' || r.estado === 'error').length;
  
  // Mostrar resumen
  elements.summary.innerHTML = `
    <div class="summary-item total">
      <div class="number">${total}</div>
      <div class="label">Total</div>
    </div>
    <div class="summary-item disponible">
      <div class="number">${disponibles}</div>
      <div class="label">Disponibles</div>
    </div>
    <div class="summary-item agotado">
      <div class="number">${agotados}</div>
      <div class="label">Agotados</div>
    </div>
    <div class="summary-item no-encontrado">
      <div class="number">${noEncontrados}</div>
      <div class="label">No encontrados</div>
    </div>
  `;
}

function addResultToTable(resultado) {
  const tr = document.createElement('tr');
  
  let badgeClass = 'badge-secondary';
  let estadoText = 'No encontrado';
  
  if (resultado.estado === 'disponible') {
    badgeClass = 'badge-success';
    estadoText = 'Disponible';
  } else if (resultado.estado === 'agotado') {
    badgeClass = 'badge-danger';
    estadoText = 'Agotado';
  }
  
  tr.innerHTML = `
    <td>${resultado.codigo}</td>
    <td title="${resultado.producto}">${truncate(resultado.producto, 25)}</td>
    <td>${resultado.stock}</td>
    <td>${resultado.precio}</td>
    <td><span class="badge ${badgeClass}">${estadoText}</span></td>
  `;
  
  elements.resultsBody.appendChild(tr);
  
  // Scroll al final
  const container = document.querySelector('.results-table-container');
  container.scrollTop = container.scrollHeight;
}

function downloadResults() {
  if (state.resultados.length === 0) return;
  
  // Crear workbook
  const ws = XLSX.utils.json_to_sheet(state.resultados.map(r => ({
    'Código': r.codigo,
    'Producto': r.producto,
    'Stock': r.stock,
    'Precio': r.precio,
    'Estado': r.estado === 'disponible' ? 'Disponible' : 
              r.estado === 'agotado' ? 'Agotado' : 'No encontrado'
  })));
  
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Resultados');
  
  // Descargar
  const fecha = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(wb, `verificacion_dusa_${fecha}.xlsx`);
}

function resetApp() {
  clearFile();
  state.resultados = [];
  elements.resultsBody.innerHTML = '';
  elements.stepResults.classList.add('hidden');
  elements.progressContainer.classList.add('hidden');
  elements.progressFill.style.width = '0%';
}

// ==================== UTILIDADES ====================

async function sendToContent(message) {
  return sendToTab(state.tabId, message);
}

async function sendToTab(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response);
      }
    });
  });
}

function showError(message) {
  elements.errorMessage.querySelector('p').textContent = message;
  elements.errorMessage.classList.remove('hidden');
}

function hideError() {
  elements.errorMessage.classList.add('hidden');
}

function truncate(str, length) {
  if (!str) return '';
  return str.length > length ? str.substring(0, length) + '...' : str;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
