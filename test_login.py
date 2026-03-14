#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar el login en DUSA.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import config

print("="*60)
print("🧪 TEST DE LOGIN EN DUSA")
print("="*60)
print(f"Usuario: {config.DUSA_USUARIO}")
print(f"Cliente: {config.DUSA_CLIENTE}")
print(f"URL: {config.DUSA_URL}")
print("="*60)

# Verificar credenciales
if config.DUSA_USUARIO == "tu_usuario_aqui":
    print("\n❌ ERROR: Debes configurar tus credenciales en config.py")
    print("   Edita DUSA_USUARIO y DUSA_PASSWORD con tus datos reales")
    exit(1)

print("\n🌐 Iniciando navegador...")

# Configurar Chrome
opciones = Options()
opciones.add_argument("--no-sandbox")
opciones.add_argument("--disable-dev-shm-usage")
opciones.add_argument("--window-size=1400,900")

servicio = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=servicio, options=opciones)

try:
    print("📍 Navegando a DUSA...")
    driver.get(config.DUSA_URL)
    time.sleep(4)
    
    print("\n🔍 Buscando elementos del formulario...")
    
    # Mostrar qué inputs encuentra
    inputs = driver.find_elements(By.CSS_SELECTOR, "input")
    print(f"   Total inputs encontrados: {len(inputs)}")
    
    for i, inp in enumerate(inputs):
        tipo = inp.get_attribute('type')
        clase = inp.get_attribute('class')
        id_elem = inp.get_attribute('id')
        print(f"   Input {i}: type={tipo}, class={clase[:40] if clase else 'N/A'}..., id={id_elem}")
    
    # Buscar campos de texto tipo Vaadin
    campos_texto = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
    print(f"\n   Campos de texto: {len(campos_texto)}")
    
    # Buscar campo password
    campos_pass = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    print(f"   Campos password: {len(campos_pass)}")
    
    # Buscar botones
    botones = driver.find_elements(By.CSS_SELECTOR, ".v-button, button, div.v-button")
    print(f"   Botones: {len(botones)}")
    for i, btn in enumerate(botones):
        texto = btn.text
        print(f"      Botón {i}: '{texto}'")
    
    print("\n" + "="*60)
    print("🔐 INTENTANDO LOGIN...")
    print("="*60)
    
    # Ingresar usuario
    if len(campos_texto) >= 1:
        campos_texto[0].clear()
        campos_texto[0].send_keys(config.DUSA_USUARIO)
        print("✓ Usuario ingresado")
    
    # Ingresar contraseña
    if len(campos_pass) >= 1:
        campos_pass[0].clear()
        campos_pass[0].send_keys(config.DUSA_PASSWORD)
        print("✓ Contraseña ingresada")
    
    # Ingresar cliente (buscar el segundo campo de texto después del password)
    campos_texto_todos = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
    if len(campos_texto_todos) >= 2:
        # El campo de cliente suele ser el último campo de texto
        campo_cliente = campos_texto_todos[-1]  # Último campo
        campo_cliente.clear()
        campo_cliente.send_keys(config.DUSA_CLIENTE)
        print("✓ Cliente ingresado")
    
    time.sleep(1)
    
    # Buscar y hacer clic en el botón
    if len(botones) >= 1:
        for btn in botones:
            if "Entrar" in btn.text or btn.text.strip():
                print(f"✓ Haciendo clic en botón: '{btn.text}'")
                btn.click()
                break
    
    print("\n⏳ Esperando respuesta del servidor...")
    time.sleep(6)
    
    # Verificar resultado
    print("\n" + "="*60)
    print("📊 RESULTADO")
    print("="*60)
    
    # Ver la URL actual
    print(f"URL actual: {driver.current_url}")
    
    # Buscar si hay mensajes de error
    errores = driver.find_elements(By.CSS_SELECTOR, ".v-errorindicator, .error, .v-label-error")
    if errores:
        print("⚠️  Se encontraron indicadores de error")
    
    # Buscar si hay algún elemento que indique login exitoso
    try:
        driver.find_element(By.CSS_SELECTOR, "#loginf")
        print("❌ El formulario de login sigue visible - login fallido")
    except NoSuchElementException:
        print("✅ Formulario de login ya no está - login exitoso!")
    
    print("\n📸 El navegador sigue abierto para que puedas verificar")
    print("   Mira si estás dentro del sistema o si hay algún error")
    input("\n>>> Presiona ENTER para cerrar y continuar...")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    input("\n>>> Presiona ENTER para cerrar...")

finally:
    driver.quit()
    print("🔒 Navegador cerrado")
