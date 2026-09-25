#!/bin/zsh
# この Mac から、GitHub の実行を起こします。
#
#   scripts/mac/kick.sh draft   … 木曜 下書きをつくる（draft.yml）
#   scripts/mac/kick.sh post    … 金曜 投稿する（post.yml）
#   scripts/mac/kick.sh today   … 水曜の朝 当日のおしらせ（today.yml）
#
# なぜ要るか
#   GitHub の定時実行（cron）は、混んでいると何時間も遅れ、飛ぶこともあります。
#   2026-09-25（金）は 11:03〜13:09 の4回とも、15時になっても1回も動きませんでした。
#   そこで、この Mac の launchd（~/Library/LaunchAgents/jp.namaoke-kokuti.*.plist）が
#   決まった時刻にこれを動かし、GitHub の実行を起こします。
#   Mac が寝ていた時刻の分は、次に起きたときに1回だけ動きます（launchd の決まり）。
#
# 承認はこれまでどおり GitHub の中で確かめます。ここで承認を省くことはしません。
#
# 二重に出さないために
#   手で起こした実行（workflow_dispatch）は、already_posted.py の判定を使いません。
#   なので、ここで先に logs/開催日.json（当日の分は -today.json）を GitHub で見て、
#   成功した記録があれば起こしません。いま動いている実行があるときも起こしません。

set -u
WHAT=${1:-}
GH=/opt/homebrew/bin/gh
REPO=0443sakura/namaoke-kokuti
LOG="$HOME/Library/Logs/namaoke-kokuti.log"
export TZ=Asia/Tokyo

say() { print -r -- "$(date '+%F %T') [$WHAT] $*" >> "$LOG"; }

case $WHAT in
  draft) WF=draft.yml ;;
  post)  WF=post.yml ;;
  today) WF=today.yml ;;
  *) print "使い方: kick.sh draft|post|today"; exit 2 ;;
esac

# 起きた直後はネットにつながっていないことがあるので、少し待ちます。
for i in {1..20}; do
  $GH api -X GET "repos/$REPO" --jq .name >/dev/null 2>&1 && break
  if (( i == 20 )); then say "GitHub につながりませんでした。今回は見送ります"; exit 1; fi
  sleep 30
done

# 投稿の記録が GitHub にあり、1つでも成功していれば true
posted() {
  $GH api -X GET "repos/$REPO/contents/logs/$1.json" \
    -H "Accept: application/vnd.github.raw" 2>/dev/null \
    | python3 -c 'import json,sys
try: print(any(r["ok"] for r in json.load(sys.stdin)["結果"]))
except Exception: print(False)'
}

if [[ $WHAT == post ]]; then
  # 次の水曜（build_draft.py と同じ考え方。水曜に動いたら翌週の水曜）
  DATE=$(python3 -c 'import datetime as d;t=d.date.today();print(t+d.timedelta((2-t.weekday())%7 or 7))')
  if [[ $(posted "$DATE") == True ]]; then say "$DATE の分はもう出ています"; exit 0; fi
elif [[ $WHAT == today ]]; then
  # 当日の分は水曜にしか出しません（寝ていて木曜に起きたときは見送り）
  if [[ $(date +%u) != 3 ]]; then say "今日は水曜ではないので見送ります"; exit 0; fi
  DATE=$(date +%F)
  if [[ $(posted "$DATE-today") == True ]]; then say "$DATE 当日の分はもう出ています"; exit 0; fi
fi

# GitHub の定時実行がちょうど動いているなら、そちらに任せます。
BUSY=$($GH run list -R $REPO --workflow $WF --json status \
  --jq '[.[]|select(.status!="completed")]|length' 2>/dev/null)
if [[ ${BUSY:-0} != 0 ]]; then say "GitHub 側でいま動いているので任せます"; exit 0; fi

if $GH workflow run $WF -R $REPO >> "$LOG" 2>&1; then
  say "$WF を起こしました"
else
  say "$WF を起こせませんでした"; exit 1
fi
