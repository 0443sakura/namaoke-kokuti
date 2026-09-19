#!/usr/bin/env python3
"""この開催日は、もう投稿ずみかどうかを答えます。

  python3 scripts/already_posted.py --draft drafts/2026-09-23.json
      posted=true  … もう出しました（1つでも成功した記録があります）
      posted=false … まだです

  python3 scripts/already_posted.py --draft drafts/2026-09-23.json --on-the-day
      当日の朝の分について、同じことを答えます。
      見る記録が logs/2026-09-23-today.json に変わるだけです。
      金曜に出していても、当日の分は「まだ」と答えます。

なぜ必要か
  GitHub の定時実行は、混んでいると遅れたり、飛ばされたりします。
  2026-09-18 に、木曜の分が5時間28分おくれて動きました。金曜の分は飛びました。
  そこで金曜は何回か起こすことにしました（11:03 / 11:33 / 12:07 / 13:09）。
  何回起きても**投稿するのは最初の1回だけ**にするための判定です。

  記録は logs/開催日.json です。post.py が投稿のたびに書きます。

手で動かしたときは、この判定を使いません。
出し直したいことがあるためです（2026-09-18 に実際に出し直しました）。
"""

import argparse
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def posted(draft_path, on_the_day=False):
    draft = json.loads(pathlib.Path(draft_path).read_text(encoding="utf-8"))
    stem = draft["開催日"] + ("-today" if on_the_day else "")
    log = ROOT / "logs" / f"{stem}.json"
    if not log.exists():
        return False
    # 全部だめだったときは「まだ」とみなします。次の回で拾い直せるようにです。
    return any(r["ok"] for r in json.loads(log.read_text(encoding="utf-8"))["結果"])


def main():
    ap = argparse.ArgumentParser(description="この開催日を投稿ずみか答えます。")
    ap.add_argument("--draft", required=True, help="drafts/YYYY-MM-DD.json")
    ap.add_argument("--on-the-day", action="store_true",
                    help="当日の朝の分について答える")
    args = ap.parse_args()

    answer = "true" if posted(args.draft, args.on_the_day) else "false"
    print(f"posted={answer}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"posted={answer}\n")


if __name__ == "__main__":
    main()
