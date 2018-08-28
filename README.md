# convert B.League schedule to ical format

- python -m venv .
- . ./bin/activate
- pip install -r requirements.txt
- python blg.py
  - or: gunicorn blg:app
  - or: FLASK_APP=blg.py flask run
