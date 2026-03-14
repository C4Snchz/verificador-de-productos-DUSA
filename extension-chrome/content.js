/**
 * Verificador DUSA - Content Script
 * Este script se inyecta en la página de DUSA y realiza las búsquedas
 */

// Escuchar mensajes del popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message).then(sendResponse);
  return true; // Mantener el canal abierto para respuesta async
});

async function handleMessage(message) {
  switch (message.action) {
    case 'checkLogin':
      return checkLogin();
    
    case 'buscarProducto':
      return buscarProducto(message.codigo);
    
    default:
      return { error: 'Acción no reconocida' };
  }
}

/**
 * Verifica si el usuario está logueado en DUSA
 */
function checkLogin() {
  // Buscar elementos que indiquen que está logueado
  // Ajustar estos selectores según la estructura real de DUSA
  
  const indicadoresLogin = [
    // Menú principal visible
    document.querySelector('.v-menubar'),
    document.querySelector('#menu'),
    document.querySelector('[class*="menu"]'),
    // Nombre de usuario visible
    document.querySelector('[class*="usuario"]'),
    document.querySelector('[class*="user"]'),
    // Formulario de búsqueda visible
    document.querySelector('input[type="text"]'),
    // NO hay formulario de login
    !document.querySelector('#loginf')
  ];
  
  const loggedIn = indicadoresLogin.some(el => el);
  
  return { loggedIn };
}

/**
 * Busca un producto por código de barras
 */
async function buscarProducto(codigo) {
  try {
    // 1. Encontrar el campo de búsqueda
    const campoBusqueda = await encontrarCampoBusqueda();
    
    if (!campoBusqueda) {
      return {
        estado: 'error',
        mensaje: 'No se encontró el campo de búsqueda'
      };
    }
    
    // 2. Limpiar y escribir el código
    campoBusqueda.value = '';
    campoBusqueda.focus();
    
    // Simular escritura
    campoBusqueda.value = codigo;
    campoBusqueda.dispatchEvent(new Event('input', { bubbles: true }));
    campoBusqueda.dispatchEvent(new Event('change', { bubbles: true }));
    
    // 3. Presionar Enter o hacer clic en buscar
    const enterEvent = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true
    });
    campoBusqueda.dispatchEvent(enterEvent);
    
    // También intentar con keyup
    campoBusqueda.dispatchEvent(new KeyboardEvent('keyup', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true
    }));
    
    // 4. Esperar resultados
    await sleep(1500);
    
    // 5. Leer resultados
    const resultado = leerResultados(codigo);
    
    return resultado;
    
  } catch (error) {
    console.error('Error buscando producto:', error);
    return {
      estado: 'error',
      mensaje: error.message
    };
  }
}

/**
 * Encuentra el campo de búsqueda en la página
 */
async function encontrarCampoBusqueda() {
  // Selectores comunes para el campo de búsqueda en DUSA (Vaadin)
  const selectores = [
    'input.v-textfield[placeholder*="buscar"]',
    'input.v-textfield[placeholder*="Buscar"]',
    'input.v-textfield[placeholder*="código"]',
    'input.v-textfield[placeholder*="producto"]',
    'input[type="text"].v-textfield',
    '.v-slot-buscar input',
    '#buscar input',
    'input.linea-form',
    // Genéricos
    'input[type="text"]:not([type="password"])'
  ];
  
  for (const selector of selectores) {
    const campo = document.querySelector(selector);
    if (campo && isVisible(campo)) {
      return campo;
    }
  }
  
  // Si no encontramos, buscar todos los inputs visibles
  const inputs = document.querySelectorAll('input[type="text"]');
  for (const input of inputs) {
    if (isVisible(input) && !input.type.includes('password')) {
      return input;
    }
  }
  
  return null;
}

/**
 * Lee los resultados de la búsqueda
 */
function leerResultados(codigoBuscado) {
  // Buscar tabla de resultados o lista de productos
  const selectoresTabla = [
    '.v-table-body tr',
    '.v-grid-body tr',
    'table tbody tr',
    '.producto-item',
    '.resultado-item',
    '[class*="resultado"]',
    '[class*="product"]'
  ];
  
  let filas = [];
  for (const selector of selectoresTabla) {
    filas = document.querySelectorAll(selector);
    if (filas.length > 0) break;
  }
  
  // Si no hay resultados
  if (filas.length === 0) {
    // Buscar mensaje de "no encontrado"
    const noEncontrado = document.body.innerText.toLowerCase();
    if (noEncontrado.includes('no se encontr') || 
        noEncontrado.includes('sin resultado') ||
        noEncontrado.includes('no hay producto')) {
      return {
        estado: 'no_encontrado',
        nombre: 'Producto no encontrado',
        stock: '-',
        precio: '-'
      };
    }
  }
  
  // Analizar primera fila de resultados
  if (filas.length > 0) {
    const fila = filas[0];
    const texto = fila.innerText;
    const celdas = fila.querySelectorAll('td');
    
    // Intentar extraer información
    let nombre = '';
    let stock = '-';
    let precio = '-';
    let estado = 'no_encontrado';
    
    // Buscar nombre del producto
    const nombreEl = fila.querySelector('[class*="nombre"], [class*="descripcion"], td:nth-child(2)');
    if (nombreEl) nombre = nombreEl.innerText.trim();
    
    // Buscar stock
    const stockEl = fila.querySelector('[class*="stock"], [class*="cantidad"], [class*="disp"]');
    if (stockEl) {
      stock = stockEl.innerText.trim();
    } else {
      // Buscar número que parezca stock
      const stockMatch = texto.match(/stock[:\s]*(\d+)/i) || texto.match(/disp[:\s]*(\d+)/i);
      if (stockMatch) stock = stockMatch[1];
    }
    
    // Buscar precio
    const precioEl = fila.querySelector('[class*="precio"], [class*="price"]');
    if (precioEl) {
      precio = precioEl.innerText.trim();
    } else {
      // Buscar patrón de precio
      const precioMatch = texto.match(/\$?\s*[\d,.]+/);
      if (precioMatch) precio = precioMatch[0];
    }
    
    // Determinar estado
    if (stock && stock !== '-') {
      const stockNum = parseInt(stock.replace(/\D/g, ''));
      if (stockNum > 0) {
        estado = 'disponible';
      } else {
        estado = 'agotado';
      }
    }
    
    // Buscar indicadores visuales de disponibilidad
    const clases = fila.className + ' ' + Array.from(fila.querySelectorAll('*')).map(e => e.className).join(' ');
    if (clases.includes('agotado') || clases.includes('sin-stock') || clases.includes('unavailable')) {
      estado = 'agotado';
    }
    if (clases.includes('disponible') || clases.includes('en-stock') || clases.includes('available')) {
      estado = 'disponible';
    }
    
    // Buscar en el texto
    const textoLower = texto.toLowerCase();
    if (textoLower.includes('agotado') || textoLower.includes('sin stock')) {
      estado = 'agotado';
    }
    
    return {
      estado: estado,
      nombre: nombre || 'Producto encontrado',
      stock: stock,
      precio: precio
    };
  }
  
  return {
    estado: 'no_encontrado',
    nombre: 'No encontrado',
    stock: '-',
    precio: '-'
  };
}

/**
 * Verifica si un elemento es visible
 */
function isVisible(element) {
  if (!element) return false;
  const style = window.getComputedStyle(element);
  return style.display !== 'none' && 
         style.visibility !== 'hidden' && 
         style.opacity !== '0' &&
         element.offsetParent !== null;
}

/**
 * Espera un tiempo
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Notificar que el content script está cargado
console.log('🔍 Verificador DUSA - Content script cargado');
