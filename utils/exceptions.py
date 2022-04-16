class StravaAPIError(Exception):
    def __init__(self, message='Strava API error'):
        self.message = message
        print('ERROR:', message)
        super().__init__(self.message)
