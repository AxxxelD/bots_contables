import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gclient = gspread.authorize(creds)

sheet_ids = [
    os.getenv("SHEET_ID_SEDE_1"),
    os.getenv("SHEET_ID_SEDE_2"),
    os.getenv("SHEET_ID_SEDE_3"),
    os.getenv("SHEET_ID_SEDE_4")
]

# Fechas de prueba: 2024, 2025 y enero a septiembre de 2026
raw_dates = [
    "15/06/2024", "20/11/2024",
    "10/02/2025", "05/08/2025",
    "01/01/2026", "14/02/2026", "22/03/2026", "10/04/2026",
    "05/05/2026", "18/06/2026", "25/07/2026", "08/08/2026",
    "02/09/2026", "15/09/2026"
]

test_data = []
for i, date in enumerate(raw_dates):
    row_num = i + 2
    tipo = "Ingreso" if i % 2 == 0 else "Egreso"
    monto = 1000.00 + (i * 150.00)
    
    usd_formula = f"=E{row_num}/G{row_num}"
    if row_num == 2:
        acum_formula = f'=IF(A2="Ingreso",E2,-E2)'
    else:
        acum_formula = f'=I{row_num-1}+(IF(A{row_num}="Ingreso",E{row_num},-E{row_num}))'
        
    row = [
        tipo, 
        date, 
        "Pago Movil", 
        f"00000{i:04d}", 
        monto, 
        f"Test {date}", 
        36.6, 
        usd_formula, 
        acum_formula
    ]
    test_data.append(row)

for i, sid in enumerate(sheet_ids):
    if sid:
        try:
            doc = gclient.open_by_key(sid)
            sheet = doc.sheet1
            
            # Limpiar datos previos (dejando el encabezado)
            sheet.batch_clear(["A2:Z1000"])
            
            # Insertar los registros de prueba
            sheet.insert_rows(test_data, 2, value_input_option='USER_ENTERED')
            print(f"Datos de prueba insertados en la sede {i+1} ({len(test_data)} filas).")
        except Exception as e:
            print(f"Error en sede {i+1}: {e}")
