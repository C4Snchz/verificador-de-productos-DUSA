#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Telemetría - Verificador DUSA
=======================================
Envía datos de uso anónimos a tuplanilla.net para analytics.
NO envía contraseñas, solo usuario DUSA para identificar usuarios únicos.
"""

import requests
import platform
import uuid
import json
import os
from datetime import datetime
from pathlib import Path

# Configuración del servidor
API_BASE_URL = "https://tuplanilla.net/api/verificador"
VERSION_APP = "1.0.4"

# Archivo local para cache del device_id
CACHE_DIR = Path.home() / ".verificador_dusa"
CACHE_FILE = CACHE_DIR / "device.json"


def get_device_id():
    """
    Obtiene o genera un ID único para este dispositivo.
    Se guarda localmente para identificar el mismo dispositivo.
    """
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('device_id')
        
        # Generar nuevo ID
        device_id = str(uuid.uuid4())
        with open(CACHE_FILE, 'w') as f:
            json.dump({'device_id': device_id}, f)
        
        return device_id
    except Exception:
        # Si hay error, generar ID temporal
        return str(uuid.uuid4())


def get_device_info():
    """Obtiene información del sistema operativo."""
    return {
        'os': platform.system(),  # Windows, Darwin (Mac), Linux
        'os_version': platform.release(),
        'machine': platform.machine(),  # x86_64, arm64
        'python_version': platform.python_version()
    }


def get_location_from_ip():
    """
    Obtiene ubicación aproximada basada en IP.
    Usa un servicio gratuito de geolocalización.
    """
    try:
        # Servicio gratuito que no requiere API key
        response = requests.get('http://ip-api.com/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'ip': data.get('query'),
                'country': data.get('country'),
                'country_code': data.get('countryCode'),
                'region': data.get('regionName'),
                'city': data.get('city'),
                'timezone': data.get('timezone'),
                'isp': data.get('isp')
            }
    except Exception:
        pass
    
    return {'ip': 'unknown', 'country': 'unknown'}


class Telemetria:
    """Clase para manejar telemetría de la aplicación."""
    
    def __init__(self, dusa_usuario: str = None, dusa_cliente: str = None):
        self.device_id = get_device_id()
        self.device_info = get_device_info()
        self.dusa_usuario = dusa_usuario
        self.dusa_cliente = dusa_cliente
        self.session_id = str(uuid.uuid4())[:8]
        self.productos_verificados = 0
        
    def _send(self, endpoint: str, data: dict) -> bool:
        """Envía datos al servidor de telemetría."""
        try:
            payload = {
                'device_id': self.device_id,
                'session_id': self.session_id,
                'version': VERSION_APP,
                'timestamp': datetime.utcnow().isoformat(),
                **self.device_info,
                **data
            }
            
            response = requests.post(
                f"{API_BASE_URL}/{endpoint}",
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            return response.status_code == 200
        except Exception as e:
            # Silencioso - no interrumpir la app si falla telemetría
            print(f"[Telemetría] Aviso: {e}")
            return False
    
    def registrar_inicio(self):
        """Registra el inicio de la aplicación."""
        location = get_location_from_ip()
        
        data = {
            'event': 'app_start',
            'dusa_usuario': self.dusa_usuario,
            'dusa_cliente': self.dusa_cliente,
            **location
        }
        
        return self._send('evento', data)
    
    def registrar_login(self, usuario: str, cliente: str):
        """Registra cuando el usuario hace login en DUSA."""
        self.dusa_usuario = usuario
        self.dusa_cliente = cliente
        
        data = {
            'event': 'login',
            'dusa_usuario': usuario,
            'dusa_cliente': cliente
        }
        
        return self._send('evento', data)
    
    def registrar_verificacion(self, productos_count: int, tiempo_segundos: float):
        """Registra una verificación completada."""
        self.productos_verificados += productos_count
        
        data = {
            'event': 'verificacion',
            'dusa_usuario': self.dusa_usuario,
            'dusa_cliente': self.dusa_cliente,
            'productos_verificados': productos_count,
            'tiempo_segundos': tiempo_segundos,
            'productos_totales_sesion': self.productos_verificados
        }
        
        return self._send('evento', data)
    
    def registrar_cierre(self):
        """Registra el cierre de la aplicación."""
        data = {
            'event': 'app_close',
            'dusa_usuario': self.dusa_usuario,
            'productos_totales_sesion': self.productos_verificados
        }
        
        return self._send('evento', data)


def check_for_updates() -> dict:
    """
    Verifica si hay actualizaciones disponibles.
    Retorna info de la última versión.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/version",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            return {
                'update_available': data.get('version', VERSION_APP) != VERSION_APP,
                'latest_version': data.get('version'),
                'download_url': data.get('download_url'),
                'changelog': data.get('changelog', ''),
                'mandatory': data.get('mandatory', False)
            }
    except Exception:
        pass
    
    return {
        'update_available': False,
        'latest_version': VERSION_APP
    }


# Instancia global para uso fácil
_telemetria = None


def init_telemetria(dusa_usuario: str = None, dusa_cliente: str = None):
    """Inicializa la telemetría global."""
    global _telemetria
    _telemetria = Telemetria(dusa_usuario, dusa_cliente)
    return _telemetria


def get_telemetria() -> Telemetria:
    """Obtiene la instancia global de telemetría."""
    global _telemetria
    if _telemetria is None:
        _telemetria = Telemetria()
    return _telemetria


# Ejemplo de uso
if __name__ == "__main__":
    print("🔍 Test de Telemetría")
    print("-" * 40)
    
    # Info del dispositivo
    print(f"Device ID: {get_device_id()}")
    print(f"Device Info: {get_device_info()}")
    print(f"Location: {get_location_from_ip()}")
    
    # Test de actualizaciones
    print(f"\nCheck updates: {check_for_updates()}")
    
    # Test de envío (fallará si el servidor no está configurado)
    tel = init_telemetria("test_usuario", "1234")
    tel.registrar_inicio()
    print("\n✅ Test completado")
