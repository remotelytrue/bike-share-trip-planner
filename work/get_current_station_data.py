import requests
import pandas as pd
import os.path
import dill
import bz2
import json
import numpy as np

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
  bikes = np.clip(n_bikes+flux.cumsum(), 0, total_docks)
  return int(bikes[4]), int(bikes[9]), int(bikes[14]), int(bikes[19])


def predict_checkins(id, n_docks, total_docks, features):
  if not (os.path.exists('estimators/checkin_estimator_high_'+str(id)+'.dill.bz2') and 
          os.path.exists('estimators/checkout_estimator_mid_'+str(id)+'.dill.bz2')):
    return None, None, None
  checkin_est = dill.load(bz2.BZ2File('estimators/checkin_estimator_high_'+str(id)+'.dill.bz2', 'r'))
  checkout_est = dill.load(bz2.BZ2File('estimators/checkout_estimator_mid_'+str(id)+'.dill.bz2', 'r'))
  flux = checkout_est.predict(features)/15 - checkin_est.predict(features)/15
  docks = np.clip(n_docks+flux.cumsum(), 0, total_docks)
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


def bike_string(n_bikes):
  if n_bikes == 1:
    return '1 bike'
  else:
    return '{} bikes'.format(n_bikes)


def generate_start_popup(row):
  return """<p>{}<br>Current: {}<br>5 minutes: {}<br>
         10 minutes: {}<br>15 minutes: {}<br>20 minutes: {}</p>"""\
         .format(row["station_name"], bike_string(row['0 min']), bike_string(row['5 min']),
                 bike_string(row['10 min']), bike_string(row['15 min']),
                 bike_string(row['20 min']))


def dock_string(n_docks):
  if n_docks == 1:
    return '1 dock'
  else:
    return '{} docks'.format(n_docks)


def generate_end_popup(row):
  return "<p>{}<br>Current: {}<br>30 minutes: {}<br>45 minutes: {}<br>60 minutes: {}</p>"\
         .format(row["station_name"], dock_string(row['0 min']), dock_string(row['30 min']),
                 dock_string(row['45 min']), dock_string(row['60 min']))


def get_start_stations(start_pos, features, station_info):
  to_plot_start = []
  [start_lat, start_lon] = start_pos
  for i, row in station_info.iterrows():
    if row['statusValue'] == 'In Service':
      if abs(row['latitude']-start_lat) < 0.005 and abs(row['longitude']-start_lon) < 0.005:
        new_row = {}
        new_row['latitude'] = row['latitude']
        new_row['longitude'] = row['longitude']
        new_row['station_name'] = row['stationName']
        new_row['0 min'] = row['availableBikes']
        new_row['5 min'], new_row['10 min'], new_row['15 min'], new_row['20 min'] = predict_checkouts(row['id'], row['availableBikes'],
                                                                                    row['totalDocks'], features)
        to_plot_start.append(new_row)
  
  to_plot_start_sorted = sorted(to_plot_start, 
                                key=lambda x: \
                                (x['latitude']-start_lat)**2 + (x['longitude']-start_lon)**2)
  to_plot_start_sorted_picked = pick_checkout(to_plot_start_sorted)
  
  for_leaflet = []
  start_info = ""
  for row in to_plot_start_sorted_picked:
    geojson_feature = { "type": "Feature",
                        "properties": {
                            "name": row['station_name'],
                            "popupContent": generate_start_popup(row)
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [row['longitude'], row['latitude']]
                        }
                      }
    
    geojson_style = { "radius": 8,
                      "fillColor": row['color'],
                      "color": "#000",
                      "weight": 1,
                      "opacity": 1,
                      "fillOpacity": 0.8
                    }

    if row['color'] == 'black':
      start_info = """Recommended start station: {}.  
                      There are currently {} bikes there. 
                      In 5 minutes, I predict there will be {} 
                      bikes; 10 minutes, {} bikes;
                      15 minutes, {} bikes; and in 20 minutes, 
                      {} bikes"""\
                      .format(row['station_name'], row['0 min'], 
                              row['5 min'], row['10 min'],
                              row['15 min'], row['20 min'])

    for_leaflet.append([geojson_feature, geojson_style])

  if not start_info:
    if not to_plot_start_sorted_picked:
      start_info = 'No stations near your start point!'
    else:
      start_info = 'No stations near you have bikes!'

  return json.dumps([start_info, for_leaflet])


def get_end_stations(end_pos, features, station_info):
  to_plot_end = []
  [end_lat, end_lon] = end_pos
  for i, row in station_info.iterrows():
    if row['statusValue'] == 'In Service':
      if abs(row['latitude']-end_lat) < 0.005 and abs(row['longitude']-end_lon) < 0.005:
        new_row = {}
        new_row['latitude'] = row['latitude']
        new_row['longitude'] = row['longitude']
        new_row['station_name'] = row['stationName']
        new_row['0 min'] = row['availableDocks']
        new_row['30 min'], new_row['45 min'], new_row['60 min'] = predict_checkins(row['id'], row['availableDocks'],
                                                                  row['totalDocks'], features)
        to_plot_end.append(new_row)
  to_plot_end_sorted = sorted(to_plot_end, 
                                key=lambda x: \
                                (x['latitude']-end_lat)**2 + (x['longitude']-end_lon)**2)
  to_plot_end_sorted_picked = pick_checkin(to_plot_end_sorted)

  for_leaflet = []
  end_info = ""
  for row in to_plot_end_sorted_picked:
    geojson_feature = { "type": "Feature",
                        "properties": {
                            "name": row['station_name'],
                            "popupContent": generate_end_popup(row)
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [row['longitude'], row['latitude']]
                        }
                      }
    
    geojson_style = { "radius": 8,
                      "fillColor": row['color'],
                      "color": "#000",
                      "weight": 1,
                      "opacity": 1,
                      "fillOpacity": 0.8
                    }

    if row['color'] == 'black':
      end_info = """Recommended end station: {}. 
                    There are currently {} docks there.
                    In 30 minutes, I predict there will be {} 
                    docks; 45 minutes, {} docks;  
                    and in 60 minutes, {} docks"""\
                    .format(row['station_name'], row['0 min'], row['30 min'],
                            row['45 min'], row['60 min'])


    for_leaflet.append([geojson_feature, geojson_style])

  if not end_info:
    if not to_plot_end_sorted_picked:
      end_info = 'No stations near your end point!'
    else:
      end_info = 'No stations have bikes at your end point!'

  return json.dumps([end_info, for_leaflet])


