from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from database import init_db, get_db_connection
from api_routes import api_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Urban Mobility Data Explorer API is running'
    })

if __name__ == '__main__':
    # Ensure tables exist; no processing here
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5003)
