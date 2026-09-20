"""
homes.co.jp 店舗物件一覧スクレイパー

元のスクレイパーは `.mod-listKks`（PR枠）だけを対象にしていたため、
一覧の大半を占める通常物件（`.mod-mergeBuilding--sale`）を取りこぼしていました。
このバージョンでは以下に対応しています。

- PR枠（.mod-listKks）と通常物件（.mod-mergeBuilding--sale）の両方を抽出
- 1棟に複数区画（部屋）がある物件は、区画ごとに1行として展開
- ページネーションを自動検出し、ページ数のハードコードをやめて全ページを巡回
- 「オンライン相談可」等の注記行を誤って物件行として拾わないようにフィルタ
- サイト負荷軽減のためページ間にランダムウェイトを追加

実行環境: GitHub Actions 等の CI からそのまま実行できるよう、
標準出力へのログと `data/stores.csv` への保存のみで完結します。
"""

import os
import random
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.homes.co.jp/tempo/tokyo/list/?page={}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 15
SLEEP_RANGE = (1.5, 3.0)  # ページ間のウェイト（秒）


def clean_text(el):
    return el.get_text(strip=True) if el else ""


def get_max_page(soup):
    """ページネーション（.mod-listPaging）から最終ページ番号を取得する。
    取得できない場合は1ページのみとみなす。
    """
    pages = [1]
    for a in soup.select(".mod-listPaging a[data-page]"):
        try:
            pages.append(int(a["data-page"]))
        except (ValueError, KeyError):
            pass
    return max(pages)


def parse_pr_items(soup):
    """PR枠（.mod-listKks）の物件を抽出する。"""
    items = []
    for item in soup.select(".mod-listKks"):
        name_el = item.select_one(".bukkenName")
        room_el = item.select_one(".bukkenRoom")
        link_el = item.select_one("a.detailLink")
        price_el = item.select_one("td.price .num")
        address_el = item.select_one("td.address")
        traffic_el = item.select_one("td.traffic")

        items.append(
            {
                "is_pr": True,
                "name": clean_text(name_el),
                "floor": clean_text(room_el),
                "room": "",
                "price_man_yen": clean_text(price_el),
                "space": "",
                "address": clean_text(address_el),
                "traffic": clean_text(traffic_el),
                "building_age": "",
                "structure": "",
                "url": link_el["href"] if link_el and link_el.has_attr("href") else "",
            }
        )
    return items


def parse_building_items(soup):
    """通常物件（.mod-mergeBuilding--sale）を抽出する。
    1棟に複数区画がある場合は区画ごとに行を分ける。
    """
    items = []
    for building in soup.select(".mod-mergeBuilding--sale"):
        name = clean_text(building.select_one(".bukkenName"))

        # 建物共通情報（最寄駅・所在地・築年数・構造）はth/tdのペアで取得
        spec = {}
        for tr in building.select(".bukkenSpec > table tr"):
            for th, td in zip(tr.find_all("th"), tr.find_all("td")):
                spec[clean_text(th)] = clean_text(td)

        traffic = spec.get("最寄駅", "")
        address = spec.get("所在地", "")
        building_age = spec.get("築年数", "")
        structure = spec.get("構造", "")

        # 実データ行は class="prg-building" が付いている行のみ。
        # 「オンライン相談可」等の注記行（prg-memberDataRow）は除外する。
        unit_rows = building.select(".unitSummary tbody tr.prg-building")

        if not unit_rows:
            # 区画テーブルが取得できない場合は建物情報のみ1行として残す
            items.append(
                {
                    "is_pr": False,
                    "name": name,
                    "floor": "",
                    "room": "",
                    "price_man_yen": "",
                    "space": "",
                    "address": address,
                    "traffic": traffic,
                    "building_age": building_age,
                    "structure": structure,
                    "url": building.select_one("a.prg-bukkenNameAnchor")["href"]
                    if building.select_one("a.prg-bukkenNameAnchor")
                    else "",
                }
            )
            continue

        for tr in unit_rows:
            link_el = tr.select_one("td.detail a")
            items.append(
                {
                    "is_pr": False,
                    "name": name,
                    "floor": clean_text(tr.select_one("td.floar")),
                    "room": clean_text(tr.select_one("td.room")),
                    "price_man_yen": clean_text(tr.select_one("td.price .num")),
                    "space": clean_text(tr.select_one("td.space")),
                    "address": address,
                    "traffic": traffic,
                    "building_age": building_age,
                    "structure": structure,
                    "url": link_el["href"]
                    if link_el and link_el.has_attr("href")
                    else tr.get("data-href", ""),
                }
            )
    return items


def scrape_page(page):
    url = BASE_URL.format(page)
    print(f"Fetching page {page}: {url}")

    r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = parse_pr_items(soup) + parse_building_items(soup)
    print(f"  -> {len(items)} 件取得")
    return items, soup


def scrape_all():
    all_items = []

    # 1ページ目を取得し、そこからページネーションを解析して総ページ数を決める
    first_items, first_soup = scrape_page(1)
    all_items.extend(first_items)

    max_page = get_max_page(first_soup)
    print(f"最終ページ: {max_page}")

    for page in range(2, max_page + 1):
        time.sleep(random.uniform(*SLEEP_RANGE))
        items, _ = scrape_page(page)
        all_items.extend(items)

    df = pd.DataFrame(all_items)

    # 見やすいように列順を整える
    columns = [
        "name",
        "floor",
        "room",
        "price_man_yen",
        "space",
        "address",
        "traffic",
        "building_age",
        "structure",
        "is_pr",
        "url",
    ]
    return df[columns] if not df.empty else df


def main():
    df = scrape_all()

    os.makedirs("data", exist_ok=True)
    out_path = "data/stores.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"CSV SAVED → {out_path}")
    print(f"合計 {len(df)} 件")
    print(df.head())


if __name__ == "__main__":
    main()
