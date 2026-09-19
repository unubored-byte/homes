from playwright.sync_api import sync_playwright
import pandas as pd
import os

URL = "https://www.homes.co.jp/tempo/tokyo/list/"

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        # Homes の店舗一覧は cassetteitem で構成されている
        page.wait_for_selector(".cassetteitem")

        items = page.query_selector_all(".cassetteitem")

        stores = []
        for item in items:
            name_el = item.query_selector(".cassetteitem_content-title")
            addr_el = item.query_selector(".cassetteitem_detail-col")

            name = name_el.inner_text().strip() if name_el else ""
            address = addr_el.inner_text().strip() if addr_el else ""

            stores.append({"name": name, "address": address})

        browser.close()

    return pd.DataFrame(stores)
