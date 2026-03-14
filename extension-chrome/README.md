# Extensión Chrome - Verificador DUSA

Extensión de Chrome que verifica la disponibilidad y precios de productos en el sistema DUSA, ejecutándose completamente en el navegador del usuario.

## Características

- ✅ **Sin servidor requerido** - Todo se ejecuta en tu navegador
- ✅ **Procesamiento paralelo** - Hasta 6 ventanas simultáneas para mayor velocidad
- ✅ **Lee archivos Excel** - Carga tu lista de productos directamente
- ✅ **Exporta resultados** - Descarga los resultados en Excel
- ✅ **Tiempo estimado** - Muestra cuánto falta para terminar

## Instalación

### Opción 1: Cargar como extensión sin empaquetar (Desarrollo)

1. Abre Chrome y ve a `chrome://extensions/`
2. Activa el **Modo de desarrollador** (esquina superior derecha)
3. Haz clic en **Cargar descomprimida**
4. Selecciona la carpeta `extension-chrome`
5. ¡Listo! Verás el ícono de la extensión en la barra de herramientas

### Opción 2: Instalar desde archivo CRX

Si tienes el archivo `.crx` empaquetado:
1. Arrastra el archivo `.crx` a la página `chrome://extensions/`
2. Confirma la instalación

## Uso

1. **Abre DUSA** - Ve a `https://pedidos.dusa.com.uy/DUSAWebUI` e inicia sesión
2. **Abre la extensión** - Haz clic en el ícono del verificador
3. **Carga tu archivo Excel** - Arrastra o selecciona tu archivo
4. **Selecciona la columna** - Elige la columna que contiene los códigos de barras
5. **Configura las ventanas** - Elige cuántas ventanas paralelas usar:
   - 1 ventana: Más lento, menos recursos
   - 3 ventanas: Recomendado
   - 6 ventanas: Más rápido, usa más recursos
6. **Inicia la verificación** - Haz clic en "Iniciar Verificación"
7. **Descarga los resultados** - Al finalizar, descarga el Excel con los resultados

## Notas técnicas

- La extensión usa `chrome.tabs` para abrir ventanas adicionales
- Los content scripts se inyectan automáticamente en las páginas de DUSA
- La librería SheetJS (XLSX) está incluida para leer/escribir archivos Excel

## Permisos requeridos

- `activeTab`: Interactuar con la pestaña activa
- `tabs`: Crear y gestionar pestañas para procesamiento paralelo
- `storage`: Guardar preferencias
- `scripting`: Inyectar scripts en las páginas de DUSA
- Acceso a `pedidos.dusa.com.uy`: Para interactuar con el sistema DUSA
