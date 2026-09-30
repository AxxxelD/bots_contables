# Bots Contables en Telegram 

Este proyecto es un sistema de automatización contable basado en múltiples bots de Telegram, diseñado para gestionar el registro de ingresos y egresos de distintas sedes de forma centralizada utilizando Google Sheets.

## Características Principales 
* **Múltiples Bots (Sedes):** Capacidad de gestionar diferentes sedes (ej. Puerto Ordaz, Puerto La Cruz, El Tigre, Porlamar) desde un solo núcleo de código.
* **Procesamiento de Comprobantes:** Los usuarios pueden enviar fotos de comprobantes de pago (transferencias, pago móvil). El bot extrae automáticamente la información clave (monto, fecha, referencia) usando Inteligencia Artificial (Google Gemini).
* **Base de Datos en la Nube:** Registra toda la contabilidad directamente en hojas de cálculo de Google Sheets en tiempo real, manteniendo un orden estricto de las finanzas.
* **Tasa de Cambio en Tiempo Real:** Obtiene la tasa oficial del Banco Central de Venezuela (BCV) consultando APIs, y procesa pagos multi-moneda (Bs. y USD).
* **Generación de Reportes PDF:** Genera automáticamente reportes mensuales de caja en formato PDF con diseños tabulares listos para revisión y auditoría.
* **Gestión Asíncrona:** Construido sobre `python-telegram-bot` usando flujos asíncronos (`async/await`) para mayor rapidez y concurrencia.

## Tecnologías Utilizadas
* **Python 3**
* **python-telegram-bot (v20+)**: Para la interfaz asíncrona de Telegram.
* **Google Gemini API**: Para la extracción de datos desde imágenes (OCR inteligente).
* **Google Sheets API & gspread**: Para el almacenamiento de base de datos.
* **FPDF**: Para la generación de reportes mensuales en PDF.
* **Requests & BeautifulSoup**: Para obtención de las tasas de cambio de divisas.
