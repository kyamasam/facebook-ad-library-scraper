"""Core scraping, parsing, and export helpers."""

from __future__ import annotations

import csv
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup


DEFAULT_URL = (
    "https://www.facebook.com/ads/library/"
    "?active_status=active"
    "&ad_type=all"
    "&country=CD"
    "&is_targeted_country=false"
    "&media_type=all"
    "&q=m-pesa%20investment"
    "&search_type=keyword_unordered"
    "&sort_data[mode]=total_impressions"
    "&sort_data[direction]=desc"
    "&start_date[min]=2026-05-06"
)

AD_LIBRARY_BASE = "https://www.facebook.com/ads/library/"


def build_url(
    query: str,
    country: str = "CD",
    active_status: str = "active",
    ad_type: str = "all",
    media_type: str = "all",
    search_type: str = "keyword_unordered",
    is_targeted_country: bool = False,
    sort_mode: str = "total_impressions",
    sort_direction: str = "desc",
    languages: Optional[list[str]] = None,
    page_ids: Optional[list[str]] = None,
    start_date_min: Optional[str] = None,
    start_date_max: Optional[str] = None,
) -> str:
    """Build a Facebook Ad Library URL from individual search parameters."""
    from urllib.parse import quote, urlencode

    parts: list[tuple[str, str]] = [
        ("active_status", active_status),
        ("ad_type", ad_type),
        ("country", country),
        ("is_targeted_country", str(is_targeted_country).lower()),
        ("media_type", media_type),
        ("q", query),
        ("search_type", search_type),
        ("sort_data[mode]", sort_mode),
        ("sort_data[direction]", sort_direction),
    ]

    if languages:
        for i, lang in enumerate(languages):
            parts.append((f"content_languages[{i}]", lang))

    if page_ids:
        for i, pid in enumerate(page_ids):
            parts.append((f"page_ids[{i}]", pid))

    if start_date_min:
        parts.append(("start_date[min]", start_date_min))
    if start_date_max:
        parts.append(("start_date[max]", start_date_max))

    return AD_LIBRARY_BASE + "?" + urlencode(parts)


@dataclass
class ScraperConfig:
    """Runtime settings for a scrape session."""

    url: str = DEFAULT_URL
    output_dir: Path = Path("ad_library_output")
    max_scrolls: int = 50
    scroll_pause: float = 3.0
    snapshot_every: int = 5
    headless: bool = False
    chrome_version: Optional[int] = None
    store_html: bool = True
    save_json: bool = True
    save_csv: bool = False
    wait_timeout: int = 20

    @property
    def html_dir(self) -> Path:
        return self.output_dir / "html_snapshots"

    @property
    def output_csv(self) -> Path:
        return self.output_dir / "ads.csv"

    @property
    def output_json(self) -> Path:
        return self.output_dir / "ads.json"


def make_driver(headless: bool = False, chrome_version: Optional[int] = None) -> Any:
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,900")
    options.add_argument("--lang=fr-FR")

    kwargs = {"options": options}
    if chrome_version is not None:
        kwargs["version_main"] = chrome_version
    return uc.Chrome(**kwargs)


def scroll_and_collect(driver: Any, config: Optional[ScraperConfig] = None) -> list[str]:
    """Scroll the page and collect HTML snapshots."""

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    config = config or ScraperConfig()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    if config.store_html:
        config.html_dir.mkdir(parents=True, exist_ok=True)

    driver.get(config.url)
    print("Waiting for initial load...")

    try:
        WebDriverWait(driver, config.wait_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "._7jyh"))
        )
    except Exception:
        print("Warning: timed out waiting for ._7jyh cards. Page may not have loaded correctly.")

    time.sleep(3)

    snapshots = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    for _ in range(config.max_scrolls):
        scroll_by = random.randint(800, 1200)
        driver.execute_script(f"window.scrollBy(0, {scroll_by});")

        pause = config.scroll_pause + random.uniform(0, 1.5)
        time.sleep(pause)

        scroll_count += 1

        if scroll_count % config.snapshot_every == 0:
            html = driver.page_source
            snapshots.append(html)
            if config.store_html:
                snap_path = config.html_dir / f"snapshot_{scroll_count:04d}.html"
                snap_path.write_text(html, encoding="utf-8")
                print(f"Scroll {scroll_count}: snapshot saved -> {snap_path}")

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print(f"No more content after scroll {scroll_count}. Stopping.")
            html = driver.page_source
            snapshots.append(html)
            if config.store_html:
                (config.html_dir / f"snapshot_{scroll_count:04d}_final.html").write_text(
                    html,
                    encoding="utf-8",
                )
            break
        last_height = new_height

    final_html = driver.page_source
    snapshots.append(final_html)
    if config.store_html:
        (config.html_dir / "snapshot_final.html").write_text(final_html, encoding="utf-8")

    return snapshots


def parse_ads(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    ads = []

    for card in soup.select("._7jyh"):
        ad = {}

        for span in card.select("span"):
            text = span.get_text(strip=True)
            if text.startswith("Library ID:"):
                ad["library_id"] = text.replace("Library ID:", "").strip()
            elif text.startswith("Started running on"):
                ad["start_date"] = text.replace("Started running on", "").strip()

        status_el = card.select_one("span.x13fj5qh")
        ad["status"] = status_el.get_text(strip=True) if status_el else None

        page_link = card.select_one("img._8nqq + div a")
        if page_link:
            ad["page_name"] = page_link.get_text(strip=True)
            ad["page_url"] = page_link.get("href", "")
        else:
            ad["page_name"] = None
            ad["page_url"] = None

        body_el = card.select_one("._7jyr [style*='white-space: pre-wrap']")
        ad["body"] = body_el.get_text(strip=True) if body_el else None

        multiple_versions_el = card.find(string=lambda t: t and "multiple versions" in t.lower())
        ad["has_multiple_versions"] = multiple_versions_el is not None

        dest_link = card.select_one("a[href*='l.facebook.com']")
        if dest_link:
            raw = dest_link.get("href", "")
            try:
                query = parse_qs(urlparse(raw).query)
                ad["destination_url"] = unquote(query.get("u", [""])[0])
            except Exception:
                ad["destination_url"] = raw
        else:
            ad["destination_url"] = None

        carousel = card.select_one("[data-testid='ad-library-ad-carousel-container']")
        if carousel:
            slides = carousel.select("._7jy-")
            ad["images"] = []
            for slide in slides:
                img = slide.select_one("div.x1ywc1zp img")
                if img and img.get("src"):
                    ad["images"].append(img.get("src"))
            ad["image_url"] = ad["images"][0] if ad["images"] else None
        else:
            img_el = card.select_one("div.x1ywc1zp img")
            ad["image_url"] = img_el.get("src") if img_el else None
            ad["images"] = [ad["image_url"]] if ad["image_url"] else []

        if carousel:
            slide_ctas = []
            for slide in carousel.select("._7jy-"):
                blocks = slide.select("._4ik4._4ik5")
                texts = [b.get_text(strip=True) for b in blocks if b.get_text(strip=True)]
                if texts:
                    slide_ctas.append(texts)
            ad["cta_texts"] = slide_ctas
            ad["cta_domain"] = slide_ctas[0][0] if slide_ctas and slide_ctas[0] else None
            ad["cta_headline"] = slide_ctas[0][1] if slide_ctas and len(slide_ctas[0]) > 1 else None
            ad["cta_button"] = slide_ctas[0][-1] if slide_ctas and len(slide_ctas[0]) > 2 else None
        else:
            if dest_link:
                cta_blocks = dest_link.select("._4ik4._4ik5")
                cta_texts = [b.get_text(strip=True) for b in cta_blocks if b.get_text(strip=True)]
                btn_el = dest_link.select_one("div.x2lah0s div[role='button'] div.x8t9es0")
                cta_button = btn_el.get_text(strip=True) if btn_el else None
            else:
                cta_texts = []
                cta_button = None
            ad["cta_texts"] = cta_texts
            ad["cta_domain"] = cta_texts[0] if len(cta_texts) > 0 else None
            ad["cta_headline"] = cta_texts[1] if len(cta_texts) > 1 else None
            ad["cta_button"] = cta_button

        flat_ctas = (
            ad["cta_texts"]
            if ad["cta_texts"] and isinstance(ad["cta_texts"][0], str)
            else [text for sub in ad["cta_texts"] for text in sub]
            if ad["cta_texts"]
            else []
        )
        ad["has_whatsapp_cta"] = any("whatsapp" in text.lower() for text in flat_ctas) or (
            ad["body"] and "whatsapp" in ad["body"].lower()
        )

        if not any([ad.get("library_id"), ad.get("page_name"), ad.get("body")]):
            continue

        ads.append(ad)

    return ads


def remove_duplicates(ads: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for ad in ads:
        key = ad.get("library_id") or (ad.get("body") or "")[:80]
        if key and key not in seen:
            seen.add(key)
            out.append(ad)
    return out


dedupe = remove_duplicates


def save_csv(ads: list[dict], path: Path) -> None:
    if not ads:
        print("No ads to save.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=ads[0].keys())
        writer.writeheader()
        writer.writerows(ads)
    print(f"CSV saved -> {path} ({len(ads)} ads)")


def save_json(ads: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(ads, file, ensure_ascii=False, indent=2)
    print(f"JSON saved -> {path} ({len(ads)} ads)")


def save_outputs(ads: list[dict], config: ScraperConfig) -> None:
    if config.save_csv:
        save_csv(ads, config.output_csv)
    if config.save_json:
        save_json(ads, config.output_json)


def scrape(config: ScraperConfig) -> list[dict]:
    """Run a full scrape session and return deduplicated ads."""
    driver = make_driver(headless=config.headless, chrome_version=config.chrome_version)
    try:
        snapshots = scroll_and_collect(driver, config)
    finally:
        driver.quit()
    all_ads = []
    for html in snapshots:
        all_ads.extend(parse_ads(html))
    ads = remove_duplicates(all_ads)
    save_outputs(ads, config)
    return ads


def parse_from_dir(html_dir: Path) -> list[dict]:
    """Parse all saved HTML snapshots without running a browser."""

    all_ads = []
    for html_file in sorted(html_dir.glob("*.html")):
        html = html_file.read_text(encoding="utf-8")
        ads = parse_ads(html)
        all_ads.extend(ads)
        print(f"{html_file.name}: {len(ads)} ads found")
    return remove_duplicates(all_ads)
