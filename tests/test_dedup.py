from paralaksa.ingest.dedup import clean_url, is_similar_title, normalize_url, url_hash


def test_clean_url_keeps_path_and_drops_tracking():
    assert (
        clean_url("https://www.pravda.com.ua/news/2026/09/23/8054670/?utm_source=rss&at_medium=RSS#c")
        == "https://www.pravda.com.ua/news/2026/09/23/8054670/"
    )
    assert clean_url("https://a.example/x?id=5&fbclid=1") == "https://a.example/x?id=5"


def test_normalize_url_strips_tracking_and_fragment():
    assert (
        normalize_url("http://News.Example.com/world/story/?utm_source=rss&id=5&fbclid=x&at_medium=RSS#top")
        == "https://news.example.com/world/story?id=5"
    )


def test_normalize_url_sorts_query_and_keeps_root():
    assert normalize_url("https://a.example/?b=2&a=1") == "https://a.example/?a=1&b=2"
    assert normalize_url("https://a.example:443") == "https://a.example/"


def test_url_hash_equal_for_equivalent_urls():
    assert url_hash("https://a.example/x/?utm_campaign=c") == url_hash("http://A.example/x")
    assert url_hash("https://a.example/x/") == url_hash("https://a.example/x")
    assert url_hash("https://a.example/x") != url_hash("https://a.example/y")


def test_similar_titles():
    others = ["NATO strengthens eastern flank amid rising tensions"]
    assert is_similar_title("NATO strengthens eastern flank amid rising tensions!", others, 0.9)
    assert is_similar_title("nato strengthens Eastern flank, amid rising tensions", others, 0.9)
    assert not is_similar_title("Poland opens new civil defence shelters programme", others, 0.9)
    assert not is_similar_title("", others, 0.9)
