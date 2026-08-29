# AI Data Acquisition Intern — Selection Task

## About this project

This project is a scraper that can collect product data (title and price) from
Amazon pages, and can fix itself automatically when the page structure changes.
This is called "self-healing". I built this for the AI Data Acquisition Intern
selection task.

The main idea is simple: websites change their design from time to time. When
that happens, a normal scraper breaks and stops working. My scraper is built to
notice when it breaks, and try different ways to fix itself before giving up.

## How the whole system works (step by step)

1. **Fetch** — the program gets the HTML of a product page (either from a saved
   file, or from the internet using an async scraper I built).
2. **Parse** — it looks at the HTML and tries to find the product title and
   price using saved rules called "selectors".
3. **Check for drift** — after trying to get the data from many pages, the
   program checks how many pages failed. If too many failed, it shows a warning
   that says "drift detected". This means something changed on the website.
4. **Heal** — if the normal selector fails on a single page, the program does
   not just give up. It tries backup methods one by one, and only uses an AI
   model (LLM) as the very last option.
5. **Serve** — all the collected data can be viewed through a small API I built
   using FastAPI, so anyone can check the results without running the Python
   script manually.

## Files in this project and what each one does

- **`selectors.json`** — This file stores the rules for finding the title and
  price on a page (for example, which HTML id or class to look for). I kept
  these rules in a separate file instead of writing them directly inside the
  Python code. This way, if the rule needs to change, I only edit this file,
  not the whole program.

- **`scrape1.py`** — This is the main file. It reads the selector rules,
  opens the saved HTML files, and tries to extract the title and price from
  each one. If the normal way does not work, it tries backup methods. It also
  prints a summary at the end showing how many pages worked and how many did
  not.

- **`chaos.py`** — This file is used only for testing. It takes one real saved
  product page and creates 8 different "broken" versions of it. Each broken
  version changes something small, like renaming an id, removing a tag, or
  moving an element inside an extra div. This copies what happens in real life
  when a website updates its design. I use these broken files to check if my
  healing logic actually works.

- **`async_scraper.py`** — This file tries to fetch many product pages from
  Amazon at the same time (instead of one by one), using something called
  "async" programming. It also adds a small delay between requests so it does
  not send too many requests too fast. I explain further down why this part
  did not fully work as expected.

- **`api.py`** — This file uses FastAPI to create two web addresses (called
  endpoints) that show the scraped data:
  - `/items` — shows the list of products, with paging support (so you can see
    10 products at a time instead of all at once).
  - `/drift` — shows how many products needed healing, and which method was
    used to fix each one.

- **`fixtures/`** — This folder has the saved HTML pages I used for testing.
  Some are real Amazon pages I saved manually, and some are the broken
  versions created by `chaos.py`.

- **`metrics.md`** — This file has the numbers: how many pages worked, how
  many needed healing, and how many tokens the AI model used.

## How the healing logic works (in detail)

For every field (title and price), the program tries methods in this order,
and stops as soon as one of them works:

**For the title:**
1. First, try the main selector saved in `selectors.json` (this is the
   fastest and cheapest method, so it is tried first).
2. If that fails, look at every `<h1>` tag on the page. Amazon pages usually
   have many `<h1>` tags (not just one), so the program checks all of them,
   not only the first one. It also rejects any text that looks like junk
   (for example, text like "Add to cart" or "Sign in"), and only accepts a
   candidate if it is longer than 15 characters and does not match any junk
   phrase.
3. If that also fails, look for a meta tag called `og:title`, which many
   websites use to describe the page for social media sharing. This often
   still has the correct product name even if the main title tag is broken.

**For the price:**
1. First, try the main selector.
2. If that fails, search the whole page text for anything that looks like a
   price (a rupee symbol followed by numbers). Sometimes a page has more than
   one price-like number on it (like EMI options or bank offers), so the
   program only trusts this method if there is exactly one number that falls
   in a normal price range (between 500 and 200,000).
3. If the page has zero matches, or more than one possible price, the program
   does not guess. Instead, it sends a small piece of the page (not the whole
   page) to an AI model (Gemini) and asks it to identify the correct price.

The important part here is the order. The AI model is only used when every
other method has already failed. This keeps the system fast and cheap most of
the time, because AI calls cost more (in time and in money/tokens) than
regular code.

## Why I check candidates before trusting them

At the start, I made a version where the backup method just took the first
`<h1>` tag on the page and used it directly. This caused a real problem: on
one broken test page, it picked up the text "Add to your order" as the
product title, because that happened to be the first `<h1>` tag on the page.
This is wrong data, but the program did not know it was wrong.

I fixed this by adding simple checks before accepting any backup value:
- The text must be longer than 15 characters (short text is usually not a
  real product title).
- The text must not match common junk phrases like "add to", "cart",
  "sign in", "submit", "sponsored".

After adding these checks, the same broken page correctly found the real
title, using the AI model instead of a wrong guess. This taught me an
important lesson: getting *some* value back is not the same as getting the
*correct* value. A fallback method needs to be checked, not blindly trusted.

## Chaos testing — what I tested and what happened

`chaos.py` creates 8 different broken versions of one real product page:

1. Renamed the title's id attribute
2. Removed the `og:title` meta tag
3. Wrapped the title element inside an extra div
4. Renamed the price's class attribute
5. Changed the currency symbol in the price
6. Reordered the HTML attributes on the title tag
7. Added an extra random attribute to the title tag
8. Wrapped the price element inside an extra nested span

Out of these 8 tests, 6 did not actually break the extraction. This is
because the library I use to read HTML (BeautifulSoup) searches through the
entire page structure, not just the top level, so small changes like
reordering attributes or adding an extra wrapper did not stop it from finding
the element. Only 2 out of 8 mutations actually broke extraction:
- The id-renamed version broke the title extraction, and was fixed using the
  `<h1>` backup method.
- The class-renamed version broke the price extraction, and was fixed using
  the AI model, because the regular text search found more than one possible
  price on the page.

## The FastAPI part

I built two endpoints:

- **`GET /items`** — returns the scraped products. It supports `limit` (how
  many results to return) and `cursor` (where to start from), so a client
  application does not need to load every product at once.
- **`GET /drift`** — returns a summary of how many products needed healing,
  and exactly which backup method was used for each one (for example,
  `backup_h1` or `llm_healed`). This is useful because in a real system,
  someone monitoring the scraper would want to know when and how often
  healing is happening, not just whether the final data looks fine.

## What I tried for scaling to more pages (and what went wrong)

The task mentions scraping around 300 pages. To work towards that, I built
`async_scraper.py`, which:
- Uses `httpx` with async/await, so it can send multiple requests at the same
  time instead of one at a time.
- Uses a semaphore to limit this to only 3 requests running at once, so it
  does not send too many requests too fast.
- Waits 2 seconds between requests as a politeness delay.
- Saves every successful response as an HTML file, automatically, without
  needing to manually save each page from the browser.

I tested this on 21 real Amazon product links. The result was that all 21
requests were blocked by Amazon and redirected to a CAPTCHA page
(`validateCaptcha`), instead of returning the real product page.

**Why this happened:** Amazon has strong bot-detection. A real browser
carries cookies, a login session, and other signals that make a request look
"human". A plain HTTP request from a Python script (even with a realistic
browser header) does not have any of that, so it gets flagged quickly,
especially when multiple requests are sent close together.

**What this means for the project:** the part of my code that extracts data
from HTML (the parsing and healing logic) does not depend on how the HTML
was obtained. It works the same whether the HTML came from a manually saved
file or from a live web request. Because of this, I was able to fully build
and test the entire healing system using saved fixture pages, even though the
live automated fetching did not succeed within the time I had. If I had more
time, the next step would be to either slow down the requests even further,
add real cookies/session handling, or use a tool like Playwright, which
controls an actual browser instead of sending plain requests.

## Token usage summary

- Out of the pages tested, the AI model (LLM) was called only once. Every
  other page was resolved using the free, non-AI methods (main selector or
  backup rules).
- Each AI call used a small amount of text (a cut-down piece of the page,
  not the whole HTML), which came to roughly 60-80 tokens total for that one
  call.
- If the program sent the *entire* page's HTML to the AI model every single
  time (instead of only when needed, and only a small snippet), it would use
  somewhere around 10,000-15,000 tokens per page, since a full Amazon page's
  HTML is very large. My approach avoids this by (1) only calling the AI
  model as a last resort, and (2) only sending a small relevant snippet, not
  the full page. This is roughly a 95% or more reduction in token usage
  compared to that naive approach. Full details are in `metrics.md`.

## Honest limitations of this project

I want to be clear about what is not fully finished, instead of hiding it:

- **Golden record validation is simplified.** The task description talks
  about testing a new selector against 50 verified "golden" records and only
  accepting it if there is about 95% agreement. I did not build this exact
  system. Instead, I used simpler rule-based checks (length and junk-word
  filtering) as a stand-in for this. With more time, I would create a real
  set of verified records and measure agreement properly before trusting any
  healed selector.
 - **Only 11 fixture pages were used for testing**, not the full ~300 pages
  mentioned in the task, because of the CAPTCHA blocking problem explained
  above.
- **The async scraper works technically, but could not get past Amazon's bot
  protection** in the time available.

## What I would add if I had more time

1. Build a real golden-record comparison system instead of simple rule-based
   checks.
2. Add cookie/session handling or use Playwright for the live scraper, to
   get past CAPTCHA blocking.
3. Get the exact token count from the Gemini API response directly, instead
   of estimating it by counting words.
4. Deploy the FastAPI app to AWS or GCP free tier so it has a public URL.

## How to run this project

Install the required packages:

pip install fastapi uvicorn httpx beautifulsoup4 python-dotenv google-generativeai


Then run these commands in order:

python chaos.py
python scrape1.py
uvicorn api:app --reload


After the last command, open these links in a browser:
- `http://127.0.0.1:8000/items`
- `http://127.0.0.1:8000/drift`

## The hardest bug I fixed

The hardest bug was the wrong title problem explained above (the "Add to your
order" issue). It looked like the code was working, because it was returning
*something* instead of `None`. But the value was completely wrong. This bug
was tricky because there was no error message — the program did not crash,
it just quietly returned incorrect data. I only noticed it by manually
checking the printed output line by line, instead of only looking at the
success/failure count. This taught me to always double-check what a fallback
actually returns, not just whether it returns something.