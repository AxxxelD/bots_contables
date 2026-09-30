import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Configurar Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    gclient = gspread.authorize(creds)
except Exception as e:
    logger.error(f"Error cargando credenciales: {e}")
    exit(1)

# Lista de IDs de los sheets
sheet_ids = [
    os.getenv("SHEET_ID_SEDE_1"),
    os.getenv("SHEET_ID_SEDE_2"),
    os.getenv("SHEET_ID_SEDE_3"),
    os.getenv("SHEET_ID_SEDE_4")
]

nombres_sedes = ["PZO/CBL", "Puerto La Cruz", "El Tigre", "Porlamar"]

encabezados = [
    "Tipo (Ingreso/Egreso)", 
    "Fecha", 
    "Tipo de Pago", 
    "Número de Referencia", 
    "Monto", 
    "Concepto", 
    "Tasa BCV", 
    "Cantidad en $", 
    "Acumulado"
]

for idx, sid in enumerate(sheet_ids):
    if not sid:
        logger.warning(f"ID de la sede {idx+1} no encontrado.")
        continue
    
    try:
        # Abrir el documento
        doc = gclient.open_by_key(sid)
        
        # Obtener la primera hoja (o crearla)
        sheet = doc.sheet1
        sheet.update_title("Registros")
        
        # Limpiar la hoja y poner encabezados
        sheet.clear()
        
        # Escribir encabezados en la primera fila
        sheet.update(range_name='A1:I1', values=[encabezados])
        
        # Formato básico para la primera fila (Negrita, fondo gris)
        sheet.format('A1:I1', {
            "backgroundColor": {
                "red": 0.8,
                "green": 0.8,
                "blue": 0.8
            },
            "textFormat": {
                "bold": True
            }
        })
        
        # Congelar la primera fila
        sheet.freeze(rows=1)
        
        logger.info(f"✅ Sede {nombres_sedes[idx]} (Hoja 'Registros') inicializada correctamente.")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando Sede {nombres_sedes[idx]}: {e}")

print("Proceso de inicialización de tablas terminado.")
