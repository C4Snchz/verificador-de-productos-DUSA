#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador DUSA - App de Escritorio
====================================
Aplicación portable que corre en la PC del usuario.
Sin necesidad de servidor externo.
"""

from flask import Flask, render_template_string, request, jsonify
import pandas as pd
import os
import time
import threading
import webbrowser
from datetime import datetime
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor
import socket

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
app.secret_key = 'verificador_dusa_local_2026'

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
    'detenido': False
}

progress_lock = threading.Lock()

# HTML de la interfaz
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verificador DUSA | Tu Planilla</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect fill='%2310B981' rx='15' width='100' height='100'/><text x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' font-size='50' font-family='system-ui' font-weight='bold' fill='white'>TP</text></svg>">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --primary: #10B981;
            --primary-dark: #059669;
            --primary-light: #D1FAE5;
            --secondary: #1F2937;
            --accent: #34D399;
            --danger: #EF4444;
            --warning: #F59E0B;
            --gray-50: #F9FAFB;
            --gray-100: #F3F4F6;
            --gray-200: #E5E7EB;
            --gray-600: #4B5563;
            --gray-900: #111827;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, var(--secondary) 0%, #374151 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        
        /* Header / Brand */
        .brand-header {
            text-align: center;
            margin-bottom: 25px;
        }
        .logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 15px;
        }
        .brand-name {
            color: white;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .brand-tagline {
            color: var(--accent);
            font-size: 14px;
            opacity: 0.9;
        }
        
        .card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            padding: 25px;
            margin-bottom: 20px;
        }
        h1 {
            color: var(--secondary);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        h2 { 
            color: var(--secondary);
            margin-bottom: 15px;
            font-size: 1.1em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .subtitle { color: var(--gray-600); margin-bottom: 20px; }
        
        /* Form */
        .form-group { margin-bottom: 15px; }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: var(--gray-900);
            font-size: 14px;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid var(--gray-200);
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s;
            background: var(--gray-50);
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: var(--primary);
            background: white;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        /* Checkbox */
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 15px;
            padding: 12px;
            background: var(--gray-50);
            border-radius: 8px;
        }
        .checkbox-group input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: var(--primary);
        }
        .checkbox-group label {
            margin: 0;
            font-size: 14px;
            color: var(--gray-600);
            cursor: pointer;
        }
        
        /* Upload zone */
        .upload-zone {
            border: 3px dashed var(--gray-200);
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: var(--gray-50);
            margin-bottom: 20px;
        }
        .upload-zone:hover, .upload-zone.dragover {
            border-color: var(--primary);
            background: var(--primary-light);
        }
        .upload-zone input { display: none; }
        .upload-zone .icon { font-size: 50px; margin-bottom: 15px; }
        
        /* Buttons */
        .btn {
            padding: 14px 30px;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
        }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-dark); transform: translateY(-1px); }
        .btn-primary:disabled { background: var(--gray-200); color: var(--gray-600); cursor: not-allowed; transform: none; }
        .btn-danger { background: var(--danger); color: white; }
        .btn-danger:hover { background: #DC2626; }
        .btn-success { background: var(--primary); color: white; }
        .btn-secondary { background: var(--gray-600); color: white; }
        
        /* Progress */
        .progress-container { margin: 20px 0; }
        .progress-bar {
            height: 30px;
            background: var(--gray-100);
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--accent));
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .progress-stats {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            color: var(--gray-600);
            font-size: 13px;
        }
        
        /* Status */
        .status-message {
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            text-align: center;
            font-weight: 500;
        }
        .status-info { background: #ECFDF5; color: var(--primary-dark); }
        .status-success { background: #D1FAE5; color: #065F46; }
        .status-error { background: #FEE2E2; color: #991B1B; }
        
        /* Summary */
        .summary {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
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
        .summary-card .label { color: #666; font-size: 14px; }
        .summary-card.total .number { color: var(--secondary); }
        .summary-card.disponible .number { color: var(--primary); }
        .summary-card.agotado .number { color: var(--danger); }
        .summary-card.no-encontrado .number { color: var(--gray-600); }
        
        /* Results table */
        .results-container {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 8px;
            margin-top: 15px;
        }
        .results-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .results-table th, .results-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .results-table th {
            background: #f5f5f5;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        
        /* Badges */
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-secondary { background: #e9ecef; color: #495057; }
        
        /* File info */
        .file-info {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 15px;
            background: var(--primary-light);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .file-info .name { font-weight: 600; color: var(--primary-dark); }
        .file-info .count { color: var(--gray-600); }
        
        .hidden { display: none !important; }
        
        /* Speed selector */
        .speed-info {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Brand Header -->
        <div class="brand-header">
            <svg class="logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <rect fill="#10B981" rx="20" width="100" height="100"/>
                <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-size="45" font-family="system-ui" font-weight="bold" fill="white">TP</text>
            </svg>
            <div class="brand-name">Tu Planilla</div>
            <div class="brand-tagline">Verificador de Productos DUSA</div>
        </div>
        
        <!-- Login Form -->
        <div class="card" id="login-section">
            <h2>🔐 Credenciales DUSA</h2>
            <form id="config-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>Usuario</label>
                        <input type="text" id="usuario" placeholder="tu.usuario" required>
                    </div>
                    <div class="form-group">
                        <label>Contraseña</label>
                        <input type="password" id="password" placeholder="••••••••" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Código Cliente (PIN)</label>
                        <input type="text" id="cliente" placeholder="1234" required>
                    </div>
                    <div class="form-group">
                        <label>Velocidad</label>
                        <select id="ventanas">
                            <option value="1">🐢 Lento (1 ventana)</option>
                            <option value="2">🚶 Normal (2 ventanas)</option>
                            <option value="3" selected>🚗 Rápido (3 ventanas)</option>
                            <option value="4">🚀 Muy rápido (4 ventanas)</option>
                            <option value="6">⚡ Ultra rápido (6 ventanas)</option>
                        </select>
                        <div class="speed-info">Más ventanas = más rápido pero usa más RAM</div>
                    </div>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" id="recordar" checked>
                    <label for="recordar">Recordar mis credenciales en este equipo</label>
                </div>
            </form>
        </div>
        
        <!-- Upload Section -->
        <div class="card" id="upload-section">
            <h2>📁 Archivo Excel</h2>
            <div class="upload-zone" id="upload-zone">
                <input type="file" id="file-input" accept=".xlsx,.xls">
                <div class="icon">📄</div>
                <p>Arrastra tu archivo Excel aquí</p>
                <p style="color: #999; font-size: 14px;">o haz clic para seleccionar</p>
            </div>
            <div id="file-info" class="file-info hidden">
                <div>
                    <span class="name" id="file-name"></span>
                    <span class="count" id="file-count"></span>
                </div>
                <button onclick="clearFile()" style="background: none; border: none; cursor: pointer; font-size: 20px;">❌</button>
            </div>
            <button class="btn btn-primary" id="btn-start" onclick="startVerification()" disabled>
                🚀 Iniciar Verificación
            </button>
        </div>
        
        <!-- Progress Section -->
        <div class="card hidden" id="progress-section">
            <h2>⏳ Procesando...</h2>
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%">0%</div>
                </div>
                <div class="progress-stats">
                    <span id="progress-text">0 / 0 productos</span>
                    <span id="progress-speed">0 prod/min</span>
                    <span id="progress-time">Tiempo restante: calculando...</span>
                </div>
            </div>
            <div id="status-message" class="status-message status-info">
                Iniciando verificación...
            </div>
            <button class="btn btn-danger" id="btn-stop" onclick="stopVerification()" style="margin-top: 15px;">
                ⏹️ Detener
            </button>
        </div>
        
        <!-- Results Section -->
        <div class="card hidden" id="results-section">
            <h2>📊 Resultados</h2>
            <div class="summary" id="summary">
                <div class="summary-card total">
                    <div class="number" id="count-total">0</div>
                    <div class="label">Total</div>
                </div>
                <div class="summary-card disponible">
                    <div class="number" id="count-disponible">0</div>
                    <div class="label">Disponibles</div>
                </div>
                <div class="summary-card agotado">
                    <div class="number" id="count-agotado">0</div>
                    <div class="label">Agotados</div>
                </div>
                <div class="summary-card no-encontrado">
                    <div class="number" id="count-noencontrado">0</div>
                    <div class="label">No encontrados</div>
                </div>
            </div>
            <button class="btn btn-success" onclick="downloadResults()">
                📥 Descargar Excel
            </button>
            <button class="btn btn-secondary" onclick="resetApp()" style="margin-top: 10px;">
                🔄 Nueva Verificación
            </button>
            <div class="results-container">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Producto</th>
                            <th>Stock</th>
                            <th>Precio</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody id="results-body"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        let productos = [];
        let fileName = '';
        let pollingInterval = null;
        
        // Cargar credenciales guardadas
        window.onload = function() {
            const saved = localStorage.getItem('tuplanilla_dusa_creds');
            if (saved) {
                try {
                    const creds = JSON.parse(saved);
                    document.getElementById('usuario').value = creds.usuario || '';
                    document.getElementById('password').value = creds.password || '';
                    document.getElementById('cliente').value = creds.cliente || '';
                    document.getElementById('ventanas').value = creds.ventanas || '3';
                } catch(e) {}
            }
        };
        
        // Guardar credenciales
        function saveCredentials() {
            if (document.getElementById('recordar').checked) {
                const creds = {
                    usuario: document.getElementById('usuario').value,
                    password: document.getElementById('password').value,
                    cliente: document.getElementById('cliente').value,
                    ventanas: document.getElementById('ventanas').value
                };
                localStorage.setItem('tuplanilla_dusa_creds', JSON.stringify(creds));
            } else {
                localStorage.removeItem('tuplanilla_dusa_creds');
            }
        }
        
        // Upload zone events
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        
        uploadZone.onclick = () => fileInput.click();
        fileInput.onchange = (e) => handleFile(e.target.files[0]);
        
        uploadZone.ondragover = (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); };
        uploadZone.ondragleave = (e) => { e.preventDefault(); uploadZone.classList.remove('dragover'); };
        uploadZone.ondrop = (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            handleFile(e.dataTransfer.files[0]);
        };
        
        async function handleFile(file) {
            if (!file) return;
            
            const formData = new FormData();
            formData.append('archivo', file);
            
            try {
                const response = await fetch('/subir', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.success) {
                    fileName = data.archivo;
                    productos = data.productos;
                    
                    document.getElementById('upload-zone').classList.add('hidden');
                    document.getElementById('file-info').classList.remove('hidden');
                    document.getElementById('file-name').textContent = file.name;
                    document.getElementById('file-count').textContent = ` - ${productos.length} productos`;
                    document.getElementById('btn-start').disabled = false;
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error subiendo archivo: ' + error.message);
            }
        }
        
        function clearFile() {
            productos = [];
            fileName = '';
            document.getElementById('upload-zone').classList.remove('hidden');
            document.getElementById('file-info').classList.add('hidden');
            document.getElementById('btn-start').disabled = true;
            fileInput.value = '';
        }
        
        async function startVerification() {
            const usuario = document.getElementById('usuario').value;
            const password = document.getElementById('password').value;
            const cliente = document.getElementById('cliente').value;
            const ventanas = document.getElementById('ventanas').value;
            
            if (!usuario || !password || !cliente) {
                alert('Por favor completa todos los campos de credenciales');
                return;
            }
            
            if (productos.length === 0) {
                alert('Por favor sube un archivo Excel con códigos de productos');
                return;
            }
            
            // Guardar credenciales si está marcado
            saveCredentials();
            
            // Mostrar sección de progreso
            document.getElementById('login-section').classList.add('hidden');
            document.getElementById('upload-section').classList.add('hidden');
            document.getElementById('progress-section').classList.remove('hidden');
            document.getElementById('results-section').classList.remove('hidden');
            document.getElementById('results-body').innerHTML = '';
            
            try {
                const response = await fetch('/iniciar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        usuario, password, cliente, ventanas: parseInt(ventanas),
                        productos: productos
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    startPolling();
                } else {
                    alert('Error: ' + data.error);
                    resetApp();
                }
            } catch (error) {
                alert('Error: ' + error.message);
                resetApp();
            }
        }
        
        function startPolling() {
            pollingInterval = setInterval(async () => {
                try {
                    const response = await fetch('/estado');
                    const data = await response.json();
                    
                    updateProgress(data);
                    updateResults(data.resultados || []);
                    
                    if (!data.procesando) {
                        stopPolling();
                        document.getElementById('btn-stop').classList.add('hidden');
                        document.getElementById('status-message').textContent = '✅ Verificación completada';
                        document.getElementById('status-message').className = 'status-message status-success';
                    }
                } catch (error) {
                    console.error('Error polling:', error);
                }
            }, 500);
        }
        
        function stopPolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
        }
        
        function updateProgress(data) {
            const percent = data.total > 0 ? Math.round((data.progreso / data.total) * 100) : 0;
            document.getElementById('progress-fill').style.width = percent + '%';
            document.getElementById('progress-fill').textContent = percent + '%';
            document.getElementById('progress-text').textContent = `${data.progreso} / ${data.total} productos`;
            document.getElementById('progress-speed').textContent = `${data.velocidad.toFixed(1)} prod/min`;
            
            if (data.velocidad > 0 && data.total > data.progreso) {
                const remaining = (data.total - data.progreso) / data.velocidad;
                document.getElementById('progress-time').textContent = `~${Math.ceil(remaining)} min restantes`;
            }
            
            document.getElementById('status-message').textContent = data.mensaje || 'Procesando...';
        }
        
        function updateResults(resultados) {
            // Contadores
            const total = resultados.length;
            const disponibles = resultados.filter(r => r.estado === 'disponible').length;
            const agotados = resultados.filter(r => r.estado === 'agotado').length;
            const noEncontrados = resultados.filter(r => r.estado === 'no_encontrado' || r.estado === 'error').length;
            
            document.getElementById('count-total').textContent = total;
            document.getElementById('count-disponible').textContent = disponibles;
            document.getElementById('count-agotado').textContent = agotados;
            document.getElementById('count-noencontrado').textContent = noEncontrados;
            
            // Tabla (últimos 50)
            const tbody = document.getElementById('results-body');
            tbody.innerHTML = resultados.slice(-50).map(r => {
                let badge = 'badge-secondary';
                let estado = 'No encontrado';
                if (r.estado === 'disponible') { badge = 'badge-success'; estado = 'Disponible'; }
                else if (r.estado === 'agotado') { badge = 'badge-danger'; estado = 'Agotado'; }
                
                return `<tr>
                    <td>${r.codigo}</td>
                    <td>${(r.nombre || '-').substring(0, 30)}</td>
                    <td>${r.stock || '-'}</td>
                    <td>${r.precio || '-'}</td>
                    <td><span class="badge ${badge}">${estado}</span></td>
                </tr>`;
            }).join('');
        }
        
        async function stopVerification() {
            try {
                await fetch('/detener', { method: 'POST' });
                stopPolling();
            } catch (error) {
                console.error('Error stopping:', error);
            }
        }
        
        async function downloadResults() {
            window.location.href = '/descargar';
        }
        
        function resetApp() {
            stopPolling();
            clearFile();
            document.getElementById('login-section').classList.remove('hidden');
            document.getElementById('upload-section').classList.remove('hidden');
            document.getElementById('progress-section').classList.add('hidden');
            document.getElementById('results-section').classList.add('hidden');
            document.getElementById('btn-stop').classList.remove('hidden');
            document.getElementById('progress-fill').style.width = '0%';
            document.getElementById('status-message').className = 'status-message status-info';
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/subir', methods=['POST'])
def subir_archivo():
    """Recibe el archivo Excel."""
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    
    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'No se seleccionó archivo'}), 400
    
    try:
        df = pd.read_excel(archivo)
        
        # Buscar códigos de productos en todas las columnas
        productos = []
        
        for col in df.columns:
            for val in df[col].dropna():
                # Convertir a string y limpiar
                val_str = str(val).strip()
                
                # Si es float (ej: 7790001234567.0), convertir a entero
                try:
                    if '.' in val_str and val_str.replace('.', '').replace('-', '').isdigit():
                        val_str = str(int(float(val_str)))
                except:
                    pass
                
                # Limpiar caracteres especiales
                val_clean = val_str.replace(' ', '').replace('-', '').replace('.', '')
                
                # Verificar si es un código válido (solo números, 4-14 dígitos)
                if val_clean.isdigit() and 4 <= len(val_clean) <= 14:
                    productos.append(val_clean)
        
        # Eliminar duplicados y ordenar
        productos = sorted(list(set(productos)))
        
        return jsonify({
            'success': True,
            'archivo': archivo.filename,
            'productos': productos,
            'total_filas': len(df)
        })
    except Exception as e:
        return jsonify({'error': f'Error leyendo archivo: {str(e)}'}), 400


@app.route('/iniciar', methods=['POST'])
def iniciar_verificacion():
    """Inicia la verificación."""
    global estado
    
    data = request.json
    
    with progress_lock:
        estado = {
            'procesando': True,
            'progreso': 0,
            'total': len(data['productos']),
            'mensaje': 'Iniciando...',
            'resultados': [],
            'tiempo_inicio': time.time(),
            'velocidad': 0,
            'ventanas_activas': 0,
            'detenido': False
        }
    
    # Iniciar en thread separado
    thread = threading.Thread(
        target=procesar_verificacion,
        args=(data['usuario'], data['password'], data['cliente'], 
              data['productos'], data['ventanas'])
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True})


@app.route('/estado')
def obtener_estado():
    """Retorna el estado actual."""
    with progress_lock:
        return jsonify(estado)


@app.route('/detener', methods=['POST'])
def detener():
    """Detiene la verificación."""
    global estado
    with progress_lock:
        estado['detenido'] = True
        estado['procesando'] = False
        estado['mensaje'] = 'Detenido por el usuario'
    return jsonify({'success': True})


@app.route('/descargar')
def descargar():
    """Descarga los resultados como Excel."""
    with progress_lock:
        resultados = estado.get('resultados', [])
    
    if not resultados:
        return "No hay resultados", 404
    
    df = pd.DataFrame(resultados)
    
    filename = f'verificacion_dusa_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    filepath = os.path.join('/tmp', filename)
    
    df.to_excel(filepath, index=False)
    
    from flask import send_file
    return send_file(filepath, as_attachment=True, download_name=filename)


def procesar_verificacion(usuario, password, cliente, productos, num_ventanas):
    """Procesa la verificación con múltiples ventanas."""
    global estado
    
    drivers = []
    
    try:
        with progress_lock:
            estado['mensaje'] = f'Abriendo {num_ventanas} ventana(s)...'
        
        # Crear drivers
        for i in range(num_ventanas):
            driver = crear_driver()
            if login_dusa(driver, usuario, password, cliente):
                drivers.append(driver)
                with progress_lock:
                    estado['ventanas_activas'] = len(drivers)
                    estado['mensaje'] = f'Ventana {i+1}/{num_ventanas} conectada'
            else:
                driver.quit()
        
        if not drivers:
            with progress_lock:
                estado['procesando'] = False
                estado['mensaje'] = 'Error: No se pudo conectar a DUSA'
            return
        
        with progress_lock:
            estado['mensaje'] = f'Verificando con {len(drivers)} ventana(s)...'
        
        # Procesar en paralelo
        productos_pendientes = list(productos)
        productos_lock = threading.Lock()
        
        def worker(driver):
            while True:
                with progress_lock:
                    if estado['detenido']:
                        return
                
                with productos_lock:
                    if not productos_pendientes:
                        return
                    codigo = productos_pendientes.pop(0)
                
                resultado = buscar_producto(driver, codigo)
                
                with progress_lock:
                    estado['resultados'].append(resultado)
                    estado['progreso'] = len(estado['resultados'])
                    
                    # Calcular velocidad
                    elapsed = time.time() - estado['tiempo_inicio']
                    if elapsed > 0:
                        estado['velocidad'] = (estado['progreso'] / elapsed) * 60
                    
                    estado['mensaje'] = f'Verificando: {codigo}'
        
        # Ejecutar workers
        with ThreadPoolExecutor(max_workers=len(drivers)) as executor:
            futures = [executor.submit(worker, d) for d in drivers]
            for f in futures:
                f.result()
        
        with progress_lock:
            estado['procesando'] = False
            estado['mensaje'] = 'Verificación completada'
            
    finally:
        # Cerrar drivers
        for d in drivers:
            try:
                d.quit()
            except:
                pass


def crear_driver():
    """Crea un driver de Chrome."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-images")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    
    return driver


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
        
        boton = driver.find_element(By.CSS_SELECTOR, ".v-button, button")
        boton.click()
        
        time.sleep(4)
        
        # Ir a productos
        driver.get("https://pedidos.dusa.com.uy/DUSAWebUI#!micuenta/productos")
        time.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"Error login: {e}")
        return False


def buscar_producto(driver, codigo):
    """Busca un producto en DUSA."""
    try:
        # Buscar campo
        driver.execute_script("""
            var inputs = document.querySelectorAll('input.v-textfield, input[type="text"]');
            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].offsetParent !== null) {
                    inputs[i].value = arguments[0];
                    inputs[i].dispatchEvent(new Event('input', {bubbles: true}));
                    inputs[i].dispatchEvent(new Event('change', {bubbles: true}));
                    inputs[i].dispatchEvent(new KeyboardEvent('keydown', {
                        key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
                    }));
                    break;
                }
            }
        """, codigo)
        
        time.sleep(1.5)
        
        # Leer resultado
        body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
        
        resultado = {
            'codigo': codigo,
            'estado': 'no_encontrado',
            'nombre': '',
            'stock': '-',
            'precio': '-'
        }
        
        try:
            tablas = driver.find_elements(By.CSS_SELECTOR, '.v-table-body tr, table tbody tr')
            if tablas:
                texto = tablas[0].text
                resultado['nombre'] = texto[:50] if texto else ''
                
                if 'agotado' in texto.lower() or 'sin stock' in texto.lower():
                    resultado['estado'] = 'agotado'
                elif len(texto) > 5:
                    resultado['estado'] = 'disponible'
        except:
            pass
        
        if 'no se encontr' in body_text or 'sin resultado' in body_text:
            resultado['estado'] = 'no_encontrado'
        
        return resultado
        
    except Exception as e:
        return {
            'codigo': codigo,
            'estado': 'error',
            'mensaje': str(e)
        }


def find_free_port():
    """Encuentra un puerto libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


if __name__ == '__main__':
    port = find_free_port()
    url = f'http://127.0.0.1:{port}'
    
    print("=" * 50)
    print("🔍 VERIFICADOR DUSA - App de Escritorio")
    print("=" * 50)
    print(f"\n✅ Abriendo en: {url}")
    print("\n⚠️  No cierres esta ventana mientras usas la app")
    print("   Presiona Ctrl+C para cerrar\n")
    
    # Abrir navegador
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    
    # Iniciar servidor
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
