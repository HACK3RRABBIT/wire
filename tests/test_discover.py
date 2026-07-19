from app.discover import extract_hashtags, extract_usernames


def test_extract_usernames_from_mention():
    assert extract_usernames("check out @durov for updates") == {"durov"}


def test_extract_usernames_from_tme_link():
    assert extract_usernames("join https://t.me/telegram now") == {"telegram"}


def test_extract_usernames_ignores_reserved_paths():
    assert extract_usernames("https://t.me/joinchat/abc123xyz") == set()


def test_extract_usernames_empty():
    assert extract_usernames("") == set()
    assert extract_usernames(None) == set()


def test_extract_hashtags():
    assert extract_hashtags("breaking #news about #crypto market") == {"news", "crypto"}


def test_extract_hashtags_none():
    assert extract_hashtags("no hashtags here") == set()
