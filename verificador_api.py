#!/usr/bin/env python3
"""
Verificador DUSA - Versión API Directa
======================================
Usa Selenium solo para login, luego hace requests HTTP directos.
MUCHO más rápido y usa menos recursos.
"""

import requests
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import config


class VerificadorDUSARapido:
    """Verificador optimizado usando API directa de Vaadin."""
    
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        self.sync_id = 1
        self.ui_id = 0
        self.base_url = config.DUSA_URL
        self.campo_busqueda_id = None
        
    def login_y_obtener_sesion(self):
        """
        Usa Selenium SOLO para el login inicial.
        Luego extrae las cookies y tokens para usar requests directos.
        """
        print("🔐 Iniciando sesión en DUSA...")
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        try:
            # Login
            driver.get(self.base_url)
            time.sleep(3)
            
            # Completar formulario
            campos = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
            if campos:
                campos[0].send_keys(config.DUSA_USUARIO)
            
            campo_pass = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            campo_pass.send_keys(config.DUSA_PASSWORD)
            
            for campo in campos[1:]:
                if campo.get_attribute('type') == 'text':
                    campo.send_keys(config.DUSA_CLIENTE)
                    break
            
            time.sleep(1)
            
            # Clic en entrar
            boton = driver.find_element(By.CSS_SELECTOR, ".v-button, button")
            boton.click()
            
            time.sleep(5)
            
            # Ir a productos
            driver.get(self.base_url + "#!micuenta/productos")
            time.sleep(3)
            
            # Extraer cookies
            cookies = driver.get_cookies()
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
            
            # Extraer CSRF token de los network logs
            logs = driver.get_log('performance')
            for log in logs:
                try:
                    msg = json.loads(log['message'])['message']
                    if msg['method'] == 'Network.requestWillBeSent':
                        post_data = msg['params']['request'].get('postData', '')
                        if 'csrfToken' in post_data:
                            match = re.search(r'"csrfToken":"([^"]+)"', post_data)
                            if match:
                                self.csrf_token = match.group(1)
                except:
                    pass
            
            # También buscar el ID del campo de búsqueda
            # Esto lo sacamos del último request que contenga "text"
            for log in reversed(logs):
                try:
                    msg = json.loads(log['message'])['message']
                    if msg['method'] == 'Network.requestWillBeSent':
                        post_data = msg['params']['request'].get('postData', '')
                        if '"syncId"' in post_data and '"text"' in post_data:
                            data = json.loads(post_data)
                            self.sync_id = data.get('syncId', 1) + 1
                            # Extraer ID del campo de búsqueda
                            for rpc in data.get('rpc', []):
                                if len(rpc) >= 3 and rpc[2] == 'v' and '"text"' in str(rpc):
                                    self.campo_busqueda_id = rpc[0]
                                    break
                except:
                    pass
            
            print(f"✅ Login exitoso")
            print(f"   CSRF Token: {self.csrf_token[:20]}...")
            print(f"   Cookies: {len(self.session.cookies)} guardadas")
            
            return True
            
        finally:
            driver.quit()
    
    def buscar_producto(self, codigo):
        """
        Busca un producto usando HTTP request directo (sin Selenium).
        """
        if not self.csrf_token:
            raise Exception("No hay sesión activa. Ejecutá login_y_obtener_sesion() primero.")
        
        url = f"{self.base_url}/UIDL/?v-uiId={self.ui_id}"
        
        # El payload RPC de Vaadin para buscar
        # Necesitamos simular: escribir texto + presionar Enter
        payload = {
            "csrfToken": self.csrf_token,
            "rpc": [
                # Escribir el código en el campo de búsqueda
                [str(self.campo_busqueda_id or "89"), "v", "v", ["text", ["s", codigo]]],
                [str(self.campo_busqueda_id or "89"), "v", "v", ["c", ["i", "13"]]],  # cursor position
                # Trigger action (Enter)
                ["0", "v", "v", ["actiontarget", ["c", str(self.campo_busqueda_id or "89")]]],
                ["0", "v", "v", ["action", ["s", "24"]]]  # 24 es el código de Enter
            ],
            "syncId": self.sync_id
        }
        
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Referer": self.base_url,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=10)
            self.sync_id += 1
            
            if response.status_code == 200:
                return self.parsear_respuesta(response.text, codigo)
            else:
                return {
                    'codigo': codigo,
                    'estado': 'error',
                    'mensaje': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'codigo': codigo,
                'estado': 'error',
                'mensaje': str(e)
            }
    
    def parsear_respuesta(self, html_response, codigo):
        """
        Parsea la respuesta UIDL de Vaadin para extraer datos del producto.
        """
        try:
            # La respuesta de Vaadin es JSON (a veces con prefijo de seguridad)
            text = html_response
            if text.startswith('for(;;);'):
                text = text[8:]  # Quitar prefijo anti-hijacking
            
            data = json.loads(text)
            
            # Buscar información del producto en la respuesta
            # Esto puede variar según cómo DUSA estructura sus respuestas
            
            resultado = {
                'codigo': codigo,
                'estado': 'no_encontrado',
                'nombre': '',
                'stock': '-',
                'precio': '-'
            }
            
            # Buscar en los cambios de estado
            if 'state' in data:
                state_str = json.dumps(data['state'])
                
                # Buscar patrones de "agotado" o "disponible"
                if 'agotado' in state_str.lower() or 'sin stock' in state_str.lower():
                    resultado['estado'] = 'agotado'
                elif 'disponible' in state_str.lower() or 'en stock' in state_str.lower():
                    resultado['estado'] = 'disponible'
                
                # Intentar extraer nombre/precio
                # Esto es muy específico de DUSA, puede necesitar ajustes
                
            return resultado
            
        except json.JSONDecodeError:
            # Si no es JSON válido, puede contener HTML con los datos
            if 'agotado' in html_response.lower():
                return {'codigo': codigo, 'estado': 'agotado', 'nombre': '', 'stock': '0', 'precio': '-'}
            elif 'no encontrado' in html_response.lower():
                return {'codigo': codigo, 'estado': 'no_encontrado', 'nombre': '', 'stock': '-', 'precio': '-'}
            else:
                return {'codigo': codigo, 'estado': 'encontrado', 'nombre': '(ver detalles)', 'stock': '-', 'precio': '-'}


def main():
    """Prueba del verificador rápido."""
    print("🚀 Verificador DUSA - Versión API Directa")
    print("=" * 50)
    
    verificador = VerificadorDUSARapido()
    
    # Login (esto sí usa Chrome, pero una sola vez)
    if not verificador.login_y_obtener_sesion():
        print("❌ Error en login")
        return
    
    # Probar búsqueda directa (sin Chrome)
    print("\n🔍 Probando búsqueda directa (sin Selenium)...")
    
    codigos_prueba = [
        "7891010604141",
        "7896015519254",
        "123456789"
    ]
    
    for codigo in codigos_prueba:
        print(f"\n  Buscando: {codigo}")
        resultado = verificador.buscar_producto(codigo)
        print(f"  Resultado: {resultado}")
        time.sleep(0.5)  # Pausa mínima
    
    print("\n✅ Prueba completada")
    print("   Si esto funciona, podemos verificar CIENTOS de productos")
    print("   en segundos, sin abrir múltiples ventanas de Chrome!")


if __name__ == "__main__":
    main()
