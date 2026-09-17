#!/usr/bin/env python3
"""はじめの一回だけ動かします。投稿に使う「鍵」を4つそろえるための道具です。

Meta の画面で取った短い有効期限のトークンを、期限のない長いトークンに交換し、
Facebook ページのID と Instagram のID もまとめて調べます。

  python3 scripts/setup_token.py

聞かれるのは3つです（セットアップ手順.md の 4 に、どこで取るかが書いてあります）。
  ・アプリID
  ・アプリシークレット
  ・ユーザーアクセストークン（短いもの）

★入力した値は画面に出ませんし、どのファイルにも保存しません。
　そろった鍵は、そのまま GitHub の Secrets に入れられます（画面に出さずに済みます）。
"""

import getpass
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta_api  # noqa: E402

REPO = "0443sakura/namaoke-kokuti"


def ask(label, secret=True):
    value = (getpass.getpass(f"{label}: ") if secret else input(f"{label}: ")).strip()
    if not value:
        raise SystemExit(f"{label} が空でした。やり直してください。")
    return value


def repo_name():
    """origin の URL から「持ち主/名前」を取り出します。分からなければ既定値です。"""
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return REPO
    name = url.rsplit("github.com", 1)[-1].lstrip(":/").removesuffix(".git")
    return name if name.count("/") == 1 else REPO


def put_secrets(secrets, repo):
    """gh コマンドで GitHub の Secrets に直接入れます。値は画面に出しません。"""
    if not shutil.which("gh"):
        return "gh コマンドが見つかりませんでした"
    for name, value in secrets.items():
        # 値は標準入力で渡します。コマンドの履歴にも残りません。
        result = subprocess.run(["gh", "secret", "set", name, "--repo", repo],
                                input=value, capture_output=True, text=True)
        if result.returncode != 0:
            return result.stderr.strip() or f"{name} を登録できませんでした"
        print(f"  ✓ {name}")
    return ""


def show(secrets):
    print("\n" + "=" * 62)
    print("次の3つを GitHub の Secrets に登録してください。")
    print("（登録のしかたは セットアップ手順.md の 5 にあります）")
    print("=" * 62)
    for name, value in secrets.items():
        print(f"\n{name}\n  {value}")
    print("\n" + "=" * 62)
    print("★ このトークンは、お店の投稿ができる鍵です。")
    print("　 人に見せたり、チャットに貼ったりしないでください。")
    print("　 この画面は、貼り終えたら閉じてください。")
    print("=" * 62)


def main():
    print(__doc__)
    if "--help" in sys.argv or "-h" in sys.argv:
        return  # 説明だけ読みたいときは、ここで終わります
    app_id = ask("アプリID（数字）", secret=False)
    app_secret = ask("アプリシークレット（打っても画面には出ません）")
    short_token = ask("ユーザーアクセストークン（打っても画面には出ません）")

    print("\n1) 期限のない長いトークンに交換しています…")
    long_user = meta_api.get("oauth/access_token", {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }, short_token)["access_token"]

    print("2) Facebook ページを探しています…")
    pages = meta_api.get("me/accounts", {"fields": "id,name,access_token"}, long_user).get("data", [])
    if not pages:
        raise SystemExit(
            "Facebook ページが1つも見つかりませんでした。\n"
            "セットアップ手順.md の 1（ページを作る）が済んでいるか、\n"
            "トークンを取るときに pages_show_list の許可を入れたかを確かめてください。"
        )

    if len(pages) == 1:
        page = pages[0]
    else:
        print("\n  どのページに投稿しますか？")
        for i, p in enumerate(pages, 1):
            print(f"    {i}. {p['name']}")
        page = pages[int(ask("  番号", secret=False)) - 1]

    print(f"3) 「{page['name']}」につながった Instagram を探しています…")
    linked = meta_api.get(page["id"], {"fields": "instagram_business_account{id,username}"},
                          page["access_token"]).get("instagram_business_account")
    if not linked:
        raise SystemExit(
            f"「{page['name']}」に Instagram がつながっていません。\n"
            "セットアップ手順.md の 2（プロアカウントに切り替えてページと連携）を先にどうぞ。"
        )

    secrets = {
        "META_PAGE_ID": page["id"],
        "IG_USER_ID": linked["id"],
        "META_PAGE_TOKEN": page["access_token"],
    }

    print("\n" + "=" * 62)
    print("鍵がそろいました。")
    print("=" * 62)
    print(f"  Facebook ページ : {page['name']}")
    print(f"  Instagram       : @{linked['username']}")

    repo = repo_name()
    answer = input(f"\nこのまま {repo} に登録しますか？　y を打って Enter: ").strip().lower()
    if answer in ("y", "yes"):
        print()
        error = put_secrets(secrets, repo)
        if not error:
            print("\n登録できました。トークンは画面に出していません。")
            print("残りは META_PLACE_ID ひとつです。")
            print("  python3 scripts/find_location.py を動かすと出ます。")
            return
        print(f"\n登録できませんでした（{error}）")
        print("下の値を、GitHub の画面から手で貼ってください。")

    show(secrets)
    print("\nMETA_PLACE_ID は scripts/find_location.py を動かすと出ます。")


if __name__ == "__main__":
    try:
        main()
    except meta_api.GraphError as e:
        raise SystemExit(f"\n❌ うまくいきませんでした。\n   {e.detail}")
