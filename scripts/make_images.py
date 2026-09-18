#!/usr/bin/env python3
"""告知画像に、その週の開催日とホストのお名前を焼き込みます。

  python3 scripts/make_images.py --draft drafts/2026-09-23.json

  images/weekly/2026-09-23/story-1.jpg
  images/weekly/2026-09-23/story-2.jpg
の2枚ができます。post.py はこちらがあれば、こちらを投稿します。

なぜ必要か
  もとの story-1.jpg には「本日！」と書いてあります。告知は金曜に出して、
  開催は翌週の水曜なので、見た人が「今日だ」と勘違いします。
  そこを開催日に差し替え、下に「次回は◯月◯日（◯）」の帯を足しています。

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
    """「次回は◯月◯日（◯）」のオレンジの帯。"""
    x0, y0, x1, y1 = box
    ImageDraw.Draw(im).rounded_rectangle(box, radius=(y1 - y0) // 4, fill=ORANGE)
    _put(im, f"次回は {date.month}月{date.day}日（{WEEK[date.weekday()]}）",
         (x0 + (x1 - x0) * .04, y0 + (y1 - y0) * .16,
          x1 - (x1 - x0) * .04, y1 - (y1 - y0) * .16), WHITE)


def _hosts_card(im, members, box):
    """「次回のホスト」の白い札。お顔が隠れない高さに置きます。"""
    x0, y0, x1, y1 = box
    card = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        box, radius=40, fill=WHITE + (247,), outline=ORANGE + (255,), width=9)
    im.paste(Image.alpha_composite(im.convert("RGBA"), card).convert("RGB"), (0, 0))

    _put(im, "次回のホスト", (x0 + 40, y0 + 22, x1 - 40, y0 + 76), ORANGE)
    labels = [f"{m['name']}（{PART.get(m['instrument'], m['instrument'])}）"
              for m in members]
    rows = [labels[i:i + 2] for i in range(0, len(labels), 2)]  # 2人ずつ並べます
    h = (y1 - 28 - (y0 + 86)) / len(rows)
    for i, row in enumerate(rows):
        _put(im, "／".join(row),
             (x0 + 40, y0 + 86 + i * h, x1 - 40, y0 + 80 + (i + 1) * h), INK)


def _story1(date, members):
    """1枚目。「本日！」を消して、見出しを組み直します。"""
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

    # 空いた上に「毎週水曜日は！」。Instagram の名前表示に隠れない高さです。
    _put(im, "毎週水曜日は！", (100, 178, 980, 302), ORANGE, angle=1.5)
    d.line([(120, 325), (960, 309)], fill=YELLOW, width=22)

    _hosts_card(im, members, [80, 1110, 1000, 1340])
    _date_banner(im, date, [40, 1652, 1040, 1876])
    return im


def _story2(date):
    """2枚目。下の白い余白に帯を足すだけです。"""
    im = Image.open(ROOT / "images" / "story-2.jpg").convert("RGB")
    _date_banner(im, date, [40, 1700, 1040, 1900])
    return im


# ── 入口 ──────────────────────────────────────────────────────

def build(draft, out_dir):
    date = dt.date.fromisoformat(draft["開催日"])
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for name, im in (("story-1.jpg", _story1(date, draft["メンバー"])),
                     ("story-2.jpg", _story2(date))):
        path = out_dir / name
        im.save(path, quality=92)
        made.append(path)

    # フィード用は、まだ日付を入れていません（上に余白がなく、同じ形にできません）。
    # 中身が変わらないものを毎週コピーすると記録が太るので、ここには置きません。
    # post.py は、無ければもとの images/feed-*.jpg を使います。
    return made


def main():
    ap = argparse.ArgumentParser(description="告知画像に開催日とホスト名を焼き込みます。")
    ap.add_argument("--draft", required=True, help="drafts/YYYY-MM-DD.json")
    ap.add_argument("--out", help="出力先（既定は images/weekly/開催日/）")
    args = ap.parse_args()

    if not FONT_PATH.exists():
        sys.exit(f"フォントがありません: {FONT_PATH}")

    draft = json.loads(pathlib.Path(args.draft).read_text(encoding="utf-8"))
    out_dir = pathlib.Path(args.out) if args.out else \
        ROOT / "images" / "weekly" / draft["開催日"]

    for path in build(draft, out_dir):
        print(f"  {path.relative_to(ROOT)}")
    print(f"開催日 {draft['開催日']} の画像をつくりました。")


if __name__ == "__main__":
    main()
