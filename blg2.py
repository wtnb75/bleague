# coding:utf-8
import time
import requests
import cachez
import flask
import json
from lxml.html import fromstring
import logging
import icalendar
import datetime

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s %(message)s", level=logging.DEBUG)
app = flask.Flask(__name__)
app.config["JSON_AS_ASCII"] = False

cachez.set_persist_folder("/tmp/cachez")


@cachez.persisted(hours=10)
def geturl(url, args):
    logging.info("fetching %s %s", url, args)
    return requests.get(url, args).content


class bleague2ical2:
    team_map = json.load(open("team_map.json"))

    def merge(self, *args):
        ret = {}
        for a in args:
            ret.update(a)
        return ret

    def __init__(self):
        self.baseurl = "https://www.bleague.jp/schedule/"
        year = 2018
        b1 = {
            "tab": 1,
            "year": year,
        }
        b2 = {
            "tab": 2,
            "year": year,
        }
        self.events = {
            "B1": self.merge(b1, {
                "event": 2,
                "club": "",
                "setuFrom": 1,
                "setuTo": 36,
            }),
            "オールスター": self.merge(b1, {"event": 5}),
            "B1チャンピオンシップ": self.merge(b1, {"event": 3}),
            "B1残留プレーオフ": self.merge(b1, {"event": 4}),
            "B1・B2入替戦": self.merge(b1, {"event": 11}),
            "アーリーカップ": self.merge(b1, {"event": 20}),
            "B2": self.merge(b2, {
                "event": 7,
                "club": "",
                "setuFrom": 1,
                "setuTo": 36,
            }),
            "B2残留プレーオフ": self.merge(b2, {"event": 9}),
            "B2プレーオフ": self.merge(b2, {"event": 8}),
            "B2・B3入替戦": self.merge(b2, {"event": 17}),
        }
        self.readAll()

    def text1(self, tree, cls):
        found = tree.find_class(cls)
        if found is not None and len(found) != 0:
            return found[0].text_content().strip()
        return ""

    def readone(self, args):
        res = []
        tree = fromstring(geturl(self.baseurl, args))
        for rlist in tree.xpath('//dl[@id="round_list"]'):
            sname = self.text1(rlist, "setsu_name")
            for games in rlist.find_class("game_list"):
                for game in games.find_class("gamedata_left"):
                    home, away = [x.text_content().strip() for x in game.find_class("team")]
                    homept, awaypt = self.text1(game, "point").split("VS")
                    arena = self.text1(game, "arena")
                    datestr = self.text1(game, "date")
                    timestr = self.text1(game, "time").split()[0]
                    name = self.text1(game, "ScheduleClassName")
                    schedkey = int(game.getparent().get("data-schedule-key"))
                    try:
                        timeval = time.localtime(int(game.getparent().get("data-game-date")))
                    except ValueError:
                        timeval = None
                    ent = {
                        "sname": sname,
                        "arena": arena,
                        "startAt": timeval,
                        "date": datestr,
                        "time": timestr,
                        "key": schedkey,
                        "name": name,
                        "home": home,
                        "away": away,
                    }
                    if homept != "":
                        ent["homept"] = int(homept)
                    if awaypt != "":
                        ent["awaypt"] = int(awaypt)
                    res.append(ent)
        return res

    def readAll(self):
        res = {}
        for k, v in self.events.items():
            res[k] = self.readone(v)
        self.data = res
        return res

    def isa_child(self, ev, k, v):
        if k == "team":
            return self.isa_child(ev, "home", v) or self.isa_child(ev, "away", v)
        val = ev.get(k)
        if val is None:
            return False
        if v.startswith("!"):
            if val == v:
                return False
        elif val != v:
            return False
        return True

    def isa(self, ev, args):
        res = True
        for k, v in args.items():
            if v is None:
                continue
            if not self.isa_child(ev, k, v):
                res = False
        return res

    def filter(self, data, **kwargs):
        res = []
        for k, v in data.items():
            for ev in v:
                ev2 = self.merge(ev, {"league": k})
                if self.isa(ev2, kwargs):
                    res.append(ev2)
        return res

    def leagueindex(self):
        res = []
        for k, v in self.data.items():
            if len(v) != 0 and k.startswith("B"):
                res.append(k)
        return res

    def teamindex(self, lg):
        if lg is None:
            return self.team_map
        teammap_rev = {}
        for k, v in self.team_map.items():
            teammap_rev[v] = k
        res = {}
        for v in self.data.get(lg):
            t1 = v.get("home")
            t2 = v.get("away")
            # assert t1 in teammap_rev
            # assert t2 in teammap_rev
            if t1 in teammap_rev:
                res[teammap_rev[t1]] = t1
            if t2 in teammap_rev:
                res[teammap_rev[t2]] = t2
        return res

    def mkdate(self, s):
        return icalendar.vDate(datetime.datetime.fromtimestamp(time.mktime(s)))

    def mktime(self, s):
        return datetime.datetime.fromtimestamp(time.mktime(s))

    def convert(self, league=None, team=None, hometeam=None, awayteam=None, stadium=None):
        ical = icalendar.Calendar()
        title = []
        teamindex = self.team_map
        if league is not None:
            title.append(league + u"リーグ")
        if hometeam is not None and hometeam in teamindex:
            title.append(u"ホーム " + teamindex[hometeam])
        if awayteam is not None and awayteam in teamindex:
            title.append(u"アウェイ" + teamindex[awayteam])
        if stadium is not None:
            title.append(stadium)
        if team is not None and team in teamindex:
            title.append(teamindex[team])
        ical.add("X-WR-CALNAME", " ".join(title))

        defval = {"homept": "", "awaypt": ""}
        for data in self.filter(self.data, team=teamindex.get(team),
                                home=teamindex.get(hometeam), away=teamindex.get(awayteam),
                                arena=stadium, league=league):
            ev = icalendar.Event()
            d = self.merge(defval, data)
            s = "%(league)s %(home)s%(homept)s - %(awaypt)s%(away)s" % (d)
            ev.add("summary", s)
            start = data.get("startAt")
            if start.tm_hour == 0:
                startat = self.mkdate(start)
                endat = startat
            else:
                startat = self.mktime(start)
                endat = startat + datetime.timedelta(hours=2)
            ev.add("dtstart", startat)
            ev.add("dtend", endat)
            ev.add("location", "%(arena)s" % (data))
            ev.add("description", u"%(league)s %(sname)s" % (d))
            ical.add_component(ev)
        return ical


@app.route("/team.json")
@app.route("/team/<league>.json")
def getteam(league=None):
    ics = bleague2ical2()
    resp = flask.jsonify(ics.teamindex(league))
    resp.status_code = 200
    return resp


@app.route("/league.json")
def getleague():
    ics = bleague2ical2()
    resp = flask.jsonify(ics.leagueindex())
    resp.status_code = 200
    return resp


@app.route("/<team>.ics")
def getical(team):
    ics = bleague2ical2()
    if team == "all":
        team = None
    if team.startswith("B"):
        resp = flask.Response(ics.convert(league=team).to_ical().decode(
            "UTF-8"), mimetype="text/calendar")
    else:
        resp = flask.Response(ics.convert(team=team).to_ical().decode(
            "UTF-8"), mimetype="text/calendar")
    return resp


@app.route("/home/<team>.ics")
def geticalhome(team):
    ics = bleague2ical2()
    if team == "all":
        team = None
    resp = flask.Response(ics.convert(hometeam=team).to_ical().decode(
        "UTF-8"), mimetype="text/calendar")
    return resp


@app.route("/away/<team>.ics")
def geticalaway(team):
    ics = bleague2ical2()
    if team == "all":
        team = None
    resp = flask.Response(ics.convert(awayteam=team).to_ical().decode(
        "UTF-8"), mimetype="text/calendar")
    return resp


@app.route("/")
@app.route("/index.html")
@app.route("/<league>.html")
def getindex(league=None):
    ics = bleague2ical2()
    data = {}
    if league is None:
        lgs = sorted(ics.leagueindex())
    else:
        lgs = [league]
    for lg in lgs:
        data[lg] = ics.teamindex(lg)
    return flask.render_template("index.j2", data=data)


if __name__ == "__main__":
    # debug = True
    debug = False
    app.run(host="localhost", port=8080, debug=debug, threaded=True)
