class Config:
    # Flask Settings
    SECRET_KEY = ''
    PERMANENT_SESSION_LIFETIME = 1800  # Timeout i sekunder (30 min)
    
    # MySQL Settings
    DEBUG = True
    MYSQL_HOST = 'localhost'
    MYSQL_USER = ''
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'myflaskapp'
    MYSQL_CURSORCLASS = 'DictCursor'
