#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador DUSA - TuPlanilla Edition
=====================================
App de escritorio empaquetable para Windows y Mac.
Con telemetría, auto-update y verificación de productos.
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import pandas as pd
import os
import sys
import time
import threading
import webbrowser
import atexit
import signal
import socket
from datetime import datetime
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Telemetría
from telemetria import init_telemetria, check_for_updates, VERSION_APP

app = Flask(__name__)
app.secret_key = 'verificador_dusa_tuplanilla_2026'
UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), '.verificador_dusa', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Estado global
estado = {
    'procesando': False,
    'progreso': 0,
    'total': 0,
    'mensaje': '',
    'resultados': [],
    'tiempo_inicio': None,
    'velocidad': 0,
    'ventanas_activas': 0,
    'detenido': False,
    'archivo_resultado': None,
    'update_info': None
}

progress_lock = threading.Lock()
active_drivers = []
drivers_lock = threading.Lock()
telemetria = None


def cleanup_drivers():
    """Cierra todos los drivers activos de forma segura."""
    global active_drivers
    with drivers_lock:
        for driver in active_drivers:
            try:
                driver.quit()
            except:
                pass
        active_drivers.clear()


def cleanup_all():
    """Limpieza completa al cerrar la aplicación."""
    global telemetria
    print("\n🧹 Limpiando recursos...")
    cleanup_drivers()
    
    # Enviar evento de cierre
    if telemetria:
        telemetria.registrar_cierre()
    
    print("✅ Recursos liberados")


atexit.register(cleanup_all)


def signal_handler(signum, frame):
    print(f"\n⚠️ Señal {signum} recibida, cerrando...")
    cleanup_all()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# HTML de la aplicación
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verificador DUSA - TuPlanilla</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
            margin-bottom: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h1 { color: #667eea; display: flex; align-items: center; gap: 10px; }
        .version { 
            background: #f0f0f0; 
            padding: 4px 12px; 
            border-radius: 20px; 
            font-size: 12px;
            color: #666;
        }
        .update-badge {
            background: #ff6b6b;
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
        }
        
        /* Credenciales */
        .credentials {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .credentials label { display: block; margin-bottom: 5px; font-weight: 500; color: #333; }
        .credentials input {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }
        .credentials input:focus { border-color: #667eea; outline: none; }
        
        /* Upload */
        .upload-zone {
            border: 3px dashed #ccc;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #fafafa;
            margin-bottom: 20px;
        }
        .upload-zone:hover { border-color: #667eea; background: #f0f4ff; }
        .upload-zone input { display: none; }
        .upload-zone .icon { font-size: 48px; margin-bottom: 10px; }
        
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
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5a6fd6; }
        .btn-primary:disabled { background: #ccc; cursor: not-allowed; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        
        /* Progress */
        .progress-container { margin: 20px 0; }
        .progress-bar {
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .status { margin-top: 10px; color: #666; }
        
        /* Results */
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 13px;
        }
        .results-table th, .results-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .results-table th { background: #f5f5f5; font-weight: 600; position: sticky; top: 0; }
        .table-container { max-height: 400px; overflow-y: auto; border-radius: 8px; border: 1px solid #eee; }
        
        /* Badges */
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .badge-warning { background: #fff3cd; color: #856404; }
        
        .hidden { display: none !important; }
        .powered-by {
            text-align: center;
            margin-top: 20px;
            color: rgba(255,255,255,0.7);
            font-size: 14px;
        }
        .powered-by a { color: white; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <h1>🔍 Verificador DUSA</h1>
                <div>
                    <span class="version">v{{ version }}</span>
                    {% if update_available %}
                    <a href="{{ download_url }}" class="update-badge">⬆️ Actualizar a v{{ latest_version }}</a>
                    {% endif %}
                </div>
            </div>
            
            <h3 style="margin-bottom: 15px;">🔐 Credenciales DUSA</h3>
            <div class="credentials">
                <div>
                    <label>Usuario</label>
                    <input type="text" id="usuario" placeholder="tu_usuario">
                </div>
                <div>
                    <label>Contraseña</label>
                    <input type="password" id="password" placeholder="••••••••">
                </div>
                <div>
                    <label>Código Cliente</label>
                    <input type="text" id="cliente" placeholder="1234">
                </div>
            </div>
            
            <h3 style="margin-bottom: 15px;">📁 Archivo Excel de Mercado Libre</h3>
            <div class="upload-zone" id="upload-zone" onclick="document.getElementById('file-input').click()">
                <input type="file" id="file-input" accept=".xlsx,.xls">
                <div class="icon">📊</div>
                <p>Arrastra tu Excel aquí o haz clic para seleccionar</p>
            </div>
            <div id="file-info" class="hidden" style="margin-bottom: 20px; padding: 10px; background: #f0f4ff; border-radius: 8px;">
                <span id="file-name"></span>
                <button onclick="clearFile()" style="float: right; background: none; border: none; cursor: pointer;">❌</button>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <button class="btn btn-primary" id="btn-start" onclick="iniciarVerificacion()" disabled>
                    ▶️ Iniciar Verificación
                </button>
                <button class="btn btn-danger hidden" id="btn-stop" onclick="detenerVerificacion()">
                    ⏹️ Detener
                </button>
            </div>
            
            <div id="progress-section" class="hidden progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%">0%</div>
                </div>
                <p class="status" id="status-text">Preparando...</p>
            </div>
        </div>
        
        <div class="card hidden" id="results-section">
            <h2 style="margin-bottom: 15px;">📊 Resultados</h2>
            <div id="summary" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px;"></div>
            <button class="btn btn-success" onclick="descargarResultados()">📥 Descargar Excel</button>
            <div class="table-container" style="margin-top: 15px;">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>Producto</th>
                            <th>Estado DUSA</th>
                            <th>Precio DUSA</th>
                            <th>Observación</th>
                        </tr>
                    </thead>
                    <tbody id="results-body"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <p class="powered-by">
        Powered by <a href="https://tuplanilla.net" target="_blank">TuPlanilla.net</a>
    </p>
    
    <script>
        let selectedFile = null;
        let pollingInterval = null;
        
        // Upload handlers
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        
        uploadZone.addEventListener('dragover', e => {
            e.preventDefault();
            uploadZone.style.borderColor = '#667eea';
        });
        
        uploadZone.addEventListener('dragleave', e => {
            uploadZone.style.borderColor = '#ccc';
        });
        
        uploadZone.addEventListener('drop', e => {
            e.preventDefault();
            uploadZone.style.borderColor = '#ccc';
            if (e.dataTransfer.files.length) {
                handleFile(e.dataTransfer.files[0]);
            }
        });
        
        fileInput.addEventListener('change', e => {
            if (e.target.files.length) {
                handleFile(e.target.files[0]);
            }
        });
        
        function handleFile(file) {
            if (!file.name.match(/\\.xlsx?$/i)) {
                alert('Por favor selecciona un archivo Excel (.xlsx o .xls)');
                return;
            }
            selectedFile = file;
            document.getElementById('file-name').textContent = `📄 ${file.name}`;
            document.getElementById('file-info').classList.remove('hidden');
            document.getElementById('upload-zone').classList.add('hidden');
            document.getElementById('btn-start').disabled = false;
        }
        
        function clearFile() {
            selectedFile = null;
            document.getElementById('file-info').classList.add('hidden');
            document.getElementById('upload-zone').classList.remove('hidden');
            document.getElementById('btn-start').disabled = true;
            fileInput.value = '';
        }
        
        async function iniciarVerificacion() {
            const usuario = document.getElementById('usuario').value;
            const password = document.getElementById('password').value;
            const cliente = document.getElementById('cliente').value;
            
            if (!usuario || !password || !cliente) {
                alert('Por favor completa las credenciales de DUSA');
                return;
            }
            
            if (!selectedFile) {
                alert('Por favor selecciona un archivo Excel');
                return;
            }
            
            // Subir archivo y comenzar
            const formData = new FormData();
            formData.append('archivo', selectedFile);
            formData.append('usuario', usuario);
            formData.append('password', password);
            formData.append('cliente', cliente);
            
            document.getElementById('btn-start').classList.add('hidden');
            document.getElementById('btn-stop').classList.remove('hidden');
            document.getElementById('progress-section').classList.remove('hidden');
            document.getElementById('results-section').classList.add('hidden');
            
            try {
                const response = await fetch('/iniciar', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (data.error) {
                    alert(data.error);
                    resetUI();
                    return;
                }
                
                // Iniciar polling de progreso
                pollingInterval = setInterval(actualizarProgreso, 1000);
                
            } catch (error) {
                alert('Error al iniciar: ' + error.message);
                resetUI();
            }
        }
        
        async function actualizarProgreso() {
            try {
                const response = await fetch('/progreso');
                const data = await response.json();
                
                const percent = data.total > 0 ? Math.round((data.progreso / data.total) * 100) : 0;
                document.getElementById('progress-fill').style.width = percent + '%';
                document.getElementById('progress-fill').textContent = percent + '%';
                document.getElementById('status-text').textContent = data.mensaje;
                
                if (!data.procesando && data.progreso > 0) {
                    clearInterval(pollingInterval);
                    mostrarResultados(data.resultados);
                }
            } catch (error) {
                console.error('Error polling:', error);
            }
        }
        
        function mostrarResultados(resultados) {
            resetUI();
            document.getElementById('results-section').classList.remove('hidden');
            
            // Contar estados
            let disponible = 0, noDisponible = 0, noEncontrado = 0;
            resultados.forEach(r => {
                if (r.disponible === 'Sí') disponible++;
                else if (r.disponible === 'No') noDisponible++;
                else noEncontrado++;
            });
            
            document.getElementById('summary').innerHTML = `
                <div style="background:#d4edda;padding:15px;border-radius:8px;text-align:center;">
                    <div style="font-size:24px;font-weight:bold;color:#155724;">${disponible}</div>
                    <div style="color:#155724;">Disponibles</div>
                </div>
                <div style="background:#fff3cd;padding:15px;border-radius:8px;text-align:center;">
                    <div style="font-size:24px;font-weight:bold;color:#856404;">${noDisponible}</div>
                    <div style="color:#856404;">No disponibles</div>
                </div>
                <div style="background:#e2e3e5;padding:15px;border-radius:8px;text-align:center;">
                    <div style="font-size:24px;font-weight:bold;color:#383d41;">${noEncontrado}</div>
                    <div style="color:#383d41;">No encontrados</div>
                </div>
                <div style="background:#cce5ff;padding:15px;border-radius:8px;text-align:center;">
                    <div style="font-size:24px;font-weight:bold;color:#004085;">${resultados.length}</div>
                    <div style="color:#004085;">Total</div>
                </div>
            `;
            
            // Tabla
            const tbody = document.getElementById('results-body');
            tbody.innerHTML = resultados.map(r => `
                <tr>
                    <td>${r.sku || '-'}</td>
                    <td>${r.titulo || '-'}</td>
                    <td><span class="badge ${r.disponible === 'Sí' ? 'badge-success' : r.disponible === 'No' ? 'badge-warning' : 'badge-danger'}">${r.disponible}</span></td>
                    <td>${r.precio_dusa || '-'}</td>
                    <td>${r.observacion || '-'}</td>
                </tr>
            `).join('');
        }
        
        async function detenerVerificacion() {
            await fetch('/detener', { method: 'POST' });
            clearInterval(pollingInterval);
            resetUI();
        }
        
        function resetUI() {
            document.getElementById('btn-start').classList.remove('hidden');
            document.getElementById('btn-stop').classList.add('hidden');
            document.getElementById('progress-section').classList.add('hidden');
        }
        
        function descargarResultados() {
            window.location.href = '/descargar';
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    """Página principal."""
    update_info = estado.get('update_info') or {}
    return render_template_string(
        HTML_TEMPLATE,
        version=VERSION_APP,
        update_available=update_info.get('update_available', False),
        latest_version=update_info.get('latest_version', VERSION_APP),
        download_url=update_info.get('download_url', '#')
    )


@app.route('/iniciar', methods=['POST'])
def iniciar():
    """Inicia la verificación."""
    global telemetria
    
    if estado['procesando']:
        return jsonify({'error': 'Ya hay una verificación en proceso'}), 400
    
    archivo = request.files.get('archivo')
    usuario = request.form.get('usuario')
    password = request.form.get('password')
    cliente = request.form.get('cliente')
    
    if not all([archivo, usuario, password, cliente]):
        return jsonify({'error': 'Faltan datos requeridos'}), 400
    
    # Guardar archivo
    filename = secure_filename(archivo.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    archivo.save(filepath)
    
    # Iniciar telemetría
    telemetria = init_telemetria(usuario, cliente)
    telemetria.registrar_inicio()
    telemetria.registrar_login(usuario, cliente)
    
    # Iniciar verificación en background
    thread = threading.Thread(
        target=procesar_verificacion,
        args=(filepath, usuario, password, cliente)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started'})


@app.route('/progreso')
def progreso():
    """Retorna el progreso actual."""
    return jsonify(estado)


@app.route('/detener', methods=['POST'])
def detener():
    """Detiene la verificación."""
    estado['detenido'] = True
    cleanup_drivers()
    return jsonify({'status': 'stopped'})


@app.route('/descargar')
def descargar():
    """Descarga el archivo de resultados."""
    if estado['archivo_resultado'] and os.path.exists(estado['archivo_resultado']):
        return send_file(estado['archivo_resultado'], as_attachment=True)
    return jsonify({'error': 'No hay archivo disponible'}), 404


def procesar_verificacion(filepath, usuario, password, cliente):
    """Procesa la verificación en background."""
    global telemetria
    
    estado['procesando'] = True
    estado['detenido'] = False
    estado['progreso'] = 0
    estado['resultados'] = []
    estado['mensaje'] = 'Cargando archivo Excel...'
    estado['tiempo_inicio'] = time.time()
    
    try:
        # Cargar Excel (especificar engine para evitar errores)
        df = pd.read_excel(filepath, engine='openpyxl')
        estado['total'] = len(df)
        
        # Iniciar navegador
        estado['mensaje'] = 'Iniciando navegador...'
        driver = crear_driver()
        
        with drivers_lock:
            active_drivers.append(driver)
        
        # Login en DUSA
        estado['mensaje'] = 'Iniciando sesión en DUSA...'
        if not login_dusa(driver, usuario, password, cliente):
            estado['mensaje'] = 'Error: No se pudo iniciar sesión en DUSA'
            estado['procesando'] = False
            return
        
        # Ir a productos
        driver.get("https://pedidos.dusa.com.uy/DUSAWebUI#!micuenta/productos")
        time.sleep(3)
        
        # Procesar cada producto
        for idx, row in df.iterrows():
            if estado['detenido']:
                break
            
            sku = str(row.get('SKU', row.get('sku', '')))
            titulo = str(row.get('Título', row.get('titulo', row.get('Nombre', ''))))
            
            estado['mensaje'] = f'Verificando: {sku or titulo[:30]}...'
            
            resultado = verificar_producto(driver, sku, titulo)
            resultado['sku'] = sku
            resultado['titulo'] = titulo
            
            estado['resultados'].append(resultado)
            estado['progreso'] = idx + 1
        
        # Guardar resultados
        estado['mensaje'] = 'Generando Excel de resultados...'
        output_file = os.path.join(
            UPLOAD_FOLDER,
            f'verificacion_dusa_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
        df_resultados = pd.DataFrame(estado['resultados'])
        df_resultados.to_excel(output_file, index=False)
        estado['archivo_resultado'] = output_file
        
        # Registrar telemetría
        tiempo_total = time.time() - estado['tiempo_inicio']
        if telemetria:
            telemetria.registrar_verificacion(len(estado['resultados']), tiempo_total)
        
        estado['mensaje'] = f'✅ Completado: {len(estado["resultados"])} productos verificados'
        
    except Exception as e:
        estado['mensaje'] = f'Error: {str(e)}'
    finally:
        estado['procesando'] = False
        cleanup_drivers()


def crear_driver():
    """Crea una instancia de Chrome."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def login_dusa(driver, usuario, password, cliente):
    """Hace login en DUSA."""
    try:
        driver.get("https://pedidos.dusa.com.uy/DUSAWebUI")
        time.sleep(3)
        
        campos = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        if campos:
            campos[0].send_keys(usuario)
        
        campo_pass = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        campo_pass.send_keys(password)
        
        for campo in campos[1:]:
            if campo.get_attribute('type') == 'text':
                campo.send_keys(cliente)
                break
        
        time.sleep(1)
        
        boton = driver.find_element(By.CSS_SELECTOR, ".v-button, button")
        boton.click()
        
        time.sleep(4)
        return True
        
    except Exception as e:
        print(f"Error login: {e}")
        return False


def verificar_producto(driver, sku, titulo):
    """Verifica un producto en DUSA."""
    resultado = {
        'encontrado': 'No',
        'disponible': 'No encontrado',
        'precio_dusa': '',
        'observacion': ''
    }
    
    try:
        # Buscar campo de búsqueda
        campo = driver.find_element(By.CSS_SELECTOR, "input.v-textfield")
        campo.clear()
        campo.send_keys(sku if sku else titulo[:20])
        campo.send_keys(Keys.RETURN)
        
        time.sleep(2)
        
        # Buscar resultados
        filas = driver.find_elements(By.CSS_SELECTOR, ".v-table-row, tr.v-table-row")
        
        if filas:
            resultado['encontrado'] = 'Sí'
            
            # Intentar extraer disponibilidad y precio
            try:
                celdas = filas[0].find_elements(By.TAG_NAME, "td")
                if len(celdas) >= 3:
                    resultado['disponible'] = 'Sí'
                    resultado['precio_dusa'] = celdas[-1].text
            except:
                resultado['disponible'] = 'Ver en DUSA'
        else:
            resultado['observacion'] = 'Producto no encontrado en DUSA'
    
    except Exception as e:
        resultado['observacion'] = f'Error: {str(e)[:50]}'
    
    return resultado


def find_free_port():
    """Encuentra un puerto libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def main():
    """Punto de entrada principal."""
    global telemetria
    
    print("=" * 50)
    print("🔍 Verificador DUSA - TuPlanilla Edition")
    print(f"   Versión: {VERSION_APP}")
    print("=" * 50)
    
    # Verificar actualizaciones
    print("\n🔄 Verificando actualizaciones...")
    estado['update_info'] = check_for_updates()
    
    if estado['update_info'].get('update_available'):
        print(f"   ⬆️ Nueva versión disponible: {estado['update_info']['latest_version']}")
    else:
        print("   ✅ Estás usando la última versión")
    
    # Encontrar puerto libre
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    
    print(f"\n🌐 Iniciando servidor en {url}")
    print("   (Se abrirá automáticamente en tu navegador)")
    
    # Abrir navegador después de un pequeño delay
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    
    # Iniciar servidor
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
