from pathlib import Path
from facebook_ad_library_scraper import ScraperConfig, scrape
from facebook_ad_library_scraper.core import build_url

url = build_url("mpesa", country="KE")
print(url)

config = ScraperConfig(
    url=url,
    output_dir=Path("output"),
    max_scrolls=2,
    headless=True,
    chrome_version=147,
    store_html=True,
    save_json=True,
    save_csv=False,
)
ads = scrape(config)
print(len(ads), "ads found")
print(ads[0] if ads else "no ads")
