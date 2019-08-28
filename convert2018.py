import sys
import json
import blg2018

b2 = blg2018.bleague2ical2()
json.dump(b2.convert2json(), fp=sys.stdout, ensure_ascii=False)
