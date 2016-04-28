import requests
import re
import pandas as pd
from bokeh.embed import components
from noaa import forecast
from pandas.tseries.holiday import USFederalHolidayCalendar as calendar

def get_station_info():
  '''
  pulls current data from the citibike JSON
  '''
  url = 'https://www.citibikenyc.com/stations/json'
  session = requests.Session()
  session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
  r = session.get(url)
  return pd.to_datetime(r.json()['executionTime']), pd.DataFrame(r.json()['stationBeanList'])
  #return {info['stationName']: [info['availableBikes'], info['availableDocks'], info ['totalDocks']] 
  #        for info in r.json()['stationBeanList']}

def get_noaa_info():
  '''
  pulls current noaa data
  '''
  fc = forecast.daily_forecast_by_zip_code('10024', num_days=1, metric=True)
  return fc[0].max_temp.value, fc[0].conditions.lower()

def build_features(time, temp, conditions):
  '''
  need ['TMAX', 'some_ppt', 'ppt', 'hour_minute', 'weekday', 'day_of_year', 'total_days', 'Holiday']
  '''
  feature_df = pd.DataFrame(columns=['TMAX', 'some_ppt', 'ppt', 
                                     'hour_minute', 'weekday', 'day_of_year', 
                                     'total_days', 'Holiday'])
  feature_df['hour_minute'] = range(time.hour*60+time.minute+1, time.hour*60+time.minute+61)
  feature_df['TMAX'] = temp*10
  feature_df['weekday'] = int(time.weekday<5)
  feature_df['day_of_year'] = time.dayofyear
  feature_df['total_days'] = (time-pd.to_datetime('July 1, 2013')).days
  
  heavy_ppt_query = r'(:?thunderstorm)|(:?blizzard)'
  ppt_query = r'(:?rain)|(:?snow)|(:?hail)'
  light_ppt_query = r'(:?drizzle)|(:?showers)'
  if re.match(heavy_ppt_query, conditions):
    feature_df[['some_ppt', 'ppt']] = [0, 1]
  elif re.match(light_ppt_query, conditions):
    feature_df[['some_ppt', 'ppt']] = [1, 0]
  elif re.match(ppt_query, conditions):
    if re.match(r'(:?light)|(:?chance)', conditions):
      feature_df[['some_ppt', 'ppt']] = [1, 0]
    else:
      feature_df[['some_ppt', 'ppt']] = [0, 1]
  else:
    feature_df[['some_ppt', 'ppt']] = [0, 0]

  cal = calendar()
  holidays = cal.holidays(start=time, end=time)
  feature_df['Holiday'] = time in holidays
  return feature_df





