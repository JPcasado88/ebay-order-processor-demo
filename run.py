# run.py
"""
Punto de Entrada para Ejecutar el Servidor de Desarrollo.

Este script carga las variables de entorno desde un archivo .env,
luego importa y ejecuta la application factory `create_app`.

Para producción, se debe usar un servidor WSGI como Gunicorn, por ejemplo:
gunicorn --workers 4 --bind 0.0.0.0:5000 "run:app"
"""

import os
from dotenv import load_dotenv

# Carga las variables de entorno del archivo .env al inicio.
# Esto debe hacerse ANTES de importar la configuración de la app y la app misma.
load_dotenv()

# Ahora que las variables de entorno están cargadas, podemos importar la app.
from ebay_processor import create_app

# Creamos la instancia de la aplicación usando nuestra factory.
app = create_app()

if __name__ == '__main__':
    # Esta sección solo se ejecuta cuando corres `python run.py` directamente.
    # Es ideal para el desarrollo local.
    app.run(
        host=os.environ.get('FLASK_RUN_HOST', '127.0.0.1'),
        port=int(os.environ.get('FLASK_RUN_PORT', 5001)),
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )