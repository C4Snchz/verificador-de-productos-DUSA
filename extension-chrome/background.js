/**
 * Verificador DUSA - Service Worker (Background)
 * Maneja eventos de la extensión
 */

// Cuando se instala la extensión
chrome.runtime.onInstalled.addListener(() => {
  console.log('Verificador DUSA instalado correctamente');
});

// Escuchar mensajes
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'openDUSA') {
    chrome.tabs.create({ 
      url: 'https://pedidos.dusa.com.uy/DUSAWebUI' 
    });
  }
  return true;
});

// Cuando se hace clic en el icono y no hay popup
chrome.action.onClicked.addListener((tab) => {
  // Si no estamos en DUSA, abrir la página
  if (!tab.url.includes('pedidos.dusa.com.uy')) {
    chrome.tabs.create({ 
      url: 'https://pedidos.dusa.com.uy/DUSAWebUI' 
    });
  }
});
