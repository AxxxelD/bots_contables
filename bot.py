import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf

from telegram import BotCommand
import tempfile
from fpdf import FPDF
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from google import genai
from google.genai import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

sede_id = sys.argv[1] if len(sys.argv) > 1 else "1"
nombres_sedes = {"1": "PZO/CBL", "2": "Puerto La Cruz", "3": "El Tigre", "4": "Porlamar"}
nombre_sede = nombres_sedes.get(sede_id, "Desconocida")

TELEGRAM_TOKEN = os.getenv(f"TELEGRAM_TOKEN_SEDE_{sede_id}")
SHEET_ID = os.getenv(f"SHEET_ID_SEDE_{sede_id}")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CUENTA_SEDE = os.getenv(f"CUENTA_SEDE_{sede_id}", "0000")
BANCO_ORIGEN_CODIGO = CUENTA_SEDE[:4]

if not TELEGRAM_TOKEN or not SHEET_ID or not GEMINI_API_KEY:
    logger.error("Faltan variables de entorno.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gclient = gspread.authorize(creds)

# Diccionario temporal para guardar mensajes antes de presionar el botón
temp_messages = {}


def generar_pdf_mes(mes, anio, sheet_id, nombre_sede):
    try:
        doc = gclient.open_by_key(sheet_id)
        sheet = doc.sheet1
        records = sheet.get_all_records()
        
        filtered_records = []
        for r in records:
            fecha_str = r.get('Fecha', '')
            if not fecha_str: continue
            try:
                from datetime import datetime
                fecha_obj = datetime.strptime(str(fecha_str), "%d/%m/%Y")
                if fecha_obj.month == mes and fecha_obj.year == anio:
                    filtered_records.append(r)
            except:
                pass
                
        if not filtered_records:
            return None
            
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        # Título
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(41, 128, 185) # Azul profesional
        pdf.cell(0, 10, f"Reporte Contable - Sede {nombre_sede}", ln=True, align='C')
        pdf.set_font("Arial", '', 14)
        pdf.set_text_color(100, 100, 100) # Gris oscuro
        pdf.cell(0, 8, f"Mes: {months[mes-1]} {anio}", ln=True, align='C')
        pdf.ln(8)
        
        # Encabezados de tabla
        pdf.set_fill_color(41, 128, 185) # Fondo azul
        pdf.set_text_color(255, 255, 255) # Texto blanco
        pdf.set_font("Arial", 'B', 7)
        pdf.set_draw_color(180, 180, 180) # Borde gris
        
        col_widths = [12, 17, 18, 19, 20, 38, 11, 17, 19, 19]
        headers = ['Tipo', 'Fecha', 'Tipo Pago', 'Referencia', 'Monto Bs', 'Concepto', 'Tasa', 'Total $', 'Acum. Bs', 'Acum. $']
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, border=1, align='C', fill=True)
        pdf.ln()
        
        # Filas de tabla
        pdf.set_font("Arial", size=7)
        pdf.set_text_color(50, 50, 50)
        
        total_ingreso_bs = 0.0
        total_egreso_bs = 0.0
        total_ingreso_usd = 0.0
        total_egreso_usd = 0.0
        
        fill = False # Alternar filas
        for r in filtered_records:
            if fill:
                pdf.set_fill_color(240, 245, 250) # Azul muy claro
            else:
                pdf.set_fill_color(255, 255, 255)
            
            monto_bs_str = str(r.get('Monto', '0')).replace(',', '.')
            try: monto_bs = float(monto_bs_str)
            except: monto_bs = 0.0
            
            usd_str = str(r.get('Cantidad en $', '0')).replace(',', '.')
            try: usd_monto = float(usd_str)
            except: usd_monto = 0.0
            
            tipo = str(r.get('Tipo (Ingreso/Egreso)', ''))
            
            if tipo.lower() == 'ingreso':
                total_ingreso_bs += monto_bs
                total_ingreso_usd += usd_monto
            else:
                total_egreso_bs += monto_bs
                total_egreso_usd += usd_monto
            
            pdf.cell(col_widths[0], 8, str(tipo)[:10], border='B', align='C', fill=fill)
            pdf.cell(col_widths[1], 8, str(r.get('Fecha', ''))[:10], border='B', align='C', fill=fill)
            pdf.cell(col_widths[2], 8, str(r.get('Tipo de Pago', ''))[:15], border='B', align='C', fill=fill)
            pdf.cell(col_widths[3], 8, str(r.get('Número de Referencia', ''))[:15], border='B', align='C', fill=fill)
            pdf.cell(col_widths[4], 8, f"{monto_bs:,.2f}", border='B', align='R', fill=fill)
            
            concepto = str(r.get('Concepto', '')).replace('\n', ' ')[:45]
            concepto = concepto.encode('latin-1', 'replace').decode('latin-1')
            
            tasa_str = str(r.get('Tasa BCV', '0')).replace(',', '.')
            try: tasa_bcv = float(tasa_str)
            except: tasa_bcv = 0.0
            
            acum_str = str(r.get('Acumulado', '0')).replace(',', '.')
            try: acum_bs = float(acum_str)
            except: acum_bs = 0.0
            
            acum_usd_str = str(r.get('Acumulado $', '0')).replace(',', '.')
            try: acum_usd = float(acum_usd_str)
            except: acum_usd = 0.0

            pdf.cell(col_widths[5], 8, concepto, border='B', fill=fill)
            pdf.cell(col_widths[6], 8, f"{tasa_bcv:,.2f}", border='B', align='C', fill=fill)
            pdf.cell(col_widths[7], 8, f"{usd_monto:,.2f}", border='B', align='R', fill=fill)
            pdf.cell(col_widths[8], 8, f"{acum_bs:,.2f}", border='B', align='R', fill=fill)
            pdf.cell(col_widths[9], 8, f"{acum_usd:,.2f}", border='B', align='R', fill=fill)
            pdf.ln()
            fill = not fill
            
        pdf.ln(10)
        
        # Resumen
        saldo_final_bs = total_ingreso_bs - total_egreso_bs
        saldo_final_usd = total_ingreso_usd - total_egreso_usd
        
        pdf.set_fill_color(230, 240, 250)
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(41, 128, 185)
        pdf.cell(120, 8, "  RESUMEN MENSUAL", border=1, ln=True, fill=True)
        
        pdf.set_text_color(50, 50, 50)
        pdf.set_font("Arial", size=10)
        pdf.cell(40, 8, "Total Ingresos:", border='L')
        pdf.set_text_color(39, 174, 96) # Verde
        pdf.cell(40, 8, f"{total_ingreso_bs:,.2f} Bs", border=0, align='R')
        pdf.cell(40, 8, f"{total_ingreso_usd:,.2f} $", border='R', align='R', ln=True)
        
        pdf.set_text_color(50, 50, 50)
        pdf.cell(40, 8, "Total Egresos:", border='L')
        pdf.set_text_color(192, 57, 43) # Rojo
        pdf.cell(40, 8, f"{total_egreso_bs:,.2f} Bs", border=0, align='R')
        pdf.cell(40, 8, f"{total_egreso_usd:,.2f} $", border='R', align='R', ln=True)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(40, 8, "SALDO NETO:", border='LB', fill=True)
        pdf.set_text_color(41, 128, 185) # Azul
        pdf.cell(40, 8, f"{saldo_final_bs:,.2f} Bs", border='B', align='R', fill=True)
        pdf.cell(40, 8, f"{saldo_final_usd:,.2f} $", border='RB', align='R', fill=True, ln=True)
        
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        pdf.output(path)
        return path
        
    except Exception as e:
        logger.error(f"Error generando PDF: {e}")
        return None

def obtener_tasa_bcv(fecha_str=None):
    if fecha_str:
        try:
            fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
            today = datetime.today()
            if fecha_obj.date() < today.date():
                for i in range(5):
                    check_date = fecha_obj - timedelta(days=i)
                    url = f"https://ve.dolarapi.com/v1/historicos/dolares/oficial/{check_date.strftime('%Y/%m/%d')}"
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        val = data.get('promedio')
                        if val: return val
        except Exception as e:
            logger.error(f"Error obteniendo tasa histórica: {e}")

    try:
        response = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=10)
        if response.status_code == 200:
            data = response.json()
            val = data.get('promedio')
            if val: return val
    except Exception as e:
        logger.error(f"Error obteniendo tasa BCV (DolarApi): {e}")
        
    try:
        # Fallback scrapeando directamente el BCV
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get('https://www.bcv.org.ve/', verify=False, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        dolar_div = soup.find('div', id='dolar')
        rate = dolar_div.find('strong').text.strip().replace(',', '.')
        return float(rate)
    except Exception as e:
        logger.error(f"Error obteniendo tasa BCV (Scraping): {e}")
        
    return 36.6 # Fallback final absoluto

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"¡Hola! Soy el Bot Contable de la Sede {nombre_sede}. Envíame la foto de un comprobante.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo_file = await update.message.photo[-1].get_file(read_timeout=30)
        message_id = update.message.message_id
        temp_messages[message_id] = {"type": "photo", "data": photo_file}
        
        keyboard = [
            [
                InlineKeyboardButton("🟢 Es un Ingreso", callback_data=f"ingreso_{message_id}"),
                InlineKeyboardButton("🔴 Es un Egreso", callback_data=f"egreso_{message_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Recibí el comprobante en foto. ¿Cómo debo clasificarlo?",
            reply_markup=reply_markup,
            reply_to_message_id=message_id
        )
    except Exception as e:
        logger.error(f"Error recibiendo foto: {e}")
        await update.message.reply_text("❌ Hubo un error de conexión al recibir la foto. Por favor, reenvíala.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        message_id = update.message.message_id
        temp_messages[message_id] = {"type": "text", "data": text}
        
        keyboard = [
            [
                InlineKeyboardButton("🟢 Es un Ingreso", callback_data=f"ingreso_{message_id}"),
                InlineKeyboardButton("🔴 Es un Egreso", callback_data=f"egreso_{message_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Recibí el comprobante en texto. ¿Cómo debo clasificarlo?",
            reply_markup=reply_markup,
            reply_to_message_id=message_id
        )
    except Exception as e:
        logger.error(f"Error recibiendo texto: {e}")
        await update.message.reply_text("❌ Hubo un error al recibir el texto. Por favor, reenvíalo.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("deshacer_"):
        parts = query.data.split('_')
        row_index = int(parts[1])
        referencia = parts[2]
        tiene_comision = parts[3] if len(parts) > 3 else "0"
        
        await query.edit_message_text(f"⏳ Intentando deshacer pago con Ref: {referencia}...")
        try:
            doc = gclient.open_by_key(SHEET_ID)
            sheet = doc.sheet1
            
            # Verificamos si sigue siendo la última fila o si al menos coincide la referencia
            refs = sheet.col_values(4)
            if len(refs) >= row_index and str(refs[row_index-1]).strip() == referencia:
                # ¡Lo borramos y recalculamos!
                if tiene_comision == "1":
                    borrar_fila_y_recalcular(sheet, row_index, 2)
                else:
                    borrar_fila_y_recalcular(sheet, row_index, 1)
                await query.edit_message_text(f"✅ Pago deshecho correctamente. (Referencia: {referencia})")
            else:
                await query.edit_message_text("❌ No se pudo deshacer. El pago ya no está en la misma posición. Por favor, usa el comando /eliminar.")
        except Exception as e:
            logger.error(f"Error al deshacer pago: {e}")
            await query.edit_message_text(f"❌ Ocurrió un error al intentar deshacer: {e}")
        return

    if query.data.startswith("reporte_"):
        if query.data == "reporte_anios":
            await query.edit_message_text("⏳ Consultando años...")
            fechas = obtener_fechas_disponibles(SHEET_ID)
            anios = sorted(list(set(y for m, y in fechas)), reverse=True)
            keyboard = []
            for a in anios:
                keyboard.append([InlineKeyboardButton(str(a), callback_data=f"reporte_anio_{a}")])
            keyboard.append([InlineKeyboardButton("⏪ Volver al más reciente", callback_data="reporte_inicio")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📅 Seleccione un año:", reply_markup=reply_markup)
            return
            
        if query.data == "reporte_inicio":
            fechas = obtener_fechas_disponibles(SHEET_ID)
            if not fechas: return
            anio_reciente = fechas[0][1]
            months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            keyboard = []
            for (m, y) in fechas:
                if y == anio_reciente:
                    keyboard.append([InlineKeyboardButton(f"{months[m-1]} {y}", callback_data=f"reporte_mes_{m}_{y}")])
            otros_anios = set(y for m, y in fechas if y != anio_reciente)
            if otros_anios:
                keyboard.append([InlineKeyboardButton("📅 Otros Años", callback_data="reporte_anios")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"🗓 Reportes de {anio_reciente}. Seleccione el mes:", reply_markup=reply_markup)
            return

        if query.data.startswith("reporte_anio_"):
            await query.edit_message_text("⏳ Consultando meses...")
            anio_seleccionado = int(query.data.split('_')[2])
            fechas = obtener_fechas_disponibles(SHEET_ID)
            months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            keyboard = []
            for (m, y) in fechas:
                if y == anio_seleccionado:
                    keyboard.append([InlineKeyboardButton(f"{months[m-1]} {y}", callback_data=f"reporte_mes_{m}_{y}")])
            keyboard.append([InlineKeyboardButton("⏪ Volver", callback_data="reporte_anios")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"🗓 Meses disponibles para {anio_seleccionado}:", reply_markup=reply_markup)
            return

        if query.data.startswith("reporte_mes_"):
            await query.edit_message_text("⏳ Generando reporte PDF. Por favor espera unos segundos...")
            parts = query.data.split('_')
            mes = int(parts[2])
            anio = int(parts[3])
            
            pdf_path = generar_pdf_mes(mes, anio, SHEET_ID, nombre_sede)
            
            if pdf_path:
                with open(pdf_path, 'rb') as f:
                    await context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename=f"Reporte_{nombre_sede}_{mes}_{anio}.pdf")
                os.remove(pdf_path)
                await query.edit_message_text("✅ Reporte generado y enviado exitosamente.")
            else:
                await query.edit_message_text("❌ No se encontraron registros para ese mes o hubo un error al generar el PDF.")
            return

    data = query.data.split('_')
    tipo_movimiento = "Ingreso" if data[0] == "ingreso" else "Egreso"
    message_id = int(data[1])
    
    if message_id not in temp_messages:
        await query.edit_message_text("Error: El mensaje expiró o no se encuentra en memoria. Por favor, reenvíalo.")
        return
        
    await query.edit_message_text(f"⏳ Procesando como {tipo_movimiento}... Analizando con IA...")
    
    msg_data = temp_messages.pop(message_id)
    
    try:
        fecha_actual_str = datetime.today().strftime('%d/%m/%Y')
        prompt = f"El código del banco origen es '{BANCO_ORIGEN_CODIGO}'.\nLa fecha de hoy es {fecha_actual_str}.\n" + """
        Eres un experto asistente contable venezolano. Analiza este comprobante de pago.
        Extrae la siguiente información y devuélvela ÚNICAMENTE como un objeto JSON válido, sin markdown ni texto adicional:
        {
            "fecha": "dd/mm/aaaa (Si dice 'Hoy' o no tiene año, usa la fecha de hoy que se indicó arriba)",
            "tipo_pago": "Clasifica como: 'Pago Móvil' (incluye Pago Plus), 'Transferencia', 'Punto de Venta' (incluye POS, voucher impreso de maquinita, TDD o tarjeta), 'Recarga' o 'Pago de Servicio'",
            "referencia": "Solo los números de la referencia bancaria, ej. 150324229212. Si dice N° de Transacción, Aprobación, Lote, Recibo o Número de Confirmación, extrae esos números.",
            "monto": "Monto exacto de la operación SIN separadores de miles y usando PUNTO para los decimales (ej. 4036.00 o 65098.89). No incluyas Bs ni $ ni signos negativos.",
            "concepto": "Motivo del pago. Si no indica, pon 'Sin concepto' o usa lo que diga en concepto/descripción.",
            "es_mismo_banco": true o false. (True si los primeros 4 dígitos de la cuenta destino coinciden con el código del banco origen especificado arriba. Si no puedes ver la cuenta destino, usa false),
            "tipo_destinatario": "Clasifica como 'Persona' o 'Comercio'. Usa 'Comercio' si ves un RIF J/G/C, el nombre de una empresa, o si dice 'Pago Plus Comercios' o P2C. De lo contrario, asume 'Persona'."
        }
        """
        max_retries = 6
        response = None
        for attempt in range(max_retries):
            try:
                if msg_data["type"] == "photo":
                    photo_bytes = await msg_data["data"].download_as_bytearray()
                    contents = [
                        prompt,
                        types.Part.from_bytes(data=bytes(photo_bytes), mime_type='image/jpeg')
                    ]
                else:
                    text_content = msg_data["data"]
                    contents = [
                        prompt + "\n\nA continuación el texto del comprobante:\n\n" + text_content
                    ]

                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=contents
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Intento {attempt+1} fallido (posible 503): {e}. Reintentando en 5s...")
                await asyncio.sleep(5)

        import re
        json_text = response.text.strip()
        match = re.search(r'\{.*\}', json_text, re.DOTALL)
        if match:
            json_text = match.group(0)
            
        extracted_data = json.loads(json_text)
        
        doc = gclient.open_by_key(SHEET_ID)
        sheet = doc.sheet1
        
        referencia_extraida = extracted_data.get('referencia', '')
        if referencia_extraida:
            referencias_existentes = sheet.col_values(4)
            # Validamos que no esté duplicada.
            if str(referencia_extraida) in [str(r).strip() for r in referencias_existentes if str(r).strip() != '']:
                await query.edit_message_text(f"⚠️ Este comprobante ya fue registrado anteriormente (Referencia: {referencia_extraida}). Se ha ignorado.")
                return
        
        tasa = obtener_tasa_bcv(extracted_data.get('fecha', ''))
        monto_raw = str(extracted_data.get('monto', '0')).strip().replace('Bs.', '').replace('Bs', '').replace('$', '').strip()
        if '.' in monto_raw and ',' in monto_raw:
            if monto_raw.rfind(',') > monto_raw.rfind('.'):
                monto_raw = monto_raw.replace('.', '').replace(',', '.')
            else:
                monto_raw = monto_raw.replace(',', '')
        elif ',' in monto_raw:
            monto_raw = monto_raw.replace(',', '.')
        monto_raw = monto_raw.replace(' ', '')
        try:
            monto_float = float(monto_raw)
            monto_float = round(monto_float, 2)
        except ValueError:
            monto_float = 0.0
            
        comision_bs = 0.0
        concepto = extracted_data.get('concepto', '')
        tipo_pago_extraido = str(extracted_data.get('tipo_pago', '')).lower()
        tipo_destinatario = str(extracted_data.get('tipo_destinatario', '')).lower()
        es_mismo_banco = extracted_data.get('es_mismo_banco', False)
        
        if tipo_movimiento == 'Egreso':
            if any(palabra in tipo_pago_extraido for palabra in ['punto', 'pos', 'recarga', 'servicio']):
                comision_bs = 0.00
            elif 'transferencia' in tipo_pago_extraido:
                if es_mismo_banco:
                    comision_bs = 0.00
                else:
                    comision_bs = 54.00
            else:
                if 'comercio' in tipo_destinatario:
                    comision_bs = max(monto_float * 0.015, 14.00) # P2C
                else:
                    comision_bs = max(monto_float * 0.003, 14.00) # P2P
        
        comision_bs = round(comision_bs, 2)
                
        next_row = len(sheet.col_values(1)) + 1
        
        tasa = round(tasa, 2)
        cantidad_dolares = f"=ROUND(E{next_row}/G{next_row}, 2)"
        if next_row == 2:
            acumulado = f"=ROUND(IF(A2=\"Ingreso\",E2,-E2), 2)"
            acumulado_usd = f"=ROUND(IF(A2=\"Ingreso\",H2,-H2), 2)"
        else:
            acumulado = f"=ROUND(I{next_row-1}+(IF(A{next_row}=\"Ingreso\",E{next_row},-E{next_row})), 2)"
            acumulado_usd = f"=ROUND(J{next_row-1}+(IF(A{next_row}=\"Ingreso\",H{next_row},-H{next_row})), 2)"
            
        row_data = [
            tipo_movimiento,
            extracted_data.get('fecha', ''),
            extracted_data.get('tipo_pago', ''),
            extracted_data.get('referencia', ''),
            monto_float,
            concepto,
            tasa,
            cantidad_dolares,
            acumulado,
            acumulado_usd
        ]
        
        sheet.insert_row(row_data, next_row, value_input_option='USER_ENTERED')
        
        tiene_comision = "0"
        if comision_bs > 0:
            tiene_comision = "1"
            comision_row_num = next_row + 1
            com_dolares = f"=ROUND(E{comision_row_num}/G{comision_row_num}, 2)"
            com_acumulado = f"=ROUND(I{comision_row_num-1}+(IF(A{comision_row_num}=\"Ingreso\",E{comision_row_num},-E{comision_row_num})), 2)"
            com_acumulado_usd = f"=ROUND(J{comision_row_num-1}+(IF(A{comision_row_num}=\"Ingreso\",H{comision_row_num},-H{comision_row_num})), 2)"
            comision_row_data = [
                'Egreso',
                extracted_data.get('fecha', ''),
                'COMISION',
                extracted_data.get('referencia', ''),
                comision_bs,
                concepto,
                tasa,
                com_dolares,
                com_acumulado,
                com_acumulado_usd
            ]
            sheet.insert_row(comision_row_data, comision_row_num, value_input_option='USER_ENTERED')
        
        mensaje_exito = f"✅ Registrado exitosamente en la Sede {nombre_sede}\n"
        mensaje_exito += f"Concepto: {concepto}\n"
        mensaje_exito += f"Monto: {monto_float:,.2f} (Ref: {extracted_data.get('referencia')})\n"
        if comision_bs > 0:
            mensaje_exito += f"Comisión: {comision_bs:,.2f} (Cobrada)\n"
        mensaje_exito += f"Tasa BCV: {tasa:,.2f}"
        
        keyboard = [[InlineKeyboardButton("❌ Deshacer este pago", callback_data=f"deshacer_{next_row}_{extracted_data.get('referencia')}_{tiene_comision}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(mensaje_exito, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        import traceback
        trace = traceback.format_exc()
        with open('error_log.txt', 'a') as f:
            f.write(trace + '\n')
        error_texto = str(e)
        if "503" in error_texto or "UNAVAILABLE" in error_texto or "429" in error_texto or "ResourceExhausted" in error_texto:
            await query.edit_message_text("⏳ Los servidores de lectura automática están muy ocupados en este instante. Por favor, reenvía la imagen en unos 30 segundos.")
        else:
            await query.edit_message_text(f"❌ Ocurrió un error inesperado al leer el comprobante. Intenta enviarlo de nuevo o revisa si la imagen es clara. (Detalle técnico: {error_texto})")


def obtener_fechas_disponibles(sheet_id):
    try:
        doc = gclient.open_by_key(sheet_id)
        sheet = doc.sheet1
        records = sheet.get_all_records()
        
        fechas_unicas = set()
        for r in records:
            fecha_str = r.get('Fecha', '')
            if fecha_str:
                try:
                    from datetime import datetime
                    f_obj = datetime.strptime(str(fecha_str), "%d/%m/%Y")
                    fechas_unicas.add((f_obj.month, f_obj.year))
                except:
                    pass
        # Order descending by year then month
        fechas_ordenadas = sorted(list(fechas_unicas), key=lambda x: (x[1], x[0]), reverse=True)
        return fechas_ordenadas
    except Exception as e:
        logger.error(f"Error obteniendo fechas disponibles: {e}")
        return []

async def reporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Consultando registros...")
    fechas = obtener_fechas_disponibles(SHEET_ID)
    if not fechas:
        await msg.edit_text("❌ No hay pagos registrados en el balance.")
        return
        
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    anio_reciente = fechas[0][1]
    
    keyboard = []
    for (m, y) in fechas:
        if y == anio_reciente:
            keyboard.append([InlineKeyboardButton(f"{months[m-1]} {y}", callback_data=f"reporte_mes_{m}_{y}")])
            
    otros_anios = set(y for m, y in fechas if y != anio_reciente)
    if otros_anios:
        keyboard.append([InlineKeyboardButton("📅 Otros Años", callback_data="reporte_anios")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.edit_text(f"🗓 Reportes de {anio_reciente}. Seleccione el mes:", reply_markup=reply_markup)

async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Calculando el saldo histórico global...")
    try:
        doc = gclient.open_by_key(SHEET_ID)
        sheet = doc.sheet1
        records = sheet.get_all_records()
        
        total_ingreso_bs = 0.0
        total_egreso_bs = 0.0
        total_ingreso_usd = 0.0
        total_egreso_usd = 0.0
        
        for r in records:
            monto_bs_str = str(r.get('Monto', '0')).replace(',', '.')
            try: monto_bs = float(monto_bs_str)
            except: monto_bs = 0.0
            
            usd_str = str(r.get('Cantidad en $', '0')).replace(',', '.')
            try: usd_monto = float(usd_str)
            except: usd_monto = 0.0
            
            tipo = str(r.get('Tipo (Ingreso/Egreso)', ''))
            
            if tipo.lower() == 'ingreso':
                total_ingreso_bs += monto_bs
                total_ingreso_usd += usd_monto
            else:
                total_egreso_bs += monto_bs
                total_egreso_usd += usd_monto
                
        saldo_bs = total_ingreso_bs - total_egreso_bs
        saldo_usd = total_ingreso_usd - total_egreso_usd
        
        if records:
            texto = (
                f"🏛 *BALANCE GLOBAL HISTÓRICO - {nombre_sede}*\n\n"
                f"📈 *Total Ingresos:*\n"
                f"    {total_ingreso_bs:,.2f} Bs\n"
                f"    {total_ingreso_usd:,.2f} $\n\n"
                f"📉 *Total Egresos:*\n"
                f"    {total_egreso_bs:,.2f} Bs\n"
                f"    {total_egreso_usd:,.2f} $\n\n"
                f"💰 *SALDO FINAL EN CAJA:*\n"
                f"    *{saldo_bs:,.2f} Bs*\n"
                f"    *{saldo_usd:,.2f} $*"
            )
            await msg.edit_text(texto, parse_mode='Markdown')
        else:
            await msg.edit_text("No hay registros en el balance todavía.")
            
    except Exception as e:
        logger.error(f"Error en comando saldo: {e}")
        await msg.edit_text("❌ Hubo un error consultando el saldo.")


def borrar_fila_y_recalcular(sheet, row_index, num_filas=1):
    for _ in range(num_filas):
        sheet.delete_rows(row_index)
        
    total_filas = len(sheet.col_values(1))
    if total_filas < row_index:
        return
        
    cell_list = sheet.range(f'I{row_index}:J{total_filas}')
    current_row = row_index
    for i in range(0, len(cell_list), 2):
        cell_list[i].value = f"=I{current_row-1}+(IF(A{current_row}=\"Ingreso\",E{current_row},-E{current_row}))"
        cell_list[i+1].value = f"=J{current_row-1}+(IF(A{current_row}=\"Ingreso\",H{current_row},-H{current_row}))"
        current_row += 1
        
    sheet.update_cells(cell_list, value_input_option='USER_ENTERED')

async def eliminar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Uso incorrecto. Debes enviar: /eliminar <referencia>")
        return
        
    referencia = context.args[0]
    msg = await update.message.reply_text(f"⏳ Buscando la referencia {referencia}...")
    
    try:
        doc = gclient.open_by_key(SHEET_ID)
        sheet = doc.sheet1
        refs = sheet.col_values(4)
        
        # Encontrar las filas que coincidan con la referencia (de abajo hacia arriba para no romper los índices)
        filas_a_borrar = []
        for i, ref in enumerate(refs):
            if str(ref).strip() == referencia:
                filas_a_borrar.insert(0, i + 1)
                
        if not filas_a_borrar:
            await msg.edit_text("❌ No se encontró ningún pago con esa referencia.")
            return
            
        for idx in filas_a_borrar:
            borrar_fila_y_recalcular(sheet, idx)
            
        await msg.edit_text(f"✅ Pago con Referencia {referencia} eliminado y saldos recalculados correctamente.")
        
    except Exception as e:
        logger.error(f"Error en comando eliminar: {e}")
        await msg.edit_text(f"❌ Ocurrió un error al intentar eliminar: {e}")

async def post_init(application: Application):
    commands = [
        BotCommand("start", "Iniciar el bot"),
        BotCommand("saldo", "Consultar el saldo actual"),
        BotCommand("reporte", "Generar reporte mensual en PDF"),
        BotCommand("eliminar", "Eliminar un pago usando su referencia")
    ]
    await application.bot.set_my_commands(commands)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).pool_timeout(30).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("saldo", saldo_command))
    application.add_handler(CommandHandler("reporte", reporte_command))
    application.add_handler(CommandHandler("eliminar", eliminar_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info(f"Iniciando Bot para Sede {nombre_sede} ({sede_id})...")
    application.run_polling()

if __name__ == '__main__':
    main()
