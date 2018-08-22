# mixmind/__init__.py

import logging
log = logging.getLogger(__name__)

from flask import Flask
from flask_uploads import UploadSet, DATA, configure_uploads


app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

# flask-uploads
app.config['UPLOADS_DEFAULT_DEST'] = './stockdb'
datafiles = UploadSet('datafiles', DATA)
configure_uploads(app, (datafiles,))

from mixmind.database import db, init_db
db.init_app(app)
with app.app_context():
    init_db()

import mixmind.views # to assosciate views with app
