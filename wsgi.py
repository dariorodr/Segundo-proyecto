import sys
import os
sys.path.insert(0, os.path.abspath('app'))

from app import app

if __name__ == "__main__":
    app.run()