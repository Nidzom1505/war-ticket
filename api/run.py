"""
TicketWar API – Entry point.

Usage:
    python run.py                  (development)
    gunicorn -b 0.0.0.0:8000 run:app  (production)
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
