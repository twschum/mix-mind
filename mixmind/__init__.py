# mixmind/__init__.py

import logging
log = logging.getLogger()

from flask import Flask
from flask_uploads import UploadSet, DATA, configure_uploads

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

# flask-uploads
app.config['UPLOADS_DEFAULT_DEST'] = './stockdb'
datafiles = UploadSet('datafiles', DATA)
configure_uploads(app, (datafiles,))

from mixmind.database import db, init_db, alembic
db.init_app(app)
alembic.init_app(app)
with app.app_context():
    init_db()

from mixmind.notifier import mail
mail.init_app(app)

from mixmind.configuration_management import MixMindServer, get_bar_config
with app.app_context():
    mms = MixMindServer(app)

from werkzeug.local import LocalProxy
current_bar = LocalProxy(get_bar_config)

with app.app_context():
    import mixmind.views # to assosciate views with app
