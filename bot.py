import yfinance as yf
import logging
import random
import re
import os
import threading
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    CommandHandler, 
    MessageHandler,  
    filters,
    CallbackQueryHandler,
    ConversationHandler
)

# Estados de la conversación
STATE_CHOOSE_TICKER, STATE_SET_PRICE = range(2)

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
MI_CHAT_ID = os.environ.get("MI_CHAT_ID")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not MI_TOKEN:
    print("!!! ERROR CRÍTICO: No se encontró la variable de entorno MI_TOKEN !!!")
    exit()
    
if not DATABASE_URL:
    print("!!! ERROR CRÍTICO: No se encontró la variable de entorno DATABASE_URL !!!")
    exit()


# --- ¡NUEVO! Conexión a la Base de Datos ---
# Creamos un "pool" de conexiones. Es como una caja de herramientas de BD.
print("Creando pool de conexiones a la base de datos...")
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, dsn=DATABASE_URL)
    print("Pool de conexiones creado con éxito.")
except (Exception, psycopg2.Error) as error:
    print("!!! ERROR CRÍTICO: No se pudo conectar a la base de datos !!!", error)
    exit()
# ----------------------------------------


from config import (
    TICKERS_A_VIGILAR,
    PATRON_SALUDO,
    PATRON_GRACIAS,
    PATRON_TICKERS,
    PATRON_OPCIONES,
    PATRON_TODO,
    POSIBLES_SALUDOS,
    POSIBLES_DE_NADA,
    PATRON_MIS_ALERTAS)
# ------------------------------------

# Configuramos el logging para ver qué pasa 
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# --- 1. Lógica del Mercado  ---

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
        
        return precio_actual, moneda 

    except Exception as e:
        print(f"*** ERROR al obtener precio para {ticker_simbolo}: {e} ***")
        return None, None 

# --- 2. Lógica de Comandos del Bot ---
async def init_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ¡Comando de un solo uso! Crea la tabla de alertas en la BD.
    """
    conn = None
    try:
        # Pide una conexión del pool
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Esta es la "sentencia" SQL para crear la tabla
        create_table_query = """
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            ticker_symbol VARCHAR(20) NOT NULL,
            alias_general VARCHAR(50) NOT NULL,
            target_price NUMERIC(12, 2) NOT NULL,
            is_triggered BOOLEAN DEFAULT FALSE,
            currency VARCHAR(10)
        );
        """
        cursor.execute(create_table_query)
        conn.commit()
        
        print("¡Tabla 'alerts' verificada/creada con éxito!")
        await update.message.reply_text("¡Base de datos inicializada! La tabla 'alerts' está lista.")
        
    except (Exception, psycopg2.Error) as error:
        print("Error al inicializar la BD:", error)
        await update.message.reply_text(f"Error al inicializar la BD: {error}")
    finally:
        # Devuelve la conexión al pool
        if conn:
            db_pool.putconn(conn)


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
        "*Opciones Disponibles*\n\n"
        "🤖 *Modo Inteligente* _(Recomendado)_:\n"
        "Escríbeme directamente el activo que buscas. Entiendo frases como:\n"
        "  -> 'sp500'\n"
        "  -> 'oro'\n\n"
        "🆘 *Comandos de Ayuda*:\n"
        "  -> /start _(ver el mensaje de bienvenida)_\n"
        "  -> /opciones _(ver este menú)_\n"
        "  -> /tickers _(ver lista de activos)_\n"
        "  -> /alerta <activo> <precio> _(crea una alerta)_\n"
        "  -> /alerta _(inicia el asistente interactivo)_\n"
        "  -> /misalertas _(ver/borrar tus alertas)_\n"
    )
    await update.message.reply_text(mensaje_opciones, parse_mode="Markdown")
    


async def tickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la lista de tickers como botones pulsables."""
    
    texto_mensaje = "*Tickers disponibles*\n_(Pulsa para ver el precio)_\n"
    
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
    
    partes_del_mensaje = [f"*RESUMEN DEL MERCADO*\n"]
    
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
            
        elif re.search(PATRON_MIS_ALERTAS, texto_recibido):
            await mis_alertas(update, context)
            
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
    


async def conv_start_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Paso 1: Inicia la conversación O ejecuta el modo rápido.
    Comprueba si el usuario ha añadido argumentos.
    """
    
    # --- MODO EXPERTO ---
    if context.args:
        # Si el usuario ha escrito /alerta sp500 650
        if len(context.args) == 2:
            # Llamamos a la lógica antigua (one-shot)
            await nueva_alerta(update, context) 
            return ConversationHandler.END # Y matamos la conversación
        else:
            # Error, mal formato
            await update.message.reply_text("Formato incorrecto. Uso: /alerta <trigger> <precio>\nO simplemente /alerta para el asistente.")
            return ConversationHandler.END

    # --- MODO NOVATO ---
    # Si el usuario solo ha escrito /alerta (sin args)
    await update.message.reply_text("¡Genial! Vamos a crear una alerta.")
    
    # Reutilizamos la función de /tickers para mostrar los botones
    await tickers(update, context) 
    
    await update.message.reply_text("¿Sobre qué activo? (Pulsa un botón de la lista de arriba)\nO escribe /cancelar para salir.")
    
    # Le decimos al ConversationHandler que pasamos al estado "elegir ticker"
    return STATE_CHOOSE_TICKER


async def conv_ticker_elegido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Paso 2: El usuario ha pulsado un botón de Ticker.
    Guarda el ticker y pregunta por el precio.
    """
    query = update.callback_query
    await query.answer()
    
    # 1. Extraemos el ticker del botón pulsado
    try:
        prefix, index_str = query.data.split(":")
        index = int(index_str)
        ticker_info = TICKERS_A_VIGILAR[index]
        
        # 2. Guardamos los datos en la "memoria a corto plazo"
        context.user_data["alerta_ticker_info"] = ticker_info
        
    except (ValueError, IndexError, KeyError):
        await query.message.reply_text("Error: No he reconocido ese botón. /cancelar para empezar de nuevo.")
        return ConversationHandler.END # Error, matamos la convo

    # 3. Preguntamos por el precio
    alias = ticker_info["alias_general"]
    await query.message.reply_text(f"¡OK! Vigilaré *{alias}*.\n\n¿Por debajo de qué precio te aviso?\n(Escribe solo el número, ej: 650)", parse_mode="Markdown")

    # Pasamos al estado "poner precio"
    return STATE_SET_PRICE


async def conv_precio_recibido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Paso 3: El usuario ha escrito un precio.
    ¡VERSIÓN SQL! Guarda la alerta en la BD.
    """
    try:
        ticker_info = context.user_data["alerta_ticker_info"]
    except KeyError:
        await update.message.reply_text("¡Ups! Me he perdido. Empecemos de nuevo con /alerta.")
        return ConversationHandler.END

    try:
        target_price = float(update.message.text)
    except ValueError:
        await update.message.reply_text(f"'{update.message.text}' no es un número válido.\n\nEscribe solo el número (ej: 650) o /cancelar.")
        return STATE_SET_PRICE # Nos quedamos en este paso

    # --- ¡LÓGICA DE BD! ---
    conn = None
    try:
        ticker_simbolo = ticker_info["tickers"][0]["symbol"]
        alias_general = ticker_info["alias_general"]
        chat_id = update.message.chat_id
        
        # --- ¡NUEVA LLAMADA PARA OBTENER MONEDA! ---
        # Hacemos una llamada rápida solo para saber la moneda y mejorar el mensaje
        precio_actual, moneda = obtener_precio_actual(ticker_simbolo)
        if moneda is None:
            moneda = "" # Si falla, dejamos la moneda vacía
        # -------------------------------------------

        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO alerts (chat_id, ticker_symbol, alias_general, target_price, currency)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (chat_id, ticker_simbolo, alias_general, target_price, moneda))
        conn.commit()

        context.user_data.clear()

        # --- ¡MENSAJE! ---
        mensaje = (
            f"¡Alerta Creada! ✅\n\n"
            f"Vigilaré *{alias_general}* y te avisaré si baja de *{target_price:,.2f} {moneda}*\n\n" 
            "Puedes verla con /misalertas."
        )
        await update.message.reply_text(mensaje, parse_mode="Markdown")
        return ConversationHandler.END
        
    except (Exception, psycopg2.Error) as error:
        print(f"Error creando alerta en BD: {error}")
        await update.message.reply_text(f"Error al guardar la alerta: {error}")
        return ConversationHandler.END
    finally:
        if conn:
            db_pool.putconn(conn)


async def conv_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela y sale de la conversación."""
    context.user_data.clear()
    await update.message.reply_text("Creación de alerta cancelada.")
    return ConversationHandler.END




async def check_all_alerts(context: ContextTypes.DEFAULT_TYPE):
    """
    ¡VERSIÓN SQL! Recorre la tabla 'alerts' de la BD.
    """
    conn = None
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, chat_id, ticker_symbol, alias_general, target_price, is_triggered FROM alerts")
        all_alerts = cursor.fetchall()

        if not all_alerts:
            print("JobQueue: No hay alertas en la BD. Durmiendo.")
            return

        print(f"JobQueue: Comprobando {len(all_alerts)} alerta(s) de la BD...")

        for alert in all_alerts:
            alert_id, chat_id_aviso, ticker_simbolo, ticker_alias, target_price, is_triggered = alert
            
            # target_price es un objeto Decimal, lo pasamos a float
            target_price = float(target_price)

            precio, moneda = obtener_precio_actual(ticker_simbolo)
            if precio is None:
                continue

            if precio < target_price and not is_triggered:
                print(f"JobQueue: ¡ALERTA DISPARADA! {ticker_alias} < {target_price}")
                mensaje = (
                    f"🔔 *¡ALERTA DE PRECIO!* 🔔\n\n"
                    f"El activo *{ticker_alias}* ha caído por debajo de tu objetivo.\n\n"
                    f"Precio Actual -> {precio:,.2f} {moneda}\n"
                    f"Tu Objetivo     -> {target_price:,.2f} {moneda}"
                )
                await context.bot.send_message(chat_id=chat_id_aviso, text=mensaje, parse_mode="Markdown")
                
                # ¡Actualizamos la BD!
                cursor.execute("UPDATE alerts SET is_triggered = TRUE WHERE id = %s", (alert_id,))
                conn.commit()

            elif precio > target_price and is_triggered:
                print(f"JobQueue: ALERTA RE-ARMADA. {ticker_alias} > {target_price}")
                mensaje = (
                    f"✅ *Alerta Reactivada* ✅\n\n"
                    f"El activo *{ticker_alias}* se ha recuperado por encima de {target_price:,.2f} {moneda}.\n"
                    f"La alerta de precio ha sido reactivada."
                )
                await context.bot.send_message(chat_id=chat_id_aviso, text=mensaje, parse_mode="Markdown")
                
                # ¡Actualizamos la BD!
                cursor.execute("UPDATE alerts SET is_triggered = FALSE WHERE id = %s", (alert_id,))
                conn.commit()

    except (Exception, psycopg2.Error) as error:
        print(f"JobQueue: Error procesando alertas: {error}")
    finally:
        if conn:
            db_pool.putconn(conn)


async def nueva_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ¡VERSIÓN SQL! Inserta una nueva alerta en la BD.
    (El comando /alerta <trigger> <precio> en modo experto)
    """
    chat_id = update.message.chat_id
    # (El resto de tu lógica de validación de args y tickers es la misma)
    if len(context.args) != 2:
        await update.message.reply_text("Formato incorrecto. Uso:\n/alerta <trigger> <precio>\n\nEjemplo: /alerta sp500 650")
        return

    trigger_usuario = context.args[0].lower()
    ticker_info_encontrada = None
    for ticker_data in TICKERS_A_VIGILAR:
        if re.search(ticker_data["patron_regex"], trigger_usuario):
            ticker_info_encontrada = ticker_data
            break
            
    if not ticker_info_encontrada:
        await update.message.reply_text(f"No reconozco el activo '{trigger_usuario}'.\nUsa /tickers para ver la lista.")
        return
        
    try:
        target_price = float(context.args[1])
    except ValueError:
        await update.message.reply_text(f"El precio '{context.args[1]}' no es un número válido.")
        return
        
    # --- ¡LÓGICA DE BD! ---
    conn = None
    try:
        ticker_simbolo = ticker_info_encontrada["tickers"][0]["symbol"]
        alias_general = ticker_info_encontrada["alias_general"]
        
        # --- ¡NUEVA LLAMADA PARA OBTENER MONEDA! ---
        precio_actual, moneda = obtener_precio_actual(ticker_simbolo)
        if moneda is None:
            moneda = "N/A"
        # -------------------------------------------

        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO alerts (chat_id, ticker_symbol, alias_general, target_price, currency) 
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (chat_id, ticker_simbolo, alias_general, target_price, moneda))
        conn.commit()
        
        mensaje = (
            f"¡Alerta Creada! ✅\n\n"
            f"Vigilaré *{alias_general}* y te avisaré si baja de *{target_price:,.2f}* {moneda}"
        )
        await update.message.reply_text(mensaje, parse_mode="Markdown")

    except (Exception, psycopg2.Error) as error:
        print(f"Error creando alerta en BD: {error}")
        await update.message.reply_text(f"Error al guardar la alerta: {error}")
    finally:
        if conn:
            db_pool.putconn(conn)


async def mis_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """¡VERSIÓN SQL! Muestra las alertas de la BD."""
    chat_id = update.message.chat_id
    conn = None
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()

        select_query = "SELECT id, alias_general, ticker_symbol, target_price, currency FROM alerts WHERE chat_id = %s"
        cursor.execute(select_query, (chat_id,))
        
        alertas_de_este_usuario = cursor.fetchall()
        
        if not alertas_de_este_usuario:
            await update.message.reply_text("No tienes ninguna alerta activa.\nCrea una con /alerta")
            return

        keyboard = []
        partes_del_mensaje = ["Tus Alertas Activas:\n"]
        
        for alert in alertas_de_este_usuario:
            alert_id, alias, ticker, target_price, currency = alert
            target_price = float(target_price) # Convertir de Decimal
            
            if currency is None or currency == "N/A":
                currency = "" # No mostramos nada si no la sabemos
            
            partes_del_mensaje.append(f"\n-> {alias} ({ticker}) < {target_price:,.2f} {currency}")
            
            boton = InlineKeyboardButton(
                text=f"Borrar {alias} ({ticker})", 
                callback_data=f"delete_alert:{alert_id}" # <-- Usamos el ID de la BD
            )
            keyboard.append([boton])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("".join(partes_del_mensaje), reply_markup=reply_markup)

    except (Exception, psycopg2.Error) as error:
        print(f"Error listando alertas: {error}")
        await update.message.reply_text(f"Error al listar tus alertas: {error}")
    finally:
        if conn:
            db_pool.putconn(conn)


async def borrar_alerta_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """¡VERSIÓN SQL! Borra una alerta de la BD."""
    query = update.callback_query
    await query.answer()
    conn = None
    try:
        prefix, alert_id_str = query.data.split(":")
        alert_id = int(alert_id_str)
        chat_id = query.message.chat_id # Para seguridad
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Borramos solo si el chat_id coincide (para que no borres alertas de otros)
        delete_query = "DELETE FROM alerts WHERE id = %s AND chat_id = %s RETURNING alias_general"
        cursor.execute(delete_query, (alert_id, chat_id))
        
        # Obtenemos el resultado de RETURNING
        deleted_alert = cursor.fetchone()
        conn.commit()
        
        if deleted_alert:
            alias = deleted_alert[0]
            await query.edit_message_text(f"Alerta para *{alias}* borrada con éxito.", parse_mode="Markdown")
        else:
            await query.edit_message_text("Error: No se encontró la alerta o no te pertenece.")

    except (Exception, psycopg2.Error) as error:
        print(f"Error borrando alerta: {error}")
        await query.edit_message_text("Error al borrar la alerta.")
    finally:
        if conn:
            db_pool.putconn(conn)


    

   

# --- 3. El Bucle Principal del Bot ---
if __name__ == '__main__':
    # ... (Comprobaciones de TOKEN y CHAT_ID, y el hilo de Flask... todo eso igual)
    if not MI_TOKEN:
        print("!!! ERROR CRÍTICO: No se encontró la variable de entorno MI_TOKEN !!!")
        exit()
    if not MI_CHAT_ID:
        print("!!! ERROR CRÍTICO: No se encontró la variable de entorno MI_CHAT_ID !!!")
        exit()
    if not DATABASE_URL:
        print("!!! ERROR CRÍTICO: No se encontró la variable de entorno DATABASE_URL !!!")
        exit()
    # ... (etc)
    
    print("Iniciando el polling del bot y la JobQueue...")
    
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    print(f"Servidor farsante iniciado en un hilo.")

    # 3. Iniciamos el BOT
    application = ApplicationBuilder().token(MI_TOKEN).build()

    # --- ¡EL NUEVO ORDEN! ---
    
    # 3.1. Definimos el ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('alerta', conv_start_alerta)],
        states={
            STATE_CHOOSE_TICKER: [
                # El bot espera ÚNICAMENTE un botón que empiece por "ticker:"
                CallbackQueryHandler(conv_ticker_elegido, pattern=r'^ticker:')
            ],
            STATE_SET_PRICE: [
                # El bot espera ÚNICAMENTE un mensaje de texto
                MessageHandler(filters.TEXT & (~filters.COMMAND), conv_precio_recibido)
            ],
        },
        fallbacks=[
            CommandHandler('cancelar', conv_cancelar)
        ],
    )
    
    # 3.2. Registramos el ConversationHandler (¡el primero!)
    application.add_handler(conv_handler)
    
    # 3.3. Registramos el RESTO de handlers (los que ya tenías)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('opciones', opciones))
    application.add_handler(CommandHandler('tickers', tickers))
    application.add_handler(CommandHandler('misalertas', mis_alertas))
    
    application.add_handler(CommandHandler('initdb', init_db))
    
    # --- Registra los "OYENTES" ---
    # (¡Ojo! Estos botones fallarán si se pulsan DENTRO de la conversación)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_texto))
    application.add_handler(CallbackQueryHandler(boton_ticker_pulsado, pattern=r'^ticker:'))
    application.add_handler(CallbackQueryHandler(resumen_mercado, pattern=r'^resumen$'))
    application.add_handler(CallbackQueryHandler(borrar_alerta_callback, pattern=r'^delete_alert:'))
    
    # --- Registra el "JobQueue" ---
    job_queue = application.job_queue
    job_queue.run_repeating(check_all_alerts, interval=300, first=10) # 5 min
    
    # 4. El bot se queda aquí
    print("Iniciando el polling del bot y la JobQueue...")
    application.run_polling()
    