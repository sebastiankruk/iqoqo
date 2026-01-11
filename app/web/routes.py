"""Defines the main routes for the web interface."""
from flask import render_template
from . import web_bp

@web_bp.route('/')
def index():
    return render_template('index.html')
