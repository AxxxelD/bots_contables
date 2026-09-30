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

for i, sid in enumerate(sheet_ids):
    if sid:
        try:
            doc = gclient.open_by_key(sid)
            sheet = doc.sheet1
            sheet.batch_clear(["A2:Z10000"])
            print(f"Sede {i+1} limpiada correctamente.")
        except Exception as e:
            print(f"Error limpiando sede {i+1}: {e}")
