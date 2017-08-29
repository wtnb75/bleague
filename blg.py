
import json
import flask
import icalendar
import cachez
import urllib.request
import datetime
import logging


logging.basicConfig(format="%(asctime)-15s %(levelname)s %(message)s", level=logging.DEBUG)
app = flask.Flask(__name__)
app.config["JSON_AS_ASCII"] = False
cachez.set_persist_folder("/tmp/cachez")


@cachez.persisted(hours=1)
def geturl(url):
    logging.info("fetching %s", url)
    return json.load(urllib.request.urlopen(url))


class bleague2ical:
    def __init__(self):
        self.urls = [
            "https://fetch.bleague.jp/1.0/gamesummary/getLeague?GameY=2017&EventKey=league",
            # "file:bleague.json",
        ]
        self.detailurl = "https://www.bleague.jp/game_detail/?YMD=%(yyyymmdd)s&TAB=R&CLUB=%(HomeMediaTeamID)s&DOUBLEHEADERFLAG=false"

    def getdata(self):
        for url in self.urls:
            yield geturl(url)

    def leagueindex(self):
        ret = set()
        for data in self.getdata():
            ret.update(data["data"].keys())
        return list(ret)

    def teamindex(self, league=None):
        ret = {}
        for data in self.getdata():
            for lg, numdata in data["data"].items():
                if league is not None and lg != league:
                    continue
                for numstr, matcharray in numdata.items():
                    for match in matcharray:
                        ret[match["HomeMediaTeamID"]] = match["HomeTeamShortName"]
                        ret[match["AwayMediaTeamID"]] = match["AwayTeamShortName"]
        return ret

    def convert(self, league=None, team=None, hometeam=None, awayteam=None, stadium=None):
        ical = icalendar.Calendar()
        title = []
        teamindex = self.teamindex()
        if league is not None:
            title.append(league + "リーグ")
        if hometeam is not None:
            title.append("ホーム " + teamindex[hometeam])
        if awayteam is not None:
            title.append("アウェイ" + teamindex[awayteam])
        if stadium is not None:
            title.append(stadium)
        if team is not None:
            title.append(teamindex[team])
        ical.add("X-WR-CALNAME", " ".join(title))
        for data in self.getdata():
            for lg, numdata in data["data"].items():
                if league is not None and lg != league:
                    continue
                for numstr, matcharray in numdata.items():
                    for match in matcharray:
                        if team is not None and team not in (match["HomeMediaTeamID"], match["AwayMediaTeamID"]):
                            continue
                        if hometeam is not None and hometeam != match["HomeMediaTeamID"]:
                            continue
                        if awayteam is not None and awayteam != match["AwayMediaTeamID"]:
                            continue
                        if stadium is not None and stadium != match["StadiumName"]:
                            continue
                        if match["FullGameDate"] == "":
                            continue
                        ev = icalendar.Event()
                        s = lg + " " + "%(HomeTeamShortName)s - %(AwayTeamShortName)s" % (match)
                        if match["GameEndedFlg"] != "before":
                            s = lg + " " + "%(HomeTeamShortName)s %(HomeTeamScore)s - %(AwayTeamScore)s %(AwayTeamShortName)s" % (match)
                        ev.add("summary", s)
                        if match["GameTime"] in ("00:00", ""):
                            startat = icalendar.vDate(datetime.datetime(*map(int, match["FullGameDate"].split("."))))
                            endat = startat
                        else:
                            startat = datetime.datetime.strptime(match["FullGameDate"] + " " + match["GameTime"], "%Y.%m.%d %H:%M")
                            endat = datetime.datetime.fromtimestamp(startat.timestamp() + 60 * 60 * 2)
                        ev.add("dtstart", startat)
                        ev.add("dtend", endat)
                        if match["Prefecture"]:
                            ev.add("location", "%(StadiumName)s (%(Prefecture)s)" % (match))
                        else:
                            ev.add("location", "%(StadiumName)s" % (match))
                        match["yyyymmdd"] = match["FullGameDate"].replace(".", "")
                        durl = self.detailurl % (match)
                        ev.add("url", durl)
                        ev.add("description", "%s 第%s節" % (lg, numstr))
                        ical.add_component(ev)
        return ical


@app.route("/team.json")
@app.route("/team/<league>.json")
def getteam(league=None):
    ics = bleague2ical()
    resp = flask.jsonify(ics.teamindex(league))
    resp.status_code = 200
    return resp


@app.route("/league.json")
def getleague():
    ics = bleague2ical()
    resp = flask.jsonify(ics.leagueindex())
    resp.status_code = 200
    return resp


@app.route("/<team>.ics")
def getical(team):
    ics = bleague2ical()
    if team == "all":
        team = None
    if team.startswith("B"):
        resp = flask.Response(ics.convert(league=team).to_ical().decode("UTF-8"), mimetype="text/calendar")
    else:
        resp = flask.Response(ics.convert(team=team).to_ical().decode("UTF-8"), mimetype="text/calendar")
    return resp


@app.route("/home/<team>.ics")
def geticalhome(team):
    ics = bleague2ical()
    if team == "all":
        team = None
    resp = flask.Response(ics.convert(hometeam=team).to_ical().decode("UTF-8"), mimetype="text/calendar")
    return resp


@app.route("/away/<team>.ics")
def geticalaway(team):
    ics = bleague2ical()
    if team == "all":
        team = None
    resp = flask.Response(ics.convert(awayteam=team).to_ical().decode("UTF-8"), mimetype="text/calendar")
    return resp


@app.route("/")
@app.route("/index.html")
@app.route("/<league>.html")
def getindex(league=None):
    ics = bleague2ical()
    body = []
    body.append("<html><head><title>B league calendar</title></head><body>")
    if league is None:
        lgs = sorted(ics.leagueindex())
    else:
        lgs = [league]
    for lg in lgs:
        body.append("<h1>%s</h1>" % (lg))
        teams = []
        tidx = ics.teamindex(lg)
        for k in sorted(tidx.keys()):
            v = tidx[k]
            teams.append("""<li><a href="/%s.ics">%s</a>(<a href="/home/%s.ics">home</a>|<a href="/away/%s.ics">away</a>)</li>""" % (k, v, k, k))
        body.append("\n".join(teams))
    body.append("</body></html>")
    resp = flask.Response("".join(body), mimetype="text/html")
    return resp


if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True, threaded=True)
