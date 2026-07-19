# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

import os
from typing import cast

import pytest

from superset.db_engine_specs.base import (
    BaseEngineSpec,
    DatabaseCategory,
    DBEngineSpecMetadata,
)
from superset.db_engine_specs.lib import (
    calculate_support_level,
    diagnose,
    format_markdown_table,
    generate_feature_tables,
    generate_focused_table,
    generate_table,
    generate_yaml_docs,
    get_documentation_metadata,
    get_name,
    has_custom_method,
    infer_category,
)
from superset.db_engine_specs.sqlite import SqliteEngineSpec


def test_has_custom_method() -> None:
    """A method is "custom" only when overridden from ``BaseEngineSpec``."""

    class Custom(BaseEngineSpec):
        @classmethod
        def epoch_to_dttm(cls) -> str:
            return "custom"

    assert has_custom_method(Custom, "epoch_to_dttm") is True
    # Inherited (not overridden) methods are not custom.
    assert has_custom_method(BaseEngineSpec, "epoch_to_dttm") is False
    # Unknown attributes are not custom.
    assert has_custom_method(Custom, "does_not_exist") is False


def test_get_name_prefers_engine_name() -> None:
    """``engine_name`` wins, falling back to ``engine``."""

    class Named(BaseEngineSpec):
        engine = "eng"
        engine_name = "Nice Name"

    class Unnamed(BaseEngineSpec):
        engine = "eng"
        engine_name = None

    assert get_name(Named) == "Nice Name"
    assert get_name(Unnamed) == "eng"


def test_format_markdown_table() -> None:
    """Headers, a separator row and body rows are rendered."""
    table = format_markdown_table(["A", "B"], [[1, 2], ["x", "y"]])
    assert table == ("| A | B |\n| --- | --- |\n| 1 | 2 |\n| x | y |")


def test_generate_focused_table_basic() -> None:
    """Databases become sorted rows with the requested feature columns."""
    info = {
        "Zeta": {"joins": True, "subqueries": False},
        "Alpha": {"joins": False, "subqueries": True},
    }
    table, excluded = generate_focused_table(
        info,
        feature_keys=["joins", "subqueries"],
        column_labels=["JOINs", "Subqueries"],
    )
    assert excluded == []
    lines = table.splitlines()
    assert lines[0] == "| Database | JOINs | Subqueries |"
    # Sorted alphabetically by default.
    assert lines[2].startswith("| Alpha |")
    assert lines[3].startswith("| Zeta |")


def test_generate_focused_table_filter_and_extractor_and_order() -> None:
    """Filtering, custom value extraction and order preservation all work."""
    info = {
        "Zeta": {"score": 5, "flag": True},
        "Alpha": {"score": 0, "flag": False},
    }

    table, excluded = generate_focused_table(
        info,
        feature_keys=["flag"],
        column_labels=["Flag"],
        filter_fn=lambda db_info: db_info["score"] > 0,
        value_extractor=lambda db_info, key: "YES" if db_info[key] else "NO",
        preserve_order=True,
    )

    assert excluded == ["Alpha"]
    lines = table.splitlines()
    assert lines[0] == "| Database | Flag |"
    assert lines[2] == "| Zeta | YES |"


def test_generate_focused_table_all_filtered_out() -> None:
    """When nothing survives the filter, an empty table is returned."""
    info = {"Alpha": {"score": 0}}
    table, excluded = generate_focused_table(
        info,
        feature_keys=["score"],
        column_labels=["Score"],
        filter_fn=lambda db_info: False,
    )
    assert table == ""
    assert excluded == ["Alpha"]


def test_calculate_support_level_no_keys() -> None:
    assert calculate_support_level({}, []) == "Not supported"


@pytest.mark.parametrize(
    "flags,expected",
    [
        ({"a": True, "b": True}, "Supported"),
        ({"a": True, "b": False}, "Partial"),
        ({"a": False, "b": False}, "Not supported"),
    ],
)
def test_calculate_support_level_regular_features(flags, expected) -> None:
    assert calculate_support_level(flags, ["a", "b"]) == expected


@pytest.mark.parametrize(
    "grains,expected",
    [
        ({"DAY": True, "WEEK": True}, "Supported"),
        ({"DAY": True, "WEEK": False}, "Partial"),
        ({"DAY": False, "WEEK": False}, "Not supported"),
    ],
)
def test_calculate_support_level_time_grains(grains, expected) -> None:
    db_info = {"time_grains": grains}
    assert (
        calculate_support_level(db_info, ["time_grains.DAY", "time_grains.WEEK"])
        == expected
    )


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Amazon Redshift", DatabaseCategory.CLOUD_AWS),
        ("Google BigQuery", DatabaseCategory.CLOUD_GCP),
        ("Microsoft Azure", DatabaseCategory.CLOUD_AZURE),
        ("Snowflake", DatabaseCategory.CLOUD_DATA_WAREHOUSES),
        ("Apache Druid", DatabaseCategory.APACHE_PROJECTS),
        ("PostgreSQL", DatabaseCategory.TRADITIONAL_RDBMS),
        ("ClickHouse", DatabaseCategory.ANALYTICAL_DATABASES),
        ("Elasticsearch", DatabaseCategory.SEARCH_NOSQL),
        ("Trino", DatabaseCategory.QUERY_ENGINES),
        ("Some Unknown DB", DatabaseCategory.OTHER),
    ],
)
def test_infer_category(name, expected) -> None:
    assert infer_category(name) == expected


def test_get_documentation_metadata_from_spec_metadata() -> None:
    """Existing ``metadata`` is preserved and a category is inferred if absent."""

    class WithMetadata(BaseEngineSpec):
        metadata = cast(DBEngineSpecMetadata, {"pypi_packages": ["pkg"]})

    result = get_documentation_metadata(WithMetadata, "PostgreSQL")
    assert result["pypi_packages"] == ["pkg"]
    assert result["category"] == DatabaseCategory.TRADITIONAL_RDBMS


def test_get_documentation_metadata_respects_existing_category() -> None:
    class WithCategory(BaseEngineSpec):
        metadata = cast(DBEngineSpecMetadata, {"category": "Custom"})

    result = get_documentation_metadata(WithCategory, "PostgreSQL")
    assert result["category"] == "Custom"


def test_get_documentation_metadata_fallback() -> None:
    """A spec without metadata gets a minimal fallback payload."""

    class NoMetadata(BaseEngineSpec):
        sqlalchemy_uri_placeholder = "engine://user:pass@host/db"

    result = get_documentation_metadata(NoMetadata, "Trino")
    assert result == {
        "pypi_packages": [],
        "connection_string": "engine://user:pass@host/db",
        "category": DatabaseCategory.QUERY_ENGINES,
    }


def test_diagnose_returns_scored_report(app_context: None) -> None:
    """``diagnose`` produces a scored capability report for a real spec."""
    report = diagnose(SqliteEngineSpec)

    assert report["module"].startswith("superset")
    assert isinstance(report["time_grains"], dict)
    assert isinstance(report["score"], int)
    assert report["max_score"] >= report["score"] >= 0
    # A few known SQLite capabilities.
    assert report["joins"] is True
    assert report["limit_method"] == SqliteEngineSpec.limit_method.value


def test_generate_feature_tables(app_context: None, monkeypatch) -> None:
    """The multi-table markdown document is generated from real specs."""
    monkeypatch.setattr(
        "superset.db_engine_specs.lib.load_engine_specs",
        lambda: [SqliteEngineSpec],
    )
    output = generate_feature_tables()
    assert "### Feature Overview" in output
    assert "### SQL Capabilities" in output
    assert "SQLite" in output


def test_generate_table(app_context: None, monkeypatch) -> None:
    """The legacy row-oriented table includes the feature/score rows."""
    monkeypatch.setattr(
        "superset.db_engine_specs.lib.load_engine_specs",
        lambda: [SqliteEngineSpec],
    )
    rows = generate_table()
    assert rows[0][0] == "Feature"
    assert rows[-1][0] == "Score"


def test_generate_yaml_docs_returns_dict(app_context: None, monkeypatch) -> None:
    """Without an output dir, ``generate_yaml_docs`` returns a dict only."""
    monkeypatch.setattr(
        "superset.db_engine_specs.lib.load_engine_specs",
        lambda: [SqliteEngineSpec],
    )
    docs = generate_yaml_docs()
    assert "SQLite" in docs
    assert docs["SQLite"]["engine"] == SqliteEngineSpec.engine
    assert "documentation" in docs["SQLite"]


def test_generate_yaml_docs_writes_files(
    app_context: None, monkeypatch, tmp_path
) -> None:
    """With an output dir, per-database YAML files and an index are written."""
    monkeypatch.setattr(
        "superset.db_engine_specs.lib.load_engine_specs",
        lambda: [SqliteEngineSpec],
    )
    generate_yaml_docs(str(tmp_path))
    written = set(os.listdir(tmp_path))
    assert "_index.yaml" in written
    assert any(name.endswith(".yaml") and name != "_index.yaml" for name in written)
