import base64
import ipaddress
import re
import socket
from html import unescape
from urllib.parse import quote, urljoin, urlparse

import requests

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
COMMONS_FILE = "https://commons.wikimedia.org/wiki/Special:Redirect/file/{filename}?width=512"
USER_AGENT = "AI-Career-Agent/1.0 (university logo resolver)"
TIMEOUT = (4, 8)
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_HTML_BYTES = 1_500_000
MAX_REDIRECTS = 5

_IMAGE_META_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)',
    re.I,
)
_IMAGE_META_RE_REVERSED = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']',
    re.I,
)
_LOGO_IMG_RE = re.compile(
    r'<img[^>]+(?:class|id|alt)=["\'][^"\']*(?:logo|brand|emblem|герб|логотип)[^"\']*["\'][^>]+src=["\']([^"\']+)',
    re.I,
)
_LOGO_IMG_RE_REVERSED = re.compile(
    r'<img[^>]+src=["\']([^"\']+)["\'][^>]+(?:class|id|alt)=["\'][^"\']*(?:logo|brand|emblem|герб|логотип)[^"\']*["\']',
    re.I,
)
_ICON_RE = re.compile(
    r'<link[^>]+rel=["\'][^"\']*(?:icon|apple-touch-icon)[^"\']*["\'][^>]+href=["\']([^"\']+)',
    re.I,
)


def _is_public_host(hostname: str) -> bool:
    if not hostname or hostname.lower() in {"localhost", "localhost.localdomain"}:
        return False
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except OSError:
        return False
    for item in addresses:
        address = item[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if not ip.is_global:
            return False
    return True


def _safe_http_url(value: str) -> str | None:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None
    expected_port = 443 if parsed.scheme == "https" else 80
    if port is not None and port != expected_port:
        return None
    if any(ord(character) < 32 for character in value):
        return None
    if not _is_public_host(parsed.hostname):
        return None
    return parsed.geturl()


def _same_site(candidate: str, official_url: str) -> bool:
    candidate_host = (urlparse(candidate).hostname or "").lower().lstrip("www.")
    official_host = (urlparse(official_url).hostname or "").lower().lstrip("www.")
    return bool(candidate_host and official_host and (candidate_host == official_host or candidate_host.endswith("." + official_host)))


def _request(url: str, *, stream: bool = False) -> requests.Response:
    current_url = _safe_http_url(url)
    if not current_url:
        raise ValueError("Недопустимый адрес")

    redirect_statuses = {301, 302, 303, 307, 308}
    for _redirect_number in range(MAX_REDIRECTS + 1):
        response = requests.get(
            current_url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"},
            timeout=TIMEOUT,
            allow_redirects=False,
            stream=stream,
        )
        if response.status_code in redirect_statuses:
            location = response.headers.get("Location", "").strip()
            response.close()
            redirected_url = _safe_http_url(urljoin(current_url, location))
            if not location or not redirected_url:
                raise ValueError("Недопустимое перенаправление")
            current_url = redirected_url
            continue

        response.raise_for_status()
        final_url = _safe_http_url(response.url or current_url)
        if not final_url:
            response.close()
            raise ValueError("Недопустимое перенаправление")
        return response

    raise ValueError("Слишком много перенаправлений")


def _read_limited_body(response: requests.Response, maximum_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        for chunk in response.iter_content(64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > maximum_bytes:
                raise ValueError("Ответ внешнего сервиса слишком большой")
            chunks.append(chunk)
    finally:
        response.close()
    return b"".join(chunks)


def _detected_image_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"\x00\x00\x01\x00"):
        return "image/x-icon"
    return None


def _claim_value(entity: dict, property_id: str):
    claims = entity.get("claims", {}).get(property_id, [])
    for claim in claims:
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if value:
            return value
    return None


def _search_entity(name: str) -> tuple[dict, str] | tuple[None, None]:
    response = requests.get(
        WIKIDATA_API,
        params={
            "action": "wbsearchentities",
            "search": name,
            "language": "ru",
            "uselang": "ru",
            "type": "item",
            "limit": 6,
            "format": "json",
            "origin": "*",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    candidates = response.json().get("search", [])
    education_words = ("универс", "институт", "академ", "колледж", "школ", "university", "institute", "academy", "college")
    ordered = sorted(
        candidates,
        key=lambda item: 0 if any(word in (item.get("description") or "").lower() for word in education_words) else 1,
    )
    for candidate in ordered:
        entity_id = candidate.get("id")
        if not entity_id:
            continue
        entity_response = requests.get(
            WIKIDATA_ENTITY.format(entity_id=entity_id),
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        entity_response.raise_for_status()
        entity = entity_response.json().get("entities", {}).get(entity_id, {})
        official_url = _claim_value(entity, "P856")
        logo_filename = _claim_value(entity, "P154")
        if official_url or logo_filename:
            return entity, candidate.get("label") or name
    return None, None


def _extract_site_image(official_url: str) -> str | None:
    response = _request(official_url, stream=True)
    content_type = (response.headers.get("Content-Type") or "").lower()
    final_url = response.url
    if "html" not in content_type:
        response.close()
        return None
    body = _read_limited_body(response, MAX_HTML_BYTES)
    encoding = response.encoding or "utf-8"
    html = body.decode(encoding, errors="replace")
    for pattern in (_LOGO_IMG_RE, _LOGO_IMG_RE_REVERSED, _IMAGE_META_RE, _IMAGE_META_RE_REVERSED, _ICON_RE):
        match = pattern.search(html)
        if not match:
            continue
        candidate = urljoin(final_url, unescape(match.group(1).strip()))
        if _safe_http_url(candidate) and _same_site(candidate, final_url):
            return candidate
    return None


def _image_to_data_url(image_url: str) -> tuple[str, str]:
    response = _request(image_url, stream=True)
    declared_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    final_url = response.url
    image_bytes = _read_limited_body(response, MAX_IMAGE_BYTES)
    if not image_bytes:
        raise ValueError("Пустое изображение")

    detected_type = _detected_image_type(image_bytes)
    allowed_declared = {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "image/x-icon",
        "image/vnd.microsoft.icon",
    }
    declared_matches = (
        declared_type in allowed_declared
        and (
            declared_type == detected_type
            or {declared_type, detected_type}
            <= {"image/x-icon", "image/vnd.microsoft.icon"}
        )
    )
    if detected_type is None or not declared_matches:
        raise ValueError("Найденный файл не является безопасным изображением")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{detected_type};base64,{encoded}", final_url


def find_university_logo(name: str) -> dict:
    clean_name = " ".join((name or "").split())[:240]
    if len(clean_name) < 3:
        raise ValueError("Укажите название учебного заведения")

    search_variants = [clean_name]
    first_part = re.split(r"[,;\n]|\s+[—–-]\s+", clean_name, maxsplit=1)[0].strip()
    if first_part and first_part != clean_name and len(first_part) >= 3:
        search_variants.append(first_part)

    entity = resolved_name = None
    for variant in search_variants:
        entity, resolved_name = _search_entity(variant)
        if entity:
            break
    if not entity:
        return {"found": False, "university_name": first_part or clean_name}

    official_url_claim = _claim_value(entity, "P856")
    official_url = _safe_http_url(str(official_url_claim)) if official_url_claim else None
    logo_filename = _claim_value(entity, "P154")
    candidates = []
    if logo_filename:
        candidates.append((COMMONS_FILE.format(filename=quote(str(logo_filename), safe="")), "wikimedia"))
    if official_url:
        try:
            site_image = _extract_site_image(str(official_url))
            if site_image:
                candidates.append((site_image, "official_site"))
        except (requests.RequestException, ValueError):
            pass

    for image_url, source in candidates:
        try:
            data_url, final_image_url = _image_to_data_url(image_url)
            return {
                "found": True,
                "university_name": resolved_name or clean_name,
                "official_url": official_url,
                "image_url": final_image_url,
                "image_data": data_url,
                "source": source,
            }
        except (requests.RequestException, ValueError):
            continue

    return {
        "found": False,
        "university_name": resolved_name or clean_name,
        "official_url": official_url,
    }
