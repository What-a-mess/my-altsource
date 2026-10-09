"""Generate a SideStore source from public GitHub release IPAs."""

import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import tempfile
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parent


def open_url(url, api=False):
    headers = {"User-Agent": "sidestore-source-updater"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        token = os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    # Authentication is only sent to the GitHub API, never IPA hosts.
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=180
    )


def select_asset(release, config):
    pattern = re.compile(config["assetRegex"], re.IGNORECASE)
    matches = [
        asset for asset in release["assets"]
        if asset["name"].lower().endswith(".ipa")
        and pattern.fullmatch(asset["name"])
    ]
    if len(matches) != 1:
        names = [asset["name"] for asset in matches]
        raise ValueError(
            f"{config['repo']}: expected exactly one IPA, got {len(matches)}: {names}"
        )
    return matches[0]


def read_ipa(asset):
    with tempfile.TemporaryFile() as ipa:
        with open_url(asset["browser_download_url"]) as response:
            shutil.copyfileobj(response, ipa)
        size = ipa.tell()
        if size != asset["size"]:
            raise ValueError(f"{asset['name']}: downloaded size does not match release")
        ipa.seek(0)
        digest = asset.get("digest")
        if digest and digest.startswith("sha256:"):
            sha256 = hashlib.sha256()
            for chunk in iter(lambda: ipa.read(1024 * 1024), b""):
                sha256.update(chunk)
            if sha256.hexdigest() != digest.removeprefix("sha256:"):
                raise ValueError(f"{asset['name']}: SHA-256 mismatch")
            ipa.seek(0)
        with zipfile.ZipFile(ipa) as archive:
            paths = [
                name for name in archive.namelist()
                if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", name)
            ]
            if len(paths) != 1:
                raise ValueError(f"{asset['name']}: cannot identify the main application")
            return plistlib.loads(archive.read(paths[0])), size


def build_app(config):
    repo = config["repo"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError(f"Invalid GitHub repository: {repo}")
    with open_url(f"https://api.github.com/repos/{repo}/releases/latest", api=True) as response:
        release = json.load(response)
    asset = select_asset(release, config)
    info, size = read_ipa(asset)
    version = {
        "version": str(info["CFBundleShortVersionString"]),
        "buildVersion": str(info["CFBundleVersion"]),
        "date": release["published_at"][:10],
        "downloadURL": asset["browser_download_url"],
        "size": size,
        "localizedDescription": release.get("body") or "",
    }
    if info.get("MinimumOSVersion"):
        version["minOSVersion"] = str(info["MinimumOSVersion"])
    app = {
        key: config[key]
        for key in ("name", "developerName", "localizedDescription", "iconURL")
    }
    app.update({
        "bundleIdentifier": info["CFBundleIdentifier"],
        "versions": [version],
        "version": version["version"],
        "versionDate": version["date"],
        "downloadURL": version["downloadURL"],
        "size": size,
    })
    print(f"{app['name']}: {version['version']} ({version['buildVersion']}) / {app['bundleIdentifier']}")
    return app


def main():
    source = json.loads((ROOT / "source-config.json").read_text(encoding="utf-8"))
    configs = json.loads((ROOT / "apps.json").read_text(encoding="utf-8"))
    if not source.get("name") or not source.get("identifier") or not configs:
        raise ValueError("Source name, identifier and at least one app are required")
    apps = [build_app(config) for config in configs]
    identifiers = [app["bundleIdentifier"] for app in apps]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError(f"Apps have conflicting bundle identifiers: {identifiers}")
    source.update({"apps": apps, "news": []})
    text = json.dumps(source, ensure_ascii=False, indent=2) + "\n"
    # Nothing is written until every release and IPA has been checked.
    temporary = ROOT / "source.json.tmp"
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(ROOT / "source.json")


if __name__ == "__main__":
    main()
