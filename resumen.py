import pandas as pd
df = pd.read_excel('/Users/carlossanchez/Downloads/resultado_dusa_20260301_0414 (1).xlsx')

def limpiar_estado(e):
    if pd.isna(e): return 'Sin datos'
    e = str(e)
    if 'Disponible' in e: return 'Disponible'
    elif 'Faltante' in e or 'Faltando' in e: return 'Faltante'
    elif 'Consultar' in e: return 'Consultar'
    elif 'No encontrado' in e: return 'No encontrado'
    return e

df['Estado'] = df['Estado DUSA'].apply(limpiar_estado)
df['Accion'] = df['Accion'].fillna('Sin accion')

total = len(df)
disponibles = len(df[df['Estado'] == 'Disponible'])
faltantes = len(df[df['Estado'] == 'Faltante'])
consultar = len(df[df['Estado'] == 'Consultar'])
no_encontrados = len(df[df['Estado'] == 'No encontrado'])

disp_activados = len(df[(df['Estado'] == 'Disponible') & (df['Accion'] == 'Activado')])
disp_no_activados = len(df[(df['Estado'] == 'Disponible') & (df['Accion'] == 'No activado')])
disp_diferida = len(df[(df['Estado'] == 'Disponible') & (df['Accion'] == 'Diferida')])
falt_incumplimiento = len(df[(df['Estado'] == 'Faltante') & (df['Accion'] == 'Incumplimiento')])

print()
print('RESUMEN VERIFICACION DUSA - 01/03/2026')
print('='*45)
print(f'Total productos analizados: {total}')
print()
print('EN EL PROVEEDOR (DUSA):')
print(f'  Disponibles: {disponibles} ({disponibles/total*100:.1f}%)')
print(f'  Faltantes: {faltantes} ({faltantes/total*100:.1f}%)')
print(f'  Consultar (llamar): {consultar} ({consultar/total*100:.1f}%)')
print(f'  No encontrados: {no_encontrados} ({no_encontrados/total*100:.1f}%)')
print()
print(f'ACCIONES EN DISPONIBLES ({disponibles}):')
print(f'  Activados: {disp_activados}')
print(f'  No activados: {disp_no_activados}')
print(f'  Diferidos: {disp_diferida}')
print()
print(f'Faltantes marcados Incumplimiento: {falt_incumplimiento}')
print('='*45)
