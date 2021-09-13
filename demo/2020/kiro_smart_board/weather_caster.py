import datetime
import requests
import json

TARGET_LATITUDE = 37.544206
TARGET_LONGITUDE = 127.053563
OPEN_WEATHER_MAP_API_KEY = "7db18b56501d7cac5f370799d97d6d7b"
OPEN_WEATHER_MAP_URL = "https://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&\%20exclude=hourly,daily&appid={}"
OPEN_WEATHER_MAP_URL = OPEN_WEATHER_MAP_URL.format(
                            TARGET_LATITUDE,
                            TARGET_LONGITUDE,
                            OPEN_WEATHER_MAP_API_KEY)
AQICN_TOKEN = "f08f11189b57774fc9da5ce7d7f5d1f303bb4bb7"
AQICN_URL = "https://api.waqi.info/feed/geo:{};{}/?token={}"
AQICN_URL = AQICN_URL.format(TARGET_LATITUDE, TARGET_LONGITUDE, AQICN_TOKEN)

class weather_caster():
    _id_map = {
        "2" : "rain",
        "3" : "rain",
        "5" : "rain",
        "6" : "snow",
        "7" : "cloud",
        "800" : "sunny",
        "8" : "cloud"
    }
    _forecast_weather = None
    _forecast_pm = None
    _final_forecast_time = None
    _forecast_interval = 1 # unit = hour

    def __init__(self):
        self._forecast()

    def _parse_weather_condition(self, id):
        id = str(id)
        if id != "800":
            id = id[0]
        
        return self._id_map[id]
    
    def _parse_weather(self):
        weather_data = json.loads(requests.get(OPEN_WEATHER_MAP_URL).text)
        current_weather = weather_data["current"]
        daily_weather = weather_data["daily"][:2]
        weathers = [
            current_weather["weather"],
            daily_weather[0]["weather"],
            daily_weather[1]["weather"]
        ]

        self._forecast_weather = []
        for w in weathers:
            try:
                weather = self._parse_weather_condition(w[0]['id'])
            except:
                weather = self._parse_weather_condition(["800"])
            self._forecast_weather.append(weather)
        return self._forecast_weather
    
    def _parse_pm(self):
        pm_data = json.loads(requests.get(AQICN_URL).text)
        pm10 = pm_data['data']['forecast']['daily']['pm10']

        dt = self._datetime_to_integer(datetime.datetime.now().date())

        forecast_days = 3
        self._forecast_pm = []
        for pm in pm10:
            date = self._datetime_to_integer(datetime.date.fromisoformat(pm['day']))
            if date >= dt and forecast_days > 0:
                self._forecast_pm.append(pm['avg'])
                forecast_days -= 1
            elif forecast_days <= 0:
                break

        return self._forecast_pm

    def _get_forecast_date_diff(self, dt):
        if self._final_forecast_time is None:
            self._final_forecast_time = datetime.datetime.now()
        if self._final_forecast_time.timestamp() > dt.timestamp():
            diff = self._final_forecast_time - dt
        else:
            diff = dt - self._final_forecast_time
        secs_in_day = 24 * 60 * 60
        return int(divmod(diff.days * secs_in_day + diff.seconds, 60)[0] / 60)
    
    def _forecast(self):
        dt = datetime.datetime.now()
        try:
            if self._final_forecast_time is None \
                or self._get_forecast_date_diff(dt) >= self._forecast_interval:
                self._parse_weather()
                self._parse_pm()
                self._final_forecast_time = dt
        except:
            self._forecast_weather = ['sunny', 'sunny', 'sunny']
            self._forecast_pm = [30, 30, 30]
            self._final_forecast_time = dt
    
    def _datetime_to_integer(self, dt_time):
        return 10000 * dt_time.year + 100 * dt_time.month + dt_time.day

    def get_forecasts(self):
        self._forecast()
        return self._forecast_weather, self._forecast_pm, self._final_forecast_time
    
    def get_parsing_interval(self):
        return self._forecast_interval
    
    def set_parsing_interval(self, interval):
        self._forecast_interval = interval


#EOF