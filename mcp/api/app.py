"""
Flask application factory and initialization
"""

from flask import Flask
from flask_cors import CORS
import logging

logger = logging.getLogger("api")


def create_app(config, engine, session):
    """Create and configure Flask application"""
    
    app = Flask(__name__)
    
    # CORS for local network access
    CORS(app, resources={
        r"/api/*": {
            "origins": ["localhost", "127.0.0.1"],
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })
    
    # Store config and database in app context
    app.config["MCP_CONFIG"] = config
    app.config["DB_ENGINE"] = engine
    app.config["DB_SESSION"] = session
    
    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "healthy", "version": "1.0.0"}, 200
    
    # Root endpoint
    @app.route("/", methods=["GET"])
    def index():
        return {
            "name": "Master Control Program (MCP)",
            "version": "1.0.0",
            "status": "running",
            "api_base": "/api/v1",
        }, 200
    
    logger.info("Flask application created and configured")
    return app
