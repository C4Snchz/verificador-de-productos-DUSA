#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para inspeccionar la página de DUSA.
Abre el navegador y te permite ver la estructura de la página.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

print("🌐 Abriendo navegador...")

# Configurar Chrome
opciones = Options()
opciones.add_argument("--no-sandbox")
opciones.add_argument("--disable-dev-shm-usage")
opciones.add_argument("--window-size=1400,900")

# Crear driver
servicio = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=servicio, options=opciones)

try:
    # Ir a DUSA
    print("📍 Navegando a DUSA...")
    driver.get("https://pedidos.dusa.com.uy/DUSAWebUI")
    
    print("\n" + "="*60)
    print("🔍 INSTRUCCIONES:")
    print("="*60)
    print("""
1. El navegador está abierto en la página de DUSA
2. Presiona F12 para abrir las herramientas de desarrollador
3. Usa el inspector (ícono de flecha) para ver los elementos

NECESITO QUE ME DIGAS:

Para el LOGIN:
- ¿Cómo es el campo de usuario? (id, name, placeholder)
- ¿Cómo es el campo de contraseña? (id, name)  
- ¿Cómo es el botón de login? (texto, id, clase)

Cuando estés listo, ingresa manualmente tu usuario y contraseña
para ver la página de productos.

Para el BUSCADOR (después de login):
- ¿Hay un campo de búsqueda? ¿Cómo se identifica?
- ¿Cómo se muestran los productos?

El navegador se cerrará cuando presiones ENTER aquí.
""")
    print("="*60)
    
    # Esperar a que el usuario inspeccione
    input("\n>>> Presiona ENTER cuando hayas terminado de inspeccionar...")
    
except Exception as e:
    print(f"❌ Error: {e}")

finally:
    driver.quit()
    print("🔒 Navegador cerrado")
