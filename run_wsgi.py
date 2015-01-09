import sys, os
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(PROJECT_DIR)
activate_this = os.path.join(PROJECT_DIR, 'venv', 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

from moz_au_web.app import create_app
from moz_au_web.settings import ProdConfig

app = create_app(ProdConfig)
application = app

if __name__ == "__main__":
    app.debug = False
    app.run()