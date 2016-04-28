import pandas
from datetime import datetime, timedelta 
import numpy as np
from bokeh.io import gridplot
from bokeh.plotting import figure
from bokeh.embed import components

#def delta_bikes(flux_series, time, time_change):
#  time_change = int(time_change)
#  times = [time+timedelta(minutes=i) for i in range(time_change)]
#  fluxes = [flux_series[time.hour]/60 for time in times]
#  deltas = []
#
#  return deltas

def make_prediction(flux_df, start_station, start_station_info, end_station, end_station_info, time):
  #station info is [stationName, availableBikes, availableDocks, totalDocks] 
  #starting location predictions
  start_fluxes = flux_df[start_station]
  start_initial_bikes = start_station_info[0]
  start_total_docks = start_station_info[2]
  #start_deltas = delta_bikes(start_fluxes, time, 60)
  #start_bikes_left = np.clip(start_initial_bikes + start_deltas, 0, start_total_docks)

  #ending location predictions
  end_fluxes = flux_df[end_station]
  end_initial_docks = end_station_info[1]
  end_total_docks = end_station_info[2]
  #end_deltas = delta_bikes(end_fluxes, time, 60)
  #end_docks_left = np.clip(end_initial_docks - end_deltas, 0, end_total_docks)

  #bokeh plot-flux for start station
  start_flux_plot = figure(plot_width = 600, plot_height = 550, 
                            x_axis_label = 'Hour of day', 
                            y_axis_label = 'Average (bikes in - bikes out) per hour',
                            title='Start station (%s bikes to start)'%start_initial_bikes)
  start_flux_plot.line(range(24), start_fluxes)

  #bokeh plot-flux for end station
  end_flux_plot = figure(plot_width = 600, plot_height = 550, 
                         x_axis_label = 'Hour of day', 
                         y_axis_label = 'Average (bikes in - bikes out) per hour',
                         title='End station (%s docks to start)'%end_initial_docks)
  end_flux_plot.line(range(24), end_fluxes)

  #bokeh plot-predicted bikes for start station
  #start_pred_plot = figure(plot_width = 600, plot_height = 550, 
  #                       x_axis_label = 'Minutes elapsed', 
  #                       y_axis_label = 'Predicted bikes',
  #                       title='Start station bike prediction')
  #start_pred_plot.line(range(60), start_bikes_left)
#
  ##bokeh plot-predicted docks for end station
  #end_pred_plot = figure(plot_width = 600, plot_height = 550,
  #                       x_axis_label = 'Minutes elapsed', 
  #                       y_axis_label = 'Predicted docks', 
  #                      title='End station dock prediction')
  #end_pred_plot.line(range(60), end_docks_left)

  p = gridplot([[start_flux_plot, end_flux_plot]])

  return components(p)

  #ending location predictions
  # get delta_bikes(flux_series)
  #delta(bike) = sum(flux(t)*t(minutes)/60)
  # number bikes left = floor(max(delta_bike) station_info())
  #
