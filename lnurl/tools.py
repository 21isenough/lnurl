from bech32 import bech32_decode, bech32_encode, convertbits
from typing import Any, Set, Tuple


def _bech32_decode(bech32: str, *, allowed_hrp: Set[str] = None) -> Tuple[str, Any]:
    hrp, data = bech32_decode(bech32)

    if None in (hrp, data) or (allowed_hrp and hrp not in allowed_hrp):
        raise ValueError(f'Invalid Human Readable Prefix (HRP): {hrp}.')

    return hrp, data


def _lnurl_decode(lnurl: str) -> str:
    """
    Decode a LNURL and return a url string without performing any validation on it.
    Use `lnurl.decode()` for validation and to get `HttpsUrl` object.
    """
    lnurl = lnurl.replace('lightning:', '') if lnurl.startswith('lightning:') else lnurl
    hrp, data = _bech32_decode(lnurl, allowed_hrp={'lnurl'})

    try:
        url = bytes(convertbits(data, 5, 8, False)).decode('utf-8')
    except UnicodeDecodeError:  # pragma: nocover
        raise ValueError('Invalid LNURL.')

    return url


def _url_encode(url: str) -> str:
    """
    Encode a URL without validating it first and return a bech32 LNURL string.
    Use `lnurl.encode()` for validation and to get a `Lnurl` object.
    """
    try:
        lnurl = bech32_encode('lnurl', convertbits(url.encode('utf-8'), 8, 5, True))
    except UnicodeEncodeError:  # pragma: nocover
        raise ValueError('Invalid URL.')

    return lnurl.upper()