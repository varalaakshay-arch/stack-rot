"""npm registry client.

Talks to the public npm registry (https://registry.npmjs.org/) to fetch
metadata about packages: last publish date, deprecation status, latest
version.

The registry is free, has no auth, and supports thousands of requests
per minute. We still cache responses in-memory for the duration of a
single scan so we don't ask twice for the same package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


NPM_REGISTRY = "https://registry.npmjs.org"
REQUEST_TIMEOUT = 10.0


@dataclass(frozen=True)
class RegistryInfo:
    """Metadata about a package from the registry.

    Attributes:
        name: Package name as queried.
        latest_version: Latest stable version string, or None if unknown.
        last_published: When the latest version was published (UTC),
            or None if unknown.
        is_deprecated: True if the registry has marked the package or
            its latest version deprecated.
        deprecation_message: The deprecation notice text, if any.
        not_found: True if the package does not exist on the registry.
    """

    name: str
    latest_version: str | None = None
    last_published: datetime | None = None
    is_deprecated: bool = False
    deprecation_message: str | None = None
    not_found: bool = False


class Registry:
    """Wraps an httpx client with simple in-memory caching."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "stack-rot/0.1 (+https://github.com/varalaakshay-arch/stack-rot)"},
        )
        self._cache: dict[str, RegistryInfo] = {}

    def fetch(self, package_name: str) -> RegistryInfo:
        """Fetch metadata for a single package. Cached per instance."""
        if package_name in self._cache:
            return self._cache[package_name]

        info = self._fetch_uncached(package_name)
        self._cache[package_name] = info
        return info

    def _fetch_uncached(self, package_name: str) -> RegistryInfo:
        url = f"{NPM_REGISTRY}/{package_name}"
        try:
            resp = self._client.get(url)
        except httpx.RequestError:
            # Network failure — treat as unknown, not an error
            return RegistryInfo(name=package_name)

        if resp.status_code == 404:
            return RegistryInfo(name=package_name, not_found=True)

        if resp.status_code != 200:
            return RegistryInfo(name=package_name)

        data = resp.json()
        return _parse_registry_payload(package_name, data)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Registry":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _parse_registry_payload(name: str, data: dict) -> RegistryInfo:
    """Pull the fields we care about from npm's full metadata blob.

    npm returns a large document per package. We extract:
      - latest stable version from "dist-tags.latest"
      - publish time of that version from "time"
      - deprecation flag from "versions[latest].deprecated"
    """
    latest = (data.get("dist-tags") or {}).get("latest")

    last_published: datetime | None = None
    if latest:
        time_str = (data.get("time") or {}).get(latest)
        if time_str:
            try:
                last_published = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                if last_published.tzinfo is None:
                    last_published = last_published.replace(tzinfo=timezone.utc)
            except ValueError:
                last_published = None

    is_deprecated = False
    deprecation_message: str | None = None
    if latest:
        version_info = (data.get("versions") or {}).get(latest) or {}
        deprecated = version_info.get("deprecated")
        if deprecated:
            is_deprecated = True
            deprecation_message = deprecated if isinstance(deprecated, str) else "deprecated"

    return RegistryInfo(
        name=name,
        latest_version=latest,
        last_published=last_published,
        is_deprecated=is_deprecated,
        deprecation_message=deprecation_message,
    )