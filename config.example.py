# ===========================================
# ARCHIVO DE EJEMPLO - Copia a config.py
# ===========================================
# cp config.example.py config.py
# Luego edita config.py con tus datos reales

# Credenciales de DUSA
DUSA_USUARIO = "tu_usuario_aqui"
DUSA_PASSWORD = "tu_password_aqui"

# URL base de DUSA
DUSA_URL = "https://pedidos.dusa.com.uy/DUSAWebUI"

# Ruta al archivo Excel de Mercado Libre (entrada)
EXCEL_ENTRADA = "productos_mercadolibre.xlsx"

# Ruta al archivo Excel de resultados (salida)
EXCEL_SALIDA = "resultados_verificacion.xlsx"

# Columnas del Excel de Mercado Libre
COLUMNA_SKU = "SKU"
COLUMNA_TITULO = "Título"

# Tiempo de espera entre búsquedas (segundos)
ESPERA_ENTRE_BUSQUEDAS = 2

# Mostrar navegador (False = modo headless)
MOSTRAR_NAVEGADOR = True
