#!/bin/bash
# ===========================================
# Verificador DUSA - Click para ejecutar
# ===========================================

cd "$(dirname "$0")"

echo ""
echo "🚀 Iniciando Verificador DUSA..."
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado"
    echo "   Instálalo desde python.org"
    read -p "Presiona Enter para salir..."
    exit 1
fi

# Verificar/instalar dependencias
echo "📦 Verificando dependencias..."
pip3 install flask pandas openpyxl selenium webdriver-manager --quiet 2>/dev/null

# Ejecutar la aplicación web
python3 app_web.py

echo ""
read -p "Presiona Enter para cerrar..."