import asyncio
import httpx
import os

URLS = [
    "https://www.amazon.in/dp/B0G1SBLX7W",
    "https://www.amazon.in/dp/B0G1SD7BXT",
    "https://www.amazon.in/dp/B0FQFVX9ZZ",
    "https://www.amazon.in/dp/B0GWLV615M",
    "https://www.amazon.in/dp/B0FN7QTRPY",
    "https://www.amazon.in/dp/B0H1BMBX9R",
    "https://www.amazon.in/dp/B0GZ7Q6K2D",
    "https://www.amazon.in/dp/B0FQF2ZJWT",
    "https://www.amazon.in/dp/B0FQFNQ5LX",
    "https://www.amazon.in/dp/B0FQFQF6D1",
    "https://www.amazon.in/dp/B0FJFVBSF4",
    "https://www.amazon.in/dp/B0FN7RN9TH",
    "https://www.amazon.in/dp/B0FQG1K1FM",
    "https://www.amazon.in/dp/B0H8NLDMTH",
    "https://www.amazon.in/dp/B0H6HY2C29",
    "https://www.amazon.in/dp/B0G827QJ7S",
    "https://www.amazon.in/dp/B0GS5Y7QBF",
    "https://www.amazon.in/dp/B0GZGBXWJZ",
    "https://www.amazon.in/dp/B0H8NW369M",
    "https://www.amazon.in/dp/B0H1WY466V",
    "https://www.amazon.in/dp/B0H1WXCRHT",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9"
}

SEMAPHORE = asyncio.Semaphore(3)


async def fetch_one(client, url, index):
    async with SEMAPHORE:
        try:
            response = await client.get(url, headers=HEADERS, follow_redirects=True)

            # agar signin/captcha pe redirect hua, skip kr dungi
            if "ap/signin" in str(response.url) or "captcha" in str(response.url).lower():
                print(f"[{index}] BLOCKED (redirected to signin/captcha): {url}")
                return

            os.makedirs("fixtures_live", exist_ok=True)
            asin = url.split("/dp/")[-1]
            path = f"fixtures_live/product_{asin}.html"

            with open(path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"[{index}] Saved: {path} (status: {response.status_code})")

        except Exception as e:
            print(f"[{index}] ERROR fetching {url}: {e}")

    
        await asyncio.sleep(2)


async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        tasks = [fetch_one(client, url, i + 1) for i, url in enumerate(URLS)]
        await asyncio.gather(*tasks)

    print(f"\nDone. Total URLs attempted: {len(URLS)}")


if __name__ == "__main__":
    asyncio.run(main())
