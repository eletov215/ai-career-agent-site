"""Read-only status; no route accepts resumes or makes billable model calls."""
from flask import Blueprint, jsonify
from security import limiter

def create_ai_status_blueprint(service):
    bp=Blueprint('ai_status',__name__)
    @bp.get('/api/ai/status')
    @limiter.limit('60 per minute')
    def status():
        response=jsonify(service.public_status())
        response.headers['Cache-Control']='no-store'
        return response
    return bp
