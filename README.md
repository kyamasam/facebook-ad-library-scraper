# Facebook Ad Library Scraper

A Python scraper for Facebook Ad Library search results. It builds Ad Library URLs, opens them with Selenium/undetected-chromedriver, scrolls through results, saves optional HTML snapshots, parses ad cards, removes duplicates, and exports ads to JSON and CSV.

> This project depends on Facebook's public page markup, so parser behavior may need updates if Facebook changes its HTML.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Python API](#python-api)
- [Parameters](#parameters)
- [Output](#output)

## Features

- Build Facebook Ad Library URLs from simple filters
- Scrape with Chrome using `undetected-chromedriver`
- Save HTML snapshots while scrolling
- Parse ad metadata, body text, page info, images, CTAs, and destination URLs
- Export results as `ads.json` and/or `ads.csv`
- Re-parse saved HTML snapshots without opening a browser

## Installation

```bash
pip install facebook-ad-library-scraper
```

For local development:

```bash
git clone https://github.com/samfastone/facebook-ad-library-scraper.git
cd facebook-ad-library-scraper
pip install -e .
```

You also need Google Chrome installed.

## Quick Start

### CLI

```bash
facebook-ad-library-scraper --query "mpesa" --country KE --output-dir output --headless
```

This writes:

- `output/ads.json`
- `output/ads.csv`
- `output/html_snapshots/*.html`

### Python

```python
from pathlib import Path

from facebook_ad_library_scraper.core import ScraperConfig, build_url, scrape

url = build_url("mpesa", country="KE")

config = ScraperConfig(
    url=url,
    output_dir=Path("output"),
    max_scrolls=10,
    headless=True,
    save_json=True,
    save_csv=True,
)

ads = scrape(config)
print(f"{len(ads)} ads found")
```

## Python API

### `build_url(...)`

Builds a Facebook Ad Library search URL.

```python
from facebook_ad_library_scraper.core import build_url

url = build_url(
    query="mpesa",
    country="KE",
    active_status="active",
    media_type="all",
)
```

### `ScraperConfig`

Runtime settings for a scrape.

```python
from pathlib import Path
from facebook_ad_library_scraper.core import ScraperConfig

config = ScraperConfig(
    url="https://www.facebook.com/ads/library/?...",
    output_dir=Path("output"),
    max_scrolls=50,
    headless=False,
)
```

### `scrape(config)`

Runs a full browser scrape, parses ads, removes duplicates, saves configured outputs, and returns a list of ad dictionaries.

```python
from facebook_ad_library_scraper.core import scrape

ads = scrape(config)
```

### `parse_ads(html)`

Parses one HTML string and returns ads found in it.

```python
from facebook_ad_library_scraper.core import parse_ads

ads = parse_ads(html)
```

### `parse_from_dir(html_dir)`

Parses all `.html` files in a snapshot directory.

```python
from pathlib import Path
from facebook_ad_library_scraper.core import parse_from_dir

ads = parse_from_dir(Path("output/html_snapshots"))
```

### `save_json(ads, path)` and `save_csv(ads, path)`

Save parsed ads to disk.

## Parameters

### `build_url`

| Parameter | Default | Description |
| --- | --- | --- |
| `query` | Required | Search keyword or phrase. |
| `country` | `CD` | Two-letter country code. |
| `active_status` | `active` | Ad status: `active`, `inactive`, or `all`. |
| `ad_type` | `all` | Facebook ad type filter. |
| `media_type` | `all` | Media filter such as `image`, `video`, or `all`. |
| `search_type` | `keyword_unordered` | Keyword matching mode. |
| `is_targeted_country` | `False` | Whether to target ads aimed at the selected country. |
| `sort_mode` | `total_impressions` | Sort field used by Facebook. |
| `sort_direction` | `desc` | Sort order: `desc` or `asc`. |
| `languages` | `None` | List of content language codes. |
| `page_ids` | `None` | List of Facebook page IDs. |
| `start_date_min` | `None` | Earliest start date, `YYYY-MM-DD`. |
| `start_date_max` | `None` | Latest start date, `YYYY-MM-DD`. |

### `ScraperConfig`

| Parameter | Default | Description |
| --- | --- | --- |
| `url` | Built-in sample URL | Facebook Ad Library URL to scrape. |
| `output_dir` | `ad_library_output` | Directory for exports and snapshots. |
| `max_scrolls` | `50` | Maximum number of scroll attempts. |
| `scroll_pause` | `3.0` | Base pause between scrolls, in seconds. |
| `snapshot_every` | `5` | Save one HTML snapshot every N scrolls. |
| `headless` | `False` | Run Chrome in headless mode. |
| `chrome_version` | `None` | Chrome major version for `undetected-chromedriver`. |
| `store_html` | `True` | Save HTML snapshots to disk. |
| `save_json` | `True` | Write `ads.json`. |
| `save_csv` | `False` | Write `ads.csv`. |
| `wait_timeout` | `20` | Seconds to wait for ad cards on initial load. |

## Output

Each parsed ad may include:

| Field | Description |
| --- | --- |
| `library_id` | Facebook Ad Library ID. |
| `status` | Current ad status text. |
| `start_date` | Start date shown by Facebook. |
| `page_name` | Advertiser page name. |
| `page_url` | Advertiser page URL. |
| `body` | Main ad text. |
| `destination_url` | Decoded outbound URL when available. |
| `image_url` | First image URL. |
| `images` | All image URLs found for the ad. |
| `cta_domain` | CTA domain text. |
| `cta_headline` | CTA headline text. |
| `cta_button` | CTA button text. |
| `cta_texts` | Raw CTA text blocks. |
| `has_multiple_versions` | Whether Facebook shows multiple versions. |
| `has_whatsapp_cta` | Whether WhatsApp appears in the CTA or body. |




## CLI Usage

Use either a full Facebook Ad Library URL:

```bash
facebook-ad-library-scraper --url "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=KE&q=mpesa"
```

Or build the URL from filters:

```bash
facebook-ad-library-scraper \
  --query "loan" \
  --country KE \
  --active-status active \
  --media-type image \
  --languages en sw \
  --start-date-min 2026-05-01 \
  --output-dir output
```

Parse existing snapshots only:

```bash
facebook-ad-library-scraper --output-dir output --parse-only
```

### CLI Options

| Option | Description |
| --- | --- |
| `--url` | Full Facebook Ad Library URL. When provided, filter flags are ignored. |
| `--query`, `-q` | Search keyword or phrase. |
| `--country` | Two-letter country code. Default: `CD`. |
| `--active-status` | `active`, `inactive`, or `all`. Default: `active`. |
| `--ad-type` | Ad type filter. Default: `all`. |
| `--media-type` | `all`, `image`, `meme`, `image_and_meme`, `video`, or `none`. |
| `--search-type` | `keyword_unordered` or `keyword_exact_phrase`. |
| `--is-targeted-country` | Sets `is_targeted_country=true` in the URL. |
| `--sort-mode` | `total_impressions` or `relevancy_monthly_grouped`. |
| `--sort-direction` | `desc` or `asc`. |
| `--languages` | One or more language codes, e.g. `--languages en fr`. |
| `--page-ids` | One or more Facebook page IDs. |
| `--start-date-min` | Earliest ad start date, `YYYY-MM-DD`. |
| `--start-date-max` | Latest ad start date, `YYYY-MM-DD`. |
| `--output-dir` | Directory for exports and snapshots. Default: `ad_library_output`. |
| `--max-scrolls` | Maximum scroll attempts. Default: `50`. |
| `--scroll-pause` | Seconds to wait between scrolls. Default: `3.0`. |
| `--snapshot-every` | Save HTML every N scrolls. Default: `5`. |
| `--headless` | Run Chrome without a visible browser window. |
| `--chrome-version` | Chrome major version to pass to the driver. |
| `--parse-only` | Parse saved snapshots without scraping again. |
