#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador DUSA - Versión con Interfaz Gráfica
================================================
Aplicación fácil de usar para verificar disponibilidad de productos en DUSA.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import threading
import time
import os
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


class VerificadorDUSAApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Verificador DUSA - Mercado Libre")
        self.root.geometry("800x650")
        self.root.resizable(True, True)
        
        # Variables
        self.archivo_excel = tk.StringVar()
        self.usuario = tk.StringVar(value="farmacia.farma")
        self.password = tk.StringVar(value="Parlantes28")
        self.cliente = tk.StringVar(value="2287")
        self.procesando = False
        self.driver = None
        self.resultados = []
        
        # Crear interfaz
        self.crear_interfaz()
    
    def crear_interfaz(self):
        """Crea todos los elementos de la interfaz."""
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # === SECCIÓN: Archivo Excel ===
        ttk.Label(main_frame, text="📁 Archivo Excel de Mercado Libre:", 
                  font=('Helvetica', 11, 'bold')).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,5))
        
        ttk.Entry(main_frame, textvariable=self.archivo_excel, width=60).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0,5))
        ttk.Button(main_frame, text="Seleccionar...", command=self.seleccionar_archivo).grid(row=1, column=2)
        
        # === SECCIÓN: Credenciales DUSA ===
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky="ew", pady=15)
        
        ttk.Label(main_frame, text="🔐 Credenciales DUSA:", 
                  font=('Helvetica', 11, 'bold')).grid(row=3, column=0, columnspan=3, sticky="w", pady=(0,5))
        
        cred_frame = ttk.Frame(main_frame)
        cred_frame.grid(row=4, column=0, columnspan=3, sticky="w")
        
        ttk.Label(cred_frame, text="Usuario:").grid(row=0, column=0, padx=(0,5))
        ttk.Entry(cred_frame, textvariable=self.usuario, width=20).grid(row=0, column=1, padx=(0,15))
        
        ttk.Label(cred_frame, text="Contraseña:").grid(row=0, column=2, padx=(0,5))
        ttk.Entry(cred_frame, textvariable=self.password, width=20, show="*").grid(row=0, column=3, padx=(0,15))
        
        ttk.Label(cred_frame, text="Cliente:").grid(row=0, column=4, padx=(0,5))
        ttk.Entry(cred_frame, textvariable=self.cliente, width=10).grid(row=0, column=5)
        
        # === SECCIÓN: Botones de acción ===
        ttk.Separator(main_frame, orient='horizontal').grid(row=5, column=0, columnspan=3, sticky="ew", pady=15)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=3)
        
        self.btn_iniciar = ttk.Button(btn_frame, text="▶️ INICIAR VERIFICACIÓN", 
                                       command=self.iniciar_verificacion, style='Accent.TButton')
        self.btn_iniciar.grid(row=0, column=0, padx=5)
        
        self.btn_detener = ttk.Button(btn_frame, text="⏹️ Detener", 
                                       command=self.detener, state='disabled')
        self.btn_detener.grid(row=0, column=1, padx=5)
        
        # === SECCIÓN: Progreso ===
        ttk.Separator(main_frame, orient='horizontal').grid(row=7, column=0, columnspan=3, sticky="ew", pady=15)
        
        self.label_estado = ttk.Label(main_frame, text="Estado: Esperando...", font=('Helvetica', 10))
        self.label_estado.grid(row=8, column=0, columnspan=3, sticky="w")
        
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.progress.grid(row=9, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.label_progreso = ttk.Label(main_frame, text="0 / 0 productos")
        self.label_progreso.grid(row=10, column=0, columnspan=3, sticky="w")
        
        # === SECCIÓN: Log ===
        ttk.Label(main_frame, text="📋 Registro:", 
                  font=('Helvetica', 11, 'bold')).grid(row=11, column=0, columnspan=3, sticky="w", pady=(15,5))
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=90, font=('Courier', 9))
        self.log_text.grid(row=12, column=0, columnspan=3, sticky="nsew", pady=5)
        main_frame.rowconfigure(12, weight=1)
        
        # === SECCIÓN: Resumen ===
        resumen_frame = ttk.Frame(main_frame)
        resumen_frame.grid(row=13, column=0, columnspan=3, sticky="ew", pady=10)
        
        self.label_resumen = ttk.Label(resumen_frame, text="", font=('Helvetica', 10))
        self.label_resumen.grid(row=0, column=0, sticky="w")
        
        self.btn_abrir_resultado = ttk.Button(resumen_frame, text="📂 Abrir Resultado", 
                                               command=self.abrir_resultado, state='disabled')
        self.btn_abrir_resultado.grid(row=0, column=1, padx=20)
        
        # Configurar tags para colores en el log
        self.log_text.tag_config('success', foreground='green')
        self.log_text.tag_config('error', foreground='red')
        self.log_text.tag_config('warning', foreground='orange')
        self.log_text.tag_config('info', foreground='blue')
    
    def log(self, mensaje, tag=None):
        """Agrega mensaje al log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {mensaje}\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def seleccionar_archivo(self):
        """Abre diálogo para seleccionar archivo Excel."""
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo Excel de Mercado Libre",
            filetypes=[
                ("Archivos Excel", "*.xlsx *.xls"),
                ("Todos los archivos", "*.*")
            ],
            initialdir=os.path.expanduser("~/Downloads")
        )
        if archivo:
            self.archivo_excel.set(archivo)
            self.log(f"Archivo seleccionado: {os.path.basename(archivo)}", 'info')
    
    def iniciar_verificacion(self):
        """Inicia el proceso de verificación en un hilo separado."""
        if not self.archivo_excel.get():
            messagebox.showwarning("Atención", "Debes seleccionar un archivo Excel primero.")
            return
        
        if not os.path.exists(self.archivo_excel.get()):
            messagebox.showerror("Error", "El archivo seleccionado no existe.")
            return
        
        # Iniciar en hilo separado
        self.procesando = True
        self.btn_iniciar.config(state='disabled')
        self.btn_detener.config(state='normal')
        self.resultados = []
        
        thread = threading.Thread(target=self.ejecutar_verificacion)
        thread.daemon = True
        thread.start()
    
    def detener(self):
        """Detiene el proceso."""
        self.procesando = False
        self.log("⏹️ Deteniendo proceso...", 'warning')
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def ejecutar_verificacion(self):
        """Ejecuta todo el proceso de verificación."""
        try:
            # 1. Leer Excel
            self.label_estado.config(text="Estado: Leyendo Excel...")
            self.log("📖 Leyendo archivo Excel...", 'info')
            
            df = self.leer_excel()
            if df is None or len(df) == 0:
                self.log("❌ No se encontraron productos válidos", 'error')
                self.finalizar()
                return
            
            total = len(df)
            self.log(f"✅ {total} productos encontrados", 'success')
            
            # 2. Iniciar navegador
            self.label_estado.config(text="Estado: Iniciando navegador...")
            self.log("🌐 Iniciando navegador Chrome...", 'info')
            
            if not self.iniciar_navegador():
                self.log("❌ Error iniciando navegador", 'error')
                self.finalizar()
                return
            
            # 3. Login
            self.label_estado.config(text="Estado: Iniciando sesión en DUSA...")
            self.log("🔐 Iniciando sesión en DUSA...", 'info')
            
            if not self.login():
                self.log("❌ Error en login - verifica credenciales", 'error')
                self.finalizar()
                return
            
            self.log("✅ Login exitoso", 'success')
            
            # 4. Ir a productos
            self.ir_a_productos()
            
            # 5. Procesar productos
            self.label_estado.config(text="Estado: Verificando productos...")
            self.progress['maximum'] = total
            
            for idx, (_, row) in enumerate(df.iterrows()):
                if not self.procesando:
                    break
                
                sku = str(row.get('SKU', '')).strip()
                titulo = str(row.get('Título', '')).strip()
                
                if (not sku or sku == 'nan') and (not titulo or titulo == 'nan'):
                    continue
                
                # Actualizar progreso
                self.progress['value'] = idx + 1
                self.label_progreso.config(text=f"{idx + 1} / {total} productos")
                
                # Buscar producto
                display = sku if sku and sku != 'nan' else titulo[:30]
                resultado = self.buscar_producto(sku, titulo)
                
                # Agregar datos de ML
                resultado['sku_ml'] = sku
                resultado['titulo_ml'] = titulo
                resultado['precio_ml'] = row.get('Precio', '')
                resultado['stock_ml'] = row.get('Stock en tu depósito', '')
                resultado['estado_ml'] = row.get('Estado', '')
                
                self.resultados.append(resultado)
                
                # Log
                if resultado['encontrado']:
                    if resultado['disponible']:
                        self.log(f"✅ {display[:40]} → DISPONIBLE ${resultado.get('precio_dusa', '')}", 'success')
                    else:
                        self.log(f"❌ {display[:40]} → FALTANTE", 'error')
                else:
                    self.log(f"⚠️ {display[:40]} → No encontrado", 'warning')
                
                time.sleep(1.5)  # Pausa entre búsquedas
            
            # 6. Generar resultado
            if self.resultados:
                self.generar_excel_resultado()
            
            self.log("🏁 Proceso completado", 'success')
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", 'error')
        
        finally:
            self.finalizar()
    
    def leer_excel(self):
        """Lee el archivo Excel de Mercado Libre."""
        try:
            # Intentar detectar la estructura del archivo
            xl = pd.ExcelFile(self.archivo_excel.get())
            
            # Buscar hoja de Publicaciones
            if 'Publicaciones' in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name='Publicaciones', skiprows=2)
            else:
                df = pd.read_excel(xl, skiprows=0)
            
            # Renombrar columnas si es necesario
            col_map = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if 'sku' in col_lower:
                    col_map[col] = 'SKU'
                elif 'título' in col_lower or 'titulo' in col_lower:
                    col_map[col] = 'Título'
                elif 'precio' in col_lower and 'ml' not in col_lower:
                    col_map[col] = 'Precio'
                elif 'stock' in col_lower:
                    col_map[col] = 'Stock en tu depósito'
                elif 'estado' in col_lower:
                    col_map[col] = 'Estado'
            
            df = df.rename(columns=col_map)
            
            # Filtrar filas válidas
            df = df[
                (df['SKU'].notna() & (df['SKU'].astype(str) != 'nan')) |
                (df['Título'].notna() & (df['Título'].astype(str) != 'nan'))
            ].copy()
            
            # Filtrar filas de instrucciones
            if 'Stock en tu depósito' in df.columns:
                df = df[~df['Stock en tu depósito'].astype(str).str.contains('Obligatorio|Opcional', case=False, na=False)]
            
            return df
            
        except Exception as e:
            self.log(f"Error leyendo Excel: {e}", 'error')
            return None
    
    def iniciar_navegador(self):
        """Inicia Chrome."""
        try:
            opciones = Options()
            opciones.add_argument("--no-sandbox")
            opciones.add_argument("--disable-dev-shm-usage")
            opciones.add_argument("--window-size=1200,800")
            
            servicio = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=servicio, options=opciones)
            return True
        except Exception as e:
            self.log(f"Error con navegador: {e}", 'error')
            return False
    
    def login(self):
        """Inicia sesión en DUSA."""
        try:
            self.driver.get("https://pedidos.dusa.com.uy/DUSAWebUI")
            time.sleep(4)
            
            # Llenar campos
            campos_texto = self.driver.find_elements(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
            campos_pass = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            
            if campos_texto:
                campos_texto[0].send_keys(self.usuario.get())
            if campos_pass:
                campos_pass[0].send_keys(self.password.get())
            if len(campos_texto) >= 2:
                campos_texto[-1].send_keys(self.cliente.get())
            
            time.sleep(1)
            
            # Clic en Entrar
            botones = self.driver.find_elements(By.CSS_SELECTOR, ".v-button, button")
            for btn in botones:
                if "Entrar" in btn.text:
                    btn.click()
                    break
            
            time.sleep(5)
            
            # Verificar login
            try:
                self.driver.find_element(By.CSS_SELECTOR, "#loginf")
                return False
            except NoSuchElementException:
                return True
                
        except Exception as e:
            self.log(f"Error en login: {e}", 'error')
            return False
    
    def ir_a_productos(self):
        """Navega a la sección de productos."""
        self.driver.get("https://pedidos.dusa.com.uy/DUSAWebUI#!micuenta/productos")
        time.sleep(3)
        self.log("📦 En sección de productos", 'info')
    
    def extraer_palabras_clave(self, titulo):
        """Extrae palabras clave de un título largo."""
        if not titulo or titulo == "nan":
            return ""
        
        ignorar = ['farmauy', 'farmacia', 'original', 'sellado', 'envio', 'gratis',
                   'pack', 'combo', 'oferta', 'promo', 'nuevo', 'uruguay', 'importado']
        
        palabras = titulo.split()[:5]
        filtradas = [p for p in palabras if p.lower() not in ignorar and len(p) > 2]
        
        return " ".join(filtradas[:3])
    
    def buscar_producto(self, sku, titulo):
        """Busca un producto en DUSA."""
        resultado = {
            'termino_busqueda': '',
            'encontrado': False,
            'disponible': None,
            'precio_dusa': None,
            'nombre_dusa': None,
            'oferta_dusa': None,
            'laboratorio': None,
            'mensaje': ''
        }
        
        # Intentar con SKU primero
        if sku and sku != 'nan':
            res = self._buscar(sku)
            if res['encontrado']:
                res['termino_busqueda'] = f"SKU: {sku}"
                return res
        
        # Buscar con palabras clave
        palabras = self.extraer_palabras_clave(titulo)
        if palabras:
            res = self._buscar(palabras)
            res['termino_busqueda'] = palabras
            return res
        
        resultado['mensaje'] = "Sin término de búsqueda"
        return resultado
    
    def _buscar(self, termino):
        """Realiza la búsqueda."""
        resultado = {
            'termino_busqueda': termino,
            'encontrado': False,
            'disponible': None,
            'precio_dusa': None,
            'nombre_dusa': None,
            'oferta_dusa': None,
            'laboratorio': None,
            'mensaje': ''
        }
        
        try:
            # Campo de búsqueda
            campo = self.driver.find_element(By.CSS_SELECTOR, "input.v-textfield, input[type='text']")
            campo.clear()
            time.sleep(0.3)
            campo.send_keys(termino)
            
            # Botón buscar
            try:
                boton = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]/..")
                boton.click()
            except:
                campo.send_keys(Keys.RETURN)
            
            time.sleep(2.5)
            
            # Analizar resultados
            filas = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
            filas_datos = [f for f in filas if f.text.strip() and "Stock" not in f.text and "Descripción" not in f.text]
            
            if filas_datos:
                primera = filas_datos[0]
                texto = primera.text.lower()
                
                resultado['encontrado'] = True
                resultado['disponible'] = "faltante" not in texto
                resultado['mensaje'] = "Faltante en laboratorio" if not resultado['disponible'] else "Disponible"
                
                # Extraer datos
                celdas = primera.find_elements(By.CSS_SELECTOR, "td")
                if len(celdas) >= 5:
                    resultado['nombre_dusa'] = celdas[1].text.split('\n')[0][:50]
                    resultado['laboratorio'] = celdas[2].text.strip()
                    resultado['oferta_dusa'] = celdas[3].text.strip()
                    resultado['precio_dusa'] = celdas[4].text.strip()
            else:
                resultado['mensaje'] = "Sin resultados"
            
            return resultado
            
        except Exception as e:
            resultado['mensaje'] = f"Error: {str(e)[:30]}"
            return resultado
    
    def generar_excel_resultado(self):
        """Genera el Excel con resultados."""
        self.log("📝 Generando archivo de resultados...", 'info')
        
        df = pd.DataFrame(self.resultados)
        
        # Ordenar columnas
        columnas = ['sku_ml', 'titulo_ml', 'estado_ml', 'encontrado', 'disponible', 
                    'nombre_dusa', 'precio_dusa', 'oferta_dusa', 'laboratorio', 
                    'precio_ml', 'stock_ml', 'mensaje']
        columnas = [c for c in columnas if c in df.columns]
        df = df[columnas]
        
        # Renombrar
        df = df.rename(columns={
            'sku_ml': 'SKU',
            'titulo_ml': 'Título ML',
            'estado_ml': 'Estado ML',
            'encontrado': 'Encontrado',
            'disponible': 'Disponible',
            'nombre_dusa': 'Producto DUSA',
            'precio_dusa': 'Precio DUSA',
            'oferta_dusa': 'Oferta',
            'laboratorio': 'Laboratorio',
            'precio_ml': 'Precio ML',
            'stock_ml': 'Stock ML',
            'mensaje': 'Observaciones'
        })
        
        # Guardar
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.archivo_resultado = os.path.join(
            os.path.dirname(self.archivo_excel.get()),
            f"verificacion_dusa_{timestamp}.xlsx"
        )
        
        df.to_excel(self.archivo_resultado, index=False)
        
        # Resumen
        total = len(df)
        encontrados = df['Encontrado'].sum() if 'Encontrado' in df.columns else 0
        disponibles = df['Disponible'].sum() if 'Disponible' in df.columns else 0
        
        self.label_resumen.config(
            text=f"📊 Total: {total} | Encontrados: {encontrados} | ✅ Disponibles: {disponibles} | ❌ Faltantes: {encontrados - disponibles}"
        )
        
        self.btn_abrir_resultado.config(state='normal')
        self.log(f"✅ Resultado guardado: {self.archivo_resultado}", 'success')
    
    def abrir_resultado(self):
        """Abre el archivo de resultado."""
        if hasattr(self, 'archivo_resultado') and os.path.exists(self.archivo_resultado):
            os.system(f'open "{self.archivo_resultado}"')
    
    def finalizar(self):
        """Limpia y habilita botones."""
        self.procesando = False
        self.btn_iniciar.config(state='normal')
        self.btn_detener.config(state='disabled')
        self.label_estado.config(text="Estado: Finalizado")
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def main():
    root = tk.Tk()
    app = VerificadorDUSAApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
