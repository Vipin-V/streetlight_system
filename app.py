# test_app.py
from flask import Flask, render_template
import os

app = Flask(__name__)

# Remove GPIO dependencies for initial testing
LIGHT_PINS = {
    'zone1': [17, 18],
    'zone2': [22, 23],
    'zone3': [24, 25]
}

# Mock light status for testing
light_status = {
    'zone1_light1': 'working',
    'zone1_light2': 'working',
    'zone2_light1': 'working',
    'zone2_light2': 'faulty',
    'zone3_light1': 'working',
    'zone3_light2': 'working'
}

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)