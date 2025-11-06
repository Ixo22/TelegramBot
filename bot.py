import yfinance as yf
import logging
import random
import re
import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    CommandHandler, 
    MessageHandler,  
    filters,
    CallbackQueryHandler 
)




# --- SERVIDOR FARSANTE PARA KOYEB ---
app = Flask(__name__)

@app.route('/')
def hello():
    """Respuesta 'estoy vivo' para el health check de Koyeb."""
    return "Bot is alive!"

def run_web_server():
    """Ejecuta el servidor web en el puerto que Koyeb asigne."""
    # Koyeb (y otros) nos dice el puerto a usar en la variable $PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
# --------------------------------------






# --- ¡CONFIGURACIÓN OBLIGATORIA! ---
MI_TOKEN = os.environ.get("MI_TOKEN")
MI_CHAT_ID = os.environ.get("MI_CHAT_ID") # (Aunque ya no lo uses, por si acaso)

if not MI_TOKEN:
    print("!!! ERROR CRÍTICO: No se encontró la variable de entorno MI_TOKEN !!!")
    # Si no hay token, el bot no puede ni arrancar
    exit()

from config import (
    TICKERS_A_VIGILAR,
    PATRON_SALUDO,
    PATRON_GRACIAS,
    PATRON_TICKERS,
    PATRON_OPCIONES,
    PATRON_TODO,
    POSIBLES_SALUDOS,
    POSIBLES_DE_NADA)
# ------------------------------------

# Configuramos el logging para ver qué pasa (buena práctica)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)



# --- 1. Lógica del Mercado (Copiada de tracker.py) ---

def obtener_precio_actual(ticker_simbolo):
    """
    Obtiene el último precio del ticker.
    Devuelve (precio_actual, moneda) o (None, None) si falla.
    """
    print(f"Buscando datos de [{ticker_simbolo}]...")
    try:
        ticker = yf.Ticker(ticker_simbolo)
        info_rapida = ticker.fast_info
        
        precio_actual = info_rapida['last_price']
        moneda = info_rapida['currency']
        
        # Devuelve los DATOS, no un mensaje
        return precio_actual, moneda 

    except Exception as e:
        print(f"*** ERROR al obtener precio para {ticker_simbolo}: {e} ***")
        return None, None # Devuelve 'Nada' para que el otro lo gestione

# --- 2. Lógica de Comandos del Bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde cuando el usuario envía /start"""
    mensaje_bienvenida = (
        "¡Hola! Soy tu Vigía de Bolsa.\n\n"
        "Simplemente escríbeme qué quieres ver:\n"
        "  -> 'sp500'\n"
        "  -> 'nasdaq'\n"
        "  -> 'cuanto vale el oro'\n\n"
        "Para ver todos los comandos de ayuda, escribe /opciones."
    )
    await update.message.reply_text(mensaje_bienvenida)


async def opciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra un menú de ayuda actualizado"""
    mensaje_opciones = (
        "**Opciones Disponibles**\n\n"
        "🤖 **Modo Inteligente** (Recomendado):\n"
        "Escríbeme directamente el activo que buscas. Entiendo frases como:\n"
        "  -> 'sp500'\n"
        "  -> 'precio del 100 (nasdaq100)'\n"
        "  -> 'oro'\n\n"
        "🆘 **Comandos de Ayuda**:\n"
        "  -> /start (Ver el mensaje de bienvenida)\n"
        "  -> /opciones (Ver este menú)\n"
        "  -> /tickers (Ver lista de activos)\n"
    )
    # parse_mode="Markdown" permite usar las negritas (**)
    await update.message.reply_text(mensaje_opciones, parse_mode="Markdown")
    


async def tickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la lista de tickers como botones pulsables."""
    
    texto_mensaje = "**Tickers disponibles**\n(Pulsa para ver el precio)\n"
    
    # Creamos la lista de filas de botones
    keyboard = []
    
    # Leemos la constante global y le añadimos un índice (i)
    for i, ticker_info in enumerate(TICKERS_A_VIGILAR):
        alias = ticker_info["alias_general"]
        
        # Creamos el botón:
        # text = Lo que ve el usuario (ej: "SP500")
        # callback_data = La "señal" secreta (ej: "ticker:0")
        boton = InlineKeyboardButton(
            text=f"{alias}", 
            callback_data=f"ticker:{i}"  # Usamos el índice como ID
        )
        
        # Añadimos el botón a la lista (cada botón en su propia fila)
        keyboard.append([boton])
    
     # --- ¡NUEVO! Añadimos el botón "TODO" al final ---
    boton_todo = InlineKeyboardButton(
        text="Resumen de Mercado",
        callback_data="resumen"  # Señal "resumen" (¡distinta!)
    )
    keyboard.append([boton_todo])

    # Creamos el "teclado" con todas las filas de botones
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Enviamos el mensaje con el teclado adjunto
    await update.message.reply_text(texto_mensaje, reply_markup=reply_markup, parse_mode="Markdown")
    
    
async def enviar_resumen_core(reply_object):
    """
    Función NÚCLEO: Genera y envía el resumen.
    'reply_object' es el objeto al que responder (ej: update.message o query.message)
    """
    # 1. Avisamos al usuario
    await reply_object.reply_text("Buscando resumen de mercado... ⌛\n(Esto puede tardar unos segundos)")
    
    partes_del_mensaje = ["**Resumen de Mercado**\n"]
    
    # 2. Bucle anidado MAESTRO (Tu lógica, intacta)
    for ticker_info in TICKERS_A_VIGILAR:
        alias_general = ticker_info["alias_general"]
        lista_de_tickers = ticker_info["tickers"]
        
        partes_del_mensaje.append(f"\n*{alias_general}*:\n")
        
        for ticker_a_buscar in lista_de_tickers:
            nombre_ticker = ticker_a_buscar["nombre"]
            symbol_ticker = ticker_a_buscar["symbol"]
            
            precio, moneda = obtener_precio_actual(symbol_ticker)
            
            if precio is not None:
                linea = f"  -> {nombre_ticker}: {precio:,.2f} {moneda}\n"
                partes_del_mensaje.append(linea)
            else:
                linea = f"  -> {nombre_ticker} [{symbol_ticker}]: Error.\n"
                partes_del_mensaje.append(linea)
                
    # 3. Envío del Mensaje Final
    mensaje_final = "".join(partes_del_mensaje)
    await reply_object.reply_text(mensaje_final, parse_mode="Markdown")
    
    

async def resumen_mercado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para el *botón* "Resumen de Mercado".
    """
    query = update.callback_query
    # 1. Responde al click (esto es específico del botón)
    await query.answer("Buscando, esto tardará unos segundos...")
    
    # 2. Llama a la función núcleo, pasándole el 'query.message'
    await enviar_resumen_core(query.message)
    
    
    
    
async def boton_ticker_pulsado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Se ejecuta cuando el usuario pulsa un botón de ticker.
    """
    # 1. Obtenemos la "señal" (callback_data) del botón
    query = update.callback_query
    
    # 2. Respondemos al "click" (importante, para que deje de "cargar")
    await query.answer()
    
    # 3. Extraemos el ID del ticker (el "0", "1", etc.)
    # query.data será "ticker:0" o "ticker:1"
    try:
        prefix, index_str = query.data.split(":")
        index = int(index_str)
        
        # 4. Buscamos la info del ticker en nuestra constante global
        ticker_info = TICKERS_A_VIGILAR[index]
        
    except (ValueError, IndexError):
        await query.message.reply_text("Error: No he reconocido ese botón.")
        return

    # 5. --- (Esta lógica es COPIADA de 'manejar_texto') ---
    alias_general = ticker_info["alias_general"]
    lista_de_tickers = ticker_info["tickers"] 
    
    # query.message.reply_text envía un NUEVO mensaje
    await query.message.reply_text(f"Buscando {alias_general}...")
    
    partes_del_mensaje = [f""]

    for ticker_a_buscar in lista_de_tickers:
        nombre_ticker = ticker_a_buscar["nombre"]
        symbol_ticker = ticker_a_buscar["symbol"]
        
        precio, moneda = obtener_precio_actual(symbol_ticker)
        
        if precio is not None:
            linea = f"  -> Precio de {alias_general} ({nombre_ticker}): {precio:,.2f} {moneda}\n"
            partes_del_mensaje.append(linea)
        else:
            linea = f"  -> {nombre_ticker} [{symbol_ticker}]: Error al obtener.\n"
            partes_del_mensaje.append(linea)
    
    mensaje_final = "".join(partes_del_mensaje)
    # Enviamos el resultado como un mensaje nuevo
    await query.message.reply_text(mensaje_final, parse_mode="Markdown")


async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_recibido = update.message.text.lower().strip()
    
    # --- Lógica de decisión ---
    ticker_encontrado = False

    # PRIMERO: Recorre la base de datos de tickers (Bucle Exterior)
    for ticker_info in TICKERS_A_VIGILAR:
        
        # Si el texto del usuario coincide con el patrón
        if re.search(ticker_info["patron_regex"], texto_recibido):
            
            ticker_encontrado = True # ¡Lo pillamos!
            
            alias_general = ticker_info["alias_general"]
            lista_de_tickers = ticker_info["tickers"] 
            
            await update.message.reply_text(f"Buscando {alias_general}...")
            
            # --- CONSTRUCCIÓN DE MENSAJE ---
            # Vamos a ir guardando las líneas del mensaje aquí
            
            #partes_del_mensaje = [f"**Precios de {alias_general}**\n"]
            partes_del_mensaje = [f""]

            # SEGUNDO: Recorre los tickers anidados (Bucle Interior)
            for ticker_a_buscar in lista_de_tickers:
                
                nombre_ticker = ticker_a_buscar["nombre"]
                symbol_ticker = ticker_a_buscar["symbol"]
                
                # Llamamos a la función PURIFICADA por cada ticker
                precio, moneda = obtener_precio_actual(symbol_ticker)
                
                # Construimos la línea para este ticker
                if precio is not None:
                    linea = f"  -> Precio de {alias_general} ({nombre_ticker}): {precio:,.2f} {moneda}\n"
                    partes_del_mensaje.append(linea)
                else:
                    linea = f"  -> {nombre_ticker} [{symbol_ticker}]: Error al obtener.\n"
                    partes_del_mensaje.append(linea)
            
            # --- Envío del Mensaje ---
            # Une todas las partes en un solo mensaje y lo envía
            mensaje_final = "".join(partes_del_mensaje)
            await update.message.reply_text(mensaje_final, parse_mode="Markdown")
            
            # Rompemos el bucle EXTERIOR (ya hemos encontrado lo que queríamos)
            break 
    
    # SI NO se encontró un ticker: Comprueba si es un saludo o gracias
    if not ticker_encontrado:
        
        # --- ¡CADENA DE INTENCIONES CON REGEX! ---
        # El orden aquí es importante.
        
        # 1. Intenciones de "AYUDA" (prioritarias)
        if re.search(PATRON_OPCIONES, texto_recibido):
            # Reutilizamos la función del comando /opciones
            await opciones(update, context)
            
        elif re.search(PATRON_TICKERS, texto_recibido):
            # Reutilizamos la función del comando /tickers
            await tickers(update, context) 
            
        # 2. Intenciones de "CHARLA" (secundarias)
        elif re.search(PATRON_SALUDO, texto_recibido): 
            saludo_elegido = random.choice(POSIBLES_SALUDOS)
            await update.message.reply_text(saludo_elegido)
        
        elif re.search(PATRON_GRACIAS, texto_recibido): 
            respuesta_gracias = random.choice(POSIBLES_DE_NADA)
            await update.message.reply_text(respuesta_gracias)
            
        elif re.search(PATRON_TODO, texto_recibido): 
            await enviar_resumen_core(update.message)
            
    # Si no es nada, se queda callado. Perfecto.
    
    
    

# --- 3. El Bucle Principal del Bot ---
if __name__ == '__main__':
    # 1. Comprobamos el Token (como antes)
    if not MI_TOKEN:
        print("!!! ERROR CRÍTICO: No se encontró la variable de entorno MI_TOKEN !!!")
        exit()

    print("MI_TOKEN encontrado. Iniciando servidor y bot...")

    # 2. Iniciamos el servidor FARSANTE en un hilo (thread)
    #    'daemon=True' significa que si el bot muere, el servidor también.
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    print(f"Servidor farsante iniciado en un hilo. (Puerto $PORT)")

    # 3. Iniciamos el BOT (como siempre)
    application = ApplicationBuilder().token(MI_TOKEN).build()

    # --- Registra los COMANDOS ---
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('opciones', opciones))
    application.add_handler(CommandHandler('tickers', tickers))
    
    # --- Registra los "OYENTES" ---
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_texto))
    application.add_handler(CallbackQueryHandler(boton_ticker_pulsado, pattern=r'^ticker:'))
    application.add_handler(CallbackQueryHandler(resumen_mercado, pattern=r'^resumen$'))
    
    # 4. El bot se queda aquí, en el hilo principal
    print("Iniciando el polling del bot...")
    application.run_polling()