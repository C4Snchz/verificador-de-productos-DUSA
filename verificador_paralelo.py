#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador DUSA - Versión Paralela
===================================
Ejecuta múltiples ventanas de Chrome en paralelo para acelerar la verificación.
Incluye barra de progreso con tiempo estimado restante.
"""

import pandas as pd
import time
import os
import sys
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Configuración
USUARIO = "farmacia.farma"
PASSWORD = "Parlantes28"
CLIENTE = "2287"
DUSA_URL = "https://pedidos.dusa.com.uy/DUSAWebUI"

# Variables globales para progreso
progreso_lock = threading.Lock()
productos_procesados = 0
total_productos = 0
tiempo_inicio = None
tiempos_por_producto = []  # Para calcular promedio


class BarraProgreso:
    """Barra de progreso con tiempo estimado."""
    
    def __init__(self, total, ancho=50):
        self.total = total
        self.ancho = ancho
        self.actual = 0
        self.tiempo_inicio = time.time()
        self.tiempos = []
        self.ultimo_tiempo = self.tiempo_inicio
        
    def actualizar(self, completados=1):
        """Actualiza la barra de progreso."""
        ahora = time.time()
        
        # Registrar tiempo de este producto
        tiempo_producto = ahora - self.ultimo_tiempo
        self.tiempos.append(tiempo_producto)
        self.ultimo_tiempo = ahora
        
        # Mantener solo los últimos 20 tiempos para el promedio
        if len(self.tiempos) > 20:
            self.tiempos = self.tiempos[-20:]
        
        self.actual += completados
        
        # Calcular porcentaje y barra
        porcentaje = self.actual / self.total
        lleno = int(self.ancho * porcentaje)
        barra = "█" * lleno + "░" * (self.ancho - lleno)
        
        # Calcular tiempo restante
        tiempo_transcurrido = ahora - self.tiempo_inicio
        tiempo_restante = self._calcular_tiempo_restante()
        
        # Formatear tiempos
        transcurrido_str = self._formatear_tiempo(tiempo_transcurrido)
        restante_str = self._formatear_tiempo(tiempo_restante)
        
        # Velocidad (productos por minuto)
        if tiempo_transcurrido > 0:
            velocidad = (self.actual / tiempo_transcurrido) * 60
        else:
            velocidad = 0
        
        # Imprimir
        sys.stdout.write(f"\r⏳ [{barra}] {self.actual}/{self.total} ({porcentaje*100:.1f}%) | "
                        f"⏱️ {transcurrido_str} | 🏁 ~{restante_str} | 🚀 {velocidad:.1f}/min")
        sys.stdout.flush()
        
    def _calcular_tiempo_restante(self):
        """Calcula tiempo restante basado en promedio de últimos productos."""
        if not self.tiempos:
            return 0
        
        promedio_por_producto = sum(self.tiempos) / len(self.tiempos)
        productos_restantes = self.total - self.actual
        
        return promedio_por_producto * productos_restantes
    
    def _formatear_tiempo(self, segundos):
        """Formatea segundos a mm:ss o hh:mm:ss."""
        if segundos < 0:
            return "calculando..."
        
        segundos = int(segundos)
        if segundos < 3600:
            minutos = segundos // 60
            segs = segundos % 60
            return f"{minutos:02d}:{segs:02d}"
        else:
            horas = segundos // 3600
            minutos = (segundos % 3600) // 60
            segs = segundos % 60
            return f"{horas}:{minutos:02d}:{segs:02d}"
    
    def finalizar(self):
        """Muestra mensaje final."""
        tiempo_total = time.time() - self.tiempo_inicio
        print(f"\n✅ Completado en {self._formatear_tiempo(tiempo_total)}")


def limpiar_pantalla():
    os.system('clear' if os.name != 'nt' else 'cls')


def mostrar_banner():
    print("\n" + "="*65)
    print("   🚀 VERIFICADOR DUSA - MODO PARALELO")
    print("   Múltiples ventanas para máxima velocidad")
    print("="*65)


def seleccionar_archivo():
    """Selecciona archivo Excel."""
    downloads = os.path.expanduser("~/Downloads")
    archivos = []
    
    if os.path.exists(downloads):
        for f in os.listdir(downloads):
            # Ignorar archivos temporales de Excel (empiezan con ~$)
            if f.startswith('~$'):
                continue
            if f.endswith(('.xlsx', '.xls')) and 'publicacion' in f.lower():
                archivos.append(os.path.join(downloads, f))
    
    archivos.sort(key=os.path.getmtime, reverse=True)
    
    if archivos:
        print("\n📋 Archivos encontrados en Descargas:")
        for i, archivo in enumerate(archivos[:5], 1):
            nombre = os.path.basename(archivo)
            fecha = datetime.fromtimestamp(os.path.getmtime(archivo)).strftime("%d/%m %H:%M")
            print(f"   {i}. {nombre} ({fecha})")
        
        print(f"   0. Otro archivo")
        
        while True:
            opcion = input("\n👉 Selecciona (1-5 o 0): ").strip()
            if opcion == '0':
                ruta = input("   Ruta completa: ").strip()
                if os.path.exists(ruta):
                    return ruta
            elif opcion.isdigit() and 1 <= int(opcion) <= len(archivos):
                return archivos[int(opcion)-1]
    
    return None


def leer_excel(ruta):
    """Lee Excel de Mercado Libre."""
    print(f"\n📖 Leyendo Excel...")
    
    try:
        xl = pd.ExcelFile(ruta)
        
        if 'Publicaciones' in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name='Publicaciones', skiprows=2)
        else:
            df = pd.read_excel(xl)
        
        # Normalizar columnas
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if 'sku' in col_lower:
                col_map[col] = 'SKU'
            elif 'título' in col_lower or 'titulo' in col_lower:
                col_map[col] = 'Titulo'
            elif 'precio' == col_lower:
                col_map[col] = 'Precio'
            elif 'stock' in col_lower:
                col_map[col] = 'Stock'
        
        df = df.rename(columns=col_map)
        
        # Filtrar válidos
        if 'SKU' in df.columns or 'Titulo' in df.columns:
            mask = pd.Series([False] * len(df))
            if 'SKU' in df.columns:
                mask |= (df['SKU'].notna() & (df['SKU'].astype(str) != 'nan'))
            if 'Titulo' in df.columns:
                mask |= (df['Titulo'].notna() & (df['Titulo'].astype(str) != 'nan'))
            df = df[mask].copy()
        
        # Filtrar instrucciones
        if 'Stock' in df.columns:
            df = df[~df['Stock'].astype(str).str.contains('Obligatorio|Opcional', case=False, na=False)]
        
        print(f"   ✅ {len(df)} productos encontrados")
        return df
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def crear_navegador(numero_ventana):
    """Crea una instancia de Chrome."""
    opciones = Options()
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument(f"--window-size=800,600")
    opciones.add_argument(f"--window-position={100 + numero_ventana * 250},{100 + numero_ventana * 50}")
    
    servicio = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servicio, options=opciones)
    
    return driver


def login(driver, numero_ventana):
    """Inicia sesión en DUSA."""
    try:
        driver.get(DUSA_URL)
        time.sleep(4)
        
        campos_texto = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        campos_pass = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        
        if campos_texto:
            campos_texto[0].send_keys(USUARIO)
        if campos_pass:
            campos_pass[0].send_keys(PASSWORD)
        if len(campos_texto) >= 2:
            campos_texto[-1].send_keys(CLIENTE)
        
        time.sleep(1)
        
        botones = driver.find_elements(By.CSS_SELECTOR, ".v-button, button")
        for btn in botones:
            if "Entrar" in btn.text:
                btn.click()
                break
        
        time.sleep(5)
        
        # Verificar login
        try:
            driver.find_element(By.CSS_SELECTOR, "#loginf")
            return False
        except NoSuchElementException:
            return True
            
    except Exception as e:
        return False


def ir_a_productos(driver):
    """Navega a productos."""
    driver.get(DUSA_URL + "#!micuenta/productos")
    time.sleep(3)


def extraer_palabras_clave(titulo):
    """Extrae palabras clave del título."""
    if not titulo or str(titulo) == 'nan':
        return ""
    
    ignorar = ['farmauy', 'farmacia', 'original', 'sellado', 'envio', 'gratis',
               'pack', 'combo', 'oferta', 'promo', 'uruguay', 'importado']
    
    palabras = str(titulo).split()[:5]
    filtradas = [p for p in palabras if p.lower() not in ignorar and len(p) > 2]
    
    return " ".join(filtradas[:3])


def buscar_producto(driver, sku, titulo):
    """Busca un producto en DUSA."""
    resultado = {
        'busqueda': '',
        'encontrado': False,
        'disponible': None,
        'precio': None,
        'nombre': None,
        'mensaje': ''
    }
    
    # Determinar término de búsqueda
    if sku and str(sku) != 'nan':
        termino = str(sku).strip()
        resultado['busqueda'] = f"SKU: {sku}"
    else:
        termino = extraer_palabras_clave(titulo)
        resultado['busqueda'] = termino
    
    if not termino:
        resultado['mensaje'] = "Sin término de búsqueda"
        return resultado
    
    try:
        # Buscar campo de búsqueda
        campos = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        if not campos:
            resultado['mensaje'] = "Campo búsqueda no encontrado"
            return resultado
        
        campo = campos[0]
        campo.clear()
        time.sleep(0.3)
        campo.send_keys(termino)
        
        # Ejecutar búsqueda
        try:
            boton = driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]/..")
            boton.click()
        except:
            campo.send_keys(Keys.RETURN)
        
        time.sleep(2)
        
        # Analizar resultados
        filas = driver.find_elements(By.CSS_SELECTOR, ".v-table-row, .v-grid-row, tr.v-table-row")
        
        if filas:
            resultado['encontrado'] = True
            
            # Intentar extraer información de la primera fila
            primera_fila = filas[0]
            texto_fila = primera_fila.text.lower()
            
            # Detectar disponibilidad
            if 'disponible' in texto_fila:
                resultado['disponible'] = True
                resultado['mensaje'] = "✅ Disponible"
            elif 'faltante' in texto_fila or 'agotado' in texto_fila:
                resultado['disponible'] = False
                resultado['mensaje'] = "❌ Faltante"
            elif 'consultar' in texto_fila:
                resultado['disponible'] = None
                resultado['mensaje'] = "📞 Consultar"
            else:
                resultado['mensaje'] = "⚠️ Estado desconocido"
            
            # Intentar extraer nombre
            celdas = primera_fila.find_elements(By.CSS_SELECTOR, "td, .v-grid-cell")
            if celdas:
                resultado['nombre'] = celdas[0].text[:50]
        else:
            resultado['mensaje'] = "🔍 No encontrado"
        
    except Exception as e:
        resultado['mensaje'] = f"Error: {str(e)[:30]}"
    
    return resultado


def procesar_lote(numero_ventana, productos_df, barra_progreso, resultados_compartidos):
    """Procesa un lote de productos en una ventana."""
    
    print(f"\n   🪟 Ventana {numero_ventana + 1}: Iniciando con {len(productos_df)} productos...")
    
    driver = None
    resultados_locales = []
    
    try:
        # Crear navegador
        driver = crear_navegador(numero_ventana)
        
        # Login
        if not login(driver, numero_ventana):
            print(f"   ❌ Ventana {numero_ventana + 1}: Error en login")
            return []
        
        # Ir a productos
        ir_a_productos(driver)
        
        # Procesar cada producto
        for idx, row in productos_df.iterrows():
            sku = row.get('SKU', '')
            titulo = row.get('Titulo', '')
            
            resultado = buscar_producto(driver, sku, titulo)
            
            resultados_locales.append({
                'SKU': sku,
                'Titulo': str(titulo)[:60] if titulo else '',
                'Precio ML': row.get('Precio', ''),
                'Stock ML': row.get('Stock', ''),
                'Busqueda': resultado['busqueda'],
                'Encontrado': resultado['encontrado'],
                'Disponible': resultado['disponible'],
                'Nombre DUSA': resultado.get('nombre', ''),
                'Estado': resultado['mensaje'],
                'Ventana': numero_ventana + 1
            })
            
            # Actualizar progreso (thread-safe)
            with progreso_lock:
                barra_progreso.actualizar()
            
            # Pequeña pausa entre búsquedas
            time.sleep(1.5)
        
    except Exception as e:
        print(f"\n   ⚠️ Ventana {numero_ventana + 1}: Error - {e}")
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    # Agregar resultados al compartido
    with progreso_lock:
        resultados_compartidos.extend(resultados_locales)
    
    return resultados_locales


def dividir_productos(df, num_partes):
    """Divide el DataFrame en partes iguales."""
    partes = []
    tamaño = len(df) // num_partes
    resto = len(df) % num_partes
    
    inicio = 0
    for i in range(num_partes):
        fin = inicio + tamaño + (1 if i < resto else 0)
        partes.append(df.iloc[inicio:fin].copy())
        inicio = fin
    
    return partes


def guardar_resultados(resultados, nombre_base="resultado_paralelo"):
    """Guarda resultados en Excel."""
    if not resultados:
        print("⚠️ No hay resultados para guardar")
        return None
    
    df = pd.DataFrame(resultados)
    
    # Ordenar por SKU original
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    nombre_archivo = f"{nombre_base}_{timestamp}.xlsx"
    ruta = os.path.join(os.path.expanduser("~/Downloads"), nombre_archivo)
    
    df.to_excel(ruta, index=False)
    
    return ruta


def main():
    import argparse
    
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Verificador DUSA Paralelo')
    parser.add_argument('-w', '--ventanas', type=int, choices=[1, 2, 4, 6], 
                        help='Número de ventanas paralelas (1, 2, 4 o 6)')
    parser.add_argument('-a', '--archivo', type=str, 
                        help='Ruta al archivo Excel')
    parser.add_argument('-y', '--yes', action='store_true', 
                        help='No pedir confirmación')
    args = parser.parse_args()
    
    limpiar_pantalla()
    mostrar_banner()
    
    # Seleccionar archivo
    if args.archivo and os.path.exists(args.archivo):
        archivo = args.archivo
        print(f"\n📁 Archivo: {os.path.basename(archivo)}")
    else:
        archivo = seleccionar_archivo()
    
    if not archivo:
        print("❌ No se seleccionó archivo")
        return
    
    # Leer Excel
    df = leer_excel(archivo)
    if df is None or len(df) == 0:
        print("❌ No se encontraron productos")
        return
    
    total = len(df)
    
    # Seleccionar número de ventanas
    if args.ventanas:
        num_ventanas = args.ventanas
        print(f"\n🪟 Ventanas: {num_ventanas}")
    else:
        print(f"\n🪟 ¿Cuántas ventanas paralelas?")
        print(f"   Total productos: {total}")
        print(f"   1. Una ventana (seguro, ~{total * 4 // 60} min)")
        print(f"   2. Dos ventanas (~{total * 4 // 60 // 2} min)")
        print(f"   4. Cuatro ventanas (~{total * 4 // 60 // 4} min)")
        print(f"   6. Seis ventanas (~{total * 4 // 60 // 6} min)")
        
        while True:
            opcion = input("\n👉 Elige (1/2/4/6): ").strip()
            if opcion in ['1', '2', '4', '6']:
                num_ventanas = int(opcion)
                break
            print("   Opción inválida")
    
    # Confirmar
    print(f"\n📊 Configuración:")
    print(f"   • Productos: {total}")
    print(f"   • Ventanas: {num_ventanas}")
    print(f"   • Productos por ventana: ~{total // num_ventanas}")
    print(f"   • Tiempo estimado: ~{total * 4 // 60 // num_ventanas} minutos")
    
    if not args.yes:
        confirmar = input("\n¿Iniciar? (S/n): ").strip().lower()
        if confirmar == 'n':
            print("Cancelado")
            return
    
    # Dividir productos
    lotes = dividir_productos(df, num_ventanas)
    
    # Preparar barra de progreso
    print(f"\n🚀 Iniciando verificación paralela...")
    print("-" * 70)
    
    barra = BarraProgreso(total)
    resultados_compartidos = []
    
    # Ejecutar en paralelo
    with ThreadPoolExecutor(max_workers=num_ventanas) as executor:
        futuros = []
        
        for i, lote in enumerate(lotes):
            futuro = executor.submit(procesar_lote, i, lote, barra, resultados_compartidos)
            futuros.append(futuro)
            time.sleep(2)  # Esperar un poco entre cada inicio de ventana
        
        # Esperar a que terminen todos
        for futuro in as_completed(futuros):
            try:
                futuro.result()
            except Exception as e:
                print(f"\n⚠️ Error en hilo: {e}")
    
    # Finalizar
    barra.finalizar()
    
    # Guardar resultados
    print(f"\n💾 Guardando resultados...")
    ruta_resultado = guardar_resultados(resultados_compartidos)
    
    if ruta_resultado:
        print(f"✅ Guardado en: {ruta_resultado}")
        
        # Resumen
        df_resultado = pd.DataFrame(resultados_compartidos)
        disponibles = len(df_resultado[df_resultado['Disponible'] == True])
        faltantes = len(df_resultado[df_resultado['Disponible'] == False])
        no_encontrados = len(df_resultado[df_resultado['Encontrado'] == False])
        
        print(f"\n📊 RESUMEN:")
        print(f"   ✅ Disponibles: {disponibles}")
        print(f"   ❌ Faltantes: {faltantes}")
        print(f"   🔍 No encontrados: {no_encontrados}")
        
        # Abrir archivo
        abrir = input("\n¿Abrir archivo de resultados? (S/n): ").strip().lower()
        if abrir != 'n':
            os.system(f'open "{ruta_resultado}"')
    
    print("\n👋 ¡Proceso completado!")


if __name__ == "__main__":
    main()
