#!/usr/bin/env python3
"""告知画像に、その週の開催日とホストのお名前を焼き込みます。

告知用（金曜に出す分）と、当日用（水曜の朝に出す分）の2組を作ります。

  python3 scripts/make_images.py --draft drafts/2026-09-23.json
      images/weekly/2026-09-23/story-1.jpg   見出し「毎週水曜日は！」
      images/weekly/2026-09-23/story-2.jpg   帯「次回は 9月23日（水）」
      images/weekly/2026-09-23/feed-1.jpg    上をフィードの形に縮めたもの

  python3 scripts/make_images.py --draft drafts/2026-09-23.json --on-the-day
      images/weekly/2026-09-23/today/story-1.jpg  見出し「本日9月23日！」
      images/weekly/2026-09-23/today/story-2.jpg  もとのまま（帯を入れません）

post.py は、あればこちらを投稿します。

なぜ必要か
  もとの story-1.jpg には「本日！」と書いてあります。告知は金曜に出して、
  開催は翌週の水曜なので、見た人が「今日だ」と勘違いします。
  そこを開催日に差し替え、下に「次回は◯月◯日（◯）」の帯を足しています。
  逆に当日の朝に出す分は、ほんとうに「本日」なので、そう書きます。

当日用はストーリーの2枚だけです（さくらさんの決定 2026-09-19）。
フィードは金曜の1回だけにして、同じ会の告知が並ばないようにしています。

当日用には、下のオレンジの帯を**入れません**（さくらさんの指示 2026-09-19）。
日付は1枚目の見出し「本日◯月◯日！」に入っているので、それで足ります。

★ 下の座標は、images/story-1.jpg と story-2.jpg を実際に測った値です。
  もとの画像を差し替えたら、ここも測り直してください。ずれると字が重なります。
"""

import argparse
import datetime as dt
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "MPLUSRounded1c-Bold.ttf"

# ポスターから拾った色です。
CREAM = (252, 236, 213)   # 地の色
ORANGE = (243, 88, 20)    # 見出しの色
YELLOW = (251, 184, 10)   # 下線の色
WHITE = (255, 255, 255)
INK = (45, 28, 20)        # お名前の色

WEEK = "月火水木金土日"

# 楽器の略し方です。さくらさんの指定（2026-09-18）。
PART = {
    "sax": "sax",
    "piano": "p",
    "bass": "b",
    "drums": "ds",
    "guitar": "g",
    "vib": "vib",
}


# ── 文字を描く道具 ────────────────────────────────────────────

def _fit(text, w, h, cap=900):
    """幅 w・高さ h に収まる、一番大きな字の大きさを探します。"""
    lo, hi = 10, cap
    while lo < hi:
        mid = (lo + hi + 1) // 2
        l, t, r, b = ImageFont.truetype(str(FONT_PATH), mid).getbbox(text)
        if r - l <= w and b - t <= h:
            lo = mid
        else:
            hi = mid - 1
    return ImageFont.truetype(str(FONT_PATH), lo)


def _put(img, text, box, color, angle=0.0):
    """箱の中央に文字を置きます。

    4倍の大きさで描いてから縮めています。そのままだと、
    斜めにしたときに輪郭が階段状になるためです。
    """
    x0, y0, x1, y1 = box
    scale = 4
    font = _fit(text, int((x1 - x0) * scale), int((y1 - y0) * scale))
    l, t, r, b = font.getbbox(text)
    layer = Image.new("RGBA", (r - l + 40, b - t + 40), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((20 - l, 20 - t), text, font=font, fill=color + (255,))
    if angle:
        layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    layer = layer.resize((layer.width // scale, layer.height // scale), Image.LANCZOS)
    img.paste(layer,
              (int((x0 + x1) / 2 - layer.width / 2),
               int((y0 + y1) / 2 - layer.height / 2)),
              layer)


# ── 部品 ──────────────────────────────────────────────────────

def _date_banner(im, date, box):
    """「次回は◯月◯日（◯）」のオレンジの帯。

    金曜の告知にだけ付けます。当日用には付けません（2026-09-19 さくらさんの指示）。
    """
    x0, y0, x1, y1 = box
    ImageDraw.Draw(im).rounded_rectangle(box, radius=(y1 - y0) // 4, fill=ORANGE)
    _put(im, f"次回は {date.month}月{date.day}日（{WEEK[date.weekday()]}）",
         (x0 + (x1 - x0) * .04, y0 + (y1 - y0) * .16,
          x1 - (x1 - x0) * .04, y1 - (y1 - y0) * .16), WHITE)


def _hosts_card(im, members, box, on_the_day=False):
    """ホストのお名前の白い札。お顔が隠れない高さに置きます。"""
    x0, y0, x1, y1 = box
    card = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        box, radius=40, fill=WHITE + (247,), outline=ORANGE + (255,), width=9)
    im.paste(Image.alpha_composite(im.convert("RGBA"), card).convert("RGB"), (0, 0))

    title = "本日のホストメンバー" if on_the_day else "次回のホスト"
    _put(im, title, (x0 + 40, y0 + 22, x1 - 40, y0 + 76), ORANGE)
    labels = [f"{m['name']}（{PART.get(m['instrument'], m['instrument'])}）"
              for m in members]
    rows = [labels[i:i + 2] for i in range(0, len(labels), 2)]  # 2人ずつ並べます
    h = (y1 - 28 - (y0 + 86)) / len(rows)
    for i, row in enumerate(rows):
        _put(im, "／".join(row),
             (x0 + 40, y0 + 86 + i * h, x1 - 40, y0 + 80 + (i + 1) * h), INK)


def _story1(date, members, on_the_day=False):
    """1枚目。もとの「本日！」を消して、見出しを組み直します。"""
    im = Image.open(ROOT / "images" / "story-1.jpg").convert("RGB")
    d = ImageDraw.Draw(im)

    # 「完全生演奏！」のかたまりを、いったん切り取っておきます。
    block = im.crop((405, 305, 912, 502))

    # もとの見出しを地の色で消します（「本日！」「完全生演奏！」「／」）。
    d.rectangle([124, 300, 402, 510], fill=CREAM)
    d.rectangle([405, 305, 985, 502], fill=CREAM)
    # 左の「＼」も消します。左下の♪を傷つけない太さにしてあります。
    d.line([(58, 406), (125, 506)], fill=CREAM, width=46)

    # 「完全生演奏！」を、画像の真ん中に貼り直します（122px 左へ）。
    im.paste(block, (283, 305))
    # 一緒に動いてしまった小さな飾りを消します。
    d.rectangle([730, 305, 772, 352], fill=CREAM)

    # 空いた上に見出し。Instagram の名前表示に隠れない高さです。
    # 当日の朝に出す分だけ、日付を入れて「本日」と言い切ります。
    headline = f"本日{date.month}月{date.day}日！" if on_the_day else "毎週水曜日は！"
    _put(im, headline, (100, 178, 980, 302), ORANGE, angle=1.5)
    d.line([(120, 325), (960, 309)], fill=YELLOW, width=22)

    _hosts_card(im, members, [80, 1110, 1000, 1340], on_the_day)
    # 当日用は帯を入れません。日付は上の見出しに入っています。
    if not on_the_day:
        _date_banner(im, date, [40, 1652, 1040, 1876])
    return im


def _story2(date, on_the_day=False):
    """2枚目。下の白い余白に帯を足すだけです。

    当日用は帯を入れないので、もとの画像がそのまま出ます。
    書いてある文字（「毎週水曜日開催！」「20:00〜23:00」）は、当日に見ても
    おかしくないので、そのままで困りません。

    それでもここで1枚書き出します。書かずにおくと post.py が
    images/weekly/開催日/story-2.jpg（「次回は…」の帯つき）を拾ってしまうためです。
    """
    im = Image.open(ROOT / "images" / "story-2.jpg").convert("RGB")
    if not on_the_day:
        _date_banner(im, date, [40, 1700, 1040, 1900])
    return im


def _feed1(story1):
    """フィード用の1枚目（1080x1350）。

    縦が短いので、ストーリー1枚目の中身をそのまま縮めて収めます。
    左右に薄い余白ができますが、中身は何も欠けません
    （さくらさんが 2026-09-18 に案Aを選ばれました）。
    ストーリーから組むので、デザインがずれることはありません。
    """
    src = story1.crop((0, 168, 1080, 1886))   # 見出しの上から帯の下まで
    w = int(src.width * 1350 / src.height)
    im = Image.new("RGB", (1080, 1350), CREAM)
    im.paste(src.resize((w, 1350), Image.LANCZOS), ((1080 - w) // 2, 0))
    return im


# ── 入口 ──────────────────────────────────────────────────────

def build(draft, out_dir, on_the_day=False):
    date = dt.date.fromisoformat(draft["開催日"])
    out_dir.mkdir(parents=True, exist_ok=True)
    story1 = _story1(date, draft["メンバー"], on_the_day)

    sheets = [("story-1.jpg", story1), ("story-2.jpg", _story2(date, on_the_day))]
    # 当日はストーリーだけ出すので、フィード用は作りません。
    if not on_the_day:
        sheets.append(("feed-1.jpg", _feed1(story1)))

    made = []
    for name, im in sheets:
        path = out_dir / name
        im.save(path, quality=92)
        made.append(path)

    # フィード用の2枚目は、もとのままで誤解を招きません（「毎週水曜日開催！」）。
    # 中身の変わらないものを毎週コピーすると記録が太るので、ここには置きません。
    # post.py は、無ければもとの images/feed-2.jpg を使います。
    return made


def main():
    ap = argparse.ArgumentParser(description="告知画像に開催日とホスト名を焼き込みます。")
    ap.add_argument("--draft", required=True, help="drafts/YYYY-MM-DD.json")
    ap.add_argument("--out", help="出力先（既定は images/weekly/開催日/）")
    ap.add_argument("--on-the-day", action="store_true",
                    help="当日の朝に出す分を作る（見出しが「本日◯月◯日！」になります）")
    args = ap.parse_args()

    if not FONT_PATH.exists():
        sys.exit(f"フォントがありません: {FONT_PATH}")

    draft = json.loads(pathlib.Path(args.draft).read_text(encoding="utf-8"))
    base = ROOT / "images" / "weekly" / draft["開催日"]
    out_dir = pathlib.Path(args.out) if args.out else \
        (base / "today" if args.on_the_day else base)

    for path in build(draft, out_dir, args.on_the_day):
        # --out でリポジトリの外に出したときは、そのままの場所を出します。
        try:
            path = path.relative_to(ROOT)
        except ValueError:
            pass
        print(f"  {path}")
    kind = "当日用" if args.on_the_day else "告知用"
    print(f"開催日 {draft['開催日']} の{kind}の画像をつくりました。")


if __name__ == "__main__":
    main()
