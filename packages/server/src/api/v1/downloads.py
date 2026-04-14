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


def detect_platform(user_agent: str) -> str:
    """Detect platform from User-Agent string.

    Returns: 'mac-arm64' | 'mac-x64' | 'windows' | 'unsupported'
    """
    ua = user_agent.lower()

    # Mobile / tablet → unsupported
    if any(m in ua for m in ("iphone", "ipad", "android", "mobile")):
        return "unsupported"

    # Windows
    if "windows" in ua:
        return "windows"

    # macOS — distinguish Intel vs Apple Silicon
    if "macintosh" in ua or "mac os" in ua:
        # Safari and Chrome on Apple Silicon include "ARM64" or run natively
        # Chrome: "Macintosh; ARM64" or via Sec-CH-UA-Arch
        # Most reliable: check for ARM indicators
        if "arm64" in ua or "aarch64" in ua:
            return "mac-arm64"
        # Intel Macs show "Intel" in UA
        if "intel" in ua:
            return "mac-x64"
        # Ambiguous (some browsers don't specify) — default to arm64
        # since most new Macs are Apple Silicon
        return "mac-arm64"

    # Linux → unsupported (we don't have Linux builds)
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
    detected = platform if platform in ("mac-arm64", "mac-x64", "windows") else detect_platform(ua)

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
    detected = platform if platform in ("mac-arm64", "mac-x64", "windows") else detect_platform(ua)

    version_key = "lifetime" if "lifetime" in version.lower() else "cloud"
    urls = DOWNLOADS.get(version_key, DOWNLOADS["cloud"])
    url = urls.get(detected)

    if detected == "unsupported" or not url:
        # Redirect to website homepage with a notice
        return RedirectResponse(url="https://voxclar.com?desktop_only=true")

    return RedirectResponse(url=url)
