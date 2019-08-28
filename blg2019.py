# coding:utf-8
import sys
import time
import requests
import cachez
import json
import click
from lxml.html import fromstring
import logging

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s %(message)s", level=logging.DEBUG)

cachez.set_persist_folder("/tmp/cachez")


# @cachez.persisted(hours=10)
def geturl(url, args):
    logging.info("fetching %s %s", url, args)
    return requests.get(url, args).content


class bleague2ical3:
    team_map = json.load(open("team_map.json"))

    def merge(self, *args):
        ret = {}
        for a in args:
            ret.update(a)
        return ret

    def __init__(self, year=2019):
        self.baseurl = "https://www.bleague.jp/schedule/"
        self.detailurl = "https://www.bleague.jp/game_detail/?ScheduleKey=%(key)s"
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
            # "オールスター": self.merge(b1, {"event": 5}),
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
                    home, away = [x.text_content().strip()
                                  for x in game.find_class("team")]
                    # print("home", home, "away", away)
                    # print("text", self.text1(game, "point"))
                    try:
                        homept, awaypt = self.text1(game, "point").split("-")
                    except ValueError:
                        homept, awaypt = '', ''
                    ar = game.find_class("arena")[0]
                    pref = ar.text.strip()
                    arena = ar.getchildren()[0].tail.strip()
                    # arena = self.text1(game, "arena")
                    datestr = self.text1(game, "date")
                    timestr = self.text1(game, "time").split()[0]
                    name = self.text1(game, "ScheduleClassName")
                    schedkey = int(game.getparent().get("data-schedule-key"))
                    try:
                        timeval = time.localtime(
                            int(game.getparent().get("data-game-date")))
                    except ValueError:
                        timeval = None
                    ent = {
                        "sname": sname,
                        "pref": pref,
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

    def team2id(self, name):
        tm = list(filter(lambda v: v[1] == name, self.team_map.items()))
        if len(tm) != 1:
            return None
        return tm[0][0]

    def convert2json(self):
        data = {}
        for lg, matches in self.data.items():
            if len(matches) == 0:
                continue
            data[lg] = {}
            for i, m in enumerate(matches):
                sn = m["sname"].lstrip("第").rstrip("節")
                hmid = self.team2id(m["home"])
                awid = self.team2id(m["away"])
                if sn not in data[lg]:
                    data[lg][sn] = []
                if m["startAt"] is None:
                    continue
                ent = {
                    "ScheduleKey": m["key"],
                    "FullGameDate": time.strftime("%Y.%m.%d", m["startAt"]),
                    "GameDate": time.strftime("%m.%d", m["startAt"]),
                    "GameTime": time.strftime("%H:%M", m["startAt"]),
                    "HomeTeamShortName": m["home"],
                    "AwayTeamShortName": m["away"],
                    "HomeMediaTeamID": hmid,
                    "AwayMediaTeamID": awid,
                    "StadiumName": m["arena"],
                    "Prefecture": m["pref"],
                    "GameEndedFlg": "after",
                    "DoubleHeaderFlag": False,
                }
                if "homept" in m:
                    ent["HomeTeamScore"] = m["homept"]
                if "awaypt" in m:
                    ent["AwayTeamScore"] = m["awaypt"]
                if time.time() < time.mktime(m["startAt"]) + 2 * 60 * 60:
                    ent["GameEndedFlg"] = "before"
                data[lg][sn].append(ent)
        return {
            "result": "OK",
            "data": data,
        }


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


@cli.command("json")
@click.option("--output", type=click.File('w'), default=sys.stdout)
@click.option("--year", type=int, default=2019)
def getjson(output, year):
    bl = bleague2ical3(year)
    json.dump(bl.convert2json(), fp=output, ensure_ascii=False)


@cli.command()
@click.option("--input", type=click.File('r'), default=sys.stdin)
@click.option("--ingame/--no-ingame", default=True)
def maychange(input, ingame):
    now = time.time()
    data = json.load(fp=input)
    for d in data.get("data", {}).values():
        for m in d.values():
            for g in m:
                if ingame:
                    if g["GameTime"] not in ("00:00", ""):
                        startAt = g["FullGameDate"] + " " + g["GameTime"]
                        t = time.mktime(time.strptime(
                            startAt, "%Y.%m.%d %H:%M"))
                        if t < now and now < t + 2 * 60 * 60:
                            logging.info("running: %s", g)
                            sys.exit(0)
                else:
                    if g["GameEndedFlg"] == "before":
                        logging.info("not ended: %s", g)
                        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    cli()
