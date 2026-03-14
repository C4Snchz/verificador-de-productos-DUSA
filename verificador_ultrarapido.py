#!/usr/bin/env python3
"""
Verificador DUSA - Versión Ultra Rápida
=======================================
Usa UN SOLO Chrome y ejecuta búsquedas mediante JavaScript.
Sin múltiples ventanas, sin Selenium lento.
IDEAL PARA SERVIDOR CON POCOS RECURSOS.
"""

import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config


class VerificadorUltraRapido:
    """
    Verificador optimizado para servidores con pocos recursos.
    Usa UN SOLO navegador y hace búsquedas super rápidas.
    """
    
    def __init__(self, headless=True):
        self.driver = None
        self.headless = headless
        self.resultados = []
        self.campo_busqueda = None
        
    def iniciar(self):
        """Inicia el navegador y hace login."""
        print("🚀 Iniciando Verificador Ultra Rápido...")
        
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        # Optimizaciones de memoria
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # No cargar imágenes
        options.add_argument("--blink-settings=imagesEnabled=false")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(5)
        
        # Login
        if not self._login():
            return False
        
        # Ir a productos
        self._ir_a_productos()
        
        # Cachear el campo de búsqueda
        self._encontrar_campo_busqueda()
        
        return True
    
    def _login(self):
        """Hace login en DUSA."""
        print("🔐 Haciendo login...")
        
        try:
            self.driver.get(config.DUSA_URL)
            time.sleep(3)
            
            campos = self.driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
            if campos:
                campos[0].send_keys(config.DUSA_USUARIO)
            
            campo_pass = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            campo_pass.send_keys(config.DUSA_PASSWORD)
            
            for campo in campos[1:]:
                if campo.get_attribute('type') == 'text':
                    campo.send_keys(config.DUSA_CLIENTE)
                    break
            
            boton = self.driver.find_element(By.CSS_SELECTOR, ".v-button, button")
            boton.click()
            
            time.sleep(4)
            print("✅ Login exitoso")
            return True
            
        except Exception as e:
            print(f"❌ Error en login: {e}")
            return False
    
    def _ir_a_productos(self):
        """Navega a la sección de productos."""
        print("📦 Navegando a productos...")
        self.driver.get(config.DUSA_URL + "#!micuenta/productos")
        time.sleep(3)
    
    def _encontrar_campo_busqueda(self):
        """Encuentra y cachea el campo de búsqueda."""
        try:
            campos = self.driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
            for campo in campos:
                if campo.is_displayed() and campo.is_enabled():
                    self.campo_busqueda = campo
                    print("✅ Campo de búsqueda encontrado")
                    return True
        except:
            pass
        print("⚠️ Campo de búsqueda no encontrado")
        return False
    
    def buscar_producto_rapido(self, codigo):
        """
        Busca un producto de forma ultra rápida.
        Usa JavaScript para manipular el DOM directamente.
        """
        try:
            # Limpiar campo con JavaScript (más rápido que .clear())
            self.driver.execute_script("""
                var inputs = document.querySelectorAll('input.v-textfield, input[type="text"]');
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].offsetParent !== null) {  // visible
                        inputs[i].value = arguments[0];
                        inputs[i].dispatchEvent(new Event('input', {bubbles: true}));
                        inputs[i].dispatchEvent(new Event('change', {bubbles: true}));
                        // Simular Enter
                        inputs[i].dispatchEvent(new KeyboardEvent('keydown', {
                            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
                        }));
                        inputs[i].dispatchEvent(new KeyboardEvent('keyup', {
                            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
                        }));
                        break;
                    }
                }
            """, codigo)
            
            # Esperar respuesta (mínimo necesario)
            time.sleep(1.2)
            
            # Leer resultados con JavaScript (más rápido)
            resultado = self.driver.execute_script("""
                var body = document.body.innerText.toLowerCase();
                var resultado = {
                    encontrado: false,
                    agotado: false,
                    disponible: false,
                    texto: ''
                };
                
                // Buscar tabla de resultados
                var tablas = document.querySelectorAll('.v-table-body tr, table tbody tr, .v-grid-body tr');
                if (tablas.length > 0) {
                    resultado.encontrado = true;
                    resultado.texto = tablas[0].innerText;
                    
                    var textoRow = tablas[0].innerText.toLowerCase();
                    if (textoRow.includes('agotado') || textoRow.includes('sin stock') || textoRow.includes('0')) {
                        resultado.agotado = true;
                    } else {
                        resultado.disponible = true;
                    }
                }
                
                // Buscar mensajes de error
                if (body.includes('no se encontr') || body.includes('sin resultado')) {
                    resultado.encontrado = false;
                }
                
                return resultado;
            """)
            
            # Construir respuesta
            if resultado.get('encontrado'):
                estado = 'agotado' if resultado.get('agotado') else 'disponible'
                return {
                    'codigo': codigo,
                    'estado': estado,
                    'texto': resultado.get('texto', '')[:100],
                    'nombre': self._extraer_nombre(resultado.get('texto', '')),
                    'stock': self._extraer_stock(resultado.get('texto', '')),
                    'precio': self._extraer_precio(resultado.get('texto', ''))
                }
            else:
                return {
                    'codigo': codigo,
                    'estado': 'no_encontrado',
                    'nombre': '',
                    'stock': '-',
                    'precio': '-'
                }
                
        except Exception as e:
            return {
                'codigo': codigo,
                'estado': 'error',
                'mensaje': str(e)
            }
    
    def _extraer_nombre(self, texto):
        """Extrae el nombre del producto del texto."""
        # Tomar la primera línea o primeras palabras
        if texto:
            partes = texto.split('\n')
            if len(partes) > 1:
                return partes[0][:50]
        return texto[:50] if texto else ''
    
    def _extraer_stock(self, texto):
        """Extrae el stock del texto."""
        import re
        # Buscar números que parezcan stock
        match = re.search(r'(\d+)\s*(unid|disp|stock)|stock[:\s]*(\d+)', texto.lower())
        if match:
            return match.group(1) or match.group(3)
        return '-'
    
    def _extraer_precio(self, texto):
        """Extrae el precio del texto."""
        import re
        match = re.search(r'\$?\s*([\d.,]+)', texto)
        if match:
            return '$' + match.group(1)
        return '-'
    
    def verificar_lista(self, codigos, callback=None):
        """
        Verifica una lista de códigos de forma ultra rápida.
        
        Args:
            codigos: Lista de códigos de barras
            callback: Función opcional llamada después de cada producto (codigo, resultado, progreso)
        
        Returns:
            Lista de resultados
        """
        total = len(codigos)
        print(f"\n🔎 Verificando {total} productos...")
        
        inicio = time.time()
        
        for i, codigo in enumerate(codigos):
            resultado = self.buscar_producto_rapido(str(codigo))
            self.resultados.append(resultado)
            
            # Callback para progreso
            if callback:
                callback(codigo, resultado, (i + 1) / total)
            
            # Mostrar progreso
            progreso = (i + 1) / total * 100
            tiempo = time.time() - inicio
            velocidad = (i + 1) / tiempo if tiempo > 0 else 0
            restante = (total - i - 1) / velocidad if velocidad > 0 else 0
            
            estado_emoji = "✅" if resultado['estado'] == 'disponible' else "❌" if resultado['estado'] == 'agotado' else "⚪"
            print(f"  [{i+1}/{total}] {estado_emoji} {codigo}: {resultado['estado']} ({velocidad:.1f}/seg, ~{restante:.0f}s restantes)")
        
        duracion = time.time() - inicio
        print(f"\n⏱️ Completado en {duracion:.1f} segundos ({total/duracion:.1f} productos/segundo)")
        
        return self.resultados
    
    def exportar_excel(self, filename=None):
        """Exporta los resultados a Excel."""
        if not self.resultados:
            print("⚠️ No hay resultados para exportar")
            return None
        
        if not filename:
            filename = f"verificacion_dusa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        df = pd.DataFrame(self.resultados)
        df.to_excel(filename, index=False)
        print(f"📊 Resultados exportados a: {filename}")
        return filename
    
    def cerrar(self):
        """Cierra el navegador."""
        if self.driver:
            self.driver.quit()
            print("👋 Navegador cerrado")


def main():
    """Prueba del verificador ultra rápido."""
    print("=" * 60)
    print("🚀 VERIFICADOR DUSA - VERSIÓN ULTRA RÁPIDA")
    print("   Un solo Chrome, búsquedas instantáneas")
    print("=" * 60)
    
    verificador = VerificadorUltraRapido(headless=True)
    
    try:
        if not verificador.iniciar():
            print("❌ Error iniciando verificador")
            return
        
        # Productos de prueba
        codigos_prueba = [
            "7891010604141",
            "7896015519254", 
            "7791290007901",
            "7790250049753",
            "7501008042199"
        ]
        
        # Verificar
        resultados = verificador.verificar_lista(codigos_prueba)
        
        # Resumen
        print("\n" + "=" * 60)
        print("📊 RESUMEN:")
        disponibles = sum(1 for r in resultados if r['estado'] == 'disponible')
        agotados = sum(1 for r in resultados if r['estado'] == 'agotado')
        no_encontrados = sum(1 for r in resultados if r['estado'] == 'no_encontrado')
        
        print(f"   ✅ Disponibles: {disponibles}")
        print(f"   ❌ Agotados: {agotados}")
        print(f"   ⚪ No encontrados: {no_encontrados}")
        
        # Exportar
        verificador.exportar_excel()
        
    finally:
        verificador.cerrar()


if __name__ == "__main__":
    main()
