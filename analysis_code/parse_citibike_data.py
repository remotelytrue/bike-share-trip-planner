import pandas as pd
import dill

'''
This program imports citibike historical data (available at 
https://s3.amazonaws.com/tripdata/index.html), and groups 
it into numberof checkouts and checkins per 15 minutes as 
well as by station (both latitude/longitude and station id)
'''
#unzipped files from citibike; otherwise unchanged
batches = [[ 'zip_files/2013-07 - Citi Bike trip data.csv', 
             'zip_files/2013-08 - Citi Bike trip data.csv',
             'zip_files/2013-09 - Citi Bike trip data.csv', 
             'zip_files/2013-10 - Citi Bike trip data.csv',
             'zip_files/2013-11 - Citi Bike trip data.csv', 
             'zip_files/2013-12 - Citi Bike trip data.csv',
             'zip_files/2014-01 - Citi Bike trip data.csv', 
             'zip_files/2014-02 - Citi Bike trip data.csv',
             'zip_files/2014-03 - Citi Bike trip data.csv', 
             'zip_files/2014-04 - Citi Bike trip data.csv',
             'zip_files/2014-05 - Citi Bike trip data.csv', 
             'zip_files/2014-06 - Citi Bike trip data.csv',
             'zip_files/2014-07 - Citi Bike trip data.csv', 
             'zip_files/2014-08 - Citi Bike trip data.csv'],
            ['zip_files/201409-citibike-tripdata.csv', 
             'zip_files/201410-citibike-tripdata.csv',
             'zip_files/201411-citibike-tripdata.csv', 
             'zip_files/201412-citibike-tripdata.csv'],
            ['zip_files/201501-citibike-tripdata.csv', 
             'zip_files/201502-citibike-tripdata.csv',
             'zip_files/201503-citibike-tripdata.csv'], 
            ['zip_files/201504-citibike-tripdata.csv',
             'zip_files/201505-citibike-tripdata.csv'],
            ['zip_files/201506-citibike-tripdata.csv'],
            ['zip_files/201507-citibike-tripdata.csv', 
             'zip_files/201508-citibike-tripdata.csv',
             'zip_files/201509-citibike-tripdata.csv', 
             'zip_files/201510-citibike-tripdata.csv',
             'zip_files/201511-citibike-tripdata.csv', 
             'zip_files/201512-citibike-tripdata.csv', 
             'zip_files/201601-citibike-tripdata.csv', 
             'zip_files/201602-citibike-tripdata.csv',
             'zip_files/201603-citibike-tripdata.csv']]
#time formats for each batch of csv files
formats = ['%Y-%m-%d %H:%M:%S', 
           '%m/%d/%Y %H:%M:%S', 
           '%m/%d/%Y %H:%M', 
           '%m/%d/%Y %H:%M:%S', 
           '%m/%d/%Y %H:%M',
           '%m/%d/%Y %H:%M:%S']

counted_checkouts_station_id = pd.Series()
counted_checkouts_lat_long = pd.Series()
counted_checkins_station_id = pd.Series()
counted_checkins_lat_long = pd.Series()

unique_stations = pd.DataFrame()

for i, batch in enumerate(batches):
    for file_name in batch:
        new_df = pd.read_csv(file_name, parse_dates = [1,2],
                             date_parser = lambda u: pd.to_datetime(u, format=formats[i]))#"2013-08-01 00:00:10
        new_df['start_lat_long'] = '('+new_df['start station latitude'].apply(str)+', '+new_df['start station longitude'].apply(str)+')'
        new_df['end_lat_long'] = '('+new_df['end station latitude'].apply(str)+', '+new_df['end station longitude'].apply(str)+')'
        #group and count checkouts
        counted_checkouts_station_id = counted_checkouts_station_id.append(new_df.groupby([pd.Grouper(key='starttime', 
                                                                                                      freq='15Min'), 
                                                                           'start station id']).count()['tripduration'])
        counted_checkouts_lat_long = counted_checkouts_lat_long.append(new_df.groupby([pd.Grouper(key='starttime', 
                                                                                                  freq='15Min'), 
                                                                               'start_lat_long']).count()['tripduration'])
        #group and count checkins
        counted_checkins_station_id = counted_checkins_station_id .append(new_df.groupby([pd.Grouper(key='stoptime', 
                                                                                                     freq='15Min'), 
                                                            'end station id']).count()['tripduration'])
        counted_checkins_lat_long = counted_checkins_lat_long.append(new_df.groupby([pd.Grouper(key='stoptime', 
                                                                                                freq='15Min'), 
                                                                              'end_lat_long']).count()['tripduration'])
        #get correspondence between station id, name, latitude and longitude
        unique_stations = unique_stations.append(new_df[['start station id', 'start station name', 
                              'start_lat_long']].drop_duplicates()).drop_duplicates()
        unique_stations = unique_stations.append(new_df[['end station id', 'end station name', 
                              'end_lat_long']].drop_duplicates()).drop_duplicates()

#sum up duplicate end times
counted_checkins_lat_long = counted_checkins_lat_long.groupby(level = ['stoptime', 'end_lat_long']).sum()
counted_checkins_station_id = counted_checkins_station_id.groupby(level = ['stoptime', 'end station id']).sum()

#unstack counted stuff
counted_checkouts_by_station_id = counted_checkouts_station_id.unstack()
counted_checkouts_by_location = counted_checkouts_lat_long.unstack()
counted_checkins_by_station_id = counted_checkins_station_id.unstack()
counted_checkins_by_location = counted_checkins_lat_long.unstack()

#dill dump dataframes
dill.dump(counted_checkouts_by_station_id, open('checkouts_by_station_id_15.dill', 'w'))
dill.dump(counted_checkouts_by_location, open('checkouts_by_location_15.dill', 'w'))
dill.dump(counted_checkins_by_station_id, open('checkins_by_station_id_15.dill', 'w'))
dill.dump(counted_checkins_by_location, open('checkins_by_location_15.dill', 'w'))

dill.dump(unique_stations, open('unique_stations.dill', 'w'))