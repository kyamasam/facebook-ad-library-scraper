"""Tools for scraping and parsing Facebook Ad Library pages."""

from .core import (
    ScraperConfig,
    dedupe,
    make_driver,
    parse_ads,
    parse_from_dir,
    remove_duplicates,
    save_csv,
    save_json,
    save_outputs,
    scrape,
    scroll_and_collect,
)

__all__ = [
    "ScraperConfig",
    "dedupe",
    "make_driver",
    "parse_ads",
    "parse_from_dir",
    "remove_duplicates",
    "save_csv",
    "save_json",
    "save_outputs",
    "scrape",
    "scroll_and_collect",
]
