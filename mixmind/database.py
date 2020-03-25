from flask_sqlalchemy import SQLAlchemy
from flask_alembic import Alembic
from . import app, log

db = SQLAlchemy()
alembic = Alembic()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from . import models
    from . import barstock
    from .authorization import user_datastore
    db.create_all()
    user_datastore.find_or_create_role(name='admin', description='An admin user may modify the parameters of the app backend')
    user_datastore.find_or_create_role(name='bartender', description='This user is a bartender at at least one bar')
    user_datastore.find_or_create_role(name='owner', description='This user can do limited management at one bar')
    user_datastore.find_or_create_role(name='customer', description='Customer may register to make it easier to order drinks')
    db.session.commit()

    # now handle alembic revisions
    #alembic.stamp('head')
    if app.config.get('DEBUG', False):
        try:
            alembic.revision('Automatic upgrade')
        except Exception as err:
            log.error("{}: {}".format(err.__class__.__name__, err))
        try:
            alembic.upgrade()
        except NotImplementedError as err:
            log.error("{}: {}".format(err.__class__.__name__, err))
    elif app.config.get('DO_DB_UPGRADE', False):
        alembic.revision('Automatic upgrade')
        alembic.upgrade()
