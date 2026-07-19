import re

_USERNAME_MENTION = re.compile(r"(?<![\w@])@(\w{5,32})")
# t.me/joinchat/<hash> and t.me/+<hash> are private invite links, not usernames — excluded via _RESERVED
_TME_LINK = re.compile(r"t\.me/(\w{5,32})", re.IGNORECASE)
_HASHTAG = re.compile(r"#(\w+)")

_RESERVED = {"joinchat", "share", "addstickers", "proxy"}


def extract_usernames(text: str) -> set[str]:
    if not text:
        return set()
    found = {m.lower() for m in _USERNAME_MENTION.findall(text)}
    found |= {m.lower() for m in _TME_LINK.findall(text) if m.lower() not in _RESERVED}
    return found


def extract_hashtags(text: str) -> set[str]:
    if not text:
        return set()
    return {m.lower() for m in _HASHTAG.findall(text)}
