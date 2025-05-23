import sys
import traceback
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, ConversationState, UserState, MemoryStorage, TurnContext
from botbuilder.schema import Activity
import logging
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

# Configura logging
logging.basicConfig(level=logging.DEBUG)

from bot import EchoBot, tipos_de_caso

# URL de ngrok (actualiza con tu URL de ngrok activa)
NGROK_URL = "https://4166-181-51-32-22.ngrok-free.app"

# Configuración del adaptador
SETTINGS = BotFrameworkAdapterSettings(os.getenv("APP_ID"), os.getenv("APP_PASSWORD"))
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Configuración del estado
MEMORY = MemoryStorage()
CONVERSATION_STATE = ConversationState(MEMORY)
USER_STATE = UserState(MEMORY)

# Instancia del bot
BOT = EchoBot(CONVERSATION_STATE, USER_STATE)

# Endpoint para recibir mensajes
async def messages(req: web.Request) -> web.Response:
    logging.debug(f"Método HTTP recibido: {req.method}")
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        logging.error("Content-Type no es application/json")
        return web.Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")
    
    # Sobrescribe el serviceUrl con la URL de ngrok
    if activity.service_url and "localhost" in activity.service_url:
        activity.service_url = f"{NGROK_URL}/api/messages"
        logging.debug(f"serviceUrl sobrescrito a: {activity.service_url}")
    
    logging.debug(f"Actividad recibida: {activity}")
    logging.debug(f"Encabezado de autorización: {auth_header}")
    
    try:
        # Procesar la actividad con el adaptador
        await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        # Guardar estados usando el contexto de turno
        turn_context = TurnContext(ADAPTER, activity)
        await CONVERSATION_STATE.save_changes(turn_context)
        await USER_STATE.save_changes(turn_context)
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Error detallado: {e}")
        logging.error(f"Tipo de error: {type(e)}")
        traceback.print_exc()
        return web.Response(status=500)

# Configuración del servidor web
app = web.Application()
app.router.add_post("/api/messages", messages)

# Manejo de cierre del servidor
async def on_shutdown(app):
    logging.info("Cerrando el servidor...")
    # No se necesita cancelar tareas explícitamente, aiohttp lo maneja
    await asyncio.sleep(0.1)  # Dar tiempo para cerrar conexiones

app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    try:
        web.run_app(app, host="localhost", port=3978)
    except Exception as e:
        logging.error(f"Error al iniciar el servidor: {e}")
        sys.exit(1)