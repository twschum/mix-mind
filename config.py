""" Configuration management module
"""
import os
import sys

from sqlalchemy.engine.url import URL

def get_config():
    if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
        return Config_GAE()
    else:
        return Config_dev()

class Config(object):
    """ Configuration object
    """
    def __init__(self):
        self.sqlalchemy_engine_params = {}

    # TODO cached property
    @property
    def sql_db_url(self):
        """ SQLAlchemy engine url
        {dialect}+{driver}://{username}:{password}@{host}:{port}/{database}
        """
        if 'driver' and 'dialect' in self.sqlalchemy_engine_params:
            kwargs['drivername'] = '{dialect}+{driver}'.format(**self.sqlalchemy_engine_params)
            del kwargs['dialect']
            del kwargs['driver']
        return URL(**self.sqlalchemy_engine_params)

class Config_dev(Config):
    def __init__(self):
        self.db_file = "db/auth.db"
        self.sqlalchemy_engine_params['drivername'] = 'sqlite'


class Config_GAE(Config):
    def __init__(self):
        # mysql connection: mysql+mysqldb://<user>:<password>@<host>[:<port>]/<dbname>
        # on GAE: mysql+mysqldb://root@/<dbname>?unix_socket=/cloudsql/<projectid>:<instancename>
        self.cloudsql_unix_socket = os.path.join('/cloudsql', CLOUDSQL_CONNECTION_NAME)

# This keeps the old module reference from being garbage collected. If
# this wasn't here we'd lose the ability to reference imported modules
#reference = sys.modules[__name__]

# Replace module level functionality with a Config class.
sys.modules[__name__] = get_config()
