from __future__ import annotations

import time
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

import bs4
from DrissionPage import ChromiumPage

from core.cloudflare_bypasser import CloudflareBypasser
from core.db import lookup_actor_from_db, save_actor_record
from core.lookup_errors import RateLimitedError, SearchStoppedError

ShouldStopFn = Callable[[], bool]

JAVLIBRARY_BASE = "https://www.javlibrary.com/en/"
MAX_WEB_ATTEMPTS = 4
RATE_LIMIT_BACKOFF_BASE = 5.0
RATE_LIMIT_BACKOFF_MAX = 120.0

# Phrase-only checks (no bare "429" — it appears inside many javlibrary video ids/urls).
RATE_LIMIT_PHRASES = (
    "rate limit",
    "too many requests",
    "too many request",
    "error 429",
    "http 429",
    "429 too many",
    "you have been blocked",
    "please try again later",
)

MessageFn = Callable[[str], None]


def _emit(on_message: MessageFn | None, text: str) -> None:
    if on_message:
        on_message(text)


def _cache_key(title_name: str) -> str:
    return title_name.strip().upper()


def _interruptible_sleep(seconds: float, should_stop: ShouldStopFn | None) -> None:
    if seconds <= 0:
        return
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if should_stop and should_stop():
            raise SearchStoppedError("Stopped by user")
        time.sleep(min(0.25, end - time.monotonic()))


def browser_is_alive(driver: ChromiumPage | None) -> bool:
    if driver is None:
        return False
    try:
        states = getattr(driver, "states", None)
        if states is not None and hasattr(states, "is_alive"):
            return bool(states.is_alive)
        _ = driver.title
        return True
    except Exception:
        return False


def _visible_page_text(soup: bs4.BeautifulSoup) -> str:
    """Text outside script/style — avoids matching ids like javli323429512."""
    clone = bs4.BeautifulSoup(str(soup), "html.parser")
    for tag in clone(["script", "style", "noscript"]):
        tag.decompose()
    return clone.get_text(" ", strip=True).lower()


def is_rate_limited_page(soup: bs4.BeautifulSoup | None, page_title: str = "") -> bool:
    if soup is None:
        return False
    # Normal search/detail pages are not throttle screens even if html mentions "429" elsewhere.
    if validate_search_result(soup):
        return False

    title_text = str(page_title).lower() if page_title else ""
    if soup.title:
        title_text = f"{title_text} {soup.title.get_text(strip=True).lower()}"
    body_text = _visible_page_text(soup)
    combined = f"{title_text} {body_text}"
    return any(phrase in combined for phrase in RATE_LIMIT_PHRASES)


def is_detail_page(soup: bs4.BeautifulSoup) -> bool:
    return soup.find(id="video_id") is not None or soup.find(id="video_title") is not None


def actor_from_detail_soup(soup: bs4.BeautifulSoup) -> str | None:
    cast = soup.find(id="video_cast")
    if cast:
        star = cast.find("span", class_="star")
        if star:
            return star.get_text(strip=True)
    star = soup.find("span", class_="star")
    if star:
        return star.get_text(strip=True)
    return None


def _code_matches_title(code: str, id_text: str, link_title: str) -> bool:
    upper = code.upper()
    id_upper = id_text.upper()
    title_upper = link_title.upper()
    if id_upper == upper:
        return True
    if title_upper.startswith(upper):
        return True
    if id_upper.startswith(upper):
        return True
    return False


def find_video_href(soup: bs4.BeautifulSoup, title_name: str) -> str | None:
    code = title_name.strip()
    for video_div in soup.find_all("div", class_="video"):
        anchor = video_div.find("a", href=True)
        if not anchor:
            continue
        id_div = video_div.find("div", class_="id")
        id_text = id_div.get_text(strip=True) if id_div else ""
        link_title = anchor.get("title") or ""
        if _code_matches_title(code, id_text, link_title):
            return anchor["href"]

    links = soup.find_all(
        "a",
        href=True,
        title=lambda x: x and _code_matches_title(code, "", x),
    )
    if links:
        return links[0]["href"]

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "v=jav" not in href and "/jav" not in href:
            continue
        id_div = anchor.find("div", class_="id")
        id_text = id_div.get_text(strip=True) if id_div else ""
        link_title = anchor.get("title") or anchor.get_text(strip=True)
        if _code_matches_title(code, id_text, link_title):
            return href
    return None


def validate_search_result(soup: bs4.BeautifulSoup | None) -> bool:
    if soup is None:
        return False
    title_text = soup.title.get_text(strip=True).lower() if soup.title else ""
    if "just a moment" in title_text or "attention required" in title_text:
        return False
    if is_detail_page(soup):
        return True
    if soup.find("div", class_="video") is not None:
        return True
    if soup.find("div", class_="videos") is not None:
        return True
    if soup.find("div", class_="videothumblist") is not None:
        return True
    if soup.select('a[href*="v=jav"]'):
        return True
    if soup.find(id="video_cast") is not None:
        return True
    return False


def extract_actor_name(
    soup: bs4.BeautifulSoup,
    title_name: str,
    driver: ChromiumPage | None = None,
    on_message: MessageFn | None = None,
    before_navigate: Callable[[], None] | None = None,
) -> str:
    if is_detail_page(soup):
        name = actor_from_detail_soup(soup)
        if name:
            _emit(on_message, f"Found actor name: {name}")
            return name
        _emit(on_message, "Empty actor name! Move to others...")
        return "Others"

    href = find_video_href(soup, title_name)
    if href is None:
        name = actor_from_detail_soup(soup)
        if name:
            return name
        _emit(on_message, "No matching links found! Move to others...")
        return "Others"

    if driver is None:
        _emit(on_message, "No matching detail page! Move to others...")
        return "Others"

    if soup.find("div", class_="videos") or len(soup.find_all("div", class_="video")) > 1:
        _emit(on_message, "Found multiple videos in the search result page...")

    url = urljoin(JAVLIBRARY_BASE, href)
    if before_navigate:
        before_navigate()
    driver.get(url)
    vp_soup = bs4.BeautifulSoup(driver.html, "html.parser")
    name = actor_from_detail_soup(vp_soup)
    if name:
        _emit(on_message, f"Found actor name: {name}")
        return name
    if is_rate_limited_page(vp_soup, driver.title):
        raise RateLimitedError("JavLibrary rate limit on detail page")
    _emit(on_message, "Empty actor name! Move to others...")
    return "Others"


def _wait_for_search_content(
    driver: ChromiumPage,
    timeout: float = 12.0,
    should_stop: ShouldStopFn | None = None,
) -> bs4.BeautifulSoup:
    deadline = time.monotonic() + timeout
    last_soup: bs4.BeautifulSoup | None = None
    while time.monotonic() < deadline:
        if should_stop and should_stop():
            raise SearchStoppedError("Stopped by user")
        if not browser_is_alive(driver):
            raise SearchStoppedError("Browser window was closed")
        last_soup = bs4.BeautifulSoup(driver.html, "html.parser")
        if validate_search_result(last_soup):
            return last_soup
        time.sleep(0.35)
    return last_soup or bs4.BeautifulSoup(driver.html, "html.parser")


class ActorLookup:
    def __init__(
        self,
        on_message: MessageFn | None = None,
        db_path: str | Path | None = None,
        web_delay_seconds: float = 0.0,
        should_stop: ShouldStopFn | None = None,
    ):
        self.on_message = on_message
        self.db_path = db_path
        self.web_delay_seconds = max(0.0, float(web_delay_seconds))
        self.should_stop = should_stop or (lambda: False)
        self.driver: ChromiumPage | None = None
        self._cf_bypassed = False
        self._cache: dict[str, str] = {}
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True
        if self.driver is None:
            return
        try:
            self.driver.quit()
        except Exception:
            pass
        finally:
            self.driver = None
            self._cf_bypassed = False

    def _check_stop(self) -> None:
        if self._stop_requested or self.should_stop():
            raise SearchStoppedError("Stopped by user")
        if self.driver is not None and not browser_is_alive(self.driver):
            self.driver = None
            raise SearchStoppedError("Browser window was closed")

    def ensure_driver(self) -> ChromiumPage:
        self._check_stop()
        if self.driver is None:
            self.driver = ChromiumPage()
        return self.driver

    def close(self) -> None:
        if self.driver is None:
            return
        try:
            self.driver.quit()
        except Exception:
            _emit(self.on_message, "Failed to close browser cleanly.")
        finally:
            self.driver = None
            self._cf_bypassed = False

    def lookup(self, title_name: str, *, media_path: str | Path | None = None) -> str:
        return self._resolve(title_name, media_path=media_path)

    def _sleep_before_web(self) -> None:
        self._check_stop()
        _interruptible_sleep(self.web_delay_seconds, self._should_stop_combined)

    def _should_stop_combined(self) -> bool:
        return self._stop_requested or self.should_stop()

    def _wait_rate_limit_backoff(self, attempt: int) -> None:
        wait = min(RATE_LIMIT_BACKOFF_BASE * (2**attempt), RATE_LIMIT_BACKOFF_MAX)
        _emit(self.on_message, f"JavLibrary rate limit — waiting {wait:.0f}s before retry...")
        _interruptible_sleep(wait, self._should_stop_combined)

    def _persist_actor(self, title_name: str, actor: str, media_path: str | Path | None) -> None:
        path_str = str(media_path) if media_path else ""
        save_actor_record(title_name, actor, path_str, self.db_path)
        _emit(self.on_message, f"Saved to database: {title_name} -> {actor}")

    def _resolve(self, title_name: str, *, media_path: str | Path | None = None) -> str:
        self._check_stop()
        key = _cache_key(title_name)
        if key in self._cache:
            return self._cache[key]

        actor = lookup_actor_from_db(title_name, self.db_path)
        if actor:
            self._cache[key] = actor
            return actor

        actor = self._lookup_web(title_name, media_path=media_path)
        self._cache[key] = actor
        return actor

    def _lookup_web(self, title_name: str, *, media_path: str | Path | None = None) -> str:
        last_error: Exception | None = None
        for attempt in range(MAX_WEB_ATTEMPTS):
            self._check_stop()
            try:
                actor = self._fetch_actor_once(title_name)
            except SearchStoppedError:
                raise
            except RateLimitedError as error:
                last_error = error
                if attempt >= MAX_WEB_ATTEMPTS - 1:
                    break
                self._wait_rate_limit_backoff(attempt)
                continue
            self._persist_actor(title_name, actor, media_path)
            return actor
        raise RateLimitedError(str(last_error) if last_error else "JavLibrary rate limit")

    def _fetch_actor_once(self, title_name: str) -> str:
        self._sleep_before_web()
        try:
            driver = self.ensure_driver()
            driver.get(f"{JAVLIBRARY_BASE}vl_searchbyid.php?keyword={title_name}")
            if not browser_is_alive(driver):
                raise SearchStoppedError("Browser window was closed")
            if not self._cf_bypassed:
                CloudflareBypasser(driver).bypass()
                self._cf_bypassed = True
            soup = _wait_for_search_content(driver, should_stop=self._should_stop_combined)
            if not validate_search_result(soup):
                if is_rate_limited_page(soup, driver.title):
                    raise RateLimitedError("JavLibrary rate limit")
                _emit(self.on_message, f"Invalid search result for {title_name}")
                return "Others"
            return extract_actor_name(
                soup,
                title_name,
                driver,
                self.on_message,
                before_navigate=self._sleep_before_web,
            )
        except (RateLimitedError, SearchStoppedError):
            raise
        except Exception as error:
            _emit(self.on_message, f"Search failed for {title_name}: {error}")
            self._cf_bypassed = False
            return "Others"
