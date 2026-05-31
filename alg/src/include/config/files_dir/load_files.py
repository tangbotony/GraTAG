import os
import json
import geoip2.database

cur_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(cur_dir, "PinyinCity.json"), "r") as f:
    PinyinCity = json.load(f)
    
GeoLite2 = geoip2.database.Reader(os.path.join(cur_dir, "GeoLite2-City.mmdb"))