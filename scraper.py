import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

URL = "https://www.homes.co.jp/tempo/tokyo/list/"

def scrape():
    r = requests.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")

    stores = []

    for item in soup.select(".cassetteitem"):
        name = item.select_one(".cassetteitem_content-title").get_text(strip=True)
        address = item.select_one(".cassetteitem_detail-col").get_text(strip=True)
        stores.append({"name": name, "address": address})

    return pd.DataFrame(stores)

def ensure_data_dir():
    # data が「フォルダ」かどうかを確認する
    if os.path.exists("data") and not os.path.isdir("data"):
        # data がファイルとして存在している場合 → 削除してフォルダを作る
        os.remove("data")
    if not os.path.isdir("data"):
        os.makedirs("data", exist_ok=True)

def load_previous():
    ensure_data_dir()
    path = "data/stores.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=["name", "address"])

def save(df):
    ensure_data_dir()
    df.to_csv("data/stores.csv", index=False)

def diff(new, old):
    ensure_data_dir()

    merged = new.merge(old, how="outer", indicator=True)
    added = merged[merged["_merge"] == "left_only"]
    removed = merged[merged["_merge"] == "right_only"]

    diff_df = pd.concat([
        added.assign(change="added"),
        removed.assign(change="removed")
    ])

    diff_df.to_csv("data/diff.csv", index=False)

def main():
    new = scrape()
    old = load_previous()
    save(new)
    diff(new, old)

if __name__ == "__main__":
    main()
