from fastapi import FastAPI, Query
import glob
import json
import re
import os
from dotenv import load_dotenv
import google.generativeai as genai
from bs4 import BeautifulSoup

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")

app = FastAPI()

with open("selectors.json", "r") as f:
    selectors = json.load(f)


def ask_llm_for_price(soup):
    price_area = soup.find(id="corePriceDisplay_desktop_feature_div") or soup.find(id="centerCol") or soup
    snippet = price_area.get_text(separator=" ", strip=True)[:1500]
    prompt = f"""Neeche diye gaye product page text mein se, sirf MAIN PRODUCT PRICE nikaalo (EMI, coupon, ya discount ka number nahi, actual selling price).
Sirf number return karo (jaise: 64900), koi aur text nahi.

Text: {snippet}"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip(), "llm_healed"
    except Exception:
        return None, "llm_failed"


def extract_field(soup, selector_info):
    strategy = selector_info["strategy"]
    value = selector_info["value"]

    if strategy == "id":
        el = soup.find(attrs={"id": value})
    elif strategy == "class":
        el = soup.find(class_=value)
    else:
        el = None

    if el:
        return el.text.strip(), "primary"

    if selector_info.get("field_name") == "title":
        h1_tags = soup.find_all("h1")
        junk_phrases = ["add to", "cart", "submit", "buy now", "sign in", "customer review", "sponsored"]
        for h1 in h1_tags:
            candidate = h1.text.strip()
            is_junk = any(phrase in candidate.lower() for phrase in junk_phrases)
            if len(candidate) > 15 and not is_junk:
                return candidate, "backup_h1"
        meta = soup.find("meta", attrs={"property": "og:title"})
        if meta and meta.get("content"):
            candidate = meta["content"].strip()
            if len(candidate) > 15:
                return candidate, "backup_meta"

    if selector_info.get("field_name") == "price":
        text = soup.get_text()
        matches = re.findall(r'₹\s?([\d,]+)', text)
        if matches:
            numbers = [int(m.replace(",", "")) for m in matches]
            valid = [n for n in numbers if 500 <= n <= 200000]
            if len(valid) == 1:
                return f"{valid[0]:,}", "backup_regex"
        return ask_llm_for_price(soup)

    return None, "failed"


def load_all_products():
    products = []
    html_files = glob.glob("fixtures/*.html")
    for idx, file_path in enumerate(html_files):
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        title_value, title_source = extract_field(soup, {**selectors["title"], "field_name": "title"})
        price_value, price_source = extract_field(soup, {**selectors["price"], "field_name": "price"})
        products.append({
            "id": idx + 1,
            "file": file_path,
            "title": title_value,
            "title_source": title_source,
            "price": price_value,
            "price_source": price_source,
        })
    return products


CACHED_PRODUCTS = load_all_products()


@app.get("/items")
def get_items(limit: int = Query(default=10, le=50), cursor: int = Query(default=0)):
    page = CACHED_PRODUCTS[cursor: cursor + limit]
    next_cursor = cursor + limit if (cursor + limit) < len(CACHED_PRODUCTS) else None
    return {"items": page, "count": len(page), "total": len(CACHED_PRODUCTS), "next_cursor": next_cursor}


@app.get("/drift")
def get_drift():
    healed = [p for p in CACHED_PRODUCTS if p["title_source"] != "primary" or p["price_source"] != "primary"]
    failed = [p for p in CACHED_PRODUCTS if p["title"] is None or p["price"] is None]
    return {
        "total_products": len(CACHED_PRODUCTS),
        "healed_count": len(healed),
        "failed_count": len(failed),
        "healed_items": [{"file": p["file"], "title_source": p["title_source"], "price_source": p["price_source"]} for p in healed],
        "failed_items": [p["file"] for p in failed],
    }