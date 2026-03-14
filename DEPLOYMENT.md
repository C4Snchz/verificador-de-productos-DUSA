# Verificador DUSA - TuPlanilla Edition
## Guía de Deployment y Analytics

---

## 📁 Archivos del Sistema

| Archivo | Descripción |
|---------|-------------|
| `app_tuplanilla.py` | App principal empaquetable |
| `telemetria.py` | Módulo de telemetría (envía datos a tuplanilla.net) |
| `verificador_api_server.py` | Endpoints API para tuplanilla.net |
| `verificador_dusa.spec` | Config de PyInstaller |
| `build.sh` | Script para generar ejecutables |

---

## 🚀 Deployment Rápido

### 1. Agregar endpoints a tuplanilla.net

En `main.py` de Gestor_de_Pedidos_FarmaUY:

```python
# Al inicio
from verificador_api_server import verificador_bp

# Después de crear app = Flask(...)
app.register_blueprint(verificador_bp)
```

### 2. Generar ejecutable

```bash
cd verificador-dusa

# Instalar dependencias
pip install pyinstaller

# Generar (Mac)
chmod +x build.sh
./build.sh

# O directamente:
pyinstaller verificador_dusa.spec
```

### 3. Subir a tuplanilla.net

- Mac: Comprime `dist/Verificador DUSA.app` → sube como ZIP
- Windows: Sube `dist/VerificadorDUSA.exe`

---

## 📊 Datos que se Recopilan

| Campo | Descripción |
|-------|-------------|
| `device_id` | ID único del dispositivo (generado localmente) |
| `dusa_usuario` | Usuario de DUSA (**solo para identificar, NO password**) |
| `dusa_cliente` | Código de cliente DUSA |
| `os`, `os_version` | Sistema operativo |
| `ip`, `country`, `city` | Ubicación aproximada |
| `productos_verificados` | Cantidad de productos procesados |
| `version` | Versión de la app |

---

## 🔍 Ver Analytics

### Endpoints disponibles:

```
GET /api/verificador/stats
→ Estadísticas globales (usuarios únicos, verificaciones, etc.)

GET /api/verificador/usuarios
→ Lista de usuarios con actividad detallada
```

### Ejemplo respuesta de `/api/verificador/usuarios`:

```json
[
  {
    "usuario": "farmacia.xyz",
    "cliente": "1234",
    "primera_vez": "2026-03-13T10:00:00",
    "ultima_vez": "2026-03-13T15:30:00",
    "pais": "Uruguay",
    "ciudad": "Montevideo",
    "os": "Windows",
    "verificaciones": 15,
    "productos_totales": 450
  }
]
```

---

## 🔄 Sistema de Actualizaciones

La app verifica automáticamente si hay nuevas versiones.

### Para publicar una actualización:

1. Modifica `VERSION_ACTUAL` en `verificador_api_server.py`:

```python
VERSION_ACTUAL = {
    'version': '1.1.0',  # Nueva versión
    'download_url_windows': 'https://tuplanilla.net/descargas/verificador-dusa-windows-1.1.0.exe',
    'download_url_mac': 'https://tuplanilla.net/descargas/verificador-dusa-mac-1.1.0.zip',
    'changelog': 'Mejoras de velocidad y corrección de bugs',
    'mandatory': False  # True si es crítica
}
```

2. Sube los nuevos ejecutables

3. Los usuarios verán el badge "Actualizar" al abrir la app

---

## 🗄️ PostgreSQL (Producción)

Para almacenar eventos en PostgreSQL en lugar de JSON:

```sql
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
CREATE INDEX idx_server_timestamp ON verificador_eventos(server_timestamp);
```

---

## 📱 Landing Page

Agregar en tuplanilla.net una página de descarga:

```
/verificador-dusa
  ├── Descripción del producto
  ├── Botón "Descargar para Windows"
  ├── Botón "Descargar para Mac"
  └── Términos de uso (mencionar telemetría)
```

---

## ⚠️ Consideraciones Legales

1. **Incluir en landing/app**: "Esta aplicación envía datos de uso anónimos para mejorar el servicio"
2. **NO** se almacenan contraseñas, solo usuario DUSA
3. Datos de ubicación son aproximados (basados en IP)
