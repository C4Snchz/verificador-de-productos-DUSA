#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Endpoints para Verificador DUSA - tuplanilla.net
=====================================================
Endpoints para recibir telemetría y servir actualizaciones.
Agregar estas rutas a main.py de tuplanilla.net
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os

# Crear blueprint para importar fácilmente
verificador_bp = Blueprint('verificador', __name__, url_prefix='/api/verificador')

# Archivo para guardar eventos (en producción usar PostgreSQL)
EVENTOS_FILE = 'verificador_eventos.json'
VERSION_FILE = 'verificador_version.json'

# Versión actual de la app
VERSION_ACTUAL = {
    'version': '1.0.0',
    'download_url_windows': 'https://tuplanilla.net/descargas/verificador-dusa-windows.exe',
    'download_url_mac': 'https://tuplanilla.net/descargas/verificador-dusa-mac.zip',
    'changelog': 'Versión inicial',
    'mandatory': False
}


def cargar_eventos():
    """Carga eventos del archivo JSON."""
    try:
        if os.path.exists(EVENTOS_FILE):
            with open(EVENTOS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def guardar_evento(evento):
    """Guarda un evento en el archivo JSON."""
    eventos = cargar_eventos()
    eventos.append(evento)
    
    with open(EVENTOS_FILE, 'w') as f:
        json.dump(eventos, f, indent=2, default=str)


@verificador_bp.route('/evento', methods=['POST'])
def recibir_evento():
    """
    Recibe eventos de telemetría de la app.
    
    Datos esperados:
    - device_id: ID único del dispositivo
    - session_id: ID de la sesión actual
    - version: Versión de la app
    - event: Tipo de evento (app_start, login, verificacion, app_close)
    - dusa_usuario: Usuario de DUSA (para identificar cliente)
    - dusa_cliente: Código de cliente DUSA
    - os, os_version: Info del sistema
    - ip, country, city: Ubicación (solo en app_start)
    - productos_verificados: Cantidad de productos (solo en verificacion)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # Agregar timestamp del servidor
        data['server_timestamp'] = datetime.utcnow().isoformat()
        data['server_ip'] = request.remote_addr
        
        # Guardar evento
        guardar_evento(data)
        
        # Log para debug
        event_type = data.get('event', 'unknown')
        usuario = data.get('dusa_usuario', 'anon')
        print(f"[Verificador] {event_type} - Usuario: {usuario}")
        
        return jsonify({'status': 'ok', 'received': True})
    
    except Exception as e:
        print(f"[Verificador] Error: {e}")
        return jsonify({'error': str(e)}), 500


@verificador_bp.route('/version', methods=['GET'])
def obtener_version():
    """
    Retorna la versión actual de la app para auto-update.
    """
    return jsonify(VERSION_ACTUAL)


@verificador_bp.route('/stats', methods=['GET'])
def obtener_estadisticas():
    """
    Retorna estadísticas de uso (proteger con auth en producción).
    """
    eventos = cargar_eventos()
    
    # Usuarios únicos
    usuarios = set()
    dispositivos = set()
    verificaciones_total = 0
    productos_total = 0
    
    for evento in eventos:
        if evento.get('dusa_usuario'):
            usuarios.add(evento['dusa_usuario'])
        if evento.get('device_id'):
            dispositivos.add(evento['device_id'])
        if evento.get('event') == 'verificacion':
            verificaciones_total += 1
            productos_total += evento.get('productos_verificados', 0)
    
    return jsonify({
        'usuarios_unicos': len(usuarios),
        'dispositivos_unicos': len(dispositivos),
        'verificaciones_total': verificaciones_total,
        'productos_verificados': productos_total,
        'eventos_total': len(eventos)
    })


@verificador_bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    """
    Lista todos los usuarios que han usado la app.
    Proteger con autenticación en producción.
    """
    eventos = cargar_eventos()
    
    usuarios = {}
    
    for evento in eventos:
        usuario = evento.get('dusa_usuario')
        if not usuario:
            continue
        
        if usuario not in usuarios:
            usuarios[usuario] = {
                'usuario': usuario,
                'cliente': evento.get('dusa_cliente'),
                'primera_vez': evento.get('server_timestamp'),
                'ultima_vez': evento.get('server_timestamp'),
                'pais': evento.get('country'),
                'ciudad': evento.get('city'),
                'os': evento.get('os'),
                'version_app': evento.get('version'),
                'verificaciones': 0,
                'productos_totales': 0
            }
        
        # Actualizar última vez
        usuarios[usuario]['ultima_vez'] = evento.get('server_timestamp')
        
        # Contar verificaciones
        if evento.get('event') == 'verificacion':
            usuarios[usuario]['verificaciones'] += 1
            usuarios[usuario]['productos_totales'] += evento.get('productos_verificados', 0)
    
    # Convertir a lista ordenada por última actividad
    lista_usuarios = sorted(
        usuarios.values(),
        key=lambda x: x['ultima_vez'] or '',
        reverse=True
    )
    
    return jsonify(lista_usuarios)


# ============================================================
# CÓDIGO PARA INTEGRAR EN main.py DE TUPLANILLA.NET
# ============================================================
"""
Para integrar estos endpoints en tuplanilla.net, agregar en main.py:

# Al inicio del archivo:
from verificador_api import verificador_bp

# Después de crear la app Flask:
app.register_blueprint(verificador_bp)

O si prefieres copiar las rutas directamente sin blueprint,
adaptar las funciones cambiando @verificador_bp.route por @app.route
y ajustando el prefix /api/verificador/ manualmente.
"""


# ============================================================
# VERSIÓN PARA USAR CON POSTGRESQL (PRODUCCIÓN)
# ============================================================
"""
Para producción con PostgreSQL, crear tabla:

CREATE TABLE verificador_eventos (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50),
    session_id VARCHAR(20),
    event VARCHAR(30),
    dusa_usuario VARCHAR(50),
    dusa_cliente VARCHAR(20),
    version VARCHAR(20),
    os VARCHAR(30),
    os_version VARCHAR(50),
    ip VARCHAR(50),
    country VARCHAR(50),
    city VARCHAR(100),
    productos_verificados INTEGER,
    tiempo_segundos FLOAT,
    client_timestamp TIMESTAMP,
    server_timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dusa_usuario ON verificador_eventos(dusa_usuario);
CREATE INDEX idx_event ON verificador_eventos(event);
CREATE INDEX idx_server_timestamp ON verificador_eventos(server_timestamp);

-- Vista de usuarios únicos
CREATE VIEW verificador_usuarios AS
SELECT 
    dusa_usuario,
    dusa_cliente,
    MIN(server_timestamp) as primera_vez,
    MAX(server_timestamp) as ultima_vez,
    COUNT(*) FILTER (WHERE event = 'verificacion') as verificaciones,
    SUM(productos_verificados) as productos_totales,
    MAX(country) as pais,
    MAX(city) as ciudad,
    MAX(os) as os 
FROM verificador_eventos
WHERE dusa_usuario IS NOT NULL
GROUP BY dusa_usuario, dusa_cliente;
"""
