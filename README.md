# Verificador de Disponibilidad DUSA

Este programa verifica la disponibilidad de productos en el sistema de DUSA (proveedor) comparándolos con tu inventario de Mercado Libre.

## 📋 Requisitos

- Python 3.8 o superior
- Google Chrome instalado
- Acceso a pedidos.dusa.com.uy

## 🚀 Instalación

### 1. Crear entorno virtual (recomendado)

```bash
cd /Users/carlossanchez/Documents/GitHub/verificador-dusa
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciales

Edita el archivo `config.py` y completa:

```python
DUSA_USUARIO = "tu_usuario_real"
DUSA_PASSWORD = "tu_contraseña_real"
```

### 4. Preparar archivo Excel

Coloca tu archivo Excel de Mercado Libre en la carpeta del proyecto con el nombre `productos_mercadolibre.xlsx` (o edita `config.py` para usar otro nombre).

## ▶️ Uso

```bash
python verificador_dusa.py
```

El programa:
1. Leerá tu Excel de Mercado Libre
2. Iniciará sesión en DUSA automáticamente
3. Buscará cada producto por SKU (o título si no hay SKU)
4. Verificará disponibilidad y precio
5. Generará `resultados_verificacion.xlsx` con toda la información

## ⚙️ Configuración

Edita `config.py` para personalizar:

| Variable | Descripción |
|----------|-------------|
| `DUSA_USUARIO` | Tu usuario de DUSA |
| `DUSA_PASSWORD` | Tu contraseña de DUSA |
| `EXCEL_ENTRADA` | Nombre del archivo Excel de origen |
| `EXCEL_SALIDA` | Nombre del archivo de resultados |
| `COLUMNA_SKU` | Nombre de la columna con SKU |
| `COLUMNA_TITULO` | Nombre de la columna con título |
| `ESPERA_ENTRE_BUSQUEDAS` | Segundos entre cada búsqueda |
| `MOSTRAR_NAVEGADOR` | True para ver el navegador, False para modo oculto |

## 📊 Resultado

El archivo `resultados_verificacion.xlsx` contendrá:

| Columna | Descripción |
|---------|-------------|
| SKU (ML) | SKU de Mercado Libre |
| Título (ML) | Título del producto en ML |
| Nº Publicación | Número de publicación en ML |
| Encontrado en DUSA | Si se encontró el producto |
| Disponible | Si está disponible para compra |
| Nombre (DUSA) | Nombre del producto en DUSA |
| Precio (DUSA) | Precio del proveedor |
| Precio (ML) | Tu precio en Mercado Libre |
| Stock (ML) | Tu stock actual |
| Observaciones | Notas adicionales |

## ⚠️ Importante: Ajustar Selectores

El script necesita ser ajustado a la estructura real de la página de DUSA. 

### Pasos para ajustar:

1. **Ejecuta con `MOSTRAR_NAVEGADOR = True`** para ver qué pasa
2. **Abre las herramientas de desarrollador** (F12) en Chrome
3. **Inspecciona los elementos** del formulario de login y buscador
4. **Actualiza los selectores** en `verificador_dusa.py`:
   - `login()`: Selectores del formulario de login
   - `buscar_producto()`: Selectores del buscador y resultados

### Ejemplo de cómo encontrar selectores:

```python
# Si el campo de usuario tiene id="txtUsuario":
campo_usuario = self.driver.find_element(By.ID, "txtUsuario")

# Si el campo tiene una clase específica:
campo_usuario = self.driver.find_element(By.CLASS_NAME, "input-usuario")

# Si necesitas usar XPath:
campo_usuario = self.driver.find_element(By.XPATH, "//input[@placeholder='Usuario']")
```

## 🔧 Solución de Problemas

### "No se encontró el formulario de login"
- Verifica que la URL sea correcta
- La página puede haber cambiado, ajusta los selectores

### "chromedriver no compatible"
- Actualiza Google Chrome a la última versión
- El script descargará automáticamente el driver correcto

### Los productos no se encuentran
- Verifica que el buscador funcione manualmente
- Ajusta los selectores de búsqueda
- Aumenta `ESPERA_ENTRE_BUSQUEDAS` si la página es lenta

## 📁 Estructura del Proyecto

```
verificador-dusa/
├── config.py                    # Configuración
├── verificador_dusa.py          # Script principal
├── requirements.txt             # Dependencias
├── README.md                    # Este archivo
├── productos_mercadolibre.xlsx  # Tu archivo de entrada
└── resultados_verificacion.xlsx # Archivo generado
```

## 🛡️ Seguridad

- **No compartas `config.py`** con tus credenciales
- Considera usar variables de entorno para las credenciales
- El archivo `.gitignore` debería excluir `config.py`

## 📝 Licencia

Uso interno - Todos los derechos reservados
