from flask import Flask, render_template, request, redirect
from work import get_current_station_data, predict, get_current_info
from datetime import datetime
import pandas

app = Flask(__name__)
app.have_locs = False
app.script = None
app.div = None

@app.route('/')
def main():
  return redirect('/index')

@app.route('/index', methods=['GET', 'POST'])
def index():
  if request.method == 'GET':
    #app.time = datetime.now()
    app.current_time, app.station_info = get_current_info.get_station_info()
    app.temp, app.conditions = get_current_info.get_noaa_info()
    app.features = get_current_info.build_features(app.current_time, app.temp, app.conditions)
    date_str = app.current_time.strftime('%A, %B %d, %Y') 
    time_str = app.current_time.strftime('%H:%M')
    return render_template('index.html', time = time_str, date=date_str,
                           temp = app.temp, conditions = app.conditions, df=str(app.features))
  else:
    app.start_point = request.form['start_point']
    app.end_point = request.form['end_point']
    app.have_locs = True
    #app.time = request.form['time'] maybe...
    return redirect('/station_map')

@app.route('/station_map')
def station_map():
  if not app.have_locs:
    return redirect('/index')
  else:
    start_string, end_string, (script, div) = get_current_station_data.get_map(app.station_info, 
                                                   app.features, app.start_point, app.end_point)
    return render_template('station_map.html', start_string = start_string,
                           end_string = end_string, script=script, div=div)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/data')
def show_data_center():
  return render_template('Week_6_Figures.slides.html')

@app.route('/error')
def error():
  return render_template('error.html')

if __name__ == '__main__':
  app.run(port=3357, debug=True) 
