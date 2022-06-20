import os

def check_env_vars():
    '''Check that all environment vars have been set.
    '''
    env_vars = [
        'SECRET_KEY',
        'STRAVA_CLIENT_ID',
        'STRAVA_CLIENT_SECRET',
        'API_WEATHER_KEY',
        'STRAVA_WEBHOOK_TOKEN',
        
        'MYSQLHOST',
        'MYSQLPORT',
        'MYSQLDATABASE',
        'MYSQLUSER',
        'MYSQLPASSWORD'
    ]

    fail_str = lambda env_var: f"environment variable: {env_var}, not found!"
    for env_var in env_vars:
        assert os.environ.get(env_var, 0) != 0, fail_str(env_var)
