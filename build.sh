#!/bin/bash
# =============================================================================
# Script de Build - Verificador DUSA
# =============================================================================
# Genera ejecutables para Windows y Mac usando PyInstaller
#
# Uso:
#   ./build.sh           # Genera para la plataforma actual
#   ./build.sh windows   # Genera para Windows (requiere Wine en Mac/Linux)
#   ./build.sh mac       # Genera para Mac
#   ./build.sh all       # Genera para todas las plataformas
#

set -e

echo "=========================================="
echo "🔨 Build - Verificador DUSA TuPlanilla"
echo "=========================================="

# Verificar que PyInstaller está instalado
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller no encontrado. Instalando..."
    pip install pyinstaller
fi

# Crear directorio de salida
mkdir -p dist
mkdir -p build

# Limpiar builds anteriores
echo "🧹 Limpiando builds anteriores..."
rm -rf build/*
rm -rf dist/*

# Determinar plataforma
PLATFORM=$1
if [ -z "$PLATFORM" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="mac"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        PLATFORM="windows"
    else
        PLATFORM="linux"
    fi
fi

echo "🎯 Plataforma objetivo: $PLATFORM"

build_app() {
    echo ""
    echo "📦 Generando ejecutable..."
    
    pyinstaller verificador_dusa.spec --clean --noconfirm
    
    echo ""
    echo "✅ Build completado!"
    echo ""
    echo "📁 Archivos generados en: dist/"
    ls -la dist/
}

# Ejecutar build
case $PLATFORM in
    "mac")
        build_app
        echo ""
        echo "📱 Para distribuir en Mac:"
        echo "   1. Comprime 'Verificador DUSA.app' en ZIP"
        echo "   2. Sube a tuplanilla.net/descargas/"
        ;;
    "windows")
        build_app
        echo ""
        echo "🪟 Para distribuir en Windows:"
        echo "   1. El archivo .exe está listo para distribuir"
        echo "   2. Sube a tuplanilla.net/descargas/"
        ;;
    "all")
        echo "⚠️  Para generar para todas las plataformas,"
        echo "   debes ejecutar este script en cada sistema operativo"
        echo "   o usar un servicio de CI/CD como GitHub Actions."
        ;;
    *)
        build_app
        ;;
esac

echo ""
echo "=========================================="
echo "🎉 Build finalizado"
echo "=========================================="
