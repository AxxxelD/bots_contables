import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Asegúrate de usar la ruta correcta a tu archivo JSON
creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client = gspread.authorize(creds)

# IDs de los documentos para cada sede
SEDES = {
    1: "1E8jtQOncO7to-5TZjil2NybO8dimj_4UTlb9uTcERSk", # Sede 1
    2: "1LMo1Xoles5OF87HxKVOrsmIx6GMxuNKAIce9N6R3IU8", # Sede 2
    3: "14ynnrc9BIlikoAZO5iiYicdxDcqSOy_89GEg9QIfs6g", # Sede 3
    4: "1QMS36ozZ3HHGCM3gR23ywc8atrSb4BY4Xy3b2ugM37s"  # Sede 4
}

def actualizar_esquemas():
    for sede_id, sheet_id in SEDES.items():
        print(f"Actualizando sede {sede_id}...")
        try:
            doc = client.open_by_key(sheet_id)
            sheets = doc.worksheets()
            for sheet in sheets:
                # Update J1 to 'Acumulado $'
                sheet.update_acell('J1', 'Acumulado $')
                print(f"  - Actualizada hoja '{sheet.title}'")
        except Exception as e:
            print(f"  - Error en sede {sede_id}: {e}")

if __name__ == "__main__":
    actualizar_esquemas()
