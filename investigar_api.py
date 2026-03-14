#!/usr/bin/env python3
"""
Script para investigar las llamadas de red de DUSA
Ejecuta esto y compartí el archivo 'dusa_network_log.json' que genera
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Importar config
try:
    import config
    USUARIO = config.DUSA_USUARIO
    PASSWORD = config.DUSA_PASSWORD
    CLIENTE = config.DUSA_CLIENTE
    URL = config.DUSA_URL
except:
    USUARIO = input("Usuario DUSA: ")
    PASSWORD = input("Contraseña DUSA: ")
    CLIENTE = input("Código cliente: ")
    URL = "https://pedidos.dusa.com.uy/DUSAWebUI"

def main():
    print("🔍 Investigando API de DUSA...")
    print("=" * 50)
    
    # Configurar Chrome para capturar network logs
    options = Options()
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    options.add_argument("--window-size=1920,1080")
    
    # Iniciar Chrome
    print("🌐 Iniciando Chrome...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    network_logs = []
    
    try:
        # 1. Ir a DUSA
        print(f"📍 Navegando a {URL}...")
        driver.get(URL)
        time.sleep(4)
        
        # 2. Login
        print("🔐 Haciendo login...")
        campos = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        if campos:
            campos[0].send_keys(USUARIO)
        
        campo_pass = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        campo_pass.send_keys(PASSWORD)
        
        # Cliente
        for campo in campos[1:]:
            if campo.get_attribute('type') == 'text':
                campo.send_keys(CLIENTE)
                break
        
        time.sleep(1)
        
        # Clic en entrar
        boton = driver.find_element(By.CSS_SELECTOR, ".v-button, button")
        boton.click()
        
        print("⏳ Esperando login...")
        time.sleep(6)
        
        # Capturar logs hasta ahora
        logs = driver.get_log('performance')
        for log in logs:
            try:
                msg = json.loads(log['message'])['message']
                if msg['method'] == 'Network.requestWillBeSent':
                    req = msg['params']['request']
                    network_logs.append({
                        'type': 'request',
                        'url': req['url'],
                        'method': req['method'],
                        'headers': req.get('headers', {}),
                        'postData': req.get('postData', '')
                    })
                elif msg['method'] == 'Network.responseReceived':
                    resp = msg['params']['response']
                    network_logs.append({
                        'type': 'response',
                        'url': resp['url'],
                        'status': resp['status'],
                        'mimeType': resp.get('mimeType', '')
                    })
            except:
                pass
        
        # 3. Ir a productos
        print("📦 Navegando a productos...")
        driver.get(URL + "#!micuenta/productos")
        time.sleep(4)
        
        # 4. Buscar un producto de prueba
        print("🔎 Buscando un producto de prueba...")
        
        # Buscar campo de búsqueda
        campos_busqueda = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        
        if campos_busqueda:
            campo = campos_busqueda[0]
            campo.clear()
            campo.send_keys("7891010604141")  # Un código de barras de ejemplo
            campo.send_keys(Keys.ENTER)
            print("   Buscando código: 7891010604141")
        
        time.sleep(5)
        
        # Capturar más logs
        logs = driver.get_log('performance')
        for log in logs:
            try:
                msg = json.loads(log['message'])['message']
                if msg['method'] == 'Network.requestWillBeSent':
                    req = msg['params']['request']
                    network_logs.append({
                        'type': 'request',
                        'url': req['url'],
                        'method': req['method'],
                        'headers': req.get('headers', {}),
                        'postData': req.get('postData', '')
                    })
                elif msg['method'] == 'Network.responseReceived':
                    resp = msg['params']['response']
                    network_logs.append({
                        'type': 'response', 
                        'url': resp['url'],
                        'status': resp['status'],
                        'mimeType': resp.get('mimeType', '')
                    })
            except:
                pass
        
        print(f"\n✅ Capturados {len(network_logs)} eventos de red")
        
    finally:
        driver.quit()
    
    # Filtrar solo las llamadas interesantes
    interesantes = []
    for log in network_logs:
        url = log.get('url', '')
        # Ignorar recursos estáticos
        if any(ext in url for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.woff', '.ico']):
            continue
        # Ignorar CDNs y analytics
        if any(domain in url for domain in ['google', 'facebook', 'analytics', 'cdn']):
            continue
        interesantes.append(log)
    
    # Guardar logs
    output_file = 'dusa_network_log.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(interesantes, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Logs guardados en: {output_file}")
    print(f"   Total eventos interesantes: {len(interesantes)}")
    
    # Mostrar resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE LLAMADAS:")
    print("=" * 50)
    
    requests_unicos = set()
    for log in interesantes:
        if log['type'] == 'request':
            key = f"{log['method']} {log['url'][:80]}"
            if key not in requests_unicos:
                requests_unicos.add(key)
                print(f"  {log['method']:6} {log['url'][:70]}...")
                if log.get('postData'):
                    print(f"         POST data: {log['postData'][:100]}...")
    
    print("\n" + "=" * 50)
    print("🎯 BUSCA LLAMADAS QUE CONTENGAN:")
    print("   - 'producto', 'articulo', 'buscar', 'search'")
    print("   - 'UIDL' (protocolo Vaadin)")
    print("   - '/api/' o '/rest/'")
    print("=" * 50)
    print(f"\n💡 Compartí el archivo '{output_file}' para que lo analice")

if __name__ == "__main__":
    main()
