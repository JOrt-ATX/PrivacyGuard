"""Arranque único del Servicio ATX PrivacyGuard."""

from __future__ import annotations

import argparse
from pathlib import Path

from privacyguard.config import load_settings
from privacyguard.pipeline import Pipeline
from privacyguard.server import create_server


def build_pipeline(root: Path) -> Pipeline:
    return Pipeline.from_files(
        policy_path=root / "data" / "policies" / "cv_scoring" / "1.0.json",
        placeholders_path=root / "data" / "placeholders" / "1.0.json",
        labels_path=root / "data" / "labels" / "1.0.json",
        generalization_path=root / "data" / "generalization" / "municipio_provincia" / "1.0.json",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    settings = load_settings(args.config)
    server = create_server(settings, build_pipeline(root))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
