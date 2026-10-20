#!/bin/zsh
# kick.sh を、この Mac の launchd に登録します（何回動かしても同じ結果になります）。
#
#   水 07:45  today … 当日のおしらせ
#   木 10:55  draft … 下書きをつくる
#   金 10:55  post  … 投稿する
#   毎日 9:30／12:30／15:30／18:30  remind … 出ていなければ画面に知らせる（remind.sh）
#
# GitHub の定時実行（11:03 など）より少し前にしてあります。こちらが先に出せば、
# あとから動いた GitHub の分は「もう出した」と判断して止まります。
#
# やめるとき:  scripts/mac/install.sh remove

set -eu
[[ ${1:-} == remove ]] && REMOVE=1 || REMOVE=0
HERE=${0:A:h}
AGENTS="$HOME/Library/LaunchAgents"
UID_=$(id -u)
mkdir -p "$AGENTS" "$HOME/Library/Logs"
chmod +x "$HERE/kick.sh" "$HERE/remind.sh" "$HERE/fbkit.sh"

# 名前 曜日(0=日) 時 分
JOBS=("today 3 7 45" "draft 4 10 55" "post 5 10 55")

for job in $JOBS; do
  set -- ${=job}
  LABEL="jp.namaoke-kokuti.$1"
  PLIST="$AGENTS/$LABEL.plist"
  launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null || true
  if (( REMOVE )); then rm -f "$PLIST"; print "やめました: $LABEL"; continue; fi
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$HERE/kick.sh</string><string>$1</string></array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>$2</integer>
    <key>Hour</key><integer>$3</integer>
    <key>Minute</key><integer>$4</integer>
  </dict>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/namaoke-kokuti.log</string>
</dict>
</plist>
EOF
  launchctl bootstrap "gui/$UID_" "$PLIST"
  print "登録しました: $LABEL"
done

# 出ていないときに知らせる係（remind.sh）。毎日4回。出ていれば何も出しません。
LABEL="jp.namaoke-kokuti.remind"
PLIST="$AGENTS/$LABEL.plist"
launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null || true
if (( REMOVE )); then rm -f "$PLIST"; print "やめました: $LABEL"; exit 0; fi
TIMES=""
for hm in "9 30" "12 30" "15 30" "18 30"; do
  set -- ${=hm}
  TIMES+="    <dict><key>Hour</key><integer>$1</integer><key>Minute</key><integer>$2</integer></dict>
"
done
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$HERE/remind.sh</string></array>
  <key>StartCalendarInterval</key>
  <array>
$TIMES  </array>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/namaoke-kokuti.log</string>
</dict>
</plist>
EOF
launchctl bootstrap "gui/$UID_" "$PLIST"
print "登録しました: $LABEL"
