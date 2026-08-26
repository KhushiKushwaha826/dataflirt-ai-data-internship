# AI Data Acquisition Intern — Selection Task

## What this does
A self-healing scraper for Amazon product pages (title + price extraction) that
detects structural drift and recovers using layered fallback strategies —
hardcoded backups first, LLM as a last resort — with token discipline built in.

## Architecture
Fetch → Parse (selector registry) → Validate/Detect Drift → Heal → Serve (FastAPI)

- `selectors.json` — versioned selector registry (not hardcoded in Python)
- `scrape1.py` — core extraction + healing pipeline
- `chaos.py` — generates 8 mutation types to simulate real-world page breakage
- `async_scraper.py` — async, concurrent, rate-limited live fetcher
- `api.py` — FastAPI serving layer (`/items`, `/drift`)
- `fixtures/` — saved HTML fixtures used for testing (offline replay)

## Healing strategy
1. **Primary**: use the selector from `selectors.json` (id/class based)
2. **Backup (title)**: scan all `<h1>` tags, reject junk candidates (e.g. "Add to cart"), accept the first plausible one (>15 chars, no junk phrases)
3. **Backup (title)**: fall back to `og:title` meta tag
4. **Backup (price)**: regex-extract ₹ values, accept only if exactly one candidate falls in a realistic range (₹500–₹200,000)
5. **LLM (last resort)**: only triggered when regex is ambiguous (0 or multiple candidates). Sends a pruned ~1,500-character snippet (not the full page) to Gemini, asking specifically for the main product price.

This ordering matters: the LLM is never on the request path unless every deterministic method has failed, keeping cost near zero for the common case.

## Chaos testing
`chaos.py` generates 8 mutation types against a real saved product page: id renamed, og:title removed, element wrapped in extra div, price class renamed, price symbol altered, attributes reordered, extra attribute injected, price element nested. Result: 6/8 mutations were silently absorbed by BeautifulSoup's deep-tree search (structural changes don't break `.find()`), 2/8 genuinely broke extraction and were recovered — one via the `h1` backup, one via the LLM. See `metrics.md` for full breakdown.

## Known limitations & honest trade-offs
- **Golden-record validation is simplified.** Rather than a full 50-record ~95% agreement check, I used rule-based sanity checks (length, junk-phrase rejection) as a proxy. With more time I'd build a proper golden-record set and compare candidate similarity against it before promoting a healed selector.
- **Live scraping was blocked by Amazon's CAPTCHA at 21/21 requests** when using plain async HTTP (httpx) with semaphore-based concurrency. This is a real, documented limitation — not a hidden failure. The extraction/healing pipeline itself is fetch-source-agnostic and was fully validated against saved fixtures instead. Scaling to 300 live pages would need session/cookie persistence or headless-browser rendering (Playwright) — a clear next step.
- **Sample size is small (11 fixtures)** due to the above constraint and time available. The pipeline design (selector registry, layered healing, drift threshold) does not change with scale — only the fetch layer would need hardening.

## What I'd add with more time
1. Real golden-record comparison (50 verified records, similarity scoring)
2. Playwright-based fetching with persistent sessions for the live scraper
3. Proper token counting via the Gemini SDK's usage metadata instead of word-count estimates
4. Deploy the FastAPI service to AWS/GCP free tier with a live URL

## How to run
pip install fastapi uvicorn httpx beautifulsoup4 python-dotenv google-generativeai
python chaos.py
python scrape1.py
uvicorn api:app --reload


## Hardest bug I fixed
The title backup (`<h1>` fallback) initially grabbed the *first* `<h1>` tag on the page, which on Amazon pages is often unrelated UI text like "Add to your order" — not the product title. Fixed by scanning *all* `<h1>` tags and validating each candidate against length + junk-phrase rules before accepting one. This taught me that a fallback returning *a* value isn't the same as it returning the *right* value — validation matters more than having a fallback.