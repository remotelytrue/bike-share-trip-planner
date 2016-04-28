import requests
import pandas as pd
import os.path
import dill
import bz2
from bokeh.io import gridplot
from bokeh.models import (
  GMapPlot, GMapOptions, ColumnDataSource, Circle, DataRange1d, PanTool, 
  WheelZoomTool, BoxSelectTool, Text
)
from bokeh.embed import components

def get_google_info(search_term):
  url = 'https://maps.googleapis.com/maps/api/geocode/json'
  params = {'sensor': 'false', 'address': search_term}
  r = requests.get(url, params=params)
  results = r.json()['results']
  location = results[0]['geometry']['location']
  return location['lat'], location['lng']

def predict_checkouts(id, n_bikes, total_docks, features):
  if not (os.path.exists('estimators/checkout_estimator_high_'+str(id)+'.dill.bz2') and 
          os.path.exists('estimators/checkin_estimator_mid_'+str(id)+'.dill.bz2')):
    return None, None, None, None
  checkout_est = dill.load(bz2.BZ2File('estimators/checkout_estimator_high_'+str(id)+'.dill.bz2', 'r'))
  checkin_est = dill.load(bz2.BZ2File('estimators/checkin_estimator_mid_'+str(id)+'.dill.bz2', 'r'))
  flux = checkin_est.predict(features)/15 - checkout_est.predict(features)/15
  bikes = n_bikes+flux.cumsum()
  return int(bikes[4]), int(bikes[9]), int(bikes[14]), int(bikes[19])

def predict_checkins(id, n_docks, total_docks, features):
  if not (os.path.exists('estimators/checkin_estimator_high_'+str(id)+'.dill.bz2') and 
          os.path.exists('estimators/checkout_estimator_mid_'+str(id)+'.dill.bz2')):
    return None, None, None
  checkin_est = dill.load(bz2.BZ2File('estimators/checkin_estimator_high_'+str(id)+'.dill.bz2', 'r'))
  checkout_est = dill.load(bz2.BZ2File('estimators/checkout_estimator_mid_'+str(id)+'.dill.bz2', 'r'))
  flux = checkout_est.predict(features)/15 - checkin_est.predict(features)/15
  docks = n_docks+flux.cumsum()
  return int(docks[29]), int(docks[44]), int(docks[59])

def pick_checkout(sorted_stations):
  picked_flag = 0
  for time in ['20 min', '15 min', '10 min', '5 min', '0 min']:
    for station in sorted_stations:
      if station[time] > 0 and picked_flag != 1:
        picked_flag=1
        station['color'] = 'black'
      elif station[time] == None:
        station['color'] = 'white'
      else:
        station['color'] = 'red'
    if picked_flag == 1:
      break
  return sorted_stations

def pick_checkin(sorted_stations):
  picked_flag = 0
  for time in ['60 min', '45 min', '30 min', '0 min']:
    for station in sorted_stations:
      if station[time] > 0 and picked_flag != 1:
        picked_flag=1
        station['color'] = 'black'
      elif station[time] == None:
        station['color'] = 'white'
      else:
        station['color'] = 'red'
    if picked_flag == 1:
      break
  return sorted_stations

def get_points(start_lat, start_lon, end_lat, end_lon, station_info, features):
  to_plot_start = []
  to_plot_end = []
  for i, row in station_info.iterrows():
    if row['statusValue'] == 'In Service':
      if abs(row['latitude']-start_lat) < 0.005 and abs(row['longitude']-start_lon) < 0.005:
        new_row = {}
        new_row['latitude'] = row['latitude']
        new_row['longitude'] = row['longitude']
        new_row['station_name'] = row['stationName']
        new_row['0 min'] = row['availableBikes']
        if row['availableBikes'] == 1:
          new_row['bike_string'] = '1 bike'
        else:
          new_row['bike_string'] = str(row['availableBikes'])+' bikes'
        new_row['5 min'], new_row['10 min'], new_row['15 min'], new_row['20 min'] = predict_checkouts(row['id'], row['availableBikes'],
                                                                 row['totalDocks'], features)
        to_plot_start.append(new_row)
      
      if abs(row['latitude']-end_lat) < 0.005 and abs(row['longitude']-end_lon) < 0.005:
        new_row = {}
        new_row['latitude'] = row['latitude']
        new_row['longitude'] = row['longitude']
        new_row['station_name'] = row['stationName']
        new_row['0 min'] = row['availableDocks']
        if row['availableDocks'] == 1:
          new_row['dock_string'] = '1 dock'
        else:
          new_row['dock_string'] = str(row['availableDocks'])+' docks'
        new_row['30 min'], new_row['45 min'], new_row['60 min'] = predict_checkins(row['id'], row['availableDocks'],
                                             row['totalDocks'], features)
        to_plot_end.append(new_row)
  
  to_plot_start_sorted = sorted(to_plot_start, 
                                key=lambda x: (x['latitude']-start_lat)**2 + (x['longitude']-start_lon)**2)
  to_plot_end_sorted = sorted(to_plot_end, 
                                key=lambda x: (x['latitude']-end_lat)**2 + (x['longitude']-end_lon)**2)
  return to_plot_start_sorted, to_plot_end_sorted

def get_map(station_info, features, start_point, end_point, city = 'New York, NY'):
  start_lat, start_lon = get_google_info(start_point+', '+city)
  end_lat, end_lon = get_google_info(end_point+', '+city)

  map1_options = GMapOptions(lat=start_lat, lng=start_lon, map_type="roadmap", zoom=16)
  plot1 = GMapPlot(
      x_range=DataRange1d(), y_range=DataRange1d(), 
      map_options=map1_options, 
      title="Start stations with current bikes"
  )
  plot1.title_text_font_size = '16pt'
  plot1.plot_width = 500
  plot1.plot_height = 500

  map2_options = GMapOptions(lat=end_lat, lng=end_lon, map_type="roadmap", zoom=16)
  plot2 = GMapPlot(
      x_range=DataRange1d(), y_range=DataRange1d(), 
      map_options=map2_options, 
      title="End stations with current docks"
  )
  plot2.title_text_font_size = '16pt'
  plot2.plot_width = 500
  plot2.plot_height = 500

  to_plot_start_sorted, to_plot_end_sorted = get_points(start_lat, start_lon, end_lat, end_lon, station_info, features)
  to_plot_start_sorted_picked = pick_checkout(to_plot_start_sorted)
  to_plot_end_sorted_picked = pick_checkin(to_plot_end_sorted)

  for row in to_plot_start_sorted_picked:    
    source = ColumnDataSource(
           data=dict(
            lat=[row['latitude']],
            lon=[row['longitude']],
            lon_txt = [row['longitude']+0.0003],
            bike_text=[str(row['0 min'])],
            )
           )
    bike_text_glyph = Text(x="lon_txt", y="lat", text='bike_text', 
                           text_baseline='middle', text_align='left', text_font_style='bold')
    circle = Circle(x="lon", y="lat", size=20, fill_color=row['color'], fill_alpha=1)
    plot1.add_glyph(source, circle)
    plot1.add_glyph(source, bike_text_glyph)
    if row['color'] == 'black':
      start_string = 'Recommended start station: '+row['station_name']+'. '
      start_string += 'In 5 minutes, I predict there will be '+str(row['5 min'])+' bikes; '
      start_string += '10 minutes, '+str(row['10 min'])+' bikes; '
      start_string += '15 minutes, '+str(row['15 min'])+' bikes; and '
      start_string += '20 minutes, '+str(row['20 min'])+' bikes.'

  for row in to_plot_end_sorted_picked:    
    source = ColumnDataSource(
           data=dict(
            lat=[row['latitude']],
            lon=[row['longitude']],
            lon_txt = [row['longitude']+0.0003],
            dock_text=[str(row['0 min'])],
            )
           )
    dock_text_glyph = Text(x="lon_txt", y="lat", text='dock_text', 
                           text_baseline='middle', text_align='left', text_font_style='bold')
    circle = Circle(x="lon", y="lat", size=20, fill_color=row['color'], fill_alpha=1)
    plot2.add_glyph(source, circle)
    plot2.add_glyph(source, dock_text_glyph)
    if row['color'] == 'black':
      end_string = 'Recommended end station: '+row['station_name']+'. '
      end_string += 'In 30 minutes, I predict there will be '+str(row['30 min'])+' docks; '
      end_string += '45 minutes, '+str(row['45 min'])+' docks; and '
      end_string += '60 minutes, '+str(row['60 min'])+' docks.'

  plot1.add_tools(PanTool(), WheelZoomTool(), BoxSelectTool())
  plot2.add_tools(PanTool(), WheelZoomTool(), BoxSelectTool())

  p = gridplot([[plot1, plot2]])
  if not to_plot_start_sorted_picked:
    start_string = 'No stations near your start point!'
  elif not start_string:
    start_string = 'No nearby stations have bikes!'
  if not to_plot_end_sorted_picked:
    end_string = 'No stations near your end point!'
  elif not end_string:
    end_string = 'No nearby stations have bikes at your end point!'
  return start_string, end_string, components(p)
  return components(p)



