import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

URL = "https://www.homes.co.jp/tempo/tokyo/list/"

def scrape():
    r = requests.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")

    stores = []

    for item in soup.select(".shopCassette"):
        name = item.select_one(".shopCassette__name")
        address = item.select_one(".shopCassette__address")

        stores.append({
            "name": name.get_text(strip=True) if name else "",
            "address": address.get_text(strip=True) if address else ""
        })

    return pd.DataFrame(stores)

def ensure_data_dir():
    if os.path.exists("data") and not os.path.isdir("data"):
        os.remove("data")
    if not os.path.isdir("data"):
        os.makedirs("data", exist_ok=True)

def load_previous():
    ensure_data_dir()
    path = "data/stores.csv"
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if set(df.columns) != {"name", "address"}:
                return pd.DataFrame(columns=["name", "address"])
            return df
        except:
            return pd.DataFrame(columns=["name", "address"])
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
