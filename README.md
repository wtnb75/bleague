# convert B.League schedule to ical format

- python -m venv .
- . ./bin/activate
- pip install -r requirements.txt
- python main.py
  - or: gunicorn main:app
  - or: FLASK_APP=main.py flask run

## access

- http://localhost:8080/      -> 2018 season
- http://localhost:8080/old/  -> 2016, 2017 season
