import sys
import os

# Añadir la carpeta app al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app import app

if __name__ == "__main__":
    app.run(debug=True)