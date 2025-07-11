from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import time
from datetime import datetime
import random
import string

app = Flask(__name__)
app.secret_key = "WolfSoftware"  # Oturumlar için şart

# Giriş bilgileri
ADMIN_USERNAME = "WolfSoftware"
ADMIN_PASSWORD = "156mal651"

MONGO_URI = "mongodb+srv://ktme156:156mal651@cluster0.8za5gwl.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["license_db"]
licenses = db["licenses"]

def generate_license_key(length=50):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def cleanup_expired_licenses():
    now = int(time.time())
    result = licenses.delete_many({"expiry": {"$lt": now}})
    print(f"[+] {result.deleted_count} adet süresi dolmuş lisans silindi.")

@app.before_request
def require_login():
    if request.endpoint not in ('login', 'static') and not session.get("logged_in"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Kullanıcı adı veya şifre hatalı.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    cleanup_expired_licenses()
    if request.method == "POST":
        duration = int(request.form["duration"])
        duration_type = request.form["duration_type"]
        license_type = request.form.get("license_type", "internal")
        if duration_type == "minute":
            expiry_seconds = duration * 60
        elif duration_type == "hour":
            expiry_seconds = duration * 3600
        elif duration_type == "day":
            expiry_seconds = duration * 3600 * 24
        elif duration_type == "week":
            expiry_seconds = duration * 3600 * 24 * 7
        else:
            expiry_seconds = 3600
        
        expiry_timestamp = int(time.time()) + expiry_seconds
        license_key = generate_license_key()
        
        licenses.insert_one({
            "license_key": license_key,
            "created_at": int(time.time()),
            "expiry": expiry_timestamp,
            "active": True,
            "type": license_type
        })
        
        return redirect(url_for("license_details", license_key=license_key))
    
    all_licenses = list(licenses.find().sort("created_at", -1))
    return render_template("index.html", licenses=all_licenses)

@app.route("/delete/<license_key>", methods=["POST"])
def delete_license(license_key):
    licenses.delete_one({"license_key": license_key})
    return redirect(url_for("index"))

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

@app.route("/license/<license_key>")
def license_details(license_key):
    license = licenses.find_one({"license_key": license_key})
    if not license:
        return "Lisans bulunamadı!", 404
    return render_template("license.html", license=license)

if __name__ == "__main__":
    app.run(host=0.0.0.0, port=5000, debug=True)
