import time
import requests
import cachez
from lxml.html import fromstring
import logging

cachez.set_persist_folder("/tmp/cachez")


@cachez.persisted(hours=1)
def geturl(url, args):
    logging.info("fetching %s %s", url, args)
    return requests.get(url, args).content


class bleague2ical2:
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
            "B1リーグ": self.merge(b1, {
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
            "B2リーグ": self.merge(b2, {
                "event": 7,
                "club": "",
                "setuFrom": 1,
                "setuTo": 36,
            }),
            "B2残留プレーオフ": self.merge(b2, {"event": 9}),
            "B2プレーオフ": self.merge(b2, {"event": 8}),
            "B2・B3入替戦": self.merge(b2, {"event": 17}),
        }

    def text1(self, tree, cls):
        found = tree.find_class(cls)
        return found[0].text_content().strip()

    def readone(self, args):
        res = []
        tree = fromstring(geturl(self.baseurl, args))
        for games in tree.find_class("game_list"):
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
        return res


def main():
    b = bleague2ical2()
    print(b.readAll())


if __name__ == "__main__":
    main()
