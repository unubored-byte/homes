from playwright.sync_api import sync_playwright
import pandas as pd
import os

URL = "https://www.homes.co.jp/tempo/tokyo/list/"

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        # 取得した HTML を保存（最重要）
        html = page.content()
        with open("page.html", "w", encoding="utf-8") as f:
            f.write(html)

        # ここではまだセレクタを決めない（HTML を見てから決める）
        return pd.DataFrame([])

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

    # new が空なので diff は空で OK
    diff_df = pd.DataFrame(columns=["name", "address", "change"])
    diff_df.to_csv("data/diff.csv", index=False)

def main():
    new = scrape()
    old = load_previous()
    save(new)
    diff(new, old)

if __name__ == "__main__":
    main()
