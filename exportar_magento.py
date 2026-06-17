"""
Descarga todos los productos ACTIVOS de Magento via API REST
y genera un Excel compatible con el verificador DUSA.

Uso:
    python3 exportar_magento.py
    python3 exportar_magento.py --salida /ruta/custom.xlsx
"""

import requests
import pandas as pd
import argparse
import sys
import time
from datetime import datetime

MAGENTO_URL  = "https://farma.uy"
MAGENTO_USER = "CarlosSanchez"
MAGENTO_PASS = "felipe1216"

SALIDA_DEFAULT = f"/Users/carlossanchez/Desktop/Magento_todos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

PAGE_SIZE = 500   # máximo que acepta Magento por página


def obtener_token():
    url = f"{MAGENTO_URL}/rest/V1/integration/admin/token"
    resp = requests.post(url, json={"username": MAGENTO_USER, "password": MAGENTO_PASS}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def obtener_pagina(token, pagina):
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "searchCriteria[filter_groups][0][filters][0][field]":          "status",
        "searchCriteria[filter_groups][0][filters][0][value]":          "1",
        "searchCriteria[filter_groups][0][filters][0][condition_type]": "eq",
        "searchCriteria[pageSize]":    PAGE_SIZE,
        "searchCriteria[currentPage]": pagina,
        # Solo los campos que necesitamos para reducir payload
        "fields": "total_count,items[sku,name,price,status,extension_attributes[stock_item[qty]]]",
    }
    url = f"{MAGENTO_URL}/rest/V1/products"
    resp = requests.get(url, headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--salida", default=SALIDA_DEFAULT)
    args = parser.parse_args()

    print("=" * 55)
    print("  EXPORTAR PRODUCTOS ACTIVOS MAGENTO → EXCEL")
    print("=" * 55)

    # Token
    print("\n🔑 Obteniendo token Magento...")
    try:
        token = obtener_token()
    except Exception as e:
        print(f"❌ Error de autenticación: {e}")
        sys.exit(1)
    print("   ✅ Token OK")

    # Primera página para saber el total
    print(f"\n📦 Descargando productos activos (página 1)...")
    data = obtener_pagina(token, 1)
    total = data.get("total_count", 0)
    items = data.get("items") or []
    print(f"   Total activos en Magento: {total:,}")

    total_paginas = (total + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"   Páginas necesarias: {total_paginas}")

    filas = []

    def procesar_items(items_list):
        for item in items_list:
            try:
                qty = (item.get("extension_attributes") or {}).get("stock_item", {}).get("qty", 0)
            except Exception:
                qty = 0
            filas.append({
                "SKU":    item.get("sku", ""),
                "Titulo": item.get("name", ""),
                "Precio": item.get("price", ""),
                "Stock":  qty,
                "Estado": "Activo",
            })

    procesar_items(items)
    print(f"   Página 1/{total_paginas} — {len(filas):,} productos acumulados")

    for pagina in range(2, total_paginas + 1):
        try:
            data = obtener_pagina(token, pagina)
            items = data.get("items") or []
            procesar_items(items)
            print(f"   Página {pagina}/{total_paginas} — {len(filas):,} productos acumulados")
            time.sleep(0.3)  # pausa suave para no saturar la API
        except Exception as e:
            print(f"   ⚠️  Error en página {pagina}: {e} — reintentando...")
            time.sleep(2)
            try:
                data = obtener_pagina(token, pagina)
                procesar_items(data.get("items") or [])
                print(f"   Página {pagina}/{total_paginas} — {len(filas):,} productos acumulados (reintento OK)")
            except Exception as e2:
                print(f"   ❌ Saltando página {pagina}: {e2}")

    print(f"\n✅ Descarga completada: {len(filas):,} productos")

    # Generar Excel
    print(f"\n💾 Generando Excel en:\n   {args.salida}")
    df = pd.DataFrame(filas)
    df.to_excel(args.salida, index=False)
    print(f"   ✅ Guardado — {len(df):,} filas")
    print("=" * 55)
    print(f"\nAhora sube este archivo al verificador DUSA:")
    print(f"   {args.salida}")
    print()


if __name__ == "__main__":
    main()
