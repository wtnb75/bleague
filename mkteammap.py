import json
import sys


def main():
    res = {}
    for fn in sys.argv[1:]:
        data = json.load(open(fn))
        for name, val in data.get("data").items():
            for num, games in val.items():
                for game in games:
                    t1 = game.get("HomeMediaTeamID")
                    n1 = game.get("HomeTeamShortName")
                    t2 = game.get("AwayMediaTeamID")
                    n2 = game.get("AwayTeamShortName")
                    assert t1 not in res or res.get(t1) == n1
                    assert t2 not in res or res.get(t2) == n2
                    res[t1] = n1
                    res[t2] = n2
    json.dump(res, fp=sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
