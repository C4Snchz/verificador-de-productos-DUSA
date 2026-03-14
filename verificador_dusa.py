#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador de Disponibilidad DUSA
==================================
Este script lee productos de un Excel de Mercado Libre,
busca cada uno en el sistema DUSA y verifica disponibilidad y precio.

Autor: Tu nombre
Fecha: 2026
"""

import pandas as pd
import time
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Importar configuración
import config


class VerificadorDUSA:
    """Clase principal para verificar productos en DUSA."""
    
    def __init__(self):
        """Inicializa el verificador."""
        self.driver = None
        self.resultados = []
        
    def iniciar_navegador(self):
        """Inicia el navegador Chrome con Selenium."""
        print("🌐 Iniciando navegador...")
        
        opciones = Options()
        
        if not config.MOSTRAR_NAVEGADOR:
            opciones.add_argument("--headless")
        
        opciones.add_argument("--no-sandbox")
        opciones.add_argument("--disable-dev-shm-usage")
        opciones.add_argument("--window-size=1920,1080")
        opciones.add_argument("--disable-gpu")
        
        # Instalar/usar ChromeDriver automáticamente
        servicio = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=servicio, options=opciones)
        self.driver.implicitly_wait(10)
        
        print("✅ Navegador iniciado correctamente")
        
    def login(self):
        """
        Inicia sesión en el sistema DUSA.
        Selectores ajustados para Vaadin/GWT.
        """
        print(f"🔐 Iniciando sesión en DUSA...")
        
        try:
            self.driver.get(config.DUSA_URL)
            time.sleep(4)  # Esperar a que cargue la SPA de Vaadin
            
            # Esperar a que aparezca el formulario de login
            wait = WebDriverWait(self.driver, 20)
            
            # El formulario tiene id="loginf" y usa clases Vaadin
            # Los campos de texto tienen clase "v-textfield linea-form"
            
            # Buscar todos los inputs de texto dentro del form de login
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#loginf, #login, form"))
            )
            
            # Buscar los campos por su posición (Usuario, Contraseña, Cliente)
            campos_texto = self.driver.find_elements(
                By.CSS_SELECTOR, "input.v-textfield.linea-form, input.linea-form, #loginf input[type='text']"
            )
            
            if len(campos_texto) >= 1:
                # Primer campo: Usuario
                campos_texto[0].clear()
                campos_texto[0].send_keys(config.DUSA_USUARIO)
                print("   ✓ Usuario ingresado")
            
            # Campo de contraseña
            campo_password = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='password'], input.v-textfield[type='password']"
            )
            campo_password.clear()
            campo_password.send_keys(config.DUSA_PASSWORD)
            print("   ✓ Contraseña ingresada")
            
            # Campo de cliente (tercer campo de texto)
            if len(campos_texto) >= 2:
                # El campo de cliente puede ser el segundo campo de texto
                # (después del usuario, el password es de otro tipo)
                for campo in campos_texto[1:]:
                    if campo.get_attribute('type') == 'text':
                        campo.clear()
                        campo.send_keys(config.DUSA_CLIENTE)
                        print("   ✓ Cliente ingresado")
                        break
            
            time.sleep(1)
            
            # Buscar botón de login - en Vaadin suele ser un div con role button o clase v-button
            boton_login = self.driver.find_element(
                By.CSS_SELECTOR, ".v-button, button, input[type='submit'], div[role='button'], .v-button-caption"
            )
            boton_login.click()
            print("   ✓ Clic en Entrar")
            
            # Esperar a que se complete el login
            time.sleep(5)
            
            # Verificar si el login fue exitoso - buscar que desaparezca el form de login
            try:
                # Si ya no existe el form de login, el login fue exitoso
                self.driver.find_element(By.CSS_SELECTOR, "#loginf")
                print("⚠️  El formulario de login sigue visible - posible error de credenciales")
                return False
            except NoSuchElementException:
                print("✅ Login exitoso")
                # Navegar a la sección de productos
                self.ir_a_productos()
                return True
            
        except TimeoutException:
            print("❌ Error: No se encontró el formulario de login")
            print("   Por favor verifica que la URL es correcta")
            return False
        except Exception as e:
            print(f"❌ Error en login: {str(e)}")
            return False
    
    def ir_a_productos(self):
        """Navega a la sección de Ver Productos."""
        print("📦 Navegando a Ver Productos...")
        self.driver.get(config.DUSA_URL + "#!micuenta/productos")
        time.sleep(3)
        print("✅ En sección de productos")
    
    def extraer_palabras_clave(self, titulo):
        """
        Extrae palabras clave de un título largo de ML.
        Ejemplo: "Actron 600 Analgesico Farmauy" -> "Actron 600"
        """
        if not titulo or titulo == "nan":
            return ""
        
        # Palabras a ignorar (marcas propias, palabras genéricas)
        palabras_ignorar = [
            "farmauy", "farmacia", "original", "sellado", "envio", "gratis",
            "pack", "combo", "oferta", "promo", "nuevo", "garantia", "oficial",
            "uruguay", "importado", "nacional", "unidad", "unidades", "caja",
            "blister", "sobre", "sachet", "frasco", "tubo", "pomo"
        ]
        
        palabras = titulo.split()
        palabras_filtradas = []
        
        for palabra in palabras[:5]:  # Tomar máximo 5 primeras palabras
            palabra_limpia = palabra.lower().strip()
            if palabra_limpia not in palabras_ignorar and len(palabra_limpia) > 2:
                palabras_filtradas.append(palabra)
        
        # Retornar las primeras 3 palabras clave
        return " ".join(palabras_filtradas[:3])
    
    def buscar_producto(self, sku, titulo):
        """
        Busca un producto en DUSA, primero por SKU, luego por nombre.
        
        Args:
            sku: SKU del producto
            titulo: Título del producto de ML
            
        Returns:
            dict con información del producto
        """
        resultado = {
            "termino_busqueda": "",
            "encontrado": False,
            "disponible": None,
            "precio_dusa": None,
            "nombre_dusa": None,
            "oferta_dusa": None,
            "laboratorio": None,
            "mensaje": ""
        }
        
        # Intentar búsqueda por SKU primero
        if sku and sku != "nan":
            resultado_busqueda = self._realizar_busqueda(sku)
            if resultado_busqueda["encontrado"]:
                resultado_busqueda["termino_busqueda"] = f"SKU: {sku}"
                return resultado_busqueda
        
        # Si no encontró por SKU, buscar por palabras clave del título
        palabras_clave = self.extraer_palabras_clave(titulo)
        if palabras_clave:
            resultado_busqueda = self._realizar_busqueda(palabras_clave)
            resultado_busqueda["termino_busqueda"] = palabras_clave
            return resultado_busqueda
        
        resultado["mensaje"] = "Sin SKU ni título válido"
        return resultado
    
    def _realizar_busqueda(self, termino):
        """
        Realiza la búsqueda en DUSA y extrae resultados.
        """
        resultado = {
            "termino_busqueda": termino,
            "encontrado": False,
            "disponible": None,
            "precio_dusa": None,
            "nombre_dusa": None,
            "oferta_dusa": None,
            "laboratorio": None,
            "mensaje": ""
        }
        
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Buscar el campo de búsqueda (es un input de texto en la página de productos)
            campo_busqueda = wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "input.v-textfield, input[type='text']"
                ))
            )
            
            # Limpiar y escribir el término
            campo_busqueda.clear()
            time.sleep(0.5)
            campo_busqueda.send_keys(termino)
            
            # Buscar y hacer clic en botón "Buscar Productos"
            try:
                boton_buscar = self.driver.find_element(
                    By.XPATH, 
                    "//div[contains(@class, 'v-button')]//span[contains(text(), 'Buscar')]/.."
                )
                boton_buscar.click()
            except:
                # Si no encuentra el botón, enviar Enter
                campo_busqueda.send_keys(Keys.RETURN)
            
            # Esperar a que carguen los resultados
            time.sleep(3)
            
            # Buscar la tabla de resultados
            # La tabla tiene columnas: Stock, Descripción, Laboratorio, Oferta, Precio
            filas = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "table tr, .v-table-row, .v-grid-row"
            )
            
            # Filtrar filas que son resultados (no encabezados)
            filas_datos = []
            for fila in filas:
                texto = fila.text.strip()
                # Ignorar filas de encabezado o vacías
                if texto and "Stock" not in texto and "Descripción" not in texto:
                    filas_datos.append(fila)
            
            if filas_datos:
                # Tomar el primer resultado
                primera_fila = filas_datos[0]
                resultado["encontrado"] = True
                
                # Detectar disponibilidad por el ícono/color
                try:
                    # Buscar ícono rojo (faltante) o verde (disponible)
                    iconos = primera_fila.find_elements(By.CSS_SELECTOR, "img, .v-icon, span")
                    texto_fila = primera_fila.text.lower()
                    
                    # Si contiene "faltante" es no disponible
                    if "faltante" in texto_fila:
                        resultado["disponible"] = False
                        resultado["mensaje"] = "Producto con faltante en laboratorio"
                    else:
                        resultado["disponible"] = True
                        resultado["mensaje"] = "Disponible"
                except:
                    pass
                
                # Extraer datos de las celdas
                celdas = primera_fila.find_elements(By.CSS_SELECTOR, "td, .v-table-cell-content")
                
                if len(celdas) >= 5:
                    # Columnas: Stock(0), Descripción(1), Laboratorio(2), Oferta(3), Precio(4)
                    try:
                        resultado["nombre_dusa"] = celdas[1].text.strip().split('\n')[0]  # Solo primera línea
                    except:
                        pass
                    
                    try:
                        resultado["laboratorio"] = celdas[2].text.strip()
                    except:
                        pass
                    
                    try:
                        resultado["oferta_dusa"] = celdas[3].text.strip()
                    except:
                        pass
                    
                    try:
                        precio_texto = celdas[4].text.strip()
                        resultado["precio_dusa"] = precio_texto
                    except:
                        pass
                elif len(celdas) >= 2:
                    # Formato alternativo
                    resultado["nombre_dusa"] = primera_fila.text.split('\n')[0][:50]
                
            else:
                resultado["mensaje"] = "Sin resultados"
            
            return resultado
            
        except TimeoutException:
            resultado["mensaje"] = "Timeout en búsqueda"
            return resultado
        except Exception as e:
            resultado["mensaje"] = f"Error: {str(e)[:50]}"
            return resultado
    
    def leer_excel_mercadolibre(self, ruta_archivo):
        """
        Lee el archivo Excel de Mercado Libre.
        
        Args:
            ruta_archivo: Ruta al archivo Excel
            
        Returns:
            DataFrame con los productos (filtrado)
        """
        print(f"📖 Leyendo Excel: {ruta_archivo}")
        
        try:
            # Leer hoja específica y saltar filas de encabezado de ML
            df = pd.read_excel(
                ruta_archivo,
                sheet_name=config.HOJA_EXCEL,
                skiprows=config.FILAS_SALTAR
            )
            
            print(f"   Columnas encontradas: {', '.join(df.columns.tolist())}")
            print(f"   Filas totales: {len(df)}")
            
            # Filtrar filas que tienen SKU o Título válido
            df_filtrado = df[
                (df[config.COLUMNA_SKU].notna() & (df[config.COLUMNA_SKU].astype(str) != 'nan')) |
                (df[config.COLUMNA_TITULO].notna() & (df[config.COLUMNA_TITULO].astype(str) != 'nan'))
            ].copy()
            
            # Filtrar filas que son encabezados o instrucciones (como "Obligatorio")
            df_filtrado = df_filtrado[
                ~df_filtrado[config.COLUMNA_STOCK].astype(str).str.contains('Obligatorio|Opcional', case=False, na=False)
            ]
            
            print(f"   Productos válidos: {len(df_filtrado)}")
            
            return df_filtrado
            
        except FileNotFoundError:
            print(f"❌ Error: No se encontró el archivo {ruta_archivo}")
            sys.exit(1)
        except KeyError as e:
            print(f"❌ Error: Columna no encontrada: {e}")
            print(f"   Verifica que HOJA_EXCEL y las columnas en config.py sean correctas")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error leyendo Excel: {str(e)}")
            sys.exit(1)
    
    def procesar_productos(self, df):
        """
        Procesa todos los productos del DataFrame.
        
        Args:
            df: DataFrame con los productos de Mercado Libre
        """
        total = len(df)
        print(f"\n🔍 Iniciando verificación de {total} productos...")
        print("=" * 60)
        
        for idx, (_, row) in enumerate(df.iterrows()):
            # Obtener SKU y título
            sku = str(row.get(config.COLUMNA_SKU, "")).strip()
            titulo = str(row.get(config.COLUMNA_TITULO, "")).strip()
            
            if (not sku or sku == "nan") and (not titulo or titulo == "nan"):
                print(f"⚠️  [{idx+1}/{total}] Producto sin SKU ni título, saltando...")
                continue
            
            # Mostrar qué estamos buscando
            display = sku if sku and sku != "nan" else titulo[:40]
            print(f"🔎 [{idx+1}/{total}] {display}...")
            
            # Buscar el producto (intenta SKU primero, luego palabras clave del título)
            resultado = self.buscar_producto(sku, titulo)
            
            # Agregar información original de ML
            resultado["sku_ml"] = sku
            resultado["titulo_ml"] = titulo
            resultado["numero_publicacion"] = row.get(config.COLUMNA_PUBLICACION, "")
            resultado["precio_ml"] = row.get(config.COLUMNA_PRECIO, "")
            resultado["stock_ml"] = row.get(config.COLUMNA_STOCK, "")
            resultado["estado_ml"] = row.get(config.COLUMNA_ESTADO, "")
            
            self.resultados.append(resultado)
            
            # Mostrar resultado
            if resultado["encontrado"]:
                if resultado.get("disponible"):
                    print(f"   ✅ Disponible | Precio: ${resultado.get('precio_dusa', 'N/A')} | Oferta: {resultado.get('oferta_dusa', '-')}")
                else:
                    print(f"   ❌ FALTANTE - {resultado.get('mensaje', '')}")
            else:
                print(f"   ⚠️  No encontrado: {resultado.get('mensaje', '')}")
            
            # Esperar entre búsquedas para no sobrecargar el servidor
            time.sleep(config.ESPERA_ENTRE_BUSQUEDAS)
        
        print("=" * 60)
        print(f"✅ Verificación completada")
    
    def generar_excel_resultados(self, ruta_salida):
        """
        Genera el Excel con los resultados de la verificación.
        
        Args:
            ruta_salida: Ruta donde guardar el archivo
        """
        print(f"\n📝 Generando Excel de resultados...")
        
        # Crear DataFrame con resultados
        df_resultados = pd.DataFrame(self.resultados)
        
        # Reordenar columnas
        columnas_orden = [
            "sku_ml",
            "titulo_ml",
            "numero_publicacion",
            "estado_ml",
            "termino_busqueda",
            "encontrado",
            "disponible",
            "nombre_dusa",
            "laboratorio",
            "oferta_dusa",
            "precio_dusa",
            "precio_ml",
            "stock_ml",
            "mensaje"
        ]
        
        # Solo incluir columnas que existan
        columnas_finales = [c for c in columnas_orden if c in df_resultados.columns]
        df_resultados = df_resultados[columnas_finales]
        
        # Renombrar columnas para el Excel final
        nombres_columnas = {
            "sku_ml": "SKU (ML)",
            "titulo_ml": "Título (ML)",
            "numero_publicacion": "Nº Publicación",
            "estado_ml": "Estado (ML)",
            "termino_busqueda": "Búsqueda realizada",
            "encontrado": "Encontrado",
            "disponible": "Disponible",
            "nombre_dusa": "Producto (DUSA)",
            "laboratorio": "Laboratorio",
            "oferta_dusa": "Oferta",
            "precio_dusa": "Precio DUSA",
            "precio_ml": "Precio ML",
            "stock_ml": "Stock ML",
            "mensaje": "Observaciones"
        }
        
        df_resultados = df_resultados.rename(columns=nombres_columnas)
        
        # Guardar Excel
        df_resultados.to_excel(ruta_salida, index=False, engine='openpyxl')
        
        print(f"✅ Resultados guardados en: {ruta_salida}")
        
        # Mostrar resumen
        total = len(df_resultados)
        encontrados = df_resultados["Encontrado"].sum() if "Encontrado" in df_resultados.columns else 0
        disponibles = df_resultados["Disponible"].sum() if "Disponible" in df_resultados.columns else 0
        faltantes = encontrados - disponibles
        
        print(f"\n📊 RESUMEN:")
        print(f"   Total productos verificados: {total}")
        print(f"   Encontrados en DUSA: {encontrados}")
        print(f"   ✅ Disponibles: {disponibles}")
        print(f"   ❌ Faltantes: {faltantes}")
        print(f"   ⚠️  No encontrados: {total - encontrados}")
    
    def cerrar(self):
        """Cierra el navegador."""
        if self.driver:
            self.driver.quit()
            print("🔒 Navegador cerrado")
    
    def ejecutar(self):
        """Ejecuta el proceso completo de verificación."""
        print("\n" + "=" * 50)
        print("🚀 VERIFICADOR DE DISPONIBILIDAD DUSA")
        print("=" * 50)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # 1. Leer Excel de ML
            df = self.leer_excel_mercadolibre(config.EXCEL_ENTRADA)
            
            # 2. Iniciar navegador
            self.iniciar_navegador()
            
            # 3. Login en DUSA
            if not self.login():
                print("❌ No se pudo iniciar sesión. Abortando.")
                return
            
            # 4. Procesar productos
            self.procesar_productos(df)
            
            # 5. Generar Excel de resultados
            self.generar_excel_resultados(config.EXCEL_SALIDA)
            
        except KeyboardInterrupt:
            print("\n⚠️  Proceso interrumpido por el usuario")
        except Exception as e:
            print(f"\n❌ Error inesperado: {str(e)}")
            raise
        finally:
            # Siempre cerrar el navegador
            self.cerrar()


def main():
    """Función principal."""
    verificador = VerificadorDUSA()
    verificador.ejecutar()


if __name__ == "__main__":
    main()
