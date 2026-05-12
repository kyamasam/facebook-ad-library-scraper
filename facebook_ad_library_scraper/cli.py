"""Command-line interface for facebook-ad-library-scraper."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core import ScraperConfig, build_url, make_driver, parse_ads, parse_from_dir, remove_duplicates, save_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape and parse Facebook Ad Library results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Pass either --url OR individual filter flags. "
            "Filter flags are ignored when --url is provided.\n\n"
            "Examples:\n"
            "  %(prog)s --url 'https://www.facebook.com/ads/library/?...'\n"
            "  %(prog)s --query 'crypto mpesa' --country CD --active-status inactive\n"
            "  %(prog)s --query 'loan' --country KE --languages en sw --page-ids 978142995379450"
        ),
    )

    # URL mode
    parser.add_argument("--url", default=None, help="Full Facebook Ad Library URL to scrape (skips filter flags).")

    # Filter flags (used when --url is not supplied)
    filt = parser.add_argument_group("filter flags (used when --url is not given)")
    filt.add_argument("--query", "-q", default=None, help="Search keyword(s).")
    filt.add_argument("--country", default="CD", help="Two-letter country code (default: CD).")
    filt.add_argument(
        "--active-status",
        choices=["active", "inactive", "all"],
        default="active",
        help="Ad active status (default: active).",
    )
    filt.add_argument("--ad-type", default="all", help="Ad type filter (default: all).")
    filt.add_argument(
        "--media-type",
        choices=["all", "image", "meme", "image_and_meme", "video", "none"],
        default="all",
        help="Media type filter (default: all).",
    )
    filt.add_argument(
        "--search-type",
        choices=["keyword_unordered", "keyword_exact_phrase"],
        default="keyword_unordered",
        help="Search match mode (default: keyword_unordered).",
    )
    filt.add_argument(
        "--is-targeted-country",
        action="store_true",
        help="Set is_targeted_country=true in the URL.",
    )
    filt.add_argument(
        "--sort-mode",
        choices=["total_impressions", "relevancy_monthly_grouped"],
        default="total_impressions",
        help="Sort mode (default: total_impressions).",
    )
    filt.add_argument(
        "--sort-direction",
        choices=["desc", "asc"],
        default="desc",
        help="Sort direction (default: desc).",
    )
    filt.add_argument(
        "--languages",
        nargs="+",
        metavar="LANG",
        default=None,
        help="ISO language codes to filter by, e.g. --languages en fr ar.",
    )
    filt.add_argument(
        "--page-ids",
        nargs="+",
        metavar="ID",
        default=None,
        help="Facebook page IDs to filter by, e.g. --page-ids 978142995379450 22437985072.",
    )
    filt.add_argument("--start-date-min", default=None, metavar="YYYY-MM-DD", help="Earliest ad start date.")
    filt.add_argument("--start-date-max", default=None, metavar="YYYY-MM-DD", help="Latest ad start date.")

    # Session options
    parser.add_argument("--output-dir", default="ad_library_output", help="Directory for snapshots and exports.")
    parser.add_argument("--max-scrolls", type=int, default=50, help="Maximum scroll attempts.")
    parser.add_argument("--scroll-pause", type=float, default=3.0, help="Seconds to wait between scrolls.")
    parser.add_argument("--snapshot-every", type=int, default=5, help="Save HTML every N scrolls.")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode.")
    parser.add_argument("--chrome-version", type=int, default=None, help="Chrome major version for the driver.")
    parser.add_argument("--parse-only", action="store_true", help="Only parse existing snapshots.")
    return parser


def run(config: ScraperConfig, parse_only: bool = False) -> list[dict]:
    if parse_only or (config.html_dir.exists() and any(config.html_dir.glob("*.html"))):
        print(f"Found existing snapshots in {config.html_dir}. Re-parsing...")
        ads = parse_from_dir(config.html_dir)
    else:
        print("Starting browser scrape...")
        driver = make_driver(headless=config.headless, chrome_version=config.chrome_version)
        try:
            snapshots = scroll_and_collect(driver, config)
        finally:
            driver.quit()

        print(f"\nParsing {len(snapshots)} snapshots...")
        all_ads = []
        for html in snapshots:
            all_ads.extend(parse_ads(html))
        ads = remove_duplicates(all_ads)

    save_outputs(ads, config)
    return ads


def scroll_and_collect(*args, **kwargs):
    from .core import scroll_and_collect as _scroll_and_collect

    return _scroll_and_collect(*args, **kwargs)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_kwargs = {
        "output_dir": Path(args.output_dir),
        "max_scrolls": args.max_scrolls,
        "scroll_pause": args.scroll_pause,
        "snapshot_every": args.snapshot_every,
        "headless": args.headless,
        "chrome_version": args.chrome_version,
        "save_csv": True,
        "save_json": True,
    }

    if args.url:
        config_kwargs["url"] = args.url
    elif args.query:
        config_kwargs["url"] = build_url(
            query=args.query,
            country=args.country,
            active_status=args.active_status,
            ad_type=args.ad_type,
            media_type=args.media_type,
            search_type=args.search_type,
            is_targeted_country=args.is_targeted_country,
            sort_mode=args.sort_mode,
            sort_direction=args.sort_direction,
            languages=args.languages,
            page_ids=args.page_ids,
            start_date_min=args.start_date_min,
            start_date_max=args.start_date_max,
        )

    config = ScraperConfig(**config_kwargs)

    print("=" * 60)
    print("Facebook Ad Library Scraper")
    print("=" * 60)
    print(f"URL: {config.url}")

    ads = run(config, parse_only=args.parse_only)

    whatsapp_count = sum(1 for ad in ads if ad.get("has_whatsapp_cta"))
    unique_pages = len(set(ad["page_name"] for ad in ads if ad.get("page_name")))
    print("\nSummary:")
    print(f"  Total ads:        {len(ads)}")
    print(f"  WhatsApp CTAs:    {whatsapp_count}")
    print(f"  Unique pages:     {unique_pages}")


if __name__ == "__main__":
    main()
