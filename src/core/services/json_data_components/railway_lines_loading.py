"""Railway lines loading helpers extracted from JsonDataRepository."""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path

from ...models.railway_line import RailwayLine


def load_railway_lines_from_json(*, repo) -> list[RailwayLine]:
    """Load railway lines from ALL JSON files in the lines directory."""

    railway_lines: list[RailwayLine] = []

    # Load the comprehensive railway lines index for metadata (if available)
    index_file = Path(repo.data_directory) / "railway_lines_index_comprehensive.json"
    index_data: dict[str, Any] = {}
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            repo.logger.info(
                "Loaded railway lines index with %s entries",
                len(index_data.get("lines", [])),
            )
        except json.JSONDecodeError as exc:
            repo.logger.error("MALFORMED JSON in railway lines index %s: %s", index_file, exc)
            repo.logger.error(
                "JSON parsing failed at line %s, column %s",
                getattr(exc, "lineno", "?"),
                getattr(exc, "colno", "?"),
            )
            index_data = {}  # Use empty dict as fallback
        except Exception as exc:  # pragma: no cover
            repo.logger.error("Failed to load railway lines index %s: %s", index_file, exc)
            index_data = {}  # Use empty dict as fallback

    # Create a mapping of file names to index info
    index_mapping: dict[str, dict[str, Any]] = {}
    for line_info in index_data.get("lines", []):
        if not isinstance(line_info, dict):
            continue

        file_name = line_info.get("file", "")
        if file_name:
            index_mapping[str(file_name)] = line_info

    # Load ALL JSON files from the lines directory
    if not repo.lines_directory.exists():
        # Optional in some deployments; do not emit ERROR on successful runs.
        repo.logger.warning("Lines directory not found: %s", repo.lines_directory)
        return railway_lines

    json_files = list(repo.lines_directory.glob("*.json"))
    # Filter out backup files
    json_files = [f for f in json_files if not f.name.endswith(".backup")]

    repo.logger.info("Found %s railway line files to load", len(json_files))

    for line_file in json_files:
        try:
            with open(line_file, "r", encoding="utf-8") as f:
                line_data = json.load(f)

            # Get index info if available, otherwise use file-based info
            line_info = index_mapping.get(line_file.name, {})

            # Parse the JSON structure
            if line_info:
                # Use index-based parsing if we have index info
                railway_line = repo._parse_railway_line_json_with_index(line_info, line_data)
            else:
                # Use file-based parsing for files not in index
                railway_line = repo._parse_railway_line_json_from_file(line_file.name, line_data)

            if railway_line:
                railway_lines.append(railway_line)
                repo.logger.debug("Loaded railway line: %s", railway_line.name)

        except json.JSONDecodeError as exc:
            repo.logger.error(
                "MALFORMED JSON in railway line file %s: %s",
                line_file.name,
                exc,
            )
            repo.logger.error(
                "JSON parsing failed at line %s, column %s",
                getattr(exc, "lineno", "?"),
                getattr(exc, "colno", "?"),
            )
            repo.logger.error(
                "CRITICAL: Skipping malformed file %s to prevent crash",
                line_file.name,
            )
            continue
        except Exception as exc:  # pragma: no cover
            repo.logger.error("Failed to load railway line from %s: %s", line_file.name, exc)
            continue

    repo.logger.info("Successfully loaded %s railway lines", len(railway_lines))
    return railway_lines

