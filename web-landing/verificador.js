/**
 * Verificador DUSA - Bookmarklet Script
 * Este script se inyecta en la página de DUSA cuando el usuario
 * hace clic en el bookmarklet.
 */

(function() {
    'use strict';
    
    // Evitar múltiples instancias
    if (window.verificadorDUSAActivo) {
        alert('El verificador ya está abierto');
        return;
    }
    window.verificadorDUSAActivo = true;
    
    // Verificar que estamos en DUSA
    if (!window.location.href.includes('dusa.com.uy')) {
        alert('⚠️ Primero abre pedidos.dusa.com.uy e inicia sesión');
        window.verificadorDUSAActivo = false;
        return;
    }
    
    // Cargar SheetJS para leer Excel
    function cargarSheetJS(callback) {
        if (window.XLSX) {
            callback();
            return;
        }
        var script = document.createElement('script');
        script.src = 'https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js';
        script.onload = callback;
        document.head.appendChild(script);
    }
    
    // Crear la interfaz flotante
    function crearInterfaz() {
        // Estilos
        var styles = document.createElement('style');
        styles.textContent = `
            #verificador-dusa-panel {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 380px;
                max-height: 90vh;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                z-index: 999999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                overflow: hidden;
            }
            #verificador-dusa-panel * {
                box-sizing: border-box;
            }
            .vd-header {
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                color: white;
                padding: 15px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: move;
            }
            .vd-header h2 {
                margin: 0;
                font-size: 16px;
            }
            .vd-close {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                line-height: 1;
            }
            .vd-body {
                padding: 20px;
                max-height: calc(90vh - 60px);
                overflow-y: auto;
            }
            .vd-upload-zone {
                border: 2px dashed #ccc;
                border-radius: 8px;
                padding: 30px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                margin-bottom: 15px;
            }
            .vd-upload-zone:hover {
                border-color: #1e3c72;
                background: #f0f4ff;
            }
            .vd-upload-zone input {
                display: none;
            }
            .vd-btn {
                width: 100%;
                padding: 12px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                cursor: pointer;
                margin-top: 10px;
            }
            .vd-btn-primary {
                background: #1e3c72;
                color: white;
            }
            .vd-btn-primary:disabled {
                background: #ccc;
            }
            .vd-btn-success {
                background: #28a745;
                color: white;
            }
            .vd-progress {
                margin: 15px 0;
            }
            .vd-progress-bar {
                height: 20px;
                background: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
            }
            .vd-progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #1e3c72, #2a5298);
                transition: width 0.3s;
                border-radius: 10px;
            }
            .vd-stats {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .vd-current {
                font-size: 12px;
                color: #666;
                margin-top: 10px;
                font-style: italic;
            }
            .vd-results {
                margin-top: 15px;
                max-height: 200px;
                overflow-y: auto;
                border: 1px solid #eee;
                border-radius: 8px;
            }
            .vd-results table {
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }
            .vd-results th, .vd-results td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            .vd-results th {
                background: #f5f5f5;
                position: sticky;
                top: 0;
            }
            .vd-badge {
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            .vd-badge-success { background: #d4edda; color: #155724; }
            .vd-badge-danger { background: #f8d7da; color: #721c24; }
            .vd-badge-secondary { background: #e9ecef; color: #495057; }
            .vd-summary {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin: 15px 0;
            }
            .vd-summary-item {
                text-align: center;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            .vd-summary-item .number {
                font-size: 24px;
                font-weight: bold;
            }
            .vd-summary-item .label {
                font-size: 11px;
                color: #666;
            }
            .vd-summary-item.disponible .number { color: #28a745; }
            .vd-summary-item.agotado .number { color: #dc3545; }
            .vd-summary-item.no-encontrado .number { color: #6c757d; }
            .vd-file-info {
                background: #e8f5e9;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .vd-file-info .name {
                font-weight: bold;
                color: #2e7d32;
            }
            .vd-file-info .count {
                font-size: 12px;
                color: #666;
            }
            .vd-hidden { display: none !important; }
        `;
        document.head.appendChild(styles);
        
        // Panel
        var panel = document.createElement('div');
        panel.id = 'verificador-dusa-panel';
        panel.innerHTML = `
            <div class="vd-header">
                <h2>🔍 Verificador DUSA</h2>
                <button class="vd-close" id="vd-close">&times;</button>
            </div>
            <div class="vd-body">
                <!-- Upload -->
                <div id="vd-step-upload">
                    <div class="vd-upload-zone" id="vd-upload-zone">
                        <input type="file" id="vd-file-input" accept=".xlsx,.xls">
                        <div>📄 <strong>Arrastra tu Excel aquí</strong></div>
                        <div style="color: #999; font-size: 12px; margin-top: 5px;">o haz clic para seleccionar</div>
                    </div>
                </div>
                
                <!-- File info -->
                <div id="vd-file-info" class="vd-file-info vd-hidden">
                    <div>
                        <span class="name" id="vd-file-name"></span>
                        <span class="count" id="vd-file-count"></span>
                    </div>
                    <button onclick="verificadorDUSA.reset()" style="background:none;border:none;cursor:pointer;font-size:18px;">❌</button>
                </div>
                
                <!-- Start button -->
                <button class="vd-btn vd-btn-primary vd-hidden" id="vd-btn-start">
                    🚀 Iniciar Verificación
                </button>
                
                <!-- Progress -->
                <div id="vd-progress" class="vd-progress vd-hidden">
                    <div class="vd-progress-bar">
                        <div class="vd-progress-fill" id="vd-progress-fill" style="width: 0%"></div>
                    </div>
                    <div class="vd-stats">
                        <span id="vd-progress-text">0 / 0</span>
                        <span id="vd-progress-percent">0%</span>
                    </div>
                    <div class="vd-current" id="vd-current"></div>
                </div>
                
                <!-- Stop button -->
                <button class="vd-btn vd-btn-primary vd-hidden" id="vd-btn-stop" style="background: #dc3545;">
                    ⏹️ Detener
                </button>
                
                <!-- Summary -->
                <div id="vd-summary" class="vd-summary vd-hidden">
                    <div class="vd-summary-item disponible">
                        <div class="number" id="vd-count-disponible">0</div>
                        <div class="label">Disponibles</div>
                    </div>
                    <div class="vd-summary-item agotado">
                        <div class="number" id="vd-count-agotado">0</div>
                        <div class="label">Agotados</div>
                    </div>
                    <div class="vd-summary-item no-encontrado">
                        <div class="number" id="vd-count-noencontrado">0</div>
                        <div class="label">No encontrados</div>
                    </div>
                </div>
                
                <!-- Results -->
                <div id="vd-results" class="vd-results vd-hidden">
                    <table>
                        <thead>
                            <tr>
                                <th>Código</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody id="vd-results-body"></tbody>
                    </table>
                </div>
                
                <!-- Download button -->
                <button class="vd-btn vd-btn-success vd-hidden" id="vd-btn-download">
                    📥 Descargar Resultados
                </button>
            </div>
        `;
        document.body.appendChild(panel);
        
        // Hacer arrastrable
        hacerArrastrable(panel);
        
        return panel;
    }
    
    // Hacer el panel arrastrable
    function hacerArrastrable(panel) {
        var header = panel.querySelector('.vd-header');
        var offsetX, offsetY, isDragging = false;
        
        header.addEventListener('mousedown', function(e) {
            isDragging = true;
            offsetX = e.clientX - panel.offsetLeft;
            offsetY = e.clientY - panel.offsetTop;
        });
        
        document.addEventListener('mousemove', function(e) {
            if (isDragging) {
                panel.style.left = (e.clientX - offsetX) + 'px';
                panel.style.top = (e.clientY - offsetY) + 'px';
                panel.style.right = 'auto';
            }
        });
        
        document.addEventListener('mouseup', function() {
            isDragging = false;
        });
    }
    
    // Lógica del verificador
    window.verificadorDUSA = {
        productos: [],
        resultados: [],
        procesando: false,
        detenido: false,
        
        init: function() {
            var self = this;
            
            // Event listeners
            document.getElementById('vd-close').onclick = function() {
                self.cerrar();
            };
            
            var uploadZone = document.getElementById('vd-upload-zone');
            var fileInput = document.getElementById('vd-file-input');
            
            uploadZone.onclick = function() { fileInput.click(); };
            fileInput.onchange = function(e) { self.procesarArchivo(e.target.files[0]); };
            
            uploadZone.ondragover = function(e) { e.preventDefault(); uploadZone.style.borderColor = '#1e3c72'; };
            uploadZone.ondragleave = function(e) { e.preventDefault(); uploadZone.style.borderColor = '#ccc'; };
            uploadZone.ondrop = function(e) {
                e.preventDefault();
                uploadZone.style.borderColor = '#ccc';
                self.procesarArchivo(e.dataTransfer.files[0]);
            };
            
            document.getElementById('vd-btn-start').onclick = function() { self.iniciar(); };
            document.getElementById('vd-btn-stop').onclick = function() { self.detener(); };
            document.getElementById('vd-btn-download').onclick = function() { self.descargar(); };
        },
        
        procesarArchivo: function(file) {
            var self = this;
            if (!file) return;
            
            var reader = new FileReader();
            reader.onload = function(e) {
                var data = new Uint8Array(e.target.result);
                var workbook = XLSX.read(data, {type: 'array'});
                var sheet = workbook.Sheets[workbook.SheetNames[0]];
                var json = XLSX.utils.sheet_to_json(sheet, {header: 1});
                
                // Extraer códigos (primera columna con datos)
                self.productos = [];
                for (var i = 0; i < json.length; i++) {
                    var row = json[i];
                    for (var j = 0; j < row.length; j++) {
                        var val = String(row[j] || '').trim();
                        if (val && /^\d{6,14}$/.test(val)) {
                            self.productos.push(val);
                            break;
                        }
                    }
                }
                
                // Eliminar duplicados
                self.productos = [...new Set(self.productos)];
                
                // Mostrar info
                document.getElementById('vd-step-upload').classList.add('vd-hidden');
                document.getElementById('vd-file-info').classList.remove('vd-hidden');
                document.getElementById('vd-file-name').textContent = file.name;
                document.getElementById('vd-file-count').textContent = ' - ' + self.productos.length + ' productos';
                document.getElementById('vd-btn-start').classList.remove('vd-hidden');
            };
            reader.readAsArrayBuffer(file);
        },
        
        reset: function() {
            this.productos = [];
            this.resultados = [];
            document.getElementById('vd-step-upload').classList.remove('vd-hidden');
            document.getElementById('vd-file-info').classList.add('vd-hidden');
            document.getElementById('vd-btn-start').classList.add('vd-hidden');
            document.getElementById('vd-progress').classList.add('vd-hidden');
            document.getElementById('vd-summary').classList.add('vd-hidden');
            document.getElementById('vd-results').classList.add('vd-hidden');
            document.getElementById('vd-btn-download').classList.add('vd-hidden');
            document.getElementById('vd-results-body').innerHTML = '';
        },
        
        iniciar: async function() {
            var self = this;
            self.procesando = true;
            self.detenido = false;
            self.resultados = [];
            
            document.getElementById('vd-btn-start').classList.add('vd-hidden');
            document.getElementById('vd-btn-stop').classList.remove('vd-hidden');
            document.getElementById('vd-progress').classList.remove('vd-hidden');
            document.getElementById('vd-summary').classList.remove('vd-hidden');
            document.getElementById('vd-results').classList.remove('vd-hidden');
            document.getElementById('vd-results-body').innerHTML = '';
            
            var total = self.productos.length;
            
            for (var i = 0; i < total; i++) {
                if (self.detenido) break;
                
                var codigo = self.productos[i];
                self.actualizarProgreso(i, total, codigo);
                
                var resultado = await self.buscarProducto(codigo);
                self.resultados.push(resultado);
                self.agregarResultado(resultado);
                self.actualizarContadores();
                
                // Pequeña pausa
                await new Promise(r => setTimeout(r, 300));
            }
            
            self.procesando = false;
            document.getElementById('vd-btn-stop').classList.add('vd-hidden');
            document.getElementById('vd-btn-download').classList.remove('vd-hidden');
            document.getElementById('vd-current').textContent = '✅ Verificación completada';
        },
        
        buscarProducto: function(codigo) {
            return new Promise(function(resolve) {
                // Buscar campo de búsqueda
                var inputs = document.querySelectorAll('input.v-textfield, input[type="text"]');
                var campo = null;
                
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].offsetParent !== null) {
                        campo = inputs[i];
                        break;
                    }
                }
                
                if (!campo) {
                    resolve({codigo: codigo, estado: 'error', mensaje: 'Campo no encontrado'});
                    return;
                }
                
                // Escribir y buscar
                campo.value = codigo;
                campo.dispatchEvent(new Event('input', {bubbles: true}));
                campo.dispatchEvent(new Event('change', {bubbles: true}));
                campo.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
                campo.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
                
                // Esperar respuesta
                setTimeout(function() {
                    var body = document.body.innerText.toLowerCase();
                    var tablas = document.querySelectorAll('.v-table-body tr, table tbody tr, .v-grid-body tr');
                    
                    var resultado = {codigo: codigo, estado: 'no_encontrado'};
                    
                    if (tablas.length > 0) {
                        var texto = tablas[0].innerText.toLowerCase();
                        if (texto.includes('agotado') || texto.includes('sin stock')) {
                            resultado.estado = 'agotado';
                        } else if (tablas[0].innerText.trim().length > 5) {
                            resultado.estado = 'disponible';
                        }
                    }
                    
                    if (body.includes('no se encontr') || body.includes('sin resultado')) {
                        resultado.estado = 'no_encontrado';
                    }
                    
                    resolve(resultado);
                }, 1200);
            });
        },
        
        detener: function() {
            this.detenido = true;
            document.getElementById('vd-btn-stop').classList.add('vd-hidden');
            document.getElementById('vd-btn-download').classList.remove('vd-hidden');
        },
        
        actualizarProgreso: function(current, total, codigo) {
            var percent = Math.round((current / total) * 100);
            document.getElementById('vd-progress-fill').style.width = percent + '%';
            document.getElementById('vd-progress-text').textContent = current + ' / ' + total;
            document.getElementById('vd-progress-percent').textContent = percent + '%';
            document.getElementById('vd-current').textContent = 'Verificando: ' + codigo;
        },
        
        agregarResultado: function(resultado) {
            var tbody = document.getElementById('vd-results-body');
            var tr = document.createElement('tr');
            
            var badgeClass = 'vd-badge-secondary';
            var estadoText = 'No encontrado';
            
            if (resultado.estado === 'disponible') {
                badgeClass = 'vd-badge-success';
                estadoText = 'Disponible';
            } else if (resultado.estado === 'agotado') {
                badgeClass = 'vd-badge-danger';
                estadoText = 'Agotado';
            }
            
            tr.innerHTML = '<td>' + resultado.codigo + '</td><td><span class="vd-badge ' + badgeClass + '">' + estadoText + '</span></td>';
            tbody.appendChild(tr);
            
            // Scroll al final
            document.getElementById('vd-results').scrollTop = document.getElementById('vd-results').scrollHeight;
        },
        
        actualizarContadores: function() {
            var disponibles = this.resultados.filter(function(r) { return r.estado === 'disponible'; }).length;
            var agotados = this.resultados.filter(function(r) { return r.estado === 'agotado'; }).length;
            var noEncontrados = this.resultados.filter(function(r) { return r.estado === 'no_encontrado' || r.estado === 'error'; }).length;
            
            document.getElementById('vd-count-disponible').textContent = disponibles;
            document.getElementById('vd-count-agotado').textContent = agotados;
            document.getElementById('vd-count-noencontrado').textContent = noEncontrados;
        },
        
        descargar: function() {
            var data = this.resultados.map(function(r) {
                return {
                    'Código': r.codigo,
                    'Estado': r.estado === 'disponible' ? 'Disponible' : r.estado === 'agotado' ? 'Agotado' : 'No encontrado'
                };
            });
            
            var ws = XLSX.utils.json_to_sheet(data);
            var wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Resultados');
            
            var fecha = new Date().toISOString().slice(0, 10);
            XLSX.writeFile(wb, 'verificacion_dusa_' + fecha + '.xlsx');
        },
        
        cerrar: function() {
            var panel = document.getElementById('verificador-dusa-panel');
            if (panel) panel.remove();
            window.verificadorDUSAActivo = false;
        }
    };
    
    // Iniciar
    cargarSheetJS(function() {
        crearInterfaz();
        verificadorDUSA.init();
    });
    
})();
