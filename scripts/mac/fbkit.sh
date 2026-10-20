#!/bin/zsh
# 当日の朝、Instagram にストーリーが出たら、Facebook のストーリーズ用を
# デスクトップに用意して（画像2枚・重ねる文字・文章）、この Mac の画面に「こちらを」と出します。
# 「開く」で4つを選んだフォルダと AirDrop の窓を開くので、iPhone へドラッグで送れます。
#
#   scripts/mac/fbkit.sh 2026-10-21         … 用意して知らせる（その日1回だけ）
#   scripts/mac/fbkit.sh 2026-10-21 again   … もう知らせた日でも、もう1回出す
#
# なぜ要るか
#   Facebook は自動で出せないので、さくらさんが手で上げます。
#   Issue のコメントにも一式がありますが、探しに行かなくても済むよう、
#   Instagram に出たところで画面に出してほしいと頼まれました（2026-10-21）。
#
# 動かすのは kick.sh today（出たのを見届けてから）と remind.sh（水曜、まだ知らせていなければ）。
# ここから投稿はしません。GitHub から画像と設定を取ってくるだけです。

set -u
DATE=${1:?使い方: fbkit.sh 開催日 [again]}
GH=/opt/homebrew/bin/gh
REPO=0443sakura/namaoke-kokuti
LOG="$HOME/Library/Logs/namaoke-kokuti.log"
HERE=${0:A:h}
ROOT=${HERE:h:h}
export TZ=Asia/Tokyo
export LANG=ja_JP.UTF-8   # launchd から動くと空なので、pbcopy の日本語が化けないように

say() { print -r -- "$(date '+%F %T') [fbkit] $*" >> "$LOG"; }

# 同じ日に二度出さないための印です。
STAMP_DIR="$HOME/Library/Application Support/namaoke-kokuti"
STAMP="$STAMP_DIR/fbkit-$DATE"
[[ -e $STAMP && ${2:-} != again ]] && exit 0

MD=$(python3 -c "import datetime as d;x=d.date.fromisoformat('$DATE');print(f'{x.month}月{x.day}日')")
DIR="$HOME/Desktop/Facebook用-$MD-本日"
mkdir -p "$DIR"

# 画像は Instagram に出したものと同じ（images/weekly/開催日/today/）です。
for n in 1 2; do
  OUT="$DIR/${n}枚目.jpg"
  if ! $GH api -X GET "repos/$REPO/contents/images/weekly/$DATE/today/story-$n.jpg" \
       -H "Accept: application/vnd.github.raw" > "$OUT" 2>/dev/null \
     || [[ $(file -b --mime-type "$OUT") != image/jpeg ]]; then
    say "$DATE の画像 $n 枚目を取ってこられませんでした"
    rm -f "$OUT"; exit 1
  fi
done

# 重ねる文字は post.py の facebook_story_texts() で作ります（Issue のコメントと同じもの）。
# 料金や時間の原典は data/config.json なので、GitHub の最新を見ます。
#
# 文章（キャプション）は、その週の下書き drafts/開催日.json の facebook の分です。
# 当日なので「次回は」を「本日は」にします（post.py の on_the_day_caption()）。
# 承認のコメントで本文を差し替えていた週はそちらが出ているので、
# 判定は github_issue.py の cmd_approval() をそのまま使います（同じ決まりを二つ持たないため）。
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
$GH api -X GET "repos/$REPO/contents/data/config.json" -H "Accept: application/vnd.github.raw" > "$TMP/config.json" 2>/dev/null
$GH api -X GET "repos/$REPO/contents/drafts/$DATE.json" -H "Accept: application/vnd.github.raw" > "$TMP/draft.json" 2>/dev/null
( cd "$TMP" && GITHUB_TOKEN=$($GH auth token) GITHUB_REPOSITORY=$REPO \
    python3 "$ROOT/scripts/github_issue.py" approval --draft draft.json >/dev/null 2>&1 )
CAPTION=$(python3 - "$ROOT/scripts" "$TMP" "$DIR" <<'PYEOF'
import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
import post
tmp, out = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
t1, t2 = post.facebook_story_texts(json.loads((tmp / "config.json").read_text(encoding="utf-8")))
(out / "重ねる文字.txt").write_text(f"1枚目に重ねる文字\n{t1}\n\n2枚目に重ねる文字\n{t2}\n", encoding="utf-8")
caption = json.loads((tmp / "draft.json").read_text(encoding="utf-8"))["captions"]["facebook"]
approval = tmp / ".approval.json"
if approval.exists():
    caption = json.loads(approval.read_text(encoding="utf-8")).get("override", {}).get("facebook") or caption
caption = post.on_the_day_caption(caption)
(out / "文章.txt").write_text(caption + "\n", encoding="utf-8")
print(caption)
PYEOF
) || { say "重ねる文字・文章を作れませんでした"; exit 1; }

mkdir -p "$STAMP_DIR"; touch "$STAMP"

ans=$(osascript - "${DIR:t}" <<'EOF' 2>/dev/null
on run argv
  display alert "【生バンドカラオケ】Instagram に本日のストーリーが出ました" message "Facebook 用は、こちらです。

デスクトップの「" & (item 1 of argv) & "」に、画像2枚（1枚目 → 2枚目の順）、重ねる文字、文章を入れました。

「開く」を押すと、4つを選んだ状態でフォルダが開き、AirDrop の窓も開きます。選んであるものを、AirDrop の窓の iPhone へドラッグすれば送れます。文章はコピーもしてあります。

上げる前に、お店のページ（ミュージックカフェsakura）になっているか見てください。" buttons {"あとで", "開く"} default button "開く"
  return button returned of result
end run
EOF
)
say "知らせました: $DATE（押したボタン: ${ans:-なし}）"
if [[ $ans == 開く ]]; then
  print -rn -- "$CAPTION" | pbcopy
  # 4つを選んだ状態で Finder に出します（そのまま AirDrop の窓へドラッグできるように）。
  osascript - "$DIR" <<'EOF' >/dev/null 2>&1
on run argv
  set f to POSIX file (item 1 of argv) as alias
  tell application "Finder"
    open f
    select (every file of f)
    activate
  end tell
end run
EOF
  open /System/Library/CoreServices/Finder.app/Contents/Applications/AirDrop.app
fi
