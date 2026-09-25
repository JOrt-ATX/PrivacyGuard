"""Catálogo e índices estables de marcas neutras."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


class PlaceholderCatalog:
    def __init__(self, prefixes: dict[str, str], version: str) -> None:
        self.prefixes = dict(prefixes)
        self.version = version

    @classmethod
    def load(cls, path: str | Path) -> "PlaceholderCatalog":
        try:
            with Path(path).open(encoding="utf-8") as handle:
                value = json.load(handle)
            prefixes = value["prefixes"]
            version = value["version"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("placeholder_catalog_load_failed") from exc
        if not isinstance(prefixes, dict) or not isinstance(version, str):
            raise ValueError("placeholder_catalog_invalid")
        return cls(prefixes, version)

    def prefix_for(self, label: str) -> str:
        try:
            prefix = self.prefixes[label]
        except KeyError as exc:
            raise ValueError("placeholder_label_unknown") from exc
        if not re.fullmatch(r"[A-Z0-9_]+", prefix):
            raise ValueError("placeholder_prefix_invalid")
        return prefix


def normalized_entity_key(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split())).casefold()


class PlaceholderAllocator:
    def __init__(self, catalog: PlaceholderCatalog) -> None:
        self.catalog = catalog
        self._indices: dict[tuple[str, str], int] = {}

    def allocate(self, label: str, entity_text: str) -> str:
        key = (label, normalized_entity_key(entity_text))
        if key not in self._indices:
            prefix = self.catalog.prefix_for(label)
            same_prefix = [item for item in self._indices if item[0] == label]
            self._indices[key] = len(same_prefix) + 1
        return "[{}_{}]".format(self.catalog.prefix_for(label), self._indices[key])
