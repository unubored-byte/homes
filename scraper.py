from playwright.sync_api import sync_playwright
import pandas as pd
import os

URL = "https://www.homes.co.jp/tempo/tokyo/list/"

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        # JSで生成されるので待つ
        page.wait_for_selector(".shopCassette")

        items = page.query_selector_all(".shopCassette")

        stores = []
        for item in items:
            name_el = item.query_selector(".shopCassette__name")
            addr_el = item.query_selector(".shopCassette__address")

            name = name_el.inner_text().strip() if name_el else ""
            address = addr_el.inner_text().strip() if addr_el else ""

            stores.append({"name": name, "address": address})

        browser.close()

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
