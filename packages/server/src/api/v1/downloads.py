"""Smart download endpoint — detects platform and returns the correct download URL.

Used by:
  - Website download buttons (cloud version)
  - Lifetime purchase confirmation emails (lifetime version)

Platform detection hierarchy:
  1. Explicit ?platform= query param (override)
  2. User-Agent header analysis

Supported platforms:
  - mac-arm64  (Apple Silicon M1/M2/M3/M4)
  - mac-x64    (Intel Mac)
  - windows    (Windows x64)
  - unsupported (mobile, Linux, etc. → show "desktop only" message)
"""
import re
import logging
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter()
logger = logging.getLogger(__name__)

BASE_URL = "https://voxclar.com/downloads"

# File mapping — update filenames here when new versions are released
DOWNLOADS = {
    "cloud": {
        "mac-arm64":  f"{BASE_URL}/Voxclar-2.0.0-mac-arm64.dmg",
        "mac-x64":    f"{BASE_URL}/Voxclar-2.0.0-mac-x64.dmg",
        "windows":    f"{BASE_URL}/Voxclar-2.0.0-win-x64.exe",
    },
    "lifetime": {
        "mac-arm64":  f"{BASE_URL}/Voxclar-Lifetime-2.0.0-mac-arm64.dmg",
        "mac-x64":    f"{BASE_URL}/Voxclar-Lifetime-2.0.0-mac-x64.dmg",
        "windows":    f"{BASE_URL}/Voxclar-Lifetime-2.0.0-win-x64.exe",
    },
}


def detect_platform(user_agent: str, sec_ch_ua_arch: str = "") -> str:
    """Detect platform from User-Agent + Client Hints.

    Returns: 'mac-arm64' | 'mac-x64' | 'windows' | 'unsupported'

    IMPORTANT: Chrome on Apple Silicon reports "Intel Mac OS X" in its UA
    string for compatibility. The only reliable way to distinguish is via
    the Sec-CH-UA-Arch client hint header. When unavailable we default to
    arm64 since the vast majority of new Macs are Apple Silicon.
    """
    ua = user_agent.lower()
    arch_hint = sec_ch_ua_arch.strip('" ').lower()

    # Mobile / tablet → unsupported
    if any(m in ua for m in ("iphone", "ipad", "android", "mobile")):
        return "unsupported"

    # Windows
    if "windows" in ua:
        return "windows"

    # macOS
    if "macintosh" in ua or "mac os" in ua:
        # Best signal: Sec-CH-UA-Arch client hint (Chrome 93+)
        if arch_hint:
            if arch_hint in ("arm", "arm64"):
                return "mac-arm64"
            if arch_hint in ("x86", "x86_64", "x64"):
                return "mac-x64"

        # Fallback: Safari on Apple Silicon says "ARM64" in UA
        if "arm64" in ua or "aarch64" in ua:
            return "mac-arm64"

        # Chrome on Apple Silicon still says "Intel" — can't distinguish
        # from real Intel Macs via UA alone. Default to arm64 since most
        # Macs sold since late 2020 are Apple Silicon.
        return "mac-arm64"

    # Linux → unsupported
    if "linux" in ua:
        return "unsupported"

    return "unsupported"


@router.get("/download")
async def smart_download(
    request: Request,
    version: str = Query("cloud", description="'cloud' or 'lifetime'"),
    platform: str = Query("", description="Override: 'mac-arm64', 'mac-x64', 'windows'"),
):
    """Smart download — auto-detect platform, redirect to correct DMG/EXE.

    Used by website download buttons:
      <a href="https://voxclar.com/api/v1/download?version=cloud">Download</a>

    Query params:
      version  — 'cloud' (default) or 'lifetime'
      platform — optional override (skip auto-detection)
    """
    ua = request.headers.get("user-agent", "")
    arch_hint = request.headers.get("sec-ch-ua-arch", "")
    detected = platform if platform in ("mac-arm64", "mac-x64", "windows") else detect_platform(ua, arch_hint)

    version_key = "lifetime" if "lifetime" in version.lower() else "cloud"
    urls = DOWNLOADS.get(version_key, DOWNLOADS["cloud"])

    if detected == "unsupported":
        return JSONResponse(
            status_code=200,
            content={
                "platform": "unsupported",
                "message": "Voxclar is a desktop application for macOS and Windows. Please visit this page from your computer to download.",
                "download_urls": urls,
            },
        )

    url = urls.get(detected)
    if not url:
        return JSONResponse(status_code=404, content={"error": f"No download available for {detected}"})

    logger.info(f"Download: version={version_key}, platform={detected}, ua={ua[:80]}")
    return JSONResponse(content={
        "platform": detected,
        "download_url": url,
        "all_urls": urls,
    })


@router.get("/download/redirect")
async def download_redirect(
    request: Request,
    version: str = Query("cloud"),
    platform: str = Query(""),
):
    """Same as /download but issues a 302 redirect to the file directly.

    Useful for direct-link buttons:
      <a href="https://voxclar.com/api/v1/download/redirect?version=cloud">
    """
    ua = request.headers.get("user-agent", "")
    arch_hint = request.headers.get("sec-ch-ua-arch", "")
    detected = platform if platform in ("mac-arm64", "mac-x64", "windows") else detect_platform(ua, arch_hint)

    version_key = "lifetime" if "lifetime" in version.lower() else "cloud"
    urls = DOWNLOADS.get(version_key, DOWNLOADS["cloud"])
    url = urls.get(detected)

    if detected == "unsupported" or not url:
        # Redirect to website homepage with a notice
        return RedirectResponse(url="https://voxclar.com?desktop_only=true")

    return RedirectResponse(url=url)
