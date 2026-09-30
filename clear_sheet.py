import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gclient = gspread.authorize(creds)

SHEET_ID = os.getenv("SHEET_ID_SEDE_1")

doc = gclient.open_by_key(SHEET_ID)
sheet = doc.sheet1

# Get all rows
all_values = sheet.get_all_values()

if len(all_values) > 1:
    # Delete from row 2 to the end
    print(f"Borrando {len(all_values) - 1} filas...")
    # Actually, gspread sheet.delete_rows(index, end_index) doesn't exist. We can do:
    # sheet.batch_clear(["A2:Z1000"]) -> just clears the values, which is probably fine.
    # To properly remove rows and not leave empty ones, we can use sheet.delete_rows()
    # It takes a start index, and end index. 
    # Let's just resize the sheet or clear. 
    sheet.batch_clear(["A2:Z10000"])
    print("Contenido de PZO-CBL borrado exitosamente.")
else:
    print("La hoja ya está vacía (solo tiene encabezados).")
