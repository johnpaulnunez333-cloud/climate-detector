import os
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


def fetch_weather(lat, lon):
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
            "timezone": "Asia/Manila",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["current"]


def valid_ph_point(lat, lon):
    return 4.0 <= lat <= 22.0 and 116.0 <= lon <= 128.0


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or "@" not in email or len(password) < 6:
        return jsonify(error="Enter a name, a valid email and a password with at least 6 characters."), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="This email is already registered."), 409

    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(token=token, user={"id": user.id, "name": user.name, "email": user.email}), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(error="Incorrect email or password."), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(token=token, user={"id": user.id, "name": user.name, "email": user.email})


@app.get("/api/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found."), 404
    return jsonify(id=user.id, name=user.name, email=user.email)


@app.get("/api/cities")
def cities():
    return jsonify(CITIES)


@app.get("/api/climate")
@jwt_required()
def climate():
    try:
        lat = float(request.args.get("lat", ""))
        lon = float(request.args.get("lon", ""))
    except ValueError:
        return jsonify(error="Latitude and longitude are required."), 400

    if not valid_ph_point(lat, lon):
        return jsonify(error="Select a location inside the Philippines."), 400

    try:
        current = fetch_weather(lat, lon)
    except requests.RequestException:
        return jsonify(error="Weather service is unavailable. Try again shortly."), 502

    temp = current.get("temperature_2m")
    feels = current.get("apparent_temperature")
    rain = current.get("precipitation")
    wind = current.get("wind_speed_10m")
    code = current.get("weather_code")
    label = (request.args.get("label") or "").strip()[:120] or f"{lat:.2f}, {lon:.2f}"

    climate_name, level, advice = classify(temp, feels, rain, wind, code)

    db.session.add(
        Search(
            user_id=int(get_jwt_identity()),
            label=label,
            lat=lat,
            lon=lon,
            climate=climate_name,
            temperature=temp,
        )
    )
    db.session.commit()

    return jsonify(
        label=label,
        lat=lat,
        lon=lon,
        climate=climate_name,
        level=level,
        advice=advice,
        temperature=temp,
        feels_like=feels,
        humidity=current.get("relative_humidity_2m"),
        rain=rain,
        wind=wind,
        time=current.get("time"),
    )


@app.get("/api/history")
@jwt_required()
def history():
    rows = (
        Search.query.filter_by(user_id=int(get_jwt_identity()))
        .order_by(Search.created_at.desc())
        .limit(10)
        .all()
    )
    return jsonify(
        [
            {
                "id": r.id,
                "label": r.label,
                "lat": r.lat,
                "lon": r.lon,
                "climate": r.climate,
                "temperature": r.temperature,
                "created_at": r.created_at.isoformat() + "Z",
            }
            for r in rows
        ]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
