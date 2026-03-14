#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador DUSA - Versión Interactiva
======================================
Fácil de usar desde terminal.
"""

import pandas as pd
import time
import os
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configuración por defecto
USUARIO = "farmacia.farma"
PASSWORD = "Parlantes28"
CLIENTE = "2287"
DUSA_URL = "https://pedidos.dusa.com.uy/DUSAWebUI"


def limpiar_pantalla():
    os.system('clear' if os.name != 'nt' else 'cls')


def mostrar_banner():
    print("\n" + "="*60)
    print("   🏥 VERIFICADOR DE DISPONIBILIDAD DUSA")
    print("   Farmacia Farmauy - Mercado Libre")
    print("="*60)


def seleccionar_archivo():
    """Permite al usuario seleccionar un archivo."""
    print("\n📁 SELECCIÓN DE ARCHIVO EXCEL")
    print("-"*40)
    
    # Buscar archivos recientes en Downloads
    downloads = os.path.expanduser("~/Downloads")
    archivos_excel = []
    
    if os.path.exists(downloads):
        for f in os.listdir(downloads):
            if f.endswith(('.xlsx', '.xls')) and 'publicacion' in f.lower():
                archivos_excel.append(os.path.join(downloads, f))
    
    # Ordenar por fecha de modificación
    archivos_excel.sort(key=os.path.getmtime, reverse=True)
    
    if archivos_excel:
        print("\n📋 Archivos de Mercado Libre encontrados en Descargas:")
        for i, archivo in enumerate(archivos_excel[:5], 1):
            nombre = os.path.basename(archivo)
            fecha = datetime.fromtimestamp(os.path.getmtime(archivo)).strftime("%d/%m %H:%M")
            print(f"   {i}. {nombre} ({fecha})")
        
        print(f"\n   0. Otro archivo (ingresar ruta)")
        
        while True:
            opcion = input("\n👉 Selecciona opción (1-5 o 0): ").strip()
            
            if opcion == '0':
                ruta = input("   Ingresa la ruta completa del archivo: ").strip()
                if os.path.exists(ruta):
                    return ruta
                print("   ❌ Archivo no encontrado")
            elif opcion.isdigit() and 1 <= int(opcion) <= len(archivos_excel):
                return archivos_excel[int(opcion)-1]
            else:
                print("   ⚠️ Opción inválida")
    else:
        ruta = input("Ingresa la ruta del archivo Excel: ").strip()
        if os.path.exists(ruta):
            return ruta
        print("❌ Archivo no encontrado")
        return None


def leer_excel(ruta):
    """Lee el Excel de Mercado Libre."""
    print(f"\n📖 Leyendo archivo...")
    
    try:
        xl = pd.ExcelFile(ruta)
        
        if 'Publicaciones' in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name='Publicaciones', skiprows=2)
        else:
            df = pd.read_excel(xl)
        
        # Normalizar nombres de columnas
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if 'sku' in col_lower:
                col_map[col] = 'SKU'
            elif 'título' in col_lower or 'titulo' in col_lower:
                col_map[col] = 'Título'
            elif 'precio' == col_lower:
                col_map[col] = 'Precio'
            elif 'stock' in col_lower:
                col_map[col] = 'Stock'
            elif 'estado' in col_lower:
                col_map[col] = 'Estado'
        
        df = df.rename(columns=col_map)
        
        # Filtrar filas válidas
        if 'SKU' in df.columns and 'Título' in df.columns:
            df = df[
                (df['SKU'].notna() & (df['SKU'].astype(str) != 'nan')) |
                (df['Título'].notna() & (df['Título'].astype(str) != 'nan'))
            ].copy()
        
        # Filtrar instrucciones
        if 'Stock' in df.columns:
            df = df[~df['Stock'].astype(str).str.contains('Obligatorio|Opcional', case=False, na=False)]
        
        print(f"   ✅ {len(df)} productos encontrados")
        return df
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def iniciar_navegador():
    """Inicia Chrome."""
    print("\n🌐 Iniciando navegador Chrome...")
    
    opciones = Options()
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1200,800")
    
    servicio = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servicio, options=opciones)
    
    print("   ✅ Navegador listo")
    return driver


def login(driver):
    """Inicia sesión en DUSA."""
    print("\n🔐 Iniciando sesión en DUSA...")
    
    driver.get(DUSA_URL)
    time.sleep(4)
    
    # Llenar formulario
    campos_texto = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
    campos_pass = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    
    if campos_texto:
        campos_texto[0].send_keys(USUARIO)
    if campos_pass:
        campos_pass[0].send_keys(PASSWORD)
    if len(campos_texto) >= 2:
        campos_texto[-1].send_keys(CLIENTE)
    
    time.sleep(1)
    
    # Clic en Entrar
    botones = driver.find_elements(By.CSS_SELECTOR, ".v-button, button")
    for btn in botones:
        if "Entrar" in btn.text:
            btn.click()
            break
    
    time.sleep(5)
    
    # Verificar
    try:
        driver.find_element(By.CSS_SELECTOR, "#loginf")
        print("   ❌ Error de login - verificar credenciales")
        return False
    except NoSuchElementException:
        print("   ✅ Login exitoso")
        return True


def ir_a_productos(driver):
    """Navega a productos."""
    print("\n📦 Navegando a catálogo de productos...")
    driver.get(DUSA_URL + "#!micuenta/productos")
    time.sleep(3)


def extraer_palabras_clave(titulo):
    """Extrae palabras clave de título."""
    if not titulo or titulo == "nan":
        return ""
    
    ignorar = ['farmauy', 'farmacia', 'original', 'sellado', 'envio', 'gratis',
               'pack', 'combo', 'oferta', 'promo', 'uruguay', 'importado', 'nuevo']
    
    palabras = str(titulo).split()[:5]
    filtradas = [p for p in palabras if p.lower() not in ignorar and len(p) > 2]
    
    return " ".join(filtradas[:3])


def buscar_producto(driver, sku, titulo):
    """Busca un producto."""
    resultado = {
        'busqueda': '',
        'encontrado': False,
        'disponible': None,
        'precio': None,
        'nombre': None,
        'oferta': None,
        'laboratorio': None,
        'mensaje': ''
    }
    
    # Intentar con SKU
    termino = None
    if sku and str(sku) != 'nan':
        termino = str(sku)
        resultado['busqueda'] = f"SKU: {sku}"
    else:
        termino = extraer_palabras_clave(titulo)
        resultado['busqueda'] = termino
    
    if not termino:
        resultado['mensaje'] = "Sin término"
        return resultado
    
    try:
        # Campo de búsqueda
        campo = driver.find_element(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        campo.clear()
        time.sleep(0.3)
        campo.send_keys(termino)
        
        # Buscar
        try:
            boton = driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]/..")
            boton.click()
        except:
            campo.send_keys(Keys.RETURN)
        
        time.sleep(2.5)
        
        # Analizar resultados
        filas = driver.find_elements(By.CSS_SELECTOR, "table tr")
        filas_datos = [f for f in filas if f.text.strip() and "Stock" not in f.text and "Descripción" not in f.text]
        
        if filas_datos:
            primera = filas_datos[0]
            texto = primera.text.lower()
            
            resultado['encontrado'] = True
            resultado['disponible'] = "faltante" not in texto
            resultado['mensaje'] = "Faltante" if not resultado['disponible'] else "OK"
            
            celdas = primera.find_elements(By.CSS_SELECTOR, "td")
            if len(celdas) >= 5:
                resultado['nombre'] = celdas[1].text.split('\n')[0][:40]
                resultado['laboratorio'] = celdas[2].text.strip()[:20]
                resultado['oferta'] = celdas[3].text.strip()
                resultado['precio'] = celdas[4].text.strip()
        else:
            resultado['mensaje'] = "No encontrado"
        
        return resultado
        
    except Exception as e:
        resultado['mensaje'] = f"Error"
        return resultado


def mostrar_progreso(actual, total, resultado):
    """Muestra barra de progreso."""
    porcentaje = int((actual / total) * 100)
    barra = "█" * (porcentaje // 5) + "░" * (20 - porcentaje // 5)
    
    if resultado['encontrado']:
        if resultado['disponible']:
            estado = "✅"
        else:
            estado = "❌"
    else:
        estado = "⚠️"
    
    print(f"\r[{barra}] {porcentaje}% ({actual}/{total}) {estado} ", end="", flush=True)


def generar_resultado(resultados, ruta_original):
    """Genera Excel de resultados."""
    print("\n\n📝 Generando archivo de resultados...")
    
    df = pd.DataFrame(resultados)
    
    # Ordenar y renombrar columnas
    columnas_orden = ['sku', 'titulo', 'estado_ml', 'encontrado', 'disponible', 
                      'nombre', 'precio', 'oferta', 'laboratorio', 'precio_ml', 'stock_ml', 'mensaje']
    columnas = [c for c in columnas_orden if c in df.columns]
    df = df[columnas]
    
    nombres = {
        'sku': 'SKU',
        'titulo': 'Título ML',
        'estado_ml': 'Estado ML',
        'encontrado': 'Encontrado',
        'disponible': 'Disponible',
        'nombre': 'Producto DUSA',
        'precio': 'Precio DUSA',
        'oferta': 'Oferta',
        'laboratorio': 'Laboratorio',
        'precio_ml': 'Precio ML',
        'stock_ml': 'Stock ML',
        'mensaje': 'Notas'
    }
    df = df.rename(columns=nombres)
    
    # Guardar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    carpeta = os.path.dirname(ruta_original)
    nombre_salida = f"DUSA_verificacion_{timestamp}.xlsx"
    ruta_salida = os.path.join(carpeta, nombre_salida)
    
    df.to_excel(ruta_salida, index=False)
    
    return ruta_salida, df


def mostrar_resumen(df, ruta):
    """Muestra resumen final."""
    total = len(df)
    encontrados = df['Encontrado'].sum() if 'Encontrado' in df.columns else 0
    disponibles = df['Disponible'].sum() if 'Disponible' in df.columns else 0
    faltantes = encontrados - disponibles
    no_encontrados = total - encontrados
    
    print("\n" + "="*60)
    print("   📊 RESUMEN DE VERIFICACIÓN")
    print("="*60)
    print(f"""
   Total productos:     {total}
   ────────────────────────────
   ✅ Disponibles:       {disponibles}
   ❌ Faltantes:         {faltantes}
   ⚠️  No encontrados:    {no_encontrados}
   ────────────────────────────
   
   📁 Archivo generado:
   {ruta}
""")


def main():
    limpiar_pantalla()
    mostrar_banner()
    
    # 1. Seleccionar archivo
    ruta_excel = seleccionar_archivo()
    if not ruta_excel:
        print("\n❌ No se seleccionó archivo. Saliendo...")
        return
    
    # 2. Leer Excel
    df = leer_excel(ruta_excel)
    if df is None or len(df) == 0:
        print("\n❌ No se encontraron productos. Saliendo...")
        return
    
    # Confirmar
    print(f"\n📋 Se verificarán {len(df)} productos en DUSA")
    confirmar = input("   ¿Continuar? (Enter=Sí, n=No): ").strip().lower()
    if confirmar == 'n':
        print("   Cancelado.")
        return
    
    # 3. Iniciar navegador
    try:
        driver = iniciar_navegador()
    except Exception as e:
        print(f"\n❌ Error iniciando navegador: {e}")
        return
    
    try:
        # 4. Login
        if not login(driver):
            driver.quit()
            return
        
        # 5. Ir a productos
        ir_a_productos(driver)
        
        # 6. Procesar productos
        print("\n🔍 VERIFICANDO PRODUCTOS...")
        print("-"*60)
        
        resultados = []
        total = len(df)
        
        for idx, (_, row) in enumerate(df.iterrows(), 1):
            sku = row.get('SKU', '')
            titulo = row.get('Título', '')
            
            if (not sku or str(sku) == 'nan') and (not titulo or str(titulo) == 'nan'):
                continue
            
            resultado = buscar_producto(driver, sku, titulo)
            
            # Agregar datos de ML
            resultado['sku'] = sku
            resultado['titulo'] = str(titulo)[:50] if titulo else ''
            resultado['precio_ml'] = row.get('Precio', '')
            resultado['stock_ml'] = row.get('Stock', '')
            resultado['estado_ml'] = row.get('Estado', '')
            
            resultados.append(resultado)
            mostrar_progreso(idx, total, resultado)
            
            time.sleep(1.5)
        
        # 7. Generar resultado
        ruta_resultado, df_resultado = generar_resultado(resultados, ruta_excel)
        
        # 8. Mostrar resumen
        mostrar_resumen(df_resultado, ruta_resultado)
        
        # 9. Abrir archivo
        abrir = input("   ¿Abrir archivo de resultados? (Enter=Sí): ").strip().lower()
        if abrir != 'n':
            os.system(f'open "{ruta_resultado}"')
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
    finally:
        print("\n🔒 Cerrando navegador...")
        driver.quit()
        print("\n✅ Finalizado")


if __name__ == "__main__":
    main()
