# app.py
from flask import Flask, render_template, jsonify, request
import sqlite3
import datetime
import RPi.GPIO as GPIO
from threading import Thread
import time

app = Flask(__name__)

# GPIO Setup
GPIO.setmode(GPIO.BCM)
# Example GPIO pins for 3 zones with 2 lights each
LIGHT_PINS = {
    'zone1': [17, 18],
    'zone2': [22, 23],
    'zone3': [24, 25]
}

# Backup power status pin
BACKUP_STATUS_PIN = 17
GPIO.setup(BACKUP_STATUS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initialize GPIO pins
for zone in LIGHT_PINS.values():
    for pin in zone:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

# Initialize database
def init_db():
    conn = sqlite3.connect('streetlights.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS light_status
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  zone TEXT,
                  light_id INTEGER,
                  status TEXT,
                  timestamp DATETIME)''')
    
    # Add backup_status table
    c.execute('''CREATE TABLE IF NOT EXISTS backup_status
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  status TEXT,
                  timestamp DATETIME)''')
    conn.commit()
    conn.close()

init_db()

# Global variables for system state
system_mode = 'normal'  # normal, emergency, zone_control
light_status = {}
backup_status = 'off'

def log_status(zone, light_id, status):
    conn = sqlite3.connect('streetlights.db')
    c = conn.cursor()
    c.execute('''INSERT INTO light_status (zone, light_id, status, timestamp)
                 VALUES (?, ?, ?, ?)''', (zone, light_id, status, datetime.datetime.now()))
    conn.commit()
    conn.close()

def log_backup_status(status):
    conn = sqlite3.connect('streetlights.db')
    c = conn.cursor()
    c.execute('''INSERT INTO backup_status (status, timestamp)
                 VALUES (?, ?)''', (status, datetime.datetime.now()))
    conn.commit()
    conn.close()

# Monitor lights and backup power
def monitor_system():
    global backup_status
    while True:
        # Monitor lights
        for zone, pins in LIGHT_PINS.items():
            for i, pin in enumerate(pins):
                status = 'working' if GPIO.input(pin) else 'faulty'
                light_key = f"{zone}_light{i+1}"
                light_status[light_key] = status
                log_status(zone, i+1, status)
        
        # Monitor backup power
        new_backup_status = 'on' if GPIO.input(BACKUP_STATUS_PIN) else 'off'
        if new_backup_status != backup_status:
            backup_status = new_backup_status
            log_backup_status(backup_status)
            
        time.sleep(5)  # Check every 5 seconds

# Start monitoring in background
monitor_thread = Thread(target=monitor_system, daemon=True)
monitor_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify({
        'system_mode': system_mode,
        'light_status': light_status,
        'backup_status': backup_status
    })

@app.route('/api/mode', methods=['POST'])
def set_mode():
    global system_mode
    new_mode = request.json.get('mode')
    if new_mode in ['normal', 'emergency', 'zone_control']:
        system_mode = new_mode
        if new_mode == 'emergency':
            # Turn on all lights in emergency mode
            for zone_pins in LIGHT_PINS.values():
                for pin in zone_pins:
                    GPIO.output(pin, GPIO.HIGH)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/control', methods=['POST'])
def control_lights():
    if system_mode != 'zone_control':
        return jsonify({'success': False, 'message': 'System not in zone control mode'})
    
    zone = request.json.get('zone')
    state = request.json.get('state')
    
    if zone in LIGHT_PINS:
        for pin in LIGHT_PINS[zone]:
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        return jsonify({'success': True})
    return jsonify({'success': False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)