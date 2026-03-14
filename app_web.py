#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador DUSA - Aplicación Web
=================================
Interfaz web amigable que se abre en el navegador.
"""

from flask import Flask, render_template, request, jsonify, send_file, session
import pandas as pd
import os
import time
import threading
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import webbrowser

app = Flask(__name__)
app.secret_key = 'verificador_dusa_2026'
app.config['UPLOAD_FOLDER'] = '/tmp/verificador_dusa'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Variables globales para el estado
estado_global = {
    'procesando': False,
    'progreso': 0,
    'total': 0,
    'mensaje': '',
    'resultados': [],
    'archivo_resultado': None,
    # Nuevos campos para tiempo y paralelo
    'tiempo_inicio': None,
    'tiempo_transcurrido': 0,
    'tiempo_estimado': 0,
    'velocidad': 0,
    'ventanas': 1,
    'ventanas_activas': 0,
    'tiempos_productos': []  # Para calcular promedio
}

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
progreso_lock = threading.Lock()

# Credenciales DUSA
DUSA_CONFIG = {
    'usuario': 'farmacia.farma',
    'password': 'Parlantes28',
    'cliente': '2287',
    'url': 'https://pedidos.dusa.com.uy/DUSAWebUI'
}

# Crear carpeta de uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')


@app.route('/subir', methods=['POST'])
def subir_archivo():
    """Recibe el archivo Excel."""
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    
    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'No se seleccionó archivo'}), 400
    
    if not archivo.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Solo se permiten archivos Excel (.xlsx, .xls)'}), 400
    
    # Guardar archivo
    filename = secure_filename(archivo.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    archivo.save(filepath)
    
    # Leer y analizar
    try:
        productos = leer_excel(filepath)
        return jsonify({
            'success': True,
            'archivo': filename,
            'total_productos': len(productos),
            'preview': productos[:10]  # Primeros 10 para preview
        })
    except Exception as e:
        return jsonify({'error': f'Error leyendo archivo: {str(e)}'}), 400


@app.route('/iniciar', methods=['POST'])
def iniciar_verificacion():
    """Inicia el proceso de verificación."""
    global estado_global
    
    if estado_global['procesando']:
        return jsonify({'error': 'Ya hay un proceso en curso'}), 400
    
    data = request.json
    archivo = data.get('archivo')
    ventanas = data.get('ventanas', 1)  # Número de ventanas paralelas
    
    if not archivo:
        return jsonify({'error': 'No se especificó archivo'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], archivo)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Archivo no encontrado'}), 400
    
    # Validar número de ventanas
    ventanas = max(1, min(6, int(ventanas)))
    estado_global['ventanas'] = ventanas
    
    # Iniciar en hilo separado
    thread = threading.Thread(target=proceso_verificacion_paralelo, args=(filepath, ventanas))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'mensaje': f'Verificación iniciada con {ventanas} ventana(s)'})


@app.route('/estado')
def obtener_estado():
    """Retorna el estado actual del proceso."""
    # Calcular tiempo transcurrido en tiempo real
    if estado_global['procesando'] and estado_global['tiempo_inicio']:
        estado_global['tiempo_transcurrido'] = time.time() - estado_global['tiempo_inicio']
    return jsonify(estado_global)


@app.route('/detener', methods=['POST'])
def detener():
    """Detiene el proceso."""
    global estado_global
    estado_global['procesando'] = False
    estado_global['mensaje'] = 'Detenido por usuario'
    return jsonify({'success': True})


@app.route('/descargar')
def descargar_resultado():
    """Descarga el archivo de resultados."""
    if estado_global['archivo_resultado'] and os.path.exists(estado_global['archivo_resultado']):
        return send_file(estado_global['archivo_resultado'], as_attachment=True)
    return jsonify({'error': 'No hay archivo disponible'}), 404


def leer_excel(filepath):
    """Lee el Excel de Mercado Libre."""
    xl = pd.ExcelFile(filepath)
    
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
        elif col_lower == 'precio':
            col_map[col] = 'Precio'
        elif 'stock' in col_lower:
            col_map[col] = 'Stock'
        elif 'estado' in col_lower:
            col_map[col] = 'Estado'
    
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
    
    # Convertir a lista de dicts
    productos = []
    for _, row in df.iterrows():
        productos.append({
            'sku': str(row.get('SKU', '')) if pd.notna(row.get('SKU')) else '',
            'titulo': str(row.get('Titulo', ''))[:60] if pd.notna(row.get('Titulo')) else '',
            'precio_ml': str(row.get('Precio', '')) if pd.notna(row.get('Precio')) else '',
            'stock_ml': str(row.get('Stock', '')) if pd.notna(row.get('Stock')) else '',
            'estado_ml': str(row.get('Estado', '')) if pd.notna(row.get('Estado')) else ''
        })
    
    return productos


def extraer_palabras_clave(titulo):
    """Extrae palabras clave."""
    if not titulo:
        return ""
    ignorar = ['farmauy', 'farmacia', 'original', 'sellado', 'envio', 'gratis',
               'pack', 'combo', 'oferta', 'promo', 'uruguay', 'importado']
    palabras = str(titulo).split()[:5]
    filtradas = [p for p in palabras if p.lower() not in ignorar and len(p) > 2]
    return " ".join(filtradas[:3])


def crear_navegador_visible(num_ventana=0):
    """Crea un navegador Chrome VISIBLE (sin headless)."""
    opciones = Options()
    # NO usar headless - queremos ver las ventanas
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-gpu")
    opciones.add_argument("--window-size=800,600")
    # Posicionar cada ventana en diferente lugar
    x_pos = 50 + (num_ventana % 3) * 300
    y_pos = 50 + (num_ventana // 3) * 200
    opciones.add_argument(f"--window-position={x_pos},{y_pos}")
    
    servicio = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servicio, options=opciones)
    return driver


def login_dusa(driver):
    """Inicia sesión en DUSA."""
    try:
        driver.get(DUSA_CONFIG['url'])
        time.sleep(3)
        
        campos_texto = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        campos_pass = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        
        if campos_texto:
            campos_texto[0].send_keys(DUSA_CONFIG['usuario'])
        if campos_pass:
            campos_pass[0].send_keys(DUSA_CONFIG['password'])
        if len(campos_texto) >= 2:
            campos_texto[-1].send_keys(DUSA_CONFIG['cliente'])
        
        time.sleep(0.5)
        botones = driver.find_elements(By.CSS_SELECTOR, ".v-button, button")
        for btn in botones:
            if "Entrar" in btn.text:
                btn.click()
                break
        
        time.sleep(3)
        
        # Verificar login exitoso
        try:
            driver.find_element(By.CSS_SELECTOR, "#loginf")
            return False
        except NoSuchElementException:
            # Ir a productos
            driver.get(DUSA_CONFIG['url'] + "#!micuenta/productos")
            time.sleep(2)
            return True
            
    except Exception:
        return False


def procesar_lote_productos(num_ventana, productos, estado_ref):
    """Procesa un lote de productos en una ventana."""
    global estado_global
    
    driver = None
    resultados_locales = []
    
    try:
        # Crear navegador VISIBLE (no headless)
        driver = crear_navegador_visible(num_ventana)
        
        with progreso_lock:
            estado_global['ventanas_activas'] += 1
        
        # Login
        if not login_dusa(driver):
            return resultados_locales
        
        tiempo_ultimo = time.time()
        
        # Procesar cada producto
        for producto in productos:
            if not estado_global['procesando']:
                break
            
            sku = producto['sku']
            titulo = producto['titulo']
            
            resultado = buscar_en_dusa(driver, sku, titulo)
            resultado.update(producto)
            
            # Calcular comparación de precios
            precio_ml_num = parsear_precio(producto.get('precio_ml', ''))
            precio_dusa_num = resultado.get('precio_dusa_num')
            
            if precio_ml_num and precio_dusa_num:
                resultado['precio_ml_num'] = precio_ml_num
                resultado['diferencia_precio'] = round(precio_ml_num - precio_dusa_num, 2)
                # Precio inferior si ML es menor que DUSA (vendemos más barato de lo que compramos)
                if precio_ml_num < precio_dusa_num:
                    resultado['precio_inferior'] = True
                    resultado['alerta'] = f'Precio ML (${precio_ml_num:.0f}) < DUSA (${precio_dusa_num:.0f})'
            
            # Alerta si no se encontró pero tiene SKU
            if not resultado['encontrado'] and sku and sku.strip():
                if resultado.get('alerta'):
                    resultado['alerta'] += ' | SKU no encontrado'
                else:
                    resultado['alerta'] = 'SKU no encontrado en DUSA'
            
            resultados_locales.append(resultado)
            
            # Actualizar estado global (thread-safe)
            with progreso_lock:
                estado_global['resultados'].append(resultado)
                estado_global['progreso'] += 1
                
                # Calcular tiempo por producto
                ahora = time.time()
                tiempo_producto = ahora - tiempo_ultimo
                tiempo_ultimo = ahora
                
                estado_global['tiempos_productos'].append(tiempo_producto)
                # Mantener solo últimos 30
                if len(estado_global['tiempos_productos']) > 30:
                    estado_global['tiempos_productos'] = estado_global['tiempos_productos'][-30:]
                
                # Calcular tiempo estimado
                if estado_global['tiempos_productos']:
                    promedio = sum(estado_global['tiempos_productos']) / len(estado_global['tiempos_productos'])
                    # Ajustar por número de ventanas activas
                    ventanas_activas = max(1, estado_global['ventanas_activas'])
                    restantes = estado_global['total'] - estado_global['progreso']
                    estado_global['tiempo_estimado'] = (promedio * restantes) / ventanas_activas
                    
                    # Velocidad (productos por minuto)
                    tiempo_total = ahora - estado_global['tiempo_inicio']
                    if tiempo_total > 0:
                        estado_global['velocidad'] = (estado_global['progreso'] / tiempo_total) * 60
                
                estado_global['mensaje'] = f"Verificando {estado_global['progreso']}/{estado_global['total']} ({estado_global['ventanas_activas']} ventanas)"
            
            time.sleep(1)  # Pausa entre búsquedas
        
    except Exception as e:
        print(f"Error en ventana {num_ventana}: {e}")
    
    finally:
        with progreso_lock:
            estado_global['ventanas_activas'] = max(0, estado_global['ventanas_activas'] - 1)
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    return resultados_locales


def proceso_verificacion_paralelo(filepath, num_ventanas=1):
    """Proceso de verificación con múltiples ventanas paralelas."""
    global estado_global
    
    # Resetear estado
    estado_global['procesando'] = True
    estado_global['progreso'] = 0
    estado_global['total'] = 0
    estado_global['resultados'] = []
    estado_global['mensaje'] = 'Leyendo archivo...'
    estado_global['tiempo_inicio'] = time.time()
    estado_global['tiempo_transcurrido'] = 0
    estado_global['tiempo_estimado'] = 0
    estado_global['velocidad'] = 0
    estado_global['ventanas_activas'] = 0
    estado_global['tiempos_productos'] = []
    
    try:
        # Leer productos
        productos = leer_excel(filepath)
        estado_global['total'] = len(productos)
        
        if not productos:
            estado_global['mensaje'] = 'No se encontraron productos'
            estado_global['procesando'] = False
            return
        
        # Dividir productos en lotes
        estado_global['mensaje'] = f'Iniciando {num_ventanas} ventana(s)...'
        
        lotes = []
        tamaño_lote = len(productos) // num_ventanas
        resto = len(productos) % num_ventanas
        
        inicio = 0
        for i in range(num_ventanas):
            fin = inicio + tamaño_lote + (1 if i < resto else 0)
            lotes.append(productos[inicio:fin])
            inicio = fin
        
        # Ejecutar en paralelo
        with ThreadPoolExecutor(max_workers=num_ventanas) as executor:
            futuros = []
            
            for i, lote in enumerate(lotes):
                if lote:  # Solo si hay productos en el lote
                    futuro = executor.submit(procesar_lote_productos, i, lote, estado_global)
                    futuros.append(futuro)
                    time.sleep(3)  # Esperar entre cada inicio de ventana
            
            # Esperar a que terminen
            for futuro in as_completed(futuros):
                try:
                    futuro.result()
                except Exception as e:
                    print(f"Error en hilo: {e}")
        
        # Generar Excel
        if estado_global['resultados']:
            estado_global['mensaje'] = 'Generando archivo de resultados...'
            generar_excel_resultado()
        
        estado_global['mensaje'] = '✅ Completado'
        
    except Exception as e:
        estado_global['mensaje'] = f'Error: {str(e)}'
    
    finally:
        estado_global['procesando'] = False


def proceso_verificacion(filepath):
    """Proceso principal de verificación."""
    global estado_global
    
    estado_global['procesando'] = True
    estado_global['progreso'] = 0
    estado_global['resultados'] = []
    estado_global['mensaje'] = 'Leyendo archivo...'
    
    driver = None
    
    try:
        # Leer productos
        productos = leer_excel(filepath)
        estado_global['total'] = len(productos)
        
        # Iniciar navegador
        estado_global['mensaje'] = 'Iniciando navegador...'
        opciones = Options()
        opciones.add_argument("--no-sandbox")
        opciones.add_argument("--disable-dev-shm-usage")
        opciones.add_argument("--window-size=1200,800")
        # Ejecutar en segundo plano (headless)
        # opciones.add_argument("--headless")  # Descomentar para ocultar navegador
        
        servicio = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servicio, options=opciones)
        
        # Login
        estado_global['mensaje'] = 'Iniciando sesión en DUSA...'
        driver.get(DUSA_CONFIG['url'])
        time.sleep(2)
        
        campos_texto = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        campos_pass = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        
        if campos_texto:
            campos_texto[0].send_keys(DUSA_CONFIG['usuario'])
        if campos_pass:
            campos_pass[0].send_keys(DUSA_CONFIG['password'])
        if len(campos_texto) >= 2:
            campos_texto[-1].send_keys(DUSA_CONFIG['cliente'])
        
        time.sleep(0.3)
        botones = driver.find_elements(By.CSS_SELECTOR, ".v-button, button")
        for btn in botones:
            if "Entrar" in btn.text:
                btn.click()
                break
        
        time.sleep(2.5)
        
        # Ir a productos
        estado_global['mensaje'] = 'Navegando a productos...'
        driver.get(DUSA_CONFIG['url'] + "#!micuenta/productos")
        time.sleep(1.5)
        
        # Verificar productos
        for idx, producto in enumerate(productos):
            if not estado_global['procesando']:
                break
            
            estado_global['progreso'] = idx + 1
            estado_global['mensaje'] = f'Verificando {idx + 1}/{len(productos)}'
            
            sku = producto['sku']
            titulo = producto['titulo']
            
            if not sku and not titulo:
                continue
            
            # Realizar búsqueda
            resultado = buscar_en_dusa(driver, sku, titulo)
            resultado.update(producto)
            
            estado_global['resultados'].append(resultado)
            time.sleep(0.3)
        
        # Generar Excel
        if estado_global['resultados']:
            estado_global['mensaje'] = 'Generando archivo de resultados...'
            generar_excel_resultado()
        
        estado_global['mensaje'] = 'Completado'
        
    except Exception as e:
        estado_global['mensaje'] = f'Error: {str(e)}'
    
    finally:
        estado_global['procesando'] = False
        if driver:
            driver.quit()


def parsear_precio(precio_str):
    """Convierte string de precio a número."""
    if not precio_str:
        return None
    try:
        # Limpiar: "$1.234,56" -> 1234.56 o "1234.56" -> 1234.56
        limpio = str(precio_str).replace('$', '').replace(' ', '').strip()
        # Detectar formato: 1.234,56 (español) vs 1,234.56 (inglés)
        if ',' in limpio and '.' in limpio:
            if limpio.rfind(',') > limpio.rfind('.'):
                # Formato español: 1.234,56
                limpio = limpio.replace('.', '').replace(',', '.')
            else:
                # Formato inglés: 1,234.56
                limpio = limpio.replace(',', '')
        elif ',' in limpio:
            # Solo coma, asumir decimal
            limpio = limpio.replace(',', '.')
        return float(limpio)
    except:
        return None


def buscar_en_dusa(driver, sku, titulo):
    """Busca un producto en DUSA."""
    resultado = {
        'busqueda': '',
        'busqueda_tipo': '',  # 'sku' o 'titulo'
        'sku_encontrado': False,  # True si se buscó por SKU y se encontró
        'encontrado': False,
        'estado_dusa': None,  # 'disponible', 'faltante', 'consultar', 'diferida'
        'disponible': None,
        'precio_dusa': '',
        'precio_dusa_num': None,
        'nombre_dusa': '',
        'oferta': '',
        'laboratorio': '',
        'precio_inferior': False,  # True si precio ML < precio DUSA
        'diferencia_precio': None,  # Diferencia numérica
        'alerta': ''  # Motivo de alerta para revisar
    }
    
    # Determinar término de búsqueda
    if sku and sku.strip():
        termino = sku.strip()
        resultado['busqueda_tipo'] = 'sku'
    else:
        termino = extraer_palabras_clave(titulo)
        resultado['busqueda_tipo'] = 'titulo'
    
    resultado['busqueda'] = termino
    
    if not termino:
        return resultado
    
    try:
        campo = driver.find_element(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        campo.clear()
        time.sleep(0.1)
        campo.send_keys(termino)
        
        try:
            boton = driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]/..")
            boton.click()
        except:
            campo.send_keys(Keys.RETURN)
        
        time.sleep(0.8)
        
        filas = driver.find_elements(By.CSS_SELECTOR, "table tr")
        filas_datos = [f for f in filas if f.text.strip() and "Stock" not in f.text and "Descripción" not in f.text]
        
        if filas_datos:
            primera = filas_datos[0]
            resultado['encontrado'] = True
            
            # Detectar estado por ícono y texto
            # Estados posibles:
            # - Verde ✅ = Disponible
            # - Rojo ❌ = Faltante ("Producto con faltante en laboratorio")
            # - Azul 🔵 = Diferida ("Por pedido. Sólo venta telefónica. Producto con entrega diferida.")
            # - Amarillo ⚠️ = Consultar
            try:
                # Buscar imagen de estado en la primera celda
                imgs = primera.find_elements(By.CSS_SELECTOR, "td img, td .v-icon")
                icono_src = ""
                icono_style = ""
                for img in imgs:
                    icono_src = img.get_attribute('src') or ''
                    icono_style = img.get_attribute('style') or ''
                    icono_class = img.get_attribute('class') or ''
                    break
                
                html_celda = primera.find_elements(By.CSS_SELECTOR, "td")[0].get_attribute('innerHTML').lower() if primera.find_elements(By.CSS_SELECTOR, "td") else ''
                texto_fila = primera.text.lower()
                
                # Detectar estado por color/clase/texto (orden de prioridad)
                # 1. Faltante (rojo)
                if 'faltante' in texto_fila or 'red' in icono_style or 'error' in html_celda or 'rojo' in html_celda:
                    resultado['estado_dusa'] = 'faltante'
                    resultado['disponible'] = False
                # 2. Diferida (azul) - Por pedido, entrega diferida
                elif 'diferida' in texto_fila or 'por pedido' in texto_fila or 'venta telefónica' in texto_fila or 'venta telefonica' in texto_fila or 'blue' in icono_style or 'azul' in html_celda:
                    resultado['estado_dusa'] = 'diferida'
                    resultado['disponible'] = 'diferida'
                # 3. Consultar (amarillo)
                elif 'yellow' in icono_style or 'warning' in html_celda or 'amarillo' in html_celda or 'consultar' in texto_fila or 'llamar' in texto_fila:
                    resultado['estado_dusa'] = 'consultar'
                    resultado['disponible'] = 'consultar'
                # 4. Disponible (verde) - default
                else:
                    resultado['estado_dusa'] = 'disponible'
                    resultado['disponible'] = True
            except:
                # Fallback: si no encuentra ícono, asumir disponible
                resultado['estado_dusa'] = 'disponible'
                resultado['disponible'] = True
            
            # Si se buscó por SKU y se encontró
            if resultado['busqueda_tipo'] == 'sku':
                resultado['sku_encontrado'] = True
            
            celdas = primera.find_elements(By.CSS_SELECTOR, "td")
            if len(celdas) >= 5:
                resultado['nombre_dusa'] = celdas[1].text.split('\n')[0][:40]
                resultado['laboratorio'] = celdas[2].text.strip()[:20]
                resultado['oferta'] = celdas[3].text.strip()
                resultado['precio_dusa'] = celdas[4].text.strip()
                resultado['precio_dusa_num'] = parsear_precio(resultado['precio_dusa'])
        
        return resultado
        
    except Exception:
        return resultado


def generar_excel_resultado():
    """Genera el Excel de resultados."""
    global estado_global
    
    df = pd.DataFrame(estado_global['resultados'])
    
    # Crear columna Estado DUSA legible
    def estado_legible(row):
        if not row.get('encontrado'):
            return '🔍 No encontrado'
        estado = row.get('estado_dusa', '')
        if estado == 'disponible':
            return '✅ Disponible'
        elif estado == 'diferida':
            return '🔵 Diferida (por pedido)'
        elif estado == 'consultar':
            return '⚠️ Consultar'
        elif estado == 'faltante':
            return '❌ Faltante'
        elif row.get('disponible') == True:
            return '✅ Disponible'
        elif row.get('disponible') == 'diferida':
            return '🔵 Diferida (por pedido)'
        elif row.get('disponible') == False:
            return '❌ Faltante'
        return 'Desconocido'
    
    df['estado_final'] = df.apply(estado_legible, axis=1)
    
    # Crear columna de alerta/revisión
    def generar_alerta(row):
        alertas = []
        if row.get('precio_inferior'):
            alertas.append('⚠️ PRECIO ML INFERIOR')
        if not row.get('encontrado') and row.get('sku') and str(row.get('sku')).strip():
            alertas.append('🔍 SKU NO ENCONTRADO')
        elif not row.get('encontrado'):
            alertas.append('🔍 No encontrado')
        return ' | '.join(alertas) if alertas else ''
    
    df['alerta_revisar'] = df.apply(generar_alerta, axis=1)
    
    # Columnas en orden de importancia
    columnas = ['alerta_revisar', 'sku', 'titulo', 'estado_final', 'nombre_dusa', 
                'precio_ml', 'precio_dusa', 'diferencia_precio',
                'oferta', 'laboratorio', 'stock_ml', 'estado_ml']
    columnas = [c for c in columnas if c in df.columns]
    df = df[columnas]
    
    nombres = {
        'alerta_revisar': '⚠️ REVISAR',
        'sku': 'SKU',
        'titulo': 'Título ML',
        'estado_final': 'Estado DUSA',
        'nombre_dusa': 'Producto DUSA',
        'precio_dusa': 'Precio DUSA',
        'precio_ml': 'Precio ML',
        'diferencia_precio': 'Diferencia ($)',
        'oferta': 'Oferta',
        'laboratorio': 'Laboratorio',
        'stock_ml': 'Stock ML'
    }
    df = df.rename(columns=nombres)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    ruta = os.path.join(app.config['UPLOAD_FOLDER'], f'resultado_dusa_{timestamp}.xlsx')
    
    # Guardar con formato
    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultados')
        
        # Hoja adicional solo con productos a revisar
        revisar = df[df['⚠️ REVISAR'].astype(str).str.len() > 0]
        if len(revisar) > 0:
            revisar.to_excel(writer, index=False, sheet_name='⚠️ A REVISAR')
    
    estado_global['archivo_resultado'] = ruta


# Crear templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(TEMPLATE_DIR, exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verificador DUSA - Farmacia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
            margin-bottom: 20px;
        }
        h1 {
            color: #1e3c72;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        h2 { color: #333; margin-bottom: 15px; font-size: 1.2em; }
        .subtitle { color: #666; margin-bottom: 20px; }
        
        /* Upload zone */
        .upload-zone {
            border: 3px dashed #ccc;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #f9f9f9;
        }
        .upload-zone:hover, .upload-zone.dragover {
            border-color: #1e3c72;
            background: #e8f0fe;
        }
        .upload-zone input { display: none; }
        .upload-zone .icon { font-size: 50px; margin-bottom: 15px; }
        .upload-zone p { color: #666; }
        
        /* Buttons */
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary {
            background: #1e3c72;
            color: white;
        }
        .btn-primary:hover { background: #2a5298; }
        .btn-primary:disabled { background: #ccc; cursor: not-allowed; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-outline {
            background: white;
            border: 2px solid #1e3c72;
            color: #1e3c72;
        }
        
        /* Progress */
        .progress-container { margin: 20px 0; }
        .progress-bar {
            height: 25px;
            background: #e9ecef;
            border-radius: 12px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #1e3c72, #2a5298);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .status { margin-top: 10px; color: #666; }
        
        /* Results table */
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 14px;
        }
        .results-table th, .results-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .results-table th {
            background: #f5f5f5;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        .results-table tr:hover { background: #f9f9f9; }
        
        /* Status badges */
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .badge-warning { background: #fff3cd; color: #856404; }
        
        /* Summary */
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .summary-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .summary-card .number {
            font-size: 32px;
            font-weight: bold;
        }
        .summary-card.disponible .number { color: #28a745; }
        .summary-card.consultar .number { color: #ffc107; }
        .summary-card.faltante .number { color: #dc3545; }
        .summary-card.no-encontrado .number { color: #6c757d; }
        .badge-secondary { background: #e2e3e5; color: #383d41; }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .tab {
            padding: 10px 20px;
            background: #f5f5f5;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tab:hover { background: #e9ecef; }
        .tab.active {
            background: #1e3c72;
            color: white;
        }
        
        /* Table container */
        .table-container {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 8px;
        }
        
        /* Hidden */
        .hidden { display: none !important; }
        
        /* Animations */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .processing { animation: pulse 1.5s infinite; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="card">
            <h1>🏥 Verificador DUSA</h1>
            <p class="subtitle">Verifica disponibilidad de productos de Mercado Libre en DUSA</p>
        </div>
        
        <!-- Upload Section -->
        <div class="card" id="uploadSection">
            <h2>📁 Paso 1: Sube tu archivo Excel de Mercado Libre</h2>
            <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
                <div class="icon">📄</div>
                <p><strong>Haz clic aquí</strong> o arrastra tu archivo Excel</p>
                <p style="margin-top:10px; font-size:12px; color:#999;">.xlsx o .xls</p>
                <input type="file" id="fileInput" accept=".xlsx,.xls">
            </div>
            <div id="fileInfo" class="hidden" style="margin-top:20px;">
                <p>✅ <strong id="fileName"></strong></p>
                <p id="productCount" style="color:#666;"></p>
            </div>
        </div>
        
        <!-- Control Section -->
        <div class="card" id="controlSection">
            <h2>🚀 Paso 2: Iniciar verificación</h2>
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <button class="btn btn-primary" id="btnIniciar" onclick="iniciarVerificacion()" disabled>
                    ▶️ Iniciar Verificación
                </button>
                <button class="btn btn-danger hidden" id="btnDetener" onclick="detenerVerificacion()">
                    ⏹️ Detener
                </button>
            </div>
            
            <div class="progress-container hidden" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width:0%">0%</div>
                </div>
                <p class="status" id="statusText">Preparando...</p>
            </div>
        </div>
        
        <!-- Results Section -->
        <div class="card hidden" id="resultsSection">
            <h2>📊 Resultados</h2>
            
            <div class="summary" id="summary"></div>
            
            <div class="tabs">
                <div class="tab active" onclick="filtrarResultados('todos')">Todos</div>
                <div class="tab" onclick="filtrarResultados('disponible')">✅ Disponibles</div>
                <div class="tab" onclick="filtrarResultados('consultar')">⚠️ Consultar</div>
                <div class="tab" onclick="filtrarResultados('faltante')">❌ Faltantes</div>
                <div class="tab" onclick="filtrarResultados('no-encontrado')">🔍 No encontrados</div>
            </div>
            
            <div class="table-container">
                <table class="results-table" id="resultsTable">
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>Título ML</th>
                            <th>Estado</th>
                            <th>Producto DUSA</th>
                            <th>Precio DUSA</th>
                            <th>Oferta</th>
                        </tr>
                    </thead>
                    <tbody id="resultsBody"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Download Section - aparece al completar -->
        <div class="card hidden" id="downloadSection" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white;">
            <h2 style="color: white;">✅ ¡Verificación Completada!</h2>
            <p style="margin: 15px 0; font-size: 16px;" id="completedMessage">Se analizaron todos los productos.</p>
            <button class="btn" id="btnDescargar" onclick="descargarResultado()" style="background: white; color: #28a745; font-size: 18px; padding: 15px 40px;">
                📥 Descargar Resultados en Excel
            </button>
            <p style="margin-top: 15px; font-size: 13px; opacity: 0.9;">El archivo incluye: SKU, Título, Estado en DUSA, Precio DUSA, Oferta y más</p>
        </div>
    </div>
    
    <script>
        let archivoActual = null;
        let pollingInterval = null;
        let todosResultados = [];
        
        // Drag & Drop
        const uploadZone = document.getElementById('uploadZone');
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                document.getElementById('fileInput').files = e.dataTransfer.files;
                subirArchivo(e.dataTransfer.files[0]);
            }
        });
        
        document.getElementById('fileInput').addEventListener('change', (e) => {
            if (e.target.files.length) {
                subirArchivo(e.target.files[0]);
            }
        });
        
        async function subirArchivo(file) {
            const formData = new FormData();
            formData.append('archivo', file);
            
            try {
                const res = await fetch('/subir', { method: 'POST', body: formData });
                const data = await res.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                archivoActual = data.archivo;
                document.getElementById('fileName').textContent = data.archivo;
                document.getElementById('productCount').textContent = 
                    `${data.total_productos} productos encontrados`;
                document.getElementById('fileInfo').classList.remove('hidden');
                document.getElementById('btnIniciar').disabled = false;
                
            } catch (e) {
                alert('Error subiendo archivo: ' + e.message);
            }
        }
        
        async function iniciarVerificacion() {
            if (!archivoActual) return;
            
            try {
                const res = await fetch('/iniciar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ archivo: archivoActual })
                });
                const data = await res.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                document.getElementById('btnIniciar').classList.add('hidden');
                document.getElementById('btnDetener').classList.remove('hidden');
                document.getElementById('progressContainer').classList.remove('hidden');
                document.getElementById('resultsSection').classList.remove('hidden');
                
                pollingInterval = setInterval(actualizarEstado, 1000);
                
            } catch (e) {
                alert('Error: ' + e.message);
            }
        }
        
        async function actualizarEstado() {
            try {
                const res = await fetch('/estado');
                const estado = await res.json();
                
                const porcentaje = estado.total > 0 ? 
                    Math.round((estado.progreso / estado.total) * 100) : 0;
                
                document.getElementById('progressFill').style.width = porcentaje + '%';
                document.getElementById('progressFill').textContent = porcentaje + '%';
                document.getElementById('statusText').textContent = estado.mensaje;
                
                // Actualizar tabla
                if (estado.resultados.length > 0) {
                    todosResultados = estado.resultados;
                    actualizarTabla(estado.resultados);
                    actualizarResumen(estado.resultados);
                }
                
                // Verificar si terminó
                if (!estado.procesando && estado.progreso > 0) {
                    clearInterval(pollingInterval);
                    document.getElementById('btnDetener').classList.add('hidden');
                    document.getElementById('btnIniciar').classList.remove('hidden');
                    document.getElementById('statusText').classList.remove('processing');
                    
                    // Mostrar sección de descarga
                    document.getElementById('downloadSection').classList.remove('hidden');
                    
                    // Actualizar mensaje con resumen
                    const total = todosResultados.length;
                    const disponibles = todosResultados.filter(r => r.encontrado && r.disponible === true).length;
                    const consultar = todosResultados.filter(r => r.encontrado && (r.disponible === 'consultar' || r.estado_dusa === 'consultar')).length;
                    const faltantes = todosResultados.filter(r => r.encontrado && r.disponible === false).length;
                    const noEncontrados = todosResultados.filter(r => !r.encontrado).length;
                    
                    document.getElementById('completedMessage').innerHTML = 
                        `Se analizaron <strong>${total}</strong> productos: ` +
                        `<strong style="color:#155724">${disponibles}</strong> disponibles, ` +
                        `<strong style="color:#856404">${consultar}</strong> a consultar, ` +
                        `<strong style="color:#721c24">${faltantes}</strong> faltantes, ` +
                        `<strong>${noEncontrados}</strong> no encontrados.`;
                }
                
            } catch (e) {
                console.error('Error actualizando estado:', e);
            }
        }
        
        function actualizarTabla(resultados) {
            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = '';
            
            resultados.forEach(r => {
                let badge = '';
                let clase = '';
                if (!r.encontrado) {
                    badge = '<span class="badge badge-secondary">No encontrado</span>';
                    clase = 'no-encontrado';
                } else if (r.disponible === 'consultar' || r.estado_dusa === 'consultar') {
                    badge = '<span class="badge badge-warning">⚠️ Consultar</span>';
                    clase = 'consultar';
                } else if (r.disponible === true || r.estado_dusa === 'disponible') {
                    badge = '<span class="badge badge-success">✅ Disponible</span>';
                    clase = 'disponible';
                } else {
                    badge = '<span class="badge badge-danger">❌ Faltante</span>';
                    clase = 'faltante';
                }
                
                const tr = document.createElement('tr');
                tr.className = clase;
                tr.innerHTML = `
                    <td>${r.sku || '-'}</td>
                    <td>${r.titulo || '-'}</td>
                    <td>${badge}</td>
                    <td>${r.nombre_dusa || '-'}</td>
                    <td>${r.precio_dusa || '-'}</td>
                    <td>${r.oferta || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        function actualizarResumen(resultados) {
            const total = resultados.length;
            const disponibles = resultados.filter(r => r.encontrado && r.disponible === true).length;
            const consultar = resultados.filter(r => r.encontrado && (r.disponible === 'consultar' || r.estado_dusa === 'consultar')).length;
            const faltantes = resultados.filter(r => r.encontrado && r.disponible === false).length;
            const noEncontrados = resultados.filter(r => !r.encontrado).length;
            
            document.getElementById('summary').innerHTML = `
                <div class="summary-card">
                    <div class="number">${total}</div>
                    <div>Total</div>
                </div>
                <div class="summary-card disponible">
                    <div class="number">${disponibles}</div>
                    <div>✅ Disponibles</div>
                </div>
                <div class="summary-card consultar">
                    <div class="number">${consultar}</div>
                    <div>⚠️ Consultar</div>
                </div>
                <div class="summary-card faltante">
                    <div class="number">${faltantes}</div>
                    <div>❌ Faltantes</div>
                </div>
                <div class="summary-card no-encontrado">
                    <div class="number">${noEncontrados}</div>
                    <div>🔍 No encontrados</div>
                </div>
            `;
        }
        
        function filtrarResultados(tipo) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            let filtrados = todosResultados;
            if (tipo === 'disponible') {
                filtrados = todosResultados.filter(r => r.encontrado && r.disponible === true);
            } else if (tipo === 'consultar') {
                filtrados = todosResultados.filter(r => r.encontrado && (r.disponible === 'consultar' || r.estado_dusa === 'consultar'));
            } else if (tipo === 'faltante') {
                filtrados = todosResultados.filter(r => r.encontrado && r.disponible === false);
            } else if (tipo === 'no-encontrado') {
                filtrados = todosResultados.filter(r => !r.encontrado);
            }
            
            actualizarTabla(filtrados);
        }
        
        async function detenerVerificacion() {
            await fetch('/detener', { method: 'POST' });
            clearInterval(pollingInterval);
            document.getElementById('btnDetener').classList.add('hidden');
            document.getElementById('btnIniciar').classList.remove('hidden');
        }
        
        function descargarResultado() {
            window.location.href = '/descargar';
        }
    </script>
</body>
</html>
'''

# Guardar template solo si no existe
template_path = os.path.join(TEMPLATE_DIR, 'index.html')
if not os.path.exists(template_path):
    with open(template_path, 'w') as f:
        f.write(HTML_TEMPLATE)


def abrir_navegador():
    """Abre el navegador después de un breve retraso."""
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5050')


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🏥 VERIFICADOR DUSA - Aplicación Web")
    print("="*50)
    print("\n🌐 Abriendo en el navegador...")
    print("   URL: http://127.0.0.1:5050")
    print("\n💡 Para detener: Ctrl+C")
    print("="*50 + "\n")
    
    # Abrir navegador automáticamente
    threading.Thread(target=abrir_navegador, daemon=True).start()
    
    # Iniciar servidor en puerto 5050 (5000 lo usa AirPlay en macOS)
    app.run(debug=False, port=5050, threaded=True)
