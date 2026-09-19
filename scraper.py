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

def load_previous():
    path = "data/stores.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=["name", "address"])

def save(df):
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/stores.csv", index=False)

def diff(new, old):
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
