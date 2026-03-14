#!/bin/bash
# =========================================
# Verificador DUSA - Iniciador Mac
# =========================================
# Doble clic para ejecutar la aplicación
# =========================================

cd "$(dirname "$0")"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    osascript -e 'display alert "Python 3 no encontrado" message "Instala Python desde python.org"'
    exit 1
fi

# Verificar/instalar dependencias
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Instalando dependencias..."
    pip3 install -r requirements.txt
fi

# Ejecutar app
python3 app_tuplanilla.py
