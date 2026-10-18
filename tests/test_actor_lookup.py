from pathlib import Path
from unittest.mock import MagicMock, patch

from core.actor_lookup import ActorLookup, is_rate_limited_page
from core.db import establish_to_db, lookup_actor_from_db
from core.lookup_errors import RateLimitedError
import bs4


def test_lookup_uses_memory_cache(tmp_path: Path):
    db_file = tmp_path / "empty.db"
    establish_to_db(db_file).close()

    lookup = ActorLookup(db_path=db_file)
    with patch.object(lookup, "_lookup_web", side_effect=["Actor A", "Actor B"]) as web:
        assert lookup.lookup("SSIS-100") == "Actor A"
        assert lookup.lookup("SSIS-100") == "Actor A"
        web.assert_called_once()
    lookup.close()


def test_lookup_uses_db_before_web(tmp_path: Path):
    db_file = tmp_path / "catalog.db"
    conn = establish_to_db(db_file)
    conn.execute(
        "INSERT INTO javlist (actor, label, timestamp, path) VALUES (?, ?, ?, ?)",
        ("Db Actor", "CUS-1", "2026-01-01", "/x.mp4"),
    )
    conn.commit()
    conn.close()

    lookup = ActorLookup(db_path=db_file)
    with patch.object(lookup, "_lookup_web") as web:
        assert lookup.lookup("CUS-1") == "Db Actor"
        web.assert_not_called()
    lookup.close()


def test_web_delay_only_on_web_path(tmp_path: Path):
    db_file = tmp_path / "catalog.db"
    establish_to_db(db_file).close()

    lookup = ActorLookup(db_path=db_file, web_delay_seconds=0.5)
    driver = MagicMock()
    driver.html = (
        "<html><head><title>Ok</title></head>"
        "<body><div class='video'><span class='star'>Web Actor</span></div></body></html>"
    )
    driver.title = "Ok"
    with (
        patch.object(lookup, "ensure_driver", return_value=driver),
        patch("core.actor_lookup.CloudflareBypasser"),
        patch("core.actor_lookup._interruptible_sleep") as sleep,
        patch("core.actor_lookup.save_actor_record"),
    ):
        assert lookup.lookup("NO-DB-1") == "Web Actor"
        assert sleep.call_args_list[0].args[0] == 0.5

        assert lookup.lookup("NO-DB-1") == "Web Actor"
        sleep.assert_called_once()
    lookup.close()


def test_persists_successful_web_lookup(tmp_path: Path):
    db_file = tmp_path / "catalog.db"
    establish_to_db(db_file).close()

    lookup = ActorLookup(db_path=db_file)
    with patch.object(lookup, "_fetch_actor_once", return_value="Web Actor"):
        lookup.lookup("SSIS-200", media_path="/videos/SSIS-200.mp4")

    assert lookup_actor_from_db("SSIS-200", db_file) == "Web Actor"
    lookup.close()


def test_rate_limited_page_detection():
    soup = bs4.BeautifulSoup(
        "<html><head><title>Error</title></head>"
        "<body>Too many requests. Please slow down.</body></html>",
        "html.parser",
    )
    assert is_rate_limited_page(soup, "Error") is True


def test_rate_limit_not_triggered_by_429_in_video_id():
    soup = bs4.BeautifulSoup(
        """
        <html><head><title>Search</title></head>
        <body>
          <script>var x = "javli323429512";</script>
          <div class="videothumblist">
            <div class="video">
              <a href="./?v=javli323429512" title="ABF-365 Title">
                <div class="id">ABF-365</div>
              </a>
            </div>
          </div>
        </body></html>
        """,
        "html.parser",
    )
    assert is_rate_limited_page(soup, "Search") is False


def test_raises_after_rate_limit_retries(tmp_path: Path):
    db_file = tmp_path / "catalog.db"
    establish_to_db(db_file).close()

    lookup = ActorLookup(db_path=db_file, web_delay_seconds=0)
    with (
        patch.object(lookup, "_fetch_actor_once", side_effect=RateLimitedError("limit")),
        patch.object(lookup, "_wait_rate_limit_backoff"),
    ):
        try:
            lookup.lookup("NO-DB-2")
            assert False, "expected RateLimitedError"
        except RateLimitedError:
            pass
    lookup.close()
