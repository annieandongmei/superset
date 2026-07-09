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

import os

import yaml

from superset.db_engine_specs.base import BaseEngineSpec, DatabaseCategory
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


def test_has_custom_method_true() -> None:
    class CustomSpec(BaseEngineSpec):
        @classmethod
        def epoch_to_dttm(cls) -> str:
            return "custom"

    assert has_custom_method(CustomSpec, "epoch_to_dttm") is True


def test_has_custom_method_false() -> None:
    # ``BaseEngineSpec`` does not override its own method.
    assert has_custom_method(BaseEngineSpec, "epoch_to_dttm") is False


def test_has_custom_method_missing() -> None:
    assert has_custom_method(BaseEngineSpec, "not_a_real_method") is False


def test_get_name_prefers_engine_name() -> None:
    class NamedSpec(BaseEngineSpec):
        engine = "named_engine"
        engine_name = "Nice Name"

    assert get_name(NamedSpec) == "Nice Name"


def test_get_name_falls_back_to_engine() -> None:
    class UnnamedSpec(BaseEngineSpec):
        engine = "raw_engine"
        engine_name = None

    assert get_name(UnnamedSpec) == "raw_engine"


def test_diagnose_structure_and_score(app_context: None) -> None:
    result = diagnose(SqliteEngineSpec)
    assert result["module"].startswith("superset")
    assert isinstance(result["time_grains"], dict)
    # score is bounded by max_score
    assert 0 <= result["score"] <= result["max_score"]
    # every diagnosed feature flag is a bool
    for key in ("joins", "subqueries", "file_upload", "sql_validation"):
        assert isinstance(result[key], bool)


def test_format_markdown_table() -> None:
    table = format_markdown_table(
        ["A", "B"],
        [["1", "2"], ["3", "4"]],
    )
    lines = table.split("\n")
    assert lines[0] == "| A | B |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 2 |"
    assert lines[3] == "| 3 | 4 |"


def test_calculate_support_level_supported() -> None:
    db_info = {"a": True, "b": True}
    assert calculate_support_level(db_info, ["a", "b"]) == "Supported"


def test_calculate_support_level_partial() -> None:
    db_info = {"a": True, "b": False}
    assert calculate_support_level(db_info, ["a", "b"]) == "Partial"


def test_calculate_support_level_not_supported() -> None:
    db_info = {"a": False, "b": False}
    assert calculate_support_level(db_info, ["a", "b"]) == "Not supported"


def test_calculate_support_level_empty_keys() -> None:
    assert calculate_support_level({}, []) == "Not supported"


def test_calculate_support_level_time_grains() -> None:
    db_info = {"time_grains": {"DAY": True, "WEEK": False}}
    assert (
        calculate_support_level(db_info, ["time_grains.DAY", "time_grains.WEEK"])
        == "Partial"
    )


def test_generate_focused_table_basic() -> None:
    info = {
        "DB B": {"feat": "yes"},
        "DB A": {"feat": "no"},
    }
    table, excluded = generate_focused_table(info, ["feat"], ["Feature"])
    assert excluded == []
    lines = table.split("\n")
    assert lines[0] == "| Database | Feature |"
    # databases are sorted alphabetically by default
    assert lines[2] == "| DB A | no |"
    assert lines[3] == "| DB B | yes |"


def test_generate_focused_table_preserve_order() -> None:
    info = {
        "DB B": {"feat": "yes"},
        "DB A": {"feat": "no"},
    }
    table, _ = generate_focused_table(info, ["feat"], ["Feature"], preserve_order=True)
    lines = table.split("\n")
    assert lines[2] == "| DB B | yes |"
    assert lines[3] == "| DB A | no |"


def test_generate_focused_table_filter_excludes() -> None:
    info = {
        "Keep": {"ok": True},
        "Drop": {"ok": False},
    }
    table, excluded = generate_focused_table(
        info,
        ["ok"],
        ["OK"],
        filter_fn=lambda db_info: db_info["ok"],
    )
    assert excluded == ["Drop"]
    assert "Keep" in table
    assert "Drop" not in table


def test_generate_focused_table_all_filtered_out() -> None:
    info = {"Drop": {"ok": False}}
    table, excluded = generate_focused_table(
        info,
        ["ok"],
        ["OK"],
        filter_fn=lambda db_info: db_info["ok"],
    )
    assert table == ""
    assert excluded == ["Drop"]


def test_generate_focused_table_value_extractor() -> None:
    info = {"DB": {"raw": 1}}
    table, _ = generate_focused_table(
        info,
        ["raw"],
        ["Raw"],
        value_extractor=lambda db_info, key: db_info[key] * 10,
    )
    assert "| DB | 10 |" in table


def test_infer_category() -> None:
    assert infer_category("Amazon Athena") == DatabaseCategory.CLOUD_AWS
    assert infer_category("Google BigQuery") == DatabaseCategory.CLOUD_GCP
    assert infer_category("Azure Synapse") == DatabaseCategory.CLOUD_AZURE
    assert infer_category("Snowflake") == DatabaseCategory.CLOUD_DATA_WAREHOUSES
    assert infer_category("PostgreSQL") == DatabaseCategory.TRADITIONAL_RDBMS
    assert infer_category("Apache Druid") == DatabaseCategory.APACHE_PROJECTS
    assert infer_category("ClickHouse") == DatabaseCategory.ANALYTICAL_DATABASES
    assert infer_category("Elasticsearch") == DatabaseCategory.SEARCH_NOSQL
    assert infer_category("Trino") == DatabaseCategory.QUERY_ENGINES
    assert infer_category("Something Unusual") == DatabaseCategory.OTHER


def test_get_documentation_metadata_fallback() -> None:
    class NoMetadataSpec(BaseEngineSpec):
        engine = "nometa"
        metadata = {}
        sqlalchemy_uri_placeholder = "nometa://user:password@host/db"

    metadata = get_documentation_metadata(NoMetadataSpec, "No Meta")
    assert metadata["pypi_packages"] == []
    assert metadata["connection_string"] == "nometa://user:password@host/db"
    assert metadata["category"] == infer_category("No Meta")


def test_get_documentation_metadata_adds_missing_category() -> None:
    class MetadataSpec(BaseEngineSpec):
        engine = "withmeta"
        metadata = {"pypi_packages": ["foo"]}

    metadata = get_documentation_metadata(MetadataSpec, "Amazon Athena")
    assert metadata["pypi_packages"] == ["foo"]
    assert metadata["category"] == DatabaseCategory.CLOUD_AWS


def test_generate_table(app_context: None) -> None:
    rows = generate_table()
    # First row is the header listing all database names.
    assert rows[0][0] == "Feature"
    assert rows[1][0] == "Module"
    # Final row reports the score for each database.
    assert rows[-1][0] == "Score"
    assert len(rows[-1]) == len(rows[0])


def test_generate_feature_tables(app_context: None) -> None:
    output = generate_feature_tables()
    assert "### Feature Overview" in output
    assert "### SQL Capabilities" in output
    assert "### Time Grains – Common" in output


def test_generate_yaml_docs_dict_only(app_context: None) -> None:
    docs = generate_yaml_docs()
    assert docs, "expected at least one documented engine spec"
    for name, data in docs.items():
        assert data["engine_name"] == name
        assert "documentation" in data
        assert "score" in data


def test_generate_yaml_docs_writes_files(app_context: None, tmp_path) -> None:
    output_dir = str(tmp_path / "databases")
    docs = generate_yaml_docs(output_dir)

    index_path = os.path.join(output_dir, "_index.yaml")
    assert os.path.exists(index_path)
    with open(index_path) as f:
        index = yaml.safe_load(f)
    assert set(index) == set(docs)

    # Each database also gets its own YAML file.
    files = [f for f in os.listdir(output_dir) if f != "_index.yaml"]
    assert len(files) == len(docs)
