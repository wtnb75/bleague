from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.serving import run_simple
from blg import app as app1
from blg2 import app as app2

app = DispatcherMiddleware(app2, {'/old': app1})

if __name__ == "__main__":
    # debug = True
    debug = False
    run_simple('localhost', 8080, app, threaded=True)
    # app.run(host="localhost", port=8080, debug=debug, threaded=True)
