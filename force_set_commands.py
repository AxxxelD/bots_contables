import os
import asyncio
from telegram import Bot, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeDefault
from dotenv import load_dotenv

load_dotenv()

async def main():
    tokens = [
        os.getenv("TELEGRAM_TOKEN_SEDE_1"),
        os.getenv("TELEGRAM_TOKEN_SEDE_2"),
        os.getenv("TELEGRAM_TOKEN_SEDE_3"),
        os.getenv("TELEGRAM_TOKEN_SEDE_4")
    ]
    
    commands = [
        BotCommand("start", "Iniciar el bot"),
        BotCommand("saldo", "Consultar el saldo actual"),
        BotCommand("reporte", "Generar reporte mensual en PDF"),
        BotCommand("eliminar", "Eliminar un pago usando su referencia")
    ]
    
    for t in tokens:
        if t:
            bot = Bot(t)
            try:
                # Set for both default and all group chats explicitly to ensure autocomplete works
                await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
                await bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
                print(f"Commands set successfully for bot with token starting {t[:5]}...")
            except Exception as e:
                print(f"Error setting commands for bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
