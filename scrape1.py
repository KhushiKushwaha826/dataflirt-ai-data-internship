import glob
import json
import re
import os
from dotenv import load_dotenv
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- LLM setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")
with open("selectors.json", "r") as f:
    selectors = json.load(f)

html_files = glob.glob("fixtures/*.html")
print(f"Total files found: {len(html_files)}")


def ask_llm_for_price(soup):
    """Jab regex confuse ho jaye, LLM se poochho asli price kaunsa hai"""
    price_area = soup.find(id="corePriceDisplay_desktop_feature_div") or soup.find(id="centerCol") or soup
    snippet = price_area.get_text(separator=" ", strip=True)[:1500]

    prompt = f"""Neeche diye gaye product page text mein se, sirf MAIN PRODUCT PRICE nikaalo (EMI, coupon, ya discount ka number nahi, actual selling price).
Sirf number return karo (jaise: 64900), koi aur text nahi.

Text: {snippet}"""

    try:
        response = model.generate_content(prompt)
        price_text = response.text.strip()
        input_tokens = len(prompt.split())
        output_tokens = len(price_text.split())
        print(f"    [LLM call] ~{input_tokens + output_tokens} tokens used")
        return price_text, "llm_healed"
    except Exception as e:
        print(f"    [LLM error] {e}")
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


all_products = []

for file_path in html_files:
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    title_value, title_source = extract_field(soup, {**selectors["title"], "field_name": "title"})
    price_value, price_source = extract_field(soup, {**selectors["price"], "field_name": "price"})

    product = {
        "file": file_path,
        "title": title_value,
        "title_source": title_source,
        "price": price_value,
        "price_source": price_source,
    }

    all_products.append(product)
    print(product)

print("\n--- Summary ---")
print(f"Successfully extracted: {sum(1 for p in all_products if p['title'])}/{len(all_products)}")

print("\n--- Drift Check ---")
null_titles = sum(1 for p in all_products if p["title"] is None)
null_prices = sum(1 for p in all_products if p["price"] is None)

null_rate_title = null_titles / len(all_products)
null_rate_price = null_prices / len(all_products)

THRESHOLD = 0.2

print(f"Title null rate: {null_rate_title:.0%}")
print(f"Price null rate: {null_rate_price:.0%}")

if null_rate_title > THRESHOLD:
    print("⚠️ DRIFT DETECTED in title extraction")
if null_rate_price > THRESHOLD:
    print("⚠️ DRIFT DETECTED in price extraction")