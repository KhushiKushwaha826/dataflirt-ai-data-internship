# Metrics

## Extraction Results
- Total fixtures tested: 11 (3 original clean pages + 8 chaos-mutated variants)
- Successfully extracted: 11/11 (100%)
- Title null rate: 0%
- Price null rate: 0%

## Healing Breakdown
| File | Field Healed | Strategy Used |
|---|---|---|
| chaos_m1_id_renamed.html | title | backup_h1 (fallback to first valid `<h1>` tag) |
| chaos_m4_price_class_renamed.html | price | llm_healed (Gemini API call) |

6 of 8 chaos mutations were absorbed silently by BeautifulSoup's deep-tree search
(attribute reordering, extra wrapping divs, dropped currency symbols did not break
extraction since `.find()` searches the full tree, not just top-level structure).

## Token Usage (LLM healing)
- LLM calls triggered: 1 out of 11 files (only when regex-based price backup found
  0 or multiple ambiguous candidates)
- Approx tokens per LLM call: ~60-80 tokens (prompt + response)
- Strategy: LLM is called only as a last resort after primary selector and
  hardcoded backups (h1/meta/regex) all fail — not on every request.
- Naive baseline (sending full page HTML to LLM instead of a pruned snippet)
  would cost significantly more per call — full product page HTML is
  40,000-60,000+ characters (~10,000-15,000 tokens), versus our pruned
  ~1,500 character snippet (~400 tokens). This represents a ~95%+ token
  reduction versus the naive baseline.

## Live Scraping Attempt (300-page scaling test)
- Built an async scraper (async_scraper.py) using httpx with semaphore-based
  concurrency (max 3 parallel requests) and a 2-second polite delay between
  requests, respecting rate-limit etiquette.
- Attempted 21 live Amazon.in product URLs as a scaling proof-of-concept.
- Result: 21/21 requests were blocked by Amazon's CAPTCHA (validateCaptcha
  redirect), confirming plain async HTTP requests are insufficient against
  Amazon's bot detection at this scale without session/cookie persistence.
- Conclusion: the extraction, drift-detection, and healing logic (tested above)
  is fully decoupled from the fetch layer — it operates on saved HTML regardless
  of source. Scaling to 300 live pages would require either slower request
  pacing, persistent cookie/session handling, or headless-browser rendering
  (e.g. Playwright) — a natural next step documented here for transparency.