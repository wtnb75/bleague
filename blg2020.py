# coding:utf-8
import sys
import time
import requests
import cachez
import json
import click
from bs4 import BeautifulSoup
import logging

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s %(message)s", level=logging.DEBUG)

cachez.set_persist_folder("/tmp/cachez")


@cachez.persisted(hours=10)
def geturl(url, args={}):
    logging.info("fetching %s %s", url, args)
    return requests.get(url, args).content


class bleague2ical4:
    def merge(self, *args):
        ret = {}
        for a in args:
            ret.update(a)
        return ret

    def __init__(self, year=2020):
        self.baseurl = "https://www.bleague.jp/schedule/"
        self.year = year
        self.team_map = json.load(open("team_map.json"))
        self.team_revmap = dict([(x[1], x[0]) for x in self.team_map.items()])

    def team_schedule(self, tid):
        team_data = self.teams[tid]
        tabmap = {
            2: 1,
            7: 2,
        }
        query = {
            "s": 1,
            "tab": tabmap.get(team_data["league_id"], 1),
            "year": self.year,
            "event": team_data["league_id"],
            "club": tid,
        }
        httpres = geturl(self.baseurl, query)
        root = BeautifulSoup(httpres, "lxml")
        tbl = root.find("dl", class_="round__def active")
        days = tbl.find_all("dt", class_="round__def--tit")
        games = tbl.find_all("div", class_="data_game")
        res = []
        for day, game in zip(days, games):
            daystr = day.text.split(" ", 1)[0]
            teams = [x.text.strip() for x in game.find_all("span", class_="team_name")]
            homeid = self.team_revmap.get(teams[0], "un")
            awayid = self.team_revmap.get(teams[1], "un")
            res.append({"FullGameDate": daystr,
                        "HomeTeamShortName": teams[0],
                        "AwayTeamShortName": teams[1],
                        "GameEndedFlg": "before",
                        "HomeMediaTeamID": homeid,
                        "AwayMediaTeamID": awayid,
                        "Prefecture": "",
                        "StadiumName": "",
                        "GameTime": "",
                        })
        return res

    def read_teams(self):
        httpres = geturl(self.baseurl)
        root = BeautifulSoup(httpres, "lxml")
        sbox = root.find("select", class_="children")
        self.teams = {}
        for i in sbox.find_all("option"):
            tid = i.get("value")
            lid = i.get("data-val")
            tname = i.text.strip()
            if tid == "" or lid == "" or tname == "":
                continue
            t = int(tid)
            self.teams[t] = {
                "id": int(t),
                "league_id": int(lid),
                "name": tname,
            }
        return self.teams

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


@cli.command()
@click.option("--output", type=click.File('w'), default=sys.stdout)
@click.option("--year", type=int, default=2020)
def teams(output, year):
    bl = bleague2ical4(year)
    json.dump(bl.read_teams(), fp=output, ensure_ascii=False)


@cli.command()
@click.option("--output", type=click.File('w'), default=sys.stdout)
@click.option("--team", type=int, default=727)
@click.option("--year", type=int, default=2020)
def team_schedule(output, year, team):
    bl = bleague2ical4(year)
    bl.read_teams()
    json.dump(bl.team_schedule(team), fp=output, ensure_ascii=False)


@cli.command()
@click.option("--output", type=click.File('w'), default=sys.stdout)
@click.option("--year", type=int, default=2020)
def all_schedule(output, year):
    bl = bleague2ical4(year)
    teams = bl.read_teams()
    scheds = {}
    lmap = {
        2: "B1",
        7: "B2",
    }
    for t, v in teams.items():
        lname = lmap.get(v["league_id"], "B1")
        if lname not in scheds:
            scheds[lname] = []
        scheds[lname].extend(bl.team_schedule(t))
    data = {}
    for k, v in scheds.items():
        data[k] = {"?": v}
    json.dump({"result": "OK", "data": data}, ensure_ascii=False, fp=output)


if __name__ == "__main__":
    cli()
