# convert B.League schedule to ical format

- python -m venv .
- . ./bin/activate
- pip install -r requirements.txt
- python main.py
  - or: gunicorn main:app
  - or: FLASK_APP=main.py flask run

## update schedule

- python blg2019.py json --output 2019.json

check and update

- update on running game
    - python blg2019.py maychange --input 2019.json && python blg2019.py json --output 2019.json
- update if game not finished
    - python blg2019.py maychange --input 2019.json --no-ingame && python blg2019.py json --output 2019.json

## access

- http://localhost:8080/
