#! /bin/sh
python=python3.4

cd $(dirname $0)
year=2019
mode=${1-minute}

case "$mode" in
  daily)
    ${python} blg2019.py maychange --input ${year}.json && \
       ${python} blg2019.py json --output ${year}.json
    ;;
  minute)
    ${python} blg2019.py maychange --input ${year}.json --no-ingame && \
       ${python} blg2019.py json --output ${year}.json
    ;;
  *)
    echo "Usage: $0 [daily|minute]"
    ;;
esac
