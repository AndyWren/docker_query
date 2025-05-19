import requests
import re
from functools import total_ordering
from packaging.version import Version, InvalidVersion


_VERSION_SUFFIX = re.compile(r'([a-z]+)(\d+)')
_STABLE_SUFFIX = re.compile(r'^v\d+\.\d+\.\d+(-k3s\d+)?(-rancher\d+)?$')

@total_ordering
class DockerVersion:
    def __init__(self, tag: str):
        self.original = tag
        self.version = self._parse_version(tag)
        self.suffix = self._parse_suffix(tag)

    def _parse_version(self, tag: str) -> Version:
        try:
            base = tag.split('-')[0].lstrip('v')
            return Version(base)
        except InvalidVersion:
            raise ValueError(f"Invalid base version in tag: {tag}")

    def _parse_suffix(self, tag: str) -> tuple:
        suffix_parts = tag.split('-')[1:]
        parsed = []
        for part in suffix_parts:
            match = re.match(_VERSION_SUFFIX, part)
            if match:
                name, num = match.groups()
                parsed.append((name, int(num)))
        return tuple(parsed)

    def __lt__(self, other):
        if self.version != other.version:
            return self.version < other.version
        return self.suffix < other.suffix

    def __eq__(self, other):
        return self.version == other.version and self.suffix == other.suffix

    def __repr__(self):
        return f"DockerVersion('{self.original}')"


def is_stable_kubernetes_tag(tag: str) -> bool:
    tag = tag.lower()
    if any(x in tag for x in ["rc", "alpha", "beta", "dev", "test", "ci", "debug", "latest"]):
        return False
    return bool(re.match(_STABLE_SUFFIX, tag))


def get_tags(image: str, page_size: int = 100):
    url = f"https://hub.docker.com/v2/repositories/{image}/tags"
    page = 1
    while True:
        params = {"page": page, "page_size": page_size}
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            break
        for tag_data in results:
            yield tag_data["name"]
        if not data.get("next"):
            break
        page += 1

def find_newer_tags(image: str, base_tag: str):
    base = DockerVersion(base_tag)
    newer_tags = []

    for tag in get_tags(image):
        if not is_stable_kubernetes_tag(tag):
            continue
        try:
            candidate = DockerVersion(tag)
        except ValueError:
            continue
        if candidate > base:
            newer_tags.append(candidate.original)
    return sorted(newer_tags, key=DockerVersion)

# Example usage
image = "rancher/k3s"
base_tag = "v1.27.2-k3s1"

newer = find_newer_tags(image, base_tag)
print("\n".join(newer))
