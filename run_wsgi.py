from moz_au_web.app import create_app
from moz_au_web.settings import ProdConfig
import os

app = create_app(ProdConfig)

if __name__ == "__main__":
    app.debug = False
    app.run()
