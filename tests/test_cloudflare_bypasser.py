from unittest.mock import MagicMock, patch

from core.cloudflare_bypasser import CloudflareBypasser


def test_is_bypassed_true_when_title_ok():
    driver = MagicMock()
    driver.title = "JAVLibrary - Search"
    bypasser = CloudflareBypasser(driver, log=False)
    assert bypasser.is_bypassed() is True


def test_bypass_stops_when_already_bypassed():
    driver = MagicMock()
    bypasser = CloudflareBypasser(driver, max_retries=3, log=False)
    bypasser.is_bypassed = MagicMock(return_value=True)
    bypasser.click_verification_button = MagicMock()
    bypasser.bypass()
    bypasser.click_verification_button.assert_not_called()


def test_bypass_respects_max_retries():
    driver = MagicMock()
    bypasser = CloudflareBypasser(driver, max_retries=1, log=False)
    bypasser.is_bypassed = MagicMock(return_value=False)
    bypasser.click_verification_button = MagicMock()
    with patch("core.cloudflare_bypasser.time.sleep"):
        bypasser.bypass()
    assert bypasser.click_verification_button.call_count == 2
