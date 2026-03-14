#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rápido - Verifica solo 5 productos para probar que todo funciona.
"""

import pandas as pd
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import config

PRODUCTOS_A_PROBAR = 5  # Cambiar para probar más o menos

print("="*60)
print("🧪 TEST RÁPIDO - VERIFICADOR DUSA")
print("="*60)

# Leer Excel
print(f"\n📖 Leyendo Excel...")
df = pd.read_excel(
    config.EXCEL_ENTRADA,
    sheet_name=config.HOJA_EXCEL,
    skiprows=config.FILAS_SALTAR
)

# Filtrar
df_filtrado = df[
    (df[config.COLUMNA_SKU].notna() & (df[config.COLUMNA_SKU].astype(str) != 'nan')) |
    (df[config.COLUMNA_TITULO].notna() & (df[config.COLUMNA_TITULO].astype(str) != 'nan'))
].copy()

df_filtrado = df_filtrado[
    ~df_filtrado[config.COLUMNA_STOCK].astype(str).str.contains('Obligatorio|Opcional', case=False, na=False)
]

print(f"   Total productos en Excel: {len(df_filtrado)}")
print(f"   Probando con los primeros {PRODUCTOS_A_PROBAR}")

# Iniciar navegador
print(f"\n🌐 Iniciando navegador...")
opciones = Options()
opciones.add_argument("--no-sandbox")
opciones.add_argument("--window-size=1400,900")

servicio = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=servicio, options=opciones)

try:
    # Login
    print(f"\n🔐 Iniciando sesión...")
    driver.get(config.DUSA_URL)
    time.sleep(4)
    
    # Llenar campos de login
    campos_texto = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
    campos_pass = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    
    if campos_texto:
        campos_texto[0].send_keys(config.DUSA_USUARIO)
    if campos_pass:
        campos_pass[0].send_keys(config.DUSA_PASSWORD)
    if len(campos_texto) >= 2:
        campos_texto[-1].send_keys(config.DUSA_CLIENTE)
    
    time.sleep(1)
    
    # Clic en Entrar
    botones = driver.find_elements(By.CSS_SELECTOR, ".v-button, button")
    for btn in botones:
        if "Entrar" in btn.text:
            btn.click()
            break
    
    time.sleep(5)
    print("✅ Login completado")
    
    # Ir a productos
    print("\n📦 Navegando a Ver Productos...")
    driver.get(config.DUSA_URL + "#!micuenta/productos")
    time.sleep(3)
    
    # Probar búsquedas
    print("\n" + "="*60)
    print("🔍 PROBANDO BÚSQUEDAS")
    print("="*60)
    
    resultados = []
    
    for i in range(min(PRODUCTOS_A_PROBAR, len(df_filtrado))):
        row = df_filtrado.iloc[i]
        sku = str(row.get(config.COLUMNA_SKU, "")).strip()
        titulo = str(row.get(config.COLUMNA_TITULO, "")).strip()
        
        print(f"\n[{i+1}/{PRODUCTOS_A_PROBAR}] SKU: {sku}")
        print(f"    Título ML: {titulo[:50]}...")
        
        # Extraer palabras clave del título
        palabras = titulo.split()[:3]
        palabras_clave = " ".join([p for p in palabras if len(p) > 2])[:30]
        
        # Buscar
        termino = sku if sku and sku != "nan" else palabras_clave
        print(f"    Buscando: {termino}")
        
        try:
            # Encontrar campo de búsqueda
            campo = driver.find_element(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
            campo.clear()
            time.sleep(0.5)
            campo.send_keys(termino)
            
            # Buscar botón
            try:
                boton = driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]/..")
                boton.click()
            except:
                campo.send_keys(Keys.RETURN)
            
            time.sleep(3)
            
            # Analizar resultados
            filas = driver.find_elements(By.CSS_SELECTOR, "table tr")
            filas_datos = [f for f in filas if f.text.strip() and "Stock" not in f.text and "Descripción" not in f.text]
            
            if filas_datos:
                primera = filas_datos[0]
                texto = primera.text
                
                # Detectar disponibilidad
                if "faltante" in texto.lower():
                    print(f"    ❌ FALTANTE en laboratorio")
                    disponible = False
                else:
                    print(f"    ✅ DISPONIBLE")
                    disponible = True
                
                # Extraer precio
                celdas = primera.find_elements(By.CSS_SELECTOR, "td")
                if len(celdas) >= 5:
                    nombre = celdas[1].text.split('\n')[0]
                    precio = celdas[4].text
                    oferta = celdas[3].text
                    print(f"    Nombre DUSA: {nombre[:40]}")
                    print(f"    Precio: ${precio} | Oferta: {oferta}")
                
                resultados.append({"sku": sku, "encontrado": True, "disponible": disponible})
            else:
                print(f"    ⚠️  No encontrado")
                resultados.append({"sku": sku, "encontrado": False, "disponible": None})
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            resultados.append({"sku": sku, "encontrado": False, "disponible": None})
        
        time.sleep(2)
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DEL TEST")
    print("="*60)
    encontrados = sum(1 for r in resultados if r["encontrado"])
    disponibles = sum(1 for r in resultados if r["disponible"])
    print(f"Productos probados: {len(resultados)}")
    print(f"Encontrados: {encontrados}")
    print(f"Disponibles: {disponibles}")
    print(f"Faltantes: {encontrados - disponibles}")
    print(f"No encontrados: {len(resultados) - encontrados}")
    
    input("\n>>> Presiona ENTER para cerrar el navegador...")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    input("\n>>> Presiona ENTER para cerrar...")

finally:
    driver.quit()
    print("🔒 Navegador cerrado")
