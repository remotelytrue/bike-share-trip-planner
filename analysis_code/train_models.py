import pandas as pd
import dill
from sklearn.ensemble import GradientBoostingRegressor
from pandas.tseries.holiday import USFederalHolidayCalendar as calendar
import json

'''
Program to 
'''
#load dill dataframes made in parse_citibike_data.py
checkouts_by_station_id= dill.load(open('checkouts_by_station_id_15.dill', 'rb'))
checkins_by_station_id = dill.load(open('checkins_by_station_id_15.dill', 'rb'))
#cut checkins
checkins_by_station_id = checkins_by_station_id[checkins_by_station_id.index<pd.to_datetime('April 1, 2016')]

#weather data requested from NOAA
weather_df = pd.read_csv('NOAA_data_through_mid_April.csv', parse_dates = [2],
                             date_parser = lambda u: pd.to_datetime(u, format='%Y%m%d'))
weather_df.index = weather_df['DATE']
weather_df_filled = weather_df.resample('15min').ffill()[['TMAX', 'TMIN', 'SNOW', 'PRCP']]

#make checkout features
checkout_plus_weather =  pd.DataFrame(checkouts_by_station_id).merge(weather_df_filled,left_index=True, right_index=True)
checkout_plus_weather['hour_minute'] = checkout_plus_weather.index.hour*60+checkout_plus_weather.index.minute
checkout_plus_weather['day_of_week'] = checkout_plus_weather.index.weekday
checkout_plus_weather['day_of_year'] = checkout_plus_weather.index.dayofyear
checkout_plus_weather['total_days'] = (checkout_plus_weather.index-pd.to_datetime('July 1, 2013')).days
checkout_plus_weather['weekday'] = (checkout_plus_weather['day_of_week'] < 5)
checkout_plus_weather['some_ppt'] = ((checkout_plus_weather['PRCP']<=0.5) & (checkout_plus_weather['PRCP']>0.05))
checkout_plus_weather['ppt'] = (checkout_plus_weather['PRCP']>0.5)

#deal with holidays
cal = calendar()
holidays = cal.holidays(start=checkout_plus_weather.index.min(), end=checkout_plus_weather.index.max())
holiday_df = pd.DataFrame(pd.Series(checkout_plus_weather.index.date).isin(holidays.date), columns = ["Holiday"])
holiday_df.index = checkout_plus_weather.index
checkout_plus_weather = checkout_plus_weather.merge(holiday_df, left_index=True, right_index=True)

#make checkin features
checkin_plus_weather =  pd.DataFrame(checkins_by_station_id).merge(weather_df_filled,left_index=True, right_index=True)
checkin_plus_weather['hour_minute'] = checkin_plus_weather.index.hour*60+checkin_plus_weather.index.minute
checkin_plus_weather['day_of_week'] = checkin_plus_weather.index.weekday
checkin_plus_weather['day_of_year'] = checkin_plus_weather.index.dayofyear
checkin_plus_weather['total_days'] = (checkin_plus_weather.index-pd.to_datetime('July 1, 2013')).days
checkin_plus_weather['weekday'] = (checkin_plus_weather['day_of_week'] < 5)
checkin_plus_weather['some_ppt'] = ((checkin_plus_weather['PRCP']<=0.5) & (checkin_plus_weather['PRCP']>0.05))
checkin_plus_weather['ppt'] = (checkin_plus_weather['PRCP']>0.5)

holidays = cal.holidays(start=checkin_plus_weather.index.min(), end=checkin_plus_weather.index.max())
holiday_df = pd.DataFrame(pd.Series(checkin_plus_weather.index.date).isin(holidays.date), columns = ["Holiday"])
holiday_df.index = checkin_plus_weather.index
checkin_plus_weather = checkin_plus_weather.merge(holiday_df, left_index=True, right_index=True)

#checkout estimators
checkout_upper_feature_importance = {}
checkout_mid_feature_importance = {}
checkout_problems = []
for column in checkouts_by_station_id.columns:
    try:
        col = checkout_plus_weather[column]
        #deal with stations being out for > 3 days
        for_roll = pd.rolling_mean(col.fillna(0), 6*24)
        back_roll = pd.rolling_mean(col.fillna(0), 6*24).shift(-6*24)
        cut_checkouts = checkout_plus_weather[(pd.notnull(for_roll) & for_roll != 0) | 
                                              (pd.notnull(back_roll) & back_roll != 0)].fillna(0)
        gb_estimator_upper = GradientBoostingRegressor(loss='quantile',alpha=0.99, learning_rate=0.1, max_depth = 3,
                                                       min_samples_leaf = 5, min_samples_split = 5, n_estimators = 400)
        gb_estimator_mid = GradientBoostingRegressor(loss='quantile',alpha=0.75, learning_rate=0.1, max_depth = 3,
                                                       min_samples_leaf = 5, min_samples_split = 5, n_estimators = 400)
        
        X = cut_checkouts[['TMAX', 'some_ppt', 'ppt', 'hour_minute', 'weekday', 'day_of_year', 'total_days', 'Holiday']]
        y = cut_checkouts[column]
        
        gb_estimator_upper.fit(X, y)
        gb_estimator_mid.fit(X, y)
        
        dill.dump(gb_estimator_upper, open('estimators/checkout_estimator_high_'+str(column)+'.dill', 'w'))
        dill.dump(gb_estimator_mid, open('estimators/checkout_estimator_mid_'+str(column)+'.dill', 'w'))
        
        checkout_upper_feature_importance[column] = list(gb_estimator_upper.feature_importances_)
        checkout_mid_feature_importance[column] = list(gb_estimator_mid.feature_importances_)
    except:
        #some manner of error list
        checkout_problems.append(column)
        continue

#checkin estimators
checkin_upper_feature_importance = {}
checkin_mid_feature_importance = {}
checkin_problems = []
for column in checkins_by_station_id.columns:
    try:
        col = checkin_plus_weather[column]
        for_roll = pd.rolling_mean(col.fillna(0), 6*24)
        back_roll = pd.rolling_mean(col.fillna(0), 6*24).shift(-6*24)
        cut_checkins = checkin_plus_weather[(pd.notnull(for_roll) & for_roll != 0) | 
                                              (pd.notnull(back_roll) & back_roll != 0)].fillna(0)
        gb_estimator_upper = GradientBoostingRegressor(loss='quantile',alpha=0.99, learning_rate=0.1, max_depth = 3,
                                                       min_samples_leaf = 5, min_samples_split = 5, n_estimators = 400)
        gb_estimator_mid = GradientBoostingRegressor(loss='quantile',alpha=0.75, learning_rate=0.1, max_depth = 3,
                                                       min_samples_leaf = 5, min_samples_split = 5, n_estimators = 400)
        
        X = cut_checkins[['TMAX', 'some_ppt', 'ppt', 'hour_minute', 'weekday', 'day_of_year', 'total_days', 'Holiday']]
        y = cut_checkins[column]
        
        gb_estimator_upper.fit(X, y)
        gb_estimator_mid.fit(X, y)
        
        #dill estimators
        dill.dump(gb_estimator_upper, open('estimators/checkin_estimator_high_'+str(column)+'.dill', 'w'))
        dill.dump(gb_estimator_mid, open('estimators/checkin_estimator_mid_'+str(column)+'.dill', 'w'))
        
        checkin_upper_feature_importance[column] = list(gb_estimator_upper.feature_importances_)
        checkin_mid_feature_importance[column] = list(gb_estimator_mid.feature_importances_)
    except:
        #add to error list
        checkin_problems.append(column)
        continue

#dump to json feature importance and any erro
with open('checkout_upper_feature_importance.json', 'w') as fp:
    json.dump(checkout_upper_feature_importance, fp)  
    
with open('checkout_mid_feature_importance.json', 'w') as fp:
    json.dump(checkout_mid_feature_importance, fp)  

with open('checkin_upper_feature_importance.json', 'w') as fp:
    json.dump(checkin_upper_feature_importance, fp)  
    
with open('checkin_mid_feature_importance.json', 'w') as fp:
    json.dump(checkin_mid_feature_importance, fp)  

with open('checkout_problems.json', 'w') as fp:
    json.dump(checkout_problems, fp)  
    
with open('checkin_problems.json', 'w') as fp:
    json.dump(checkin_problems, fp) 