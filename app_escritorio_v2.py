#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador DUSA - App de Escritorio Tu Planilla
=================================================
Aplicación portable que corre en la PC del usuario.
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import pandas as pd
import os
import time
import threading
import webbrowser
from datetime import datetime
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor
import socket
import signal
import sys
import atexit
import subprocess

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
app.secret_key = 'verificador_dusa_tuplanilla_2026'
UPLOAD_FOLDER = '/tmp/verificador_dusa'
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
    'archivo_resultado': None
}

progress_lock = threading.Lock()

# Lista global de drivers activos para poder cerrarlos desde cualquier lugar
active_drivers = []
drivers_lock = threading.Lock()


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


def cleanup_chromedriver_processes():
    """Mata procesos ChromeDriver huérfanos de esta sesión."""
    try:
        # En macOS/Linux, buscar y matar chromedrivers huérfanos
        if sys.platform != 'win32':
            subprocess.run(['pkill', '-f', 'chromedriver'], 
                         capture_output=True, timeout=5)
    except:
        pass


def cleanup_all():
    """Limpieza completa al cerrar la aplicación."""
    print("\n🧹 Limpiando recursos...")
    cleanup_drivers()
    cleanup_chromedriver_processes()
    print("✅ Recursos liberados")


# Registrar cleanup al salir
atexit.register(cleanup_all)


def signal_handler(signum, frame):
    """Maneja señales de terminación."""
    print(f"\n⚠️ Señal {signum} recibida, cerrando...")
    cleanup_all()
    sys.exit(0)


# Registrar handlers de señales
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Logo SVG real de tuplanilla.net
LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">
  <defs>
    <linearGradient id="tuplanilla-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#9333ea"/>
      <stop offset="100%" stop-color="#ec4899"/>
    </linearGradient>
  </defs>
  <rect width="50" height="50" rx="10" fill="url(#tuplanilla-bg)"/>
  <g fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <polygon points="25,10 38,18 25,26 12,18" />
    <line x1="12" y1="18" x2="12" y2="32" />
    <line x1="25" y1="26" x2="25" y2="40" />
    <line x1="38" y1="18" x2="38" y2="32" />
    <line x1="12" y1="32" x2="25" y2="40" />
    <line x1="25" y1="40" x2="38" y2="32" />
  </g>
</svg>'''

# HTML de la interfaz
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verificador DUSA | Tu Planilla</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 50'><defs><linearGradient id='g' x1='0%25' y1='0%25' x2='100%25' y2='100%25'><stop offset='0%25' stop-color='%239333ea'/><stop offset='100%25' stop-color='%23ec4899'/></linearGradient></defs><rect width='50' height='50' rx='10' fill='url(%23g)'/><g fill='none' stroke='white' stroke-width='2.5'><polygon points='25,10 38,18 25,26 12,18'/><line x1='12' y1='18' x2='12' y2='32'/><line x1='25' y1='26' x2='25' y2='40'/><line x1='38' y1='18' x2='38' y2='32'/><line x1='12' y1='32' x2='25' y2='40'/><line x1='25' y1='40' x2='38' y2='32'/></g></svg>">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --primary: #9333ea;
            --primary-dark: #7c3aed;
            --secondary: #ec4899;
            --bg-dark: #1a1a2e;
            --bg-card: #16213e;
            --text: #e8e8e8;
            --text-muted: #a0a0a0;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, #0f0f23 100%);
            min-height: 100vh;
            padding: 20px;
            color: var(--text);
        }
        
        .container { max-width: 900px; margin: 0 auto; }
        
        /* Brand Header */
        .brand-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo {
            width: 70px;
            height: 70px;
            margin: 0 auto 15px;
        }
        .brand-name {
            font-size: 26px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .brand-tagline {
            color: var(--text-muted);
            font-size: 14px;
            margin-top: 5px;
        }
        
        .card {
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.1);
            padding: 25px;
            margin-bottom: 20px;
        }
        
        h2 {
            font-size: 1.1em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text);
        }
        
        /* Form */
        .form-group { margin-bottom: 15px; }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            font-size: 13px;
            color: var(--text-muted);
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px 14px;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            font-size: 15px;
            background: rgba(255,255,255,0.05);
            color: var(--text);
            transition: all 0.3s;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: var(--primary);
            background: rgba(255,255,255,0.08);
        }
        .form-group select option {
            background: var(--bg-card);
            color: var(--text);
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
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
        }
        .checkbox-group input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: var(--primary);
        }
        .checkbox-group label {
            margin: 0;
            font-size: 13px;
            color: var(--text-muted);
            cursor: pointer;
        }
        
        /* Upload zone */
        .upload-zone {
            border: 2px dashed rgba(255,255,255,0.2);
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: rgba(255,255,255,0.02);
            margin-bottom: 20px;
        }
        .upload-zone:hover, .upload-zone.dragover {
            border-color: var(--primary);
            background: rgba(147, 51, 234, 0.1);
        }
        .upload-zone input { display: none; }
        .upload-zone .icon { font-size: 45px; margin-bottom: 15px; }
        .upload-zone p { color: var(--text-muted); }
        
        /* File info */
        .file-info {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 15px;
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .file-info .name { font-weight: 600; color: var(--success); }
        .file-info .count { color: var(--text-muted); font-size: 14px; }
        .file-info button {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 18px;
            opacity: 0.7;
        }
        .file-info button:hover { opacity: 1; }
        
        /* Preview table */
        .preview-section {
            margin-bottom: 20px;
            max-height: 200px;
            overflow-y: auto;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .preview-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        .preview-table th, .preview-table td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .preview-table th {
            background: rgba(255,255,255,0.05);
            font-weight: 600;
            position: sticky;
            top: 0;
            color: var(--text-muted);
        }
        .preview-table td {
            color: var(--text);
        }
        
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
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(147, 51, 234, 0.3);
        }
        .btn-primary:disabled {
            background: rgba(255,255,255,0.1);
            color: var(--text-muted);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .btn-danger {
            background: var(--danger);
            color: white;
        }
        .btn-success {
            background: var(--success);
            color: white;
        }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: var(--text);
        }
        
        /* Progress */
        .progress-container { margin: 20px 0; }
        .progress-bar {
            height: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 13px;
        }
        .progress-stats {
            display: flex;
            justify-content: space-between;
            margin-top: 12px;
            color: var(--text-muted);
            font-size: 13px;
        }
        
        /* Status */
        .status-message {
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            text-align: center;
            font-weight: 500;
            font-size: 14px;
        }
        .status-info {
            background: rgba(147, 51, 234, 0.1);
            color: var(--primary);
            border: 1px solid rgba(147, 51, 234, 0.3);
        }
        .status-success {
            background: rgba(34, 197, 94, 0.1);
            color: var(--success);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .status-error {
            background: rgba(239, 68, 68, 0.1);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        /* Summary */
        .summary {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin: 20px 0;
        }
        .summary-card {
            background: rgba(255,255,255,0.03);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
            cursor: help;
            transition: transform 0.2s, background 0.2s;
        }
        .summary-card:hover {
            transform: translateY(-2px);
            background: rgba(255,255,255,0.06);
        }
        .summary-card .number {
            font-size: 28px;
            font-weight: bold;
        }
        .summary-card .label {
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 5px;
        }
        .summary-card.total .number { color: var(--text); }
        .summary-card.disponible .number { color: var(--success); }
        .summary-card.agotado .number { color: var(--danger); }
        .summary-card.no-encontrado .number { color: var(--warning); }
        .summary-card.diferida .number { color: #3b82f6; }
        .summary-card.consultar .number { color: #f59e0b; }
        .summary-card.alertas .number { color: #ef4444; }
        
        /* Results table */
        .results-container {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            margin-top: 15px;
        }
        .results-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .results-table th, .results-table td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .results-table th {
            background: rgba(255,255,255,0.05);
            font-weight: 600;
            position: sticky;
            top: 0;
            color: var(--text-muted);
        }
        
        /* Badges */
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-success { background: rgba(34, 197, 94, 0.2); color: var(--success); }
        .badge-danger { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
        .badge-warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
        .badge-info { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
        .badge-secondary { background: rgba(255,255,255,0.1); color: var(--text-muted); }
        
        .row-alert { background: rgba(239, 68, 68, 0.1); }
        .alert-cell { color: #ef4444; font-weight: 600; }
        
        /* Filtros clickeables */
        .summary-card {
            cursor: pointer;
            transition: all 0.2s ease;
            border: 2px solid transparent;
        }
        .summary-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .summary-card.active {
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(147, 51, 234, 0.4);
        }
        
        /* Barra de filtros */
        .filter-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 15px 0;
            padding: 10px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            flex-wrap: nowrap;
            overflow: hidden;
        }
        .filter-bar input {
            flex: 1;
            min-width: 150px;
            max-width: 100%;
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.2);
            color: var(--text);
            font-size: 13px;
        }
        .filter-bar input:focus {
            outline: none;
            border-color: var(--primary);
        }
        .filter-label {
            font-size: 12px;
            color: var(--primary);
            font-weight: 600;
            white-space: nowrap;
        }
        .btn-outline {
            flex: 0 0 auto;
            width: auto !important;
            background: transparent;
            border: 1px solid var(--danger);
            color: var(--danger);
            padding: 6px 12px;
            font-size: 11px;
            white-space: nowrap;
        }
        .btn-outline:hover {
            background: var(--danger);
            color: white;
        }
        
        .hidden { display: none !important; }
        
        .speed-info {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 6px;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }
    </style>
</head>
<body>
    <div class="container">
        <!-- Brand Header -->
        <div class="brand-header">
            <svg class="logo" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <linearGradient id="tuplanilla-bg" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#9333ea"/>
                        <stop offset="100%" stop-color="#ec4899"/>
                    </linearGradient>
                </defs>
                <rect width="50" height="50" rx="10" fill="url(#tuplanilla-bg)"/>
                <g fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="25,10 38,18 25,26 12,18" />
                    <line x1="12" y1="18" x2="12" y2="32" />
                    <line x1="25" y1="26" x2="25" y2="40" />
                    <line x1="38" y1="18" x2="38" y2="32" />
                    <line x1="12" y1="32" x2="25" y2="40" />
                    <line x1="25" y1="40" x2="38" y2="32" />
                </g>
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
            <h2>📁 Archivo Excel de Mercado Libre</h2>
            <div class="upload-zone" id="upload-zone">
                <input type="file" id="file-input" accept=".xlsx,.xls">
                <div class="icon">📄</div>
                <p>Arrastra tu archivo Excel aquí</p>
                <p style="font-size: 12px;">o haz clic para seleccionar</p>
            </div>
            <div id="file-info" class="file-info hidden">
                <div>
                    <span class="name" id="file-name"></span>
                    <span class="count" id="file-count"></span>
                </div>
                <button onclick="clearFile()">❌</button>
            </div>
            <div id="preview-section" class="preview-section hidden">
                <table class="preview-table">
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>Título</th>
                            <th>Precio ML</th>
                            <th>Stock ML</th>
                        </tr>
                    </thead>
                    <tbody id="preview-body"></tbody>
                </table>
            </div>
            <button class="btn btn-primary" id="btn-start" onclick="startVerification()" disabled>
                🚀 Iniciar Verificación
            </button>
        </div>
        
        <!-- Progress Section -->
        <div class="card hidden" id="progress-section">
            <h2>⏳ Verificando productos...</h2>
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%">0%</div>
                </div>
                <div class="progress-stats">
                    <span id="progress-text">0 / 0 productos</span>
                    <span id="progress-speed">0 prod/min</span>
                    <span id="progress-time">Calculando...</span>
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
            <div class="summary">
                <div class="summary-card total active" onclick="setFilter('todos')" title="Cantidad total de productos verificados en DUSA">
                    <div class="number" id="count-total">0</div>
                    <div class="label">Total</div>
                </div>
                <div class="summary-card disponible" onclick="setFilter('disponible')" title="Productos con stock disponible en DUSA para venta inmediata">
                    <div class="number" id="count-disponible">0</div>
                    <div class="label">Disponibles</div>
                </div>
                <div class="summary-card agotado" onclick="setFilter('agotado')" title="Productos sin stock en DUSA (faltante/agotado)">
                    <div class="number" id="count-agotado">0</div>
                    <div class="label">Agotados</div>
                </div>
                <div class="summary-card no-encontrado" onclick="setFilter('no_encontrado')" title="Productos que no se encontraron en el catálogo de DUSA (puede ser SKU incorrecto o producto descontinuado)">
                    <div class="number" id="count-noencontrado">0</div>
                    <div class="label">No encontrados</div>
                </div>
                <div class="summary-card diferida" onclick="setFilter('diferida')" title="Productos por pedido/venta telefónica. Requieren solicitar a DUSA y tienen tiempo de entrega mayor">
                    <div class="number" id="count-diferida">0</div>
                    <div class="label">Diferida</div>
                </div>
                <div class="summary-card consultar" onclick="setFilter('consultar')" title="Productos que requieren consulta con DUSA para confirmar disponibilidad o precio">
                    <div class="number" id="count-consultar">0</div>
                    <div class="label">Consultar</div>
                </div>
                <div class="summary-card alertas" onclick="setFilter('alertas')" title="⚠️ Productos donde tu precio de venta en ML es MENOR al precio de compra en DUSA. Revisar urgente!">
                    <div class="number" id="count-alertas">0</div>
                    <div class="label">⚠️ Alertas</div>
                </div>
            </div>
            <button class="btn btn-success" onclick="downloadResults()">
                📥 Descargar Excel con Resultados
            </button>
            <button class="btn btn-secondary" onclick="resetApp()" style="margin-top: 10px;">
                🔄 Nueva Verificación
            </button>
            
            <!-- Barra de filtros y búsqueda -->
            <div class="filter-bar">
                <input type="text" id="search-results" placeholder="🔍 Buscar en resultados..." onkeyup="filterResults()">
                <button class="btn btn-outline" id="btn-clear-filter" onclick="clearFilter()" style="display:none;">✖ Limpiar</button>
                <span id="filter-label" class="filter-label"></span>
            </div>
            
            <div class="results-container">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>Título</th>
                            <th>Precio DUSA</th>
                            <th>Laboratorio</th>
                            <th>Estado</th>
                            <th>Alerta</th>
                        </tr>
                    </thead>
                    <tbody id="results-body"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        let productos = [];
        let archivoNombre = '';
        let pollingInterval = null;
        let allResultados = [];  // Todos los resultados sin filtrar
        let currentFilter = 'todos';  // Filtro actual
        
        // Funciones de filtrado
        function setFilter(filter) {
            currentFilter = filter;
            
            // Actualizar clase active en los cards
            document.querySelectorAll('.summary-card').forEach(card => {
                card.classList.remove('active');
            });
            
            // Encontrar y activar el card correspondiente
            const cardMap = {
                'todos': '.summary-card.total',
                'disponible': '.summary-card.disponible',
                'agotado': '.summary-card.agotado',
                'no_encontrado': '.summary-card.no-encontrado',
                'diferida': '.summary-card.diferida',
                'consultar': '.summary-card.consultar',
                'alertas': '.summary-card.alertas'
            };
            
            const activeCard = document.querySelector(cardMap[filter]);
            if (activeCard) activeCard.classList.add('active');
            
            // Mostrar/ocultar botón limpiar y label
            const btnClear = document.getElementById('btn-clear-filter');
            const filterLabel = document.getElementById('filter-label');
            
            if (filter !== 'todos') {
                btnClear.style.display = 'inline-block';
                const labels = {
                    'disponible': '✅ Mostrando: Disponibles',
                    'agotado': '❌ Mostrando: Agotados/Faltantes',
                    'no_encontrado': '🔍 Mostrando: No encontrados',
                    'diferida': '📦 Mostrando: Diferida',
                    'consultar': '📞 Mostrando: Consultar',
                    'alertas': '⚠️ Mostrando: Con alertas de precio'
                };
                filterLabel.textContent = labels[filter] || '';
            } else {
                btnClear.style.display = 'none';
                filterLabel.textContent = '';
            }
            
            filterResults();
        }
        
        function clearFilter() {
            document.getElementById('search-results').value = '';
            setFilter('todos');
        }
        
        function filterResults() {
            const searchTerm = document.getElementById('search-results').value.toLowerCase();
            
            let filtered = allResultados.filter(r => {
                // Filtro por estado
                let passFilter = true;
                if (currentFilter === 'disponible') {
                    passFilter = r.estado === 'disponible';
                } else if (currentFilter === 'agotado') {
                    passFilter = r.estado === 'agotado' || r.estado === 'faltante';
                } else if (currentFilter === 'no_encontrado') {
                    passFilter = r.estado === 'no_encontrado' || r.estado === 'error' || !r.encontrado;
                } else if (currentFilter === 'diferida') {
                    passFilter = r.estado === 'diferida';
                } else if (currentFilter === 'consultar') {
                    passFilter = r.estado === 'consultar';
                } else if (currentFilter === 'alertas') {
                    passFilter = r.precio_inferior === true || (r.alerta && r.alerta.length > 0);
                }
                
                // Filtro por búsqueda de texto
                if (searchTerm && passFilter) {
                    const searchIn = [r.sku, r.titulo, r.nombre_dusa, r.laboratorio].join(' ').toLowerCase();
                    passFilter = searchIn.includes(searchTerm);
                }
                
                return passFilter;
            });
            
            renderResultsTable(filtered);
        }
        
        function renderResultsTable(resultados) {
            const tbody = document.getElementById('results-body');
            tbody.innerHTML = resultados.map(r => {
                let badge = 'badge-secondary';
                let estado = '🔍 No encontrado';
                
                if (r.estado === 'disponible') { 
                    badge = 'badge-success'; 
                    estado = '✅ Disponible'; 
                }
                else if (r.estado === 'agotado' || r.estado === 'faltante') { 
                    badge = 'badge-danger'; 
                    estado = '❌ Agotado/Faltante'; 
                }
                else if (r.estado === 'diferida') { 
                    badge = 'badge-info'; 
                    estado = '📦 Diferida'; 
                }
                else if (r.estado === 'consultar') { 
                    badge = 'badge-warning'; 
                    estado = '📞 Consultar'; 
                }
                
                const alertaText = r.precio_inferior ? '⚠️ Precio bajo' : '';
                
                return `<tr class="${r.precio_inferior ? 'row-alert' : ''}">
                    <td>${r.sku || '-'}</td>
                    <td>${(r.titulo || r.nombre_dusa || '-').substring(0, 35)}</td>
                    <td>${r.precio_dusa || '-'}</td>
                    <td>${r.laboratorio || '-'}</td>
                    <td><span class="badge ${badge}">${estado}</span></td>
                    <td class="alert-cell">${alertaText}</td>
                </tr>`;
            }).join('');
        }
        
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
        
        // Upload zone
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        
        uploadZone.onclick = () => fileInput.click();
        fileInput.onchange = (e) => handleFile(e.target.files[0]);
        
        uploadZone.ondragover = (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); };
        uploadZone.ondragleave = () => uploadZone.classList.remove('dragover');
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
                    archivoNombre = data.archivo;
                    productos = data.productos;
                    
                    document.getElementById('upload-zone').classList.add('hidden');
                    document.getElementById('file-info').classList.remove('hidden');
                    document.getElementById('file-name').textContent = file.name;
                    document.getElementById('file-count').textContent = ` - ${productos.length} productos`;
                    document.getElementById('btn-start').disabled = false;
                    
                    // Mostrar preview
                    if (data.preview && data.preview.length > 0) {
                        document.getElementById('preview-section').classList.remove('hidden');
                        const previewBody = document.getElementById('preview-body');
                        previewBody.innerHTML = data.preview.map(p => `
                            <tr>
                                <td>${p.sku || '-'}</td>
                                <td>${(p.titulo || '').substring(0, 40)}...</td>
                                <td>${p.precio_ml || '-'}</td>
                                <td>${p.stock_ml || '-'}</td>
                            </tr>
                        `).join('');
                    }
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error subiendo archivo: ' + error.message);
            }
        }
        
        function clearFile() {
            productos = [];
            archivoNombre = '';
            document.getElementById('upload-zone').classList.remove('hidden');
            document.getElementById('file-info').classList.add('hidden');
            document.getElementById('preview-section').classList.add('hidden');
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
                alert('Por favor sube un archivo Excel con productos');
                return;
            }
            
            saveCredentials();
            
            // Mostrar progreso
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
                        usuario, password, cliente, 
                        ventanas: parseInt(ventanas),
                        archivo: archivoNombre
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
            document.getElementById('progress-speed').textContent = `${(data.velocidad || 0).toFixed(1)} prod/min`;
            
            if (data.velocidad > 0 && data.total > data.progreso) {
                const remaining = (data.total - data.progreso) / data.velocidad;
                document.getElementById('progress-time').textContent = `~${Math.ceil(remaining)} min`;
            }
            
            document.getElementById('status-message').textContent = data.mensaje || 'Procesando...';
        }
        
        function updateResults(resultados) {
            // Guardar todos los resultados
            allResultados = resultados;
            
            const total = resultados.length;
            const disponibles = resultados.filter(r => r.estado === 'disponible').length;
            const agotados = resultados.filter(r => r.estado === 'agotado' || r.estado === 'faltante').length;
            const noEncontrados = resultados.filter(r => r.estado === 'no_encontrado' || r.estado === 'error' || !r.encontrado).length;
            const diferidas = resultados.filter(r => r.estado === 'diferida').length;
            const consultarCount = resultados.filter(r => r.estado === 'consultar').length;
            const alertas = resultados.filter(r => r.precio_inferior === true || r.alerta).length;
            
            document.getElementById('count-total').textContent = total;
            document.getElementById('count-disponible').textContent = disponibles;
            document.getElementById('count-agotado').textContent = agotados;
            document.getElementById('count-noencontrado').textContent = noEncontrados;
            document.getElementById('count-diferida').textContent = diferidas;
            document.getElementById('count-consultar').textContent = consultarCount;
            document.getElementById('count-alertas').textContent = alertas;
            
            // Aplicar filtro actual
            filterResults();
        }
        
        async function stopVerification() {
            try {
                await fetch('/detener', { method: 'POST' });
                stopPolling();
            } catch (error) {
                console.error('Error stopping:', error);
            }
        }
        
        function downloadResults() {
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
    """Recibe el archivo Excel - MISMA LÓGICA QUE APP_WEB.PY ORIGINAL."""
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    
    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'No se seleccionó archivo'}), 400
    
    if not archivo.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Solo se permiten archivos Excel (.xlsx, .xls)'}), 400
    
    # Guardar archivo
    filename = secure_filename(archivo.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    archivo.save(filepath)
    
    try:
        productos = leer_excel(filepath)
        return jsonify({
            'success': True,
            'archivo': filename,
            'productos': productos,
            'total_productos': len(productos),
            'preview': productos[:10]
        })
    except Exception as e:
        return jsonify({'error': f'Error leyendo archivo: {str(e)}'}), 400


def leer_excel(filepath):
    """Lee el Excel de Mercado Libre - COPIA EXACTA DE APP_WEB.PY."""
    xl = pd.ExcelFile(filepath, engine='openpyxl')
    
    # Si tiene hoja "Publicaciones", usarla con skiprows=2
    if 'Publicaciones' in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name='Publicaciones', skiprows=2, engine='openpyxl')
    else:
        df = pd.read_excel(xl, engine='openpyxl')
    
    # Normalizar nombres de columnas
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
    
    # Filtrar filas válidas (que tengan SKU o Título)
    if 'SKU' in df.columns or 'Titulo' in df.columns:
        mask = pd.Series([False] * len(df))
        if 'SKU' in df.columns:
            mask |= (df['SKU'].notna() & (df['SKU'].astype(str) != 'nan'))
        if 'Titulo' in df.columns:
            mask |= (df['Titulo'].notna() & (df['Titulo'].astype(str) != 'nan'))
        df = df[mask].copy()
    
    # Filtrar filas de instrucciones
    if 'Stock' in df.columns:
        df = df[~df['Stock'].astype(str).str.contains('Obligatorio|Opcional', case=False, na=False)]
    
    # Convertir a lista de diccionarios
    productos = []
    for _, row in df.iterrows():
        # Parsear precio como número
        precio_raw = row.get('Precio', '')
        if pd.notna(precio_raw):
            try:
                precio_ml = float(str(precio_raw).replace('$', '').replace(',', '').strip())
            except:
                precio_ml = 0
        else:
            precio_ml = 0
        
        productos.append({
            'sku': str(row.get('SKU', '')) if pd.notna(row.get('SKU')) else '',
            'titulo': str(row.get('Titulo', ''))[:60] if pd.notna(row.get('Titulo')) else '',
            'precio_ml': precio_ml,
            'stock_ml': str(row.get('Stock', '')) if pd.notna(row.get('Stock')) else '',
            'estado_ml': str(row.get('Estado', 'Activa')) if pd.notna(row.get('Estado')) else 'Activa'
        })
    
    return productos


def extraer_palabras_clave(titulo):
    """Extrae palabras clave del título para buscar."""
    if not titulo:
        return ""
    ignorar = ['farmauy', 'farmacia', 'original', 'sellado', 'envio', 'gratis',
               'pack', 'combo', 'oferta', 'promo', 'uruguay', 'importado']
    palabras = str(titulo).split()[:5]
    filtradas = [p for p in palabras if p.lower() not in ignorar and len(p) > 2]
    return " ".join(filtradas[:3])


def parsear_precio(precio_str):
    """Convierte string de precio a número."""
    if not precio_str:
        return None
    try:
        limpio = str(precio_str).replace('$', '').replace(' ', '').strip()
        if ',' in limpio and '.' in limpio:
            if limpio.rfind(',') > limpio.rfind('.'):
                limpio = limpio.replace('.', '').replace(',', '.')
            else:
                limpio = limpio.replace(',', '')
        elif ',' in limpio:
            limpio = limpio.replace(',', '.')
        return float(limpio)
    except:
        return None


def generar_excel_profesional(resultados, filepath):
    """Genera un Excel profesional con el formato original."""
    filas = []
    
    for r in resultados:
        # Determinar alerta
        alerta = ''
        estado_raw = r.get('estado', '')
        precio_ml = r.get('precio_ml', 0) or 0
        precio_dusa_str = r.get('precio_dusa', '')
        precio_dusa = parsear_precio(precio_dusa_str) if precio_dusa_str else None
        
        if estado_raw in ['no_encontrado', 'error'] or not r.get('encontrado', False):
            alerta = '🔍 SKU NO ENCONTRADO'
        elif precio_dusa and precio_ml and precio_ml < precio_dusa:
            alerta = '⚠️ PRECIO ML INFERIOR'
        elif estado_raw == 'faltante':
            alerta = '❌ PRODUCTO FALTANTE'
        elif estado_raw == 'diferida':
            alerta = '📦 VENTA DIFERIDA'
        elif estado_raw == 'consultar':
            alerta = '📞 CONSULTAR DUSA'
        
        # Estado con emoji
        estado_emoji = '🔍 No encontrado'
        if estado_raw == 'disponible':
            estado_emoji = '✅ Disponible'
        elif estado_raw == 'faltante' or estado_raw == 'agotado':
            estado_emoji = '❌ Faltante'
        elif estado_raw == 'diferida':
            estado_emoji = '📦 Diferida'
        elif estado_raw == 'consultar':
            estado_emoji = '📞 Consultar'
        
        # Calcular diferencia
        diferencia = None
        if precio_ml and precio_dusa:
            diferencia = round(precio_ml - precio_dusa, 2)
        
        fila = {
            '⚠️ REVISAR': alerta if alerta else None,
            'SKU': r.get('sku', ''),
            'Título ML': r.get('titulo', ''),
            'Estado DUSA': estado_emoji,
            'Producto DUSA': r.get('nombre_dusa', ''),
            'Precio ML': precio_ml if precio_ml else None,
            'Precio DUSA': precio_dusa_str,
            'Diferencia ($)': diferencia,
            'Oferta': r.get('oferta', 'NO') or 'NO',
            'Laboratorio': r.get('laboratorio', ''),
            'Stock ML': r.get('stock_ml', ''),
            'estado_ml': r.get('estado_ml', 'Activa'),
        }
        filas.append(fila)
    
    df = pd.DataFrame(filas)
    
    # Ordenar: primero los que tienen alerta
    df['_orden'] = df['⚠️ REVISAR'].apply(lambda x: 0 if pd.notna(x) and x else 1)
    df = df.sort_values('_orden').drop(columns=['_orden'])
    
    # Guardar con formato
    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados')
            
            # Ajustar anchos de columna
            worksheet = writer.sheets['Resultados']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 40)
        
        print(f"[Excel] Guardado profesional: {filepath}")
        return True
    except Exception as e:
        print(f"[Excel] Error con openpyxl, usando método simple: {e}")
        df.to_excel(filepath, index=False)
        return True


@app.route('/iniciar', methods=['POST'])
def iniciar_verificacion():
    """Inicia la verificación."""
    global estado
    
    if estado['procesando']:
        return jsonify({'error': 'Ya hay un proceso en curso'}), 400
    
    data = request.json
    archivo = data.get('archivo')
    ventanas = max(1, min(6, int(data.get('ventanas', 3))))
    
    if not archivo:
        return jsonify({'error': 'No se especificó archivo'}), 400
    
    filepath = os.path.join(UPLOAD_FOLDER, archivo)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Archivo no encontrado'}), 400
    
    with progress_lock:
        productos = leer_excel(filepath)
        estado = {
            'procesando': True,
            'progreso': 0,
            'total': len(productos),
            'mensaje': 'Iniciando...',
            'resultados': [],
            'tiempo_inicio': time.time(),
            'velocidad': 0,
            'ventanas_activas': 0,
            'detenido': False,
            'archivo_resultado': None
        }
    
    # Iniciar en thread separado
    thread = threading.Thread(
        target=procesar_verificacion,
        args=(data['usuario'], data['password'], data['cliente'], 
              productos, ventanas, filepath)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'mensaje': f'Verificación iniciada con {ventanas} ventana(s)'})


@app.route('/estado')
def obtener_estado():
    """Retorna el estado actual."""
    with progress_lock:
        if estado['procesando'] and estado['tiempo_inicio']:
            elapsed = time.time() - estado['tiempo_inicio']
            if elapsed > 0 and estado['progreso'] > 0:
                estado['velocidad'] = (estado['progreso'] / elapsed) * 60
        return jsonify(estado)


@app.route('/detener', methods=['POST'])
def detener():
    """Detiene la verificación y cierra los drivers."""
    global estado
    with progress_lock:
        estado['detenido'] = True
        estado['procesando'] = False
        estado['mensaje'] = 'Detenido por el usuario'
    
    # Cerrar todos los drivers activos
    cleanup_drivers()
    
    return jsonify({'success': True})


@app.route('/descargar')
def descargar():
    """Descarga los resultados como Excel profesional."""
    with progress_lock:
        resultados = estado.get('resultados', [])
        archivo_resultado = estado.get('archivo_resultado')
    
    if archivo_resultado and os.path.exists(archivo_resultado):
        return send_file(archivo_resultado, as_attachment=True, 
                        download_name=os.path.basename(archivo_resultado))
    
    if not resultados:
        return "No hay resultados para descargar", 404
    
    # Guardar en escritorio con formato profesional
    desktop = os.path.expanduser('~/Desktop')
    filename = f'resultado_dusa_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    filepath = os.path.join(desktop, filename)
    
    generar_excel_profesional(resultados, filepath)
    
    return send_file(filepath, as_attachment=True, download_name=filename)


def crear_driver(num_ventana=0):
    """Crea un driver de Chrome VISIBLE (sin headless)."""
    opciones = Options()
    # NO usar headless - ventanas visibles para que el usuario vea
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-gpu")
    opciones.add_argument("--window-size=800,600")
    
    # Posicionar cada ventana en diferente lugar
    x_pos = 50 + (num_ventana % 3) * 350
    y_pos = 50 + (num_ventana // 3) * 250
    opciones.add_argument(f"--window-position={x_pos},{y_pos}")
    
    servicio = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servicio, options=opciones)
    
    return driver


def login_dusa(driver, usuario, password, cliente):
    """Inicia sesión en DUSA - Igual que app_web.py original."""
    try:
        print(f"[Login] Abriendo DUSA...")
        driver.get("https://pedidos.dusa.com.uy/DUSAWebUI")
        time.sleep(2)
        
        # Buscar campos de texto y password
        campos_texto = driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        campos_pass = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        
        print(f"[Login] Campos texto: {len(campos_texto)}, Password: {len(campos_pass)}")
        
        # Usuario (primer campo de texto)
        if campos_texto:
            campos_texto[0].send_keys(usuario)
            print(f"[Login] Usuario ingresado")
        
        # Contraseña
        if campos_pass:
            campos_pass[0].send_keys(password)
            print(f"[Login] Contraseña ingresada")
        
        # Cliente (último campo de texto)
        if len(campos_texto) >= 2:
            campos_texto[-1].send_keys(cliente)
            print(f"[Login] Cliente ingresado")
        
        time.sleep(0.5)
        
        # Buscar botón "Entrar"
        botones = driver.find_elements(By.CSS_SELECTOR, ".v-button, button")
        for btn in botones:
            if "Entrar" in btn.text or "entrar" in btn.text.lower():
                btn.click()
                print(f"[Login] Click en Entrar")
                break
        
        time.sleep(2)
        
        # Verificar si el login fue exitoso (form de login ya no existe)
        try:
            driver.find_element(By.CSS_SELECTOR, "#loginf")
            print(f"[Login] FALLO - Form de login sigue visible")
            return False
        except NoSuchElementException:
            print(f"[Login] EXITOSO")
            # Ir a productos
            driver.get("https://pedidos.dusa.com.uy/DUSAWebUI#!micuenta/productos")
            time.sleep(1.5)
            return True
            
    except Exception as e:
        print(f"[Login] ERROR: {e}")
        return False


def buscar_producto(driver, producto):
    """Busca un producto en DUSA - Lógica completa igual que app_web.py."""
    
    resultado = {
        **producto,
        'estado': 'no_encontrado',
        'estado_dusa': None,
        'encontrado': False,
        'nombre_dusa': '',
        'precio_dusa': '-',
        'laboratorio': '',
        'oferta': '',
        'stock_dusa': '-'
    }
    
    # Determinar qué buscar: SKU o palabras clave del título
    sku = producto.get('sku', '')
    titulo = producto.get('titulo', '')
    
    if sku and sku.strip() and sku.strip() != 'nan':
        termino = sku.strip()
        busqueda_tipo = 'sku'
    else:
        termino = extraer_palabras_clave(titulo)
        busqueda_tipo = 'titulo'
    
    resultado['busqueda'] = termino
    resultado['busqueda_tipo'] = busqueda_tipo
    
    if not termino:
        resultado['estado'] = 'no_encontrado'
        resultado['mensaje'] = 'Sin SKU ni título'
        return resultado
    
    try:
        # Buscar campo de búsqueda
        campo = driver.find_element(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
        campo.clear()
        time.sleep(0.1)
        campo.send_keys(termino)
        
        # Intentar hacer clic en botón Buscar o presionar Enter
        try:
            boton = driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]/..")
            boton.click()
        except:
            campo.send_keys(Keys.RETURN)
        
        time.sleep(0.5)
        
        # Buscar filas de resultados en la tabla
        filas = driver.find_elements(By.CSS_SELECTOR, "table tr")
        # Filtrar filas de encabezado
        filas_datos = [f for f in filas if f.text.strip() and "Stock" not in f.text and "Descripción" not in f.text]
        
        if filas_datos:
            primera = filas_datos[0]
            resultado['encontrado'] = True
            
            # Detectar estado por ícono y texto
            # Estados: Verde=Disponible, Rojo=Faltante, Azul=Diferida, Amarillo=Consultar
            try:
                # Buscar imagen de estado
                imgs = primera.find_elements(By.CSS_SELECTOR, "td img, td .v-icon")
                icono_style = ""
                for img in imgs:
                    icono_style = img.get_attribute('style') or ''
                    break
                
                celdas_td = primera.find_elements(By.CSS_SELECTOR, "td")
                html_celda = celdas_td[0].get_attribute('innerHTML').lower() if celdas_td else ''
                texto_fila = primera.text.lower()
                
                # Detectar estado por color/clase/texto
                # 1. Faltante (rojo)
                if 'faltante' in texto_fila or 'red' in icono_style or 'error' in html_celda or 'rojo' in html_celda:
                    resultado['estado_dusa'] = 'faltante'
                    resultado['estado'] = 'agotado'
                # 2. Diferida (azul) - Por pedido
                elif 'diferida' in texto_fila or 'por pedido' in texto_fila or 'venta telefónica' in texto_fila or 'venta telefonica' in texto_fila or 'blue' in icono_style:
                    resultado['estado_dusa'] = 'diferida'
                    resultado['estado'] = 'diferida'
                # 3. Consultar (amarillo)
                elif 'yellow' in icono_style or 'warning' in html_celda or 'consultar' in texto_fila or 'llamar' in texto_fila:
                    resultado['estado_dusa'] = 'consultar'
                    resultado['estado'] = 'consultar'
                # 4. Disponible (verde) - default si hay resultado
                else:
                    resultado['estado_dusa'] = 'disponible'
                    resultado['estado'] = 'disponible'
            except:
                # Fallback: si encontró fila, asumir disponible
                resultado['estado_dusa'] = 'disponible'
                resultado['estado'] = 'disponible'
            
            # Extraer datos de las celdas
            celdas = primera.find_elements(By.CSS_SELECTOR, "td")
            if len(celdas) >= 5:
                resultado['nombre_dusa'] = celdas[1].text.split('\n')[0][:40]
                resultado['laboratorio'] = celdas[2].text.strip()[:20]
                resultado['oferta'] = celdas[3].text.strip()
                resultado['precio_dusa'] = celdas[4].text.strip()
        else:
            # No hay filas de datos = no encontrado
            resultado['estado'] = 'no_encontrado'
            resultado['encontrado'] = False
        
        return resultado
        
    except Exception as e:
        resultado['estado'] = 'error'
        resultado['mensaje'] = str(e)
        return resultado


def procesar_verificacion(usuario, password, cliente, productos, num_ventanas, filepath_original):
    """Procesa la verificación con múltiples ventanas."""
    global estado, active_drivers
    
    drivers = []
    
    try:
        with progress_lock:
            estado['mensaje'] = f'Abriendo {num_ventanas} ventana(s)...'
        
        # Crear drivers y hacer login
        for i in range(num_ventanas):
            with progress_lock:
                if estado['detenido']:
                    break
                estado['mensaje'] = f'Conectando ventana {i+1}/{num_ventanas}...'
            
            driver = crear_driver(i)
            if login_dusa(driver, usuario, password, cliente):
                drivers.append(driver)
                # Registrar en lista global para poder cerrar desde /detener
                with drivers_lock:
                    active_drivers.append(driver)
                with progress_lock:
                    estado['ventanas_activas'] = len(drivers)
            else:
                driver.quit()
        
        if not drivers:
            with progress_lock:
                estado['procesando'] = False
                estado['mensaje'] = 'Error: No se pudo conectar a DUSA'
            return
        
        with progress_lock:
            estado['mensaje'] = f'Verificando con {len(drivers)} ventana(s)...'
        
        # Procesar productos
        productos_pendientes = list(productos)
        productos_lock = threading.Lock()
        
        def worker(driver, worker_id):
            while True:
                with progress_lock:
                    if estado['detenido']:
                        return
                
                with productos_lock:
                    if not productos_pendientes:
                        return
                    producto = productos_pendientes.pop(0)
                
                resultado = buscar_producto(driver, producto)
                
                # Calcular alertas de precio
                try:
                    precio_ml = producto.get('precio_ml', 0)
                    precio_dusa_str = resultado.get('precio_dusa', '')
                    precio_dusa = parsear_precio(precio_dusa_str) if precio_dusa_str else 0
                    
                    if precio_ml and precio_dusa and precio_dusa > 0:
                        diferencia = precio_ml - precio_dusa
                        resultado['precio_ml'] = precio_ml
                        resultado['precio_dusa_num'] = precio_dusa
                        resultado['diferencia'] = round(diferencia, 2)
                        
                        if precio_ml < precio_dusa:
                            resultado['alerta'] = f'⚠️ Precio ML (${precio_ml:.2f}) < DUSA (${precio_dusa:.2f})'
                            resultado['precio_inferior'] = True
                        else:
                            resultado['alerta'] = ''
                            resultado['precio_inferior'] = False
                    else:
                        resultado['alerta'] = ''
                        resultado['precio_inferior'] = False
                except Exception as e:
                    resultado['alerta'] = ''
                    resultado['precio_inferior'] = False
                
                with progress_lock:
                    estado['resultados'].append(resultado)
                    estado['progreso'] = len(estado['resultados'])
                    estado['mensaje'] = f'Buscando: {producto.get("sku", producto.get("titulo", "...")[:20])}'
        
        # Ejecutar workers
        with ThreadPoolExecutor(max_workers=len(drivers)) as executor:
            futures = [executor.submit(worker, d, i) for i, d in enumerate(drivers)]
            for f in futures:
                f.result()
        
        # Guardar resultados en Excel profesional
        with progress_lock:
            resultados = estado['resultados']
            
            # Guardar en el escritorio del usuario con formato profesional
            desktop = os.path.expanduser('~/Desktop')
            filename = f'resultado_dusa_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            filepath_resultado = os.path.join(desktop, filename)
            
            try:
                generar_excel_profesional(resultados, filepath_resultado)
            except Exception as e:
                # Fallback a /tmp si falla el escritorio
                filepath_resultado = os.path.join('/tmp', filename)
                generar_excel_profesional(resultados, filepath_resultado)
                print(f"[Excel] Guardado en /tmp: {filepath_resultado}")
            
            estado['archivo_resultado'] = filepath_resultado
            estado['procesando'] = False
            estado['mensaje'] = f'✅ Completado: {len(resultados)} productos. Excel guardado en Escritorio.'
            
    finally:
        # Cerrar drivers y limpiar lista global
        for d in drivers:
            try:
                d.quit()
            except:
                pass
        # Limpiar lista global
        with drivers_lock:
            active_drivers.clear()
        with progress_lock:
            estado['ventanas_activas'] = 0


def find_free_port():
    """Encuentra un puerto libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


if __name__ == '__main__':
    port = find_free_port()
    url = f'http://127.0.0.1:{port}'
    
    print("=" * 50)
    print("📦 VERIFICADOR DUSA - Tu Planilla")
    print("=" * 50)
    print(f"\n✅ Abriendo en: {url}")
    print("\n⚠️  No cierres esta ventana mientras usas la app")
    print("   Presiona Ctrl+C para cerrar\n")
    
    # Abrir navegador
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    
    # Iniciar servidor
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
