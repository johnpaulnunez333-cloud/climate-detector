import os
import time
from datetime import datetime, timedelta

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "change-this-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

frontend_url = os.environ.get("FRONTEND_URL", "*")
origins = "*" if frontend_url == "*" else [o.strip() for o in frontend_url.split(",")]
CORS(app, resources={r"/api/*": {"origins": origins}})

db = SQLAlchemy(app)
jwt = JWTManager(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    label = db.Column(db.String(120))
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    climate = db.Column(db.String(60), nullable=False)
    temperature = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


CITIES = [
    {"name": "Manila", "lat": 14.5995, "lon": 120.9842},
    {"name": "Quezon City", "lat": 14.6760, "lon": 121.0437},
    {"name": "Baguio", "lat": 16.4023, "lon": 120.5960},
    {"name": "Legazpi", "lat": 13.1391, "lon": 123.7438},
    {"name": "Puerto Princesa", "lat": 9.7392, "lon": 118.7353},
    {"name": "Cebu City", "lat": 10.3157, "lon": 123.8854},
    {"name": "Tacloban", "lat": 11.2543, "lon": 124.9630},
    {"name": "Iloilo City", "lat": 10.7202, "lon": 122.5621},
    {"name": "Cagayan de Oro", "lat": 8.4542, "lon": 124.6319},
    {"name": "Davao City", "lat": 7.1907, "lon": 125.4553},
    {"name": "Zamboanga City", "lat": 6.9214, "lon": 122.0790},
    {"name": "Tuguegarao", "lat": 17.6132, "lon": 121.7270},
]

RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
STORM_CODES = {95, 96, 99}


def classify(temp, feels, rain, wind, code):
    if code in STORM_CODES:
        return "Thunderstorm", "danger", "Stay indoors, avoid open areas and unplug sensitive devices."
    if wind is not None and wind >= 62:
        return "Storm-force winds", "danger", "Secure loose objects and avoid coastal or elevated areas."
    if (rain is not None and rain >= 7.6) or code in {65, 67, 82}:
        return "Heavy rain", "warning", "Expect flooding in low areas. Avoid crossing flooded roads."
    if (rain is not None and rain > 0) or code in RAIN_CODES:
        return "Rainy", "info", "Bring an umbrella and watch for slippery roads."
    if feels is not None and feels >= 41:
        return "Dangerous heat", "danger", "Limit outdoor activity, drink water often and rest in shade."
    if feels is not None and feels >= 33:
        return "Hot and humid", "warning", "Drink plenty of water and avoid long sun exposure."
    if temp is not None and temp >= 27:
        return "Warm", "success", "Comfortable for most outdoor activities."
    return "Cool", "primary", "Light layers recommended, especially in the evening."


weather_cache = {}
# Pinalaki natin ang cache duration para kumonti ang requests (30 mins)
CACHE_SECONDS = 1800 

def fetch_weather(lat, lon):
    key = (round(lat, 1), round(lon, 1))
    now = time.time()
    cached = weather_cache.get(key)
    
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]

    last_error = None
    
    headers = {
        "User-Agent": "ClimateDetectorApp/1.0 (contact: your_email@example.com)"
    }
    
    # 3 attempts, exponential backoff
    for attempt in range(3):
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": key[0],
                    "longitude": key[1],
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
                    "timezone": "Asia/Manila",
                },
                headers=headers,
                timeout=15,
            )
            
            if response.status_code == 429:
                last_error = "rate limited (429)"
                wait_time = 2 * (2 ** attempt) 
                app.logger.warning(f"Rate limited. Retrying in {wait_time}s... (Attempt {attempt+1}/3)")
                time.sleep(wait_time)
                continue
                
            response.raise_for_status()
            current = response.json()["current"]
            weather_cache[key] = (now, current)
            return current
            
        except (requests.RequestException, KeyError, ValueError) as error:
            last_error = repr(error)
            time.sleep(2) # Maghintay muna bago mag retry kapag may ibang error

    app.logger.error("Open-Meteo failed after retries: %s", last_error)
    
    if cached:
        app.logger.info("Returning stale cache data as fallback.")
        return cached[1]
        
    raise requests.RequestException(last_error)


def valid_ph_point(lat, lon):
    return 4.0 <= lat <= 22.0 and 116.0 <= lon <= 128.0


@app.get("/api/health")
def health():
    return jsonify(status="ok")
