import bs4

from core.actor_lookup import (
    actor_from_detail_soup,
    extract_actor_name,
    find_video_href,
    is_detail_page,
    validate_search_result,
)


def test_validate_detail_page_after_single_hit_redirect():
    soup = bs4.BeautifulSoup(
        """
        <html><head><title>ABF-186 - JAVLibrary</title></head>
        <body>
          <div id="video_title"><h3>Sample Title</h3></div>
          <div id="video_id"><span class="text">ABF-186</span></div>
          <div id="video_cast"><span class="star">Actor Name</span></div>
        </body></html>
        """,
        "html.parser",
    )
    assert is_detail_page(soup)
    assert validate_search_result(soup) is True
    assert actor_from_detail_soup(soup) == "Actor Name"
    assert extract_actor_name(soup, "ABF-186") == "Actor Name"


def test_find_video_href_by_div_id():
    soup = bs4.BeautifulSoup(
        """
        <html><body>
          <div class="videothumblist">
            <div class="videos">
              <div class="video">
                <a href="./?v=jav12345" title="ABF-274 Long Title">
                  <div class="id">ABF-274</div>
                </a>
              </div>
            </div>
          </div>
        </body></html>
        """,
        "html.parser",
    )
    assert validate_search_result(soup) is True
    assert find_video_href(soup, "ABF-274") == "./?v=jav12345"


def test_validate_videothumblist_without_videos_wrapper():
    soup = bs4.BeautifulSoup(
        """
        <html><body>
          <div class="videothumblist">
            <div class="video">
              <a href="./?v=jav99" title="ABF-318 x">
                <div class="id">ABF-318</div>
              </a>
            </div>
          </div>
        </body></html>
        """,
        "html.parser",
    )
    assert validate_search_result(soup) is True
    assert find_video_href(soup, "ABF-318") == "./?v=jav99"
