# 📈 Tracker de Bolsa - Telegram Bot

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?style=for-the-badge&logo=postgresql&logoColor=white)

Un bot de Telegram financiero avanzado, diseñado para operar 24/7 en la nube. Realiza seguimiento de activos (ETFs, Cripto, Índices) y gestiona alertas de precio personalizadas con persistencia en base de datos.

## 🚀 Características

* **Datos en Tiempo Real:** Obtiene precios y variación diaria (%) usando `yfinance`.
* **Reconocimiento Inteligente:** Entiende lenguaje natural (Regex). Puedes escribir "precio del sp500", "btc", "oro" y te entiende.
* **Sistema de Alertas Persistente:**
    * Crea alertas de precio objetivo (ej: "Avísame si SP500 baja de 600").
    * Las alertas se guardan en una base de datos **PostgreSQL** (Neon Tech), sobreviviendo a reinicios del servidor.
    * Monitoreo continuo mediante `JobQueue` (cada 5 minutos).
* **Interfaz Interactiva:**
    * Menús con botones (`InlineKeyboard`).
    * Asistente de creación de alertas paso a paso (`ConversationHandler`).
* **Despliegue Gratuito (Hack):** Incluye un servidor Flask ligero ("dummy server") para mantener el bot activo en servicios PaaS gratuitos como Koyeb o Render.

## 🛠️ Tecnologías

* **Lenguaje:** Python 3.13
* **Librerías Clave:**
    * `python-telegram-bot` (Interacción con API de Telegram)
    * `yfinance` (Datos de mercado)
    * `psycopg2-binary` (Conexión a Base de Datos)
    * `Flask` (Servidor web para health-checks)
    * `APScheduler` (Gestión de tareas cron)

## ⚙️ Instalación y Uso Local

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/tu-usuario/tu-repo.git](https://github.com/tu-usuario/tu-repo.git)
    cd tu-repo
    ```

2.  **Crear entorno virtual:**
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno:**
    Crea un archivo `.env` en la raíz y añade tus credenciales (¡No subas esto a GitHub!):
    ```env
    MI_TOKEN=tu_token_de_telegram
    MI_CHAT_ID=tu_id_de_usuario
    DATABASE_URL=tu_url_de_postgres_neon
    ```

5.  **Ejecutar:**
    ```bash
    python bot.py
    ```

## 🤖 Comandos del Bot

| Comando | Descripción |
| :--- | :--- |
| `/start` | Inicia el bot y muestra el mensaje de bienvenida. |
| `/opciones` | Muestra el menú de ayuda y comandos disponibles. |
| `/tickers` | Muestra botones interactivos con los activos disponibles. |
| `/alerta` | Inicia el asistente interactivo para crear una alerta. |
| `/misalertas` | Muestra tus alertas activas y permite borrarlas. |
| `/initdb` | (Admin) Inicializa la tabla de base de datos si no existe. |

## ⚠️ Disclaimer

Este software es un proyecto educativo y una herramienta de asistencia. **No constituye asesoramiento financiero.** El autor no se hace responsable de pérdidas económicas derivadas del uso de este bot o de fallos en las alertas. Opera bajo tu propia responsabilidad.

---
Hecho con 🐍 y mucho café.
