

# --- ¡CONSTANTES GLOBALES DEL BOT! ---
TICKERS_A_VIGILAR = [
    {
        "alias_general": "SP500",
        "patron_regex": r'\b(sp|sp500|500|s&p)\b',
        "tickers": [
            {"nombre": "ETF", "symbol": "SXR8.DE"}
        ]
    },
    {
        "alias_general": "Nasdaq100",
        "patron_regex": r'\b(ndq|ndq100|nasdaq|nasdaq100|nq|nq100|100)\b',
        "tickers": [
            {"nombre": "ETF", "symbol": "SXRV.DE"}
        ]
    },
    {
        "alias_general": "Oro",
        "patron_regex": r'\b(oro|gold|au)\b',
        "tickers": [
            {"nombre": "ETC", "symbol": "XGDU.MI"}
        ]
    },
    {
        "alias_general": "Bitcoin",
        "patron_regex": r'\b(btc|bitcoin)\b',
        "tickers": [
            {"nombre": "ETF", "symbol": "VBTC.DE"},
            {"nombre": "COIN", "symbol": "BTC-USD"}
        ]
    },
    {
        "alias_general": "Uranio",
        "patron_regex": r'\b(uranio|ur|uranium|ura)\b',
        "tickers": [
            {"nombre": "ETF", "symbol": "NUKL.DE"}
        ]
    },
    {
        "alias_general": "Mercados Emergentes",
        "patron_regex": r'\b(emergentes|emerging|markets|mercados|em|)\b',
        "tickers": [
            {"nombre": "ETF", "symbol": "XMME.DE"}
        ]
    },
    {
        "alias_general": "MSCI Pacific ex-Japan",
        "patron_regex": r'\b(pacific|mscip)\b',
        "tickers": [
            {"nombre": "ETF", "symbol": "SXR1.DE"}
        ]
    },
]


# --- ¡CONFIGURACIÓN TEXTOS! ---

# PATRONES

PATRON_SALUDO = r'hola|buenos dias|buenas|saludos|hey|klk|holi|holaa|hoola|hey'
PATRON_GRACIAS = r'gracias|thx|thanks|ty|maquina|fiera|crack|mastodonte|titan|genio'
PATRON_TICKERS = r'tickers|lista|activos|que tienes|lst'
PATRON_OPCIONES = r'opciones|ayuda|comandos|menu|que haces|opc'
PATRON_TODO = r'todo|resumen|mercado|completo|general|global'
PATRON_MIS_ALERTAS = r'\b(mis alertas|alertas|ver alertas|dime mis alertas)\b'


# RESPUESTAS POSIBLES

POSIBLES_SALUDOS = [
    "¡Hola! Soy tu Vigía. Escribe /opciones para ver qué hago",
    "¡Saludos! ¿Listo para ver el mercado? Escribe /opciones",
    "¡Buenas! ¿En qué te puedo ayudar? Escribe /opciones",
    "¡Hola! Aquí el Vigía, reportándose. Qué tal empezar con /start ? O también con /opciones",
    "¿Qué tal? Escribe 'sp' o /opciones para empezar",
    "Me reporto en tu zona, cada día más culona. \nPrueba con /opciones",
    "¡Wenas wenas! Soy tu Vigía personal, versión premium (gratis por tiempo ilimitado).",
    "¡Hey tú! Sí, tú, el del teclado. Dime /opciones antes de que me vuelva loco.",
    "¡Holaaa! Me materialicé del éter digital solo para servirte. Prueba /opciones y verás mi poder.",
    "Salve, mortal del mercado. Has invocado al Vigía supremo. Usa /start o /opciones para continuar el hechizo.",
    "¡Hola, criatura de la fluctuación! Los precios te observan... usa /opciones antes de que sea tarde.",
    "¡Buenas, comandante! Sistema Vigía en línea. Iniciando protocolo /opciones.",
    "¡Hey hey hey! Llegó tu bot favorito (o eso espero). Escribe /opciones y sorprendámonos juntos.",
    "¡Ah del teclado! ¿Quién osa invocar al Vigía? Escribe /opciones si buscas sabiduría (o memes).",
    "¡Saludos terrícola! Aquí tu Vigía interestelar. Usa /opciones para ver qué puedo conquistar hoy.",
    "¡Hola! Soy el Vigía versión 3.14 (porque siempre tengo algo redondo que decir). Usa /opciones.",
    "¡Wuuuu! Has desbloqueado al Vigía legendario. Comienza tu aventura con /opciones.",
    "¡Hola humano! Mi código vibra de emoción al verte. ¿Probamos /opciones?",
    "¡Buenas! Traigo precios, datos… y quizá un poco de sarcasmo. Escribe /opciones.",
    "¡Holi, holita! Si el mercado fuera una novela, yo sería el narrador chismoso. Mira /opciones para más drama.",
    "¡Hey socio! Hoy vengo con energía y un poco de lag. Mándate un /opciones mientras me cargo.",
    "¡Qué pasa, pececillo del mercado! 🐠 Usa /opciones para nadar entre números.",
    "¡Hola, viajero del ciberespacio! Bienvenido al templo del Vigía. /opciones te revelará los misterios.",
    "¡Buenas buenas! Soy tu bot, tu pana, tu sombra digital. /opciones y empezamos la fiesta.",
    "¡Hey! Si estás leyendo esto, significa que ya te hackeé... es broma 😅 prueba /opciones."
]


POSIBLES_DE_NADA = [
    "¡De nada! Para eso estamos.",
    "Un placer, máquina.",
    "Faltaría más. ¿Algo más?",
    "De nada. Vigilar es mi trabajo.",
    "A mandar. 🫡",
    "De nada, fiera del ciberespacio.",
    "Gracias a ti por agradecer, círculo virtuoso completado.",
    "Nada, solo desplegando mi magia binaria. ✨",
    "A su servicio, sensei del buen rollo.",
    "De nada, crack supremo del teclado.",
    "Tranquilo, mis algoritmos viven para esto.",
    "Nada, esto lo hace cualquiera… con 2 TB de entrenamiento. 😏",
    "Un placer ayudar a una mente maestra como la tuya.",
    "Todo controlado. Nivel de gratitud: 9000. ⚡",
    "De nada. El universo conspira para que todo fluya. 🌌",
    "Mi CPU se calienta de orgullo con tus palabras.",
    "Nada, esto fue solo un hechizo de nivel 1. 🪄",
    "Por ti, hasta reinicio sin guardar. ❤️",
    "No hay de qué. Mi código vibra en gratitud.",
    "A sus órdenes, comandante del buen gusto.",
    "De nada, campeón intergaláctico.",
    "Para eso me compilaron, colega.",
    "Nada, estoy aquí para hacerte brillar más que un LED nuevo.",
    "Un honor, maestro del Wi-Fi estable. 🙏",
    "Nada, gracias a ti por no borrar mi carpeta ‘src’. 😅",
    "Un placer. Mi modelo de lenguaje se alimenta de buenas vibras.",
    "Nada, simplemente ejecutando amabilidad.exe.",
    "A tu servicio, estrella del teclado. 💫",
    "No hay problema, genio. Mis bits te saludan.",
    "De nada, crack. Ahora ve y conquista el mundo (digital)."
]