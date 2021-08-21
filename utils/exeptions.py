class StravaAPIError(Exception):
    def __init__(self, message='Strava API error'):
        print('ERROR:', message)


class WeatherAPIError(Exception):
    def __init__(self, message='OpenWeather API error'):
        print('ERROR:', message)
