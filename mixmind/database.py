#from sqlalchemy import create_engine
#from sqlalchemy.orm import scoped_session, sessionmaker
#from sqlalchemy.ext.declarative import declarative_base

#import config

#engine = create_engine(config.sql_db_url, convert_unicode=True)
# TODO investigate: http://docs.sqlalchemy.org/en/latest/orm/contextual.html
#db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
#Base = declarative_base()
#Base.query = db_session.query_property()

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import models
    import barstock
    db.create_all()
