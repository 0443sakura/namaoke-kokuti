#!/bin/zsh
# 告知がまだ出ていないとき、この Mac の画面に「まだ出てないですよ」と出します。
#
#   scripts/mac/remind.sh        … 確かめて、出ていなければ知らせる
#   scripts/mac/remind.sh test   … 試しに1回知らせる
#
# なぜ要るか
#   2026-10-02（金）は承認（approve）を忘れ、告知が 10/6（火）まで出ませんでした。
#   さくらさんから「違う作業をしていても、まだ出てないと教えてほしい」と頼まれて作りました。
#   Claude のアプリを閉じていても、launchd が動かします（install.sh で登録）。
#
# 見るのは GitHub の記録だけです。ここから投稿したり、承認を入れたりはしません。
#   ・承認がまだ          → 「承認してください」と出して、ボタンで Issue を開く
#   ・承認ずみなのに、金曜13時を過ぎても出ていない → 「まだ出ていません」と出す
#   ・水曜 9時を過ぎても当日のストーリーが出ていない → 同じく知らせる
# 画面の真ん中に出して、ボタンを押すまで消えません（通知の端っこだと見のがすため）。

set -u
GH=/opt/homebrew/bin/gh
REPO=0443sakura/namaoke-kokuti
LOG="$HOME/Library/Logs/namaoke-kokuti.log"
export TZ=Asia/Tokyo

say() { print -r -- "$(date '+%F %T') [remind] $*" >> "$LOG"; }

# 画面の真ん中に出します。「ページを開く」を押すと Chrome で開きます。
alert() {  # alert 見出し 本文 URL
  local ans
  ans=$(osascript - "$1" "$2" <<'EOF' 2>/dev/null
on run argv
  display alert (item 1 of argv) message (item 2 of argv) buttons {"あとで", "ページを開く"} default button "ページを開く"
  return button returned of result
end run
EOF
)
  say "知らせました: $1（押したボタン: ${ans:-なし}）"
  [[ $ans == ページを開く ]] && open -a "Google Chrome" "$3"
}

ISSUES="https://github.com/$REPO/issues"

if [[ ${1:-} == test ]]; then
  alert "【生バンドカラオケ】試しのお知らせ" "これが見えれば、準備はできています。告知が出ていないときに、こうしてお知らせします。" "$ISSUES"
  exit 0
fi

# 起きた直後はネットにつながっていないことがあるので、少し待ちます。
for i in {1..20}; do
  $GH api -X GET "repos/$REPO" --jq .name >/dev/null 2>&1 && break
  if (( i == 20 )); then say "GitHub につながりませんでした。今回は見送ります"; exit 1; fi
  sleep 30
done

# 投稿の記録が GitHub にあり、1つでも成功していれば True（kick.sh と同じ）
posted() {
  $GH api -X GET "repos/$REPO/contents/logs/$1.json" \
    -H "Accept: application/vnd.github.raw" 2>/dev/null \
    | python3 -c 'import json,sys
try: print(any(r["ok"] for r in json.load(sys.stdin)["結果"]))
except Exception: print(False)'
}

WD=$(date +%u)   # 1=月 … 3=水 … 7=日
HOUR=$(date +%H)

if [[ $WD == 3 ]]; then
  # 水曜は開催日です。当日の朝のストーリーだけ見ます。
  DATE=$(date +%F)
  (( 10#$HOUR < 9 )) && exit 0
  if [[ $(posted "$DATE-today") == True ]]; then say "$DATE 当日の分は出ています"; exit 0; fi
  alert "【生バンドカラオケ】本日のストーリーが、まだ出ていません" \
    "今日の朝の Instagram ストーリーが出ていません。Claude に「当日のストーリーが出ていない」と話しかけてください。" "$ISSUES"
  exit 0
fi

# 次の水曜（build_draft.py と同じ考え方）
DATE=$(python3 -c 'import datetime as d;t=d.date.today();print(t+d.timedelta((2-t.weekday())%7 or 7))')
LABEL=$(python3 -c "import datetime as d;x=d.date.fromisoformat('$DATE');print(f'{x.month}/{x.day}（水）')")

if [[ $(posted "$DATE") == True ]]; then say "$DATE の分は出ています"; exit 0; fi

# その週の Issue（タイトルは github_issue.py の title_for() と同じ）
NUM=$($GH issue list -R $REPO --state all --label 告知 -L 10 --json number,title \
  --jq ".[] | select(.title == \"$LABEL の告知 — 承認をお願いします\") | .number" 2>/dev/null | head -1)
if [[ -z $NUM ]]; then say "$LABEL の Issue はまだありません（下書き前）"; exit 0; fi
URL="$ISSUES/$NUM"

# 承認の判定は github_issue.py の cmd_approval() と同じ決まりです。
# 持ち主のコメントだけを新しいほうから見て、先に当たったほうで決めます。
STATE=$($GH api "repos/$REPO/issues/$NUM/comments?per_page=100" 2>/dev/null | python3 -c '
import json, re, sys
APPROVE = re.compile(r"\bapprove\b|承認|\bok\b", re.I)
CANCEL = re.compile(r"やめ|中止|取り消|取消|キャンセル|\bcancel\b|\bstop\b", re.I)
for c in reversed(json.load(sys.stdin)):
    if c["user"]["login"].lower() != "0443sakura":
        continue
    body = re.sub(r"```.*?```", "", c["body"] or "", flags=re.S)
    if CANCEL.search(body): print("cancel"); break
    if APPROVE.search(body): print("approved"); break
else:
    print("waiting")')

case $STATE in
  cancel)
    say "$LABEL は「やめ」と書かれています。知らせません" ;;
  waiting)
    if (( WD == 4 )); then WHEN="承認が入れば、金曜の11時ごろに出ます。"
    elif (( WD == 5 )); then WHEN="もう金曜です。承認が入れば、すぐ出せます。"
    else WHEN="告知が遅れています。今からでも出せます。"; fi
    alert "【生バンドカラオケ】$LABEL の告知が、まだ出てないですよ" \
      "承認（approve）がまだです。$WHEN

「ページを開く」を押して、いちばん下のコメント欄に approve と書いてください。今週お休みなら やめ と書けば、もう聞きません。" "$URL" ;;
  approved)
    # 金曜の11時に出るはずなので、13時までは待ちます。
    if (( WD == 4 )) || { (( WD == 5 )) && (( 10#$HOUR < 13 )); }; then
      say "$LABEL は承認ずみ。金曜に出るのを待ちます"; exit 0
    fi
    alert "【生バンドカラオケ】$LABEL の告知が、まだ出てないですよ" \
      "承認は入っていますが、まだ Instagram に出ていません。Claude に「告知が出ていない」と話しかけてください。" "$URL" ;;
  *)
    say "コメントを読めませんでした" ;;
esac
