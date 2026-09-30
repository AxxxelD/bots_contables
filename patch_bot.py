import os

with open('bot.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add imports
imports = """from telegram import BotCommand
import tempfile
from fpdf import FPDF
"""
code = code.replace("from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup", imports + "from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup")

# Add generar_pdf_mes
pdf_func = """
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
            
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Reporte Contable - Sede {nombre_sede}", ln=True, align='C')
        pdf.cell(0, 10, f"Mes: {months[mes-1]} {anio}", ln=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 8)
        col_widths = [15, 20, 25, 25, 20, 60, 15, 25, 25]
        headers = ['Tipo', 'Fecha', 'Tipo Pago', 'Referencia', 'Monto Bs', 'Concepto', 'Tasa', 'Total $', 'Acumulado']
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, border=1, align='C')
        pdf.ln()
        
        pdf.set_font("Arial", size=8)
        total_ingreso_bs = 0.0
        total_egreso_bs = 0.0
        total_ingreso_usd = 0.0
        total_egreso_usd = 0.0
        
        for r in filtered_records:
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
            
            pdf.cell(col_widths[0], 6, str(tipo)[:10], border=1)
            pdf.cell(col_widths[1], 6, str(r.get('Fecha', ''))[:10], border=1)
            pdf.cell(col_widths[2], 6, str(r.get('Tipo de Pago', ''))[:15], border=1)
            pdf.cell(col_widths[3], 6, str(r.get('Número de Referencia', ''))[:15], border=1)
            pdf.cell(col_widths[4], 6, f"{monto_bs:,.2f}", border=1, align='R')
            
            # Limpiar saltos de linea en concepto
            concepto = str(r.get('Concepto', '')).replace('\\n', ' ')[:45]
            # Replace invalid latin-1 characters that might break fpdf
            concepto = concepto.encode('latin-1', 'replace').decode('latin-1')
            
            pdf.cell(col_widths[5], 6, concepto, border=1)
            pdf.cell(col_widths[6], 6, str(r.get('Tasa BCV', ''))[:10], border=1)
            pdf.cell(col_widths[7], 6, f"{usd_monto:,.2f}", border=1, align='R')
            pdf.cell(col_widths[8], 6, str(r.get('Acumulado', ''))[:15], border=1, align='R')
            pdf.ln()
            
        pdf.ln(5)
        
        saldo_final_bs = total_ingreso_bs - total_egreso_bs
        saldo_final_usd = total_ingreso_usd - total_egreso_usd
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, "RESUMEN DEL MES:", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(60, 6, f"Total Ingresos:", border=0)
        pdf.cell(60, 6, f"{total_ingreso_bs:,.2f} Bs", border=0, align='R')
        pdf.cell(60, 6, f"{total_ingreso_usd:,.2f} $", border=0, align='R', ln=True)
        
        pdf.cell(60, 6, f"Total Egresos:", border=0)
        pdf.cell(60, 6, f"{total_egreso_bs:,.2f} Bs", border=0, align='R')
        pdf.cell(60, 6, f"{total_egreso_usd:,.2f} $", border=0, align='R', ln=True)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(60, 8, f"SALDO FINAL DEL MES:", border=0)
        pdf.cell(60, 8, f"{saldo_final_bs:,.2f} Bs", border=0, align='R')
        pdf.cell(60, 8, f"{saldo_final_usd:,.2f} $", border=0, align='R', ln=True)
        
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        pdf.output(path)
        return path
        
    except Exception as e:
        logger.error(f"Error generando PDF: {e}")
        return None

"""
code = code.replace("def obtener_tasa_bcv", pdf_func + "def obtener_tasa_bcv")

# Add reporte command
reporte_cmd = """
async def reporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    keyboard = []
    now = datetime.now()
    for i in range(6):
        m = (now.month - i - 1) % 12 + 1
        y = now.year + (now.month - i - 1) // 12
        month_name = f"{months[m-1]} {y}"
        callback_data = f"reporte_{m}_{y}"
        keyboard.append([InlineKeyboardButton(month_name, callback_data=callback_data)])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🗓 Seleccione el mes para generar el reporte PDF:", reply_markup=reply_markup)

"""
code = code.replace("async def saldo_command", reporte_cmd + "async def saldo_command")

# Add callback handler for reporte
reporte_handler = """    if query.data.startswith("reporte_"):
        await query.edit_message_text("⏳ Generando reporte PDF. Por favor espera unos segundos...")
        parts = query.data.split('_')
        mes = int(parts[1])
        anio = int(parts[2])
        
        pdf_path = generar_pdf_mes(mes, anio, SHEET_ID, nombre_sede)
        
        if pdf_path:
            with open(pdf_path, 'rb') as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename=f"Reporte_{nombre_sede}_{mes}_{anio}.pdf")
            os.remove(pdf_path)
            await query.edit_message_text("✅ Reporte generado y enviado exitosamente.")
        else:
            await query.edit_message_text("❌ No se encontraron registros para ese mes o hubo un error al generar el PDF.")
        return

"""
code = code.replace("    data = query.data.split('_')", reporte_handler + "    data = query.data.split('_')")

# Add BotCommand init
bot_command = """
async def post_init(application: Application):
    commands = [
        BotCommand("start", "Iniciar el bot"),
        BotCommand("saldo", "Consultar el saldo actual"),
        BotCommand("reporte", "Generar reporte mensual en PDF")
    ]
    await application.bot.set_my_commands(commands)

"""
code = code.replace("def main():", bot_command + "def main():")

# Attach post_init and command handler
code = code.replace("Application.builder().token(TELEGRAM_TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).pool_timeout(30).build()", "Application.builder().token(TELEGRAM_TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).pool_timeout(30).post_init(post_init).build()")
code = code.replace("application.add_handler(CommandHandler(\"saldo\", saldo_command))", "application.add_handler(CommandHandler(\"saldo\", saldo_command))\n    application.add_handler(CommandHandler(\"reporte\", reporte_command))")

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch successful.")
