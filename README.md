[![Quality&Tests](https://github.com/vol1ura/strava_weather_app/actions/workflows/python-app.yml/badge.svg)](https://github.com/vol1ura/strava_weather_app/actions/workflows/python-app.yml)
[![codecov](https://codecov.io/gh/vol1ura/strava_weather_app/branch/master/graph/badge.svg)](https://codecov.io/gh/vol1ura/strava_weather_app)
[![Code Style](https://img.shields.io/badge/Code%20Style-PEP%208-blueviolet)](https://www.python.org/dev/peps/pep-0008/) 
![W3C Validation](https://img.shields.io/w3c-validation/html?targetUrl=http%3A%2F%2Fstrava.pythonanywhere.com%2F)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
![Contributions](https://img.shields.io/badge/Contributions-Welcome-brightgreen)

# Strava Weather

Web application to add weather conditions to description of Strava activities. You can deploy this application as your own private app with your custom weather server and personal API tokens.
It is a free analog to Premium [klimat.app](http://klimat.app)

In application set russian language for description by default.

## Main features:

* You will get brief description of weather condition.
* Your own workout description will be saved and added to the description as well.
* You can select the metrics to be used in the description.
* No fees, no advertising, no branding and any additional marks.
* Air quality and pollution measurement data.
* You can select language -  russian or english.
* You can suggest your wishes and ideas in Issues. I will try to take them into account and implement them if I can.

![Description example](static/pic1.png)

You can also set adding only an emoji in the activity title:

![Emoji in the title](static/pic2.png)

### Run tests

```shell
pip install -r tests/requirements.txt
pytest --cov-report=term-missing:skip-covered --cov=. tests/
```
