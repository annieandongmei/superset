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

import pytest

from superset.db_engine_specs.base import BaseEngineSpec
from superset.db_engine_specs.lib import (
    has_custom_method,
    get_name,
    format_markdown_table,
    generate_focused_table,
    calculate_support_level,
    infer_category,
    get_documentation_metadata,
)


class MockSpec(BaseEngineSpec):
    """Mock spec for testing."""
    engine = "mock"
    engine_name = "Mock Database"


def test_has_custom_method_true() -> None:
    """Test has_custom_method returns True when method is overridden."""
    class CustomSpec(BaseEngineSpec):
        engine = "custom"
        
        @classmethod
        def mask_encrypted_extra(cls, encrypted_extra: str | None) -> str | None:
            return encrypted_extra
    
    assert has_custom_method(CustomSpec, "mask_encrypted_extra") is True


def test_has_custom_method_false() -> None:
    """Test has_custom_method returns False when method is not overridden."""
    assert has_custom_method(BaseEngineSpec, "mask_encrypted_extra") is False


def test_has_custom_method_missing() -> None:
    """Test has_custom_method returns False when method doesn't exist."""
    assert has_custom_method(BaseEngineSpec, "nonexistent_method") is False


def test_get_name_with_engine_name() -> None:
    """Test get_name returns engine_name when available."""
    spec = MockSpec()
    assert get_name(spec.__class__) == "Mock Database"


def test_get_name_fallback_to_engine() -> None:
    """Test get_name falls back to engine when engine_name is not set."""
    class NoNameSpec(BaseEngineSpec):
        engine = "fallback_engine"
    
    assert get_name(NoNameSpec) == "fallback_engine"


def test_format_markdown_table() -> None:
    """Test format_markdown_table formats headers and rows correctly."""
    headers = ["Name", "Age"]
    rows = [["Alice", 30], ["Bob", 25]]
    
    result = format_markdown_table(headers, rows)
    
    assert "| Name | Age |" in result
    assert "| --- | --- |" in result
    assert "| Alice | 30 |" in result
    assert "| Bob | 25 |" in result


def test_generate_focused_table() -> None:
    """Test generate_focused_table with basic parameters."""
    info = {
        "db1": {"feature1": True, "feature2": False},
        "db2": {"feature1": False, "feature2": True},
    }
    
    table, excluded = generate_focused_table(
        info,
        feature_keys=["feature1", "feature2"],
        column_labels=["Feature 1", "Feature 2"],
    )
    
    assert "| Database | Feature 1 | Feature 2 |" in table
    assert "| db1 | True | False |" in table
    assert "| db2 | False | True |" in table
    assert excluded == []


def test_generate_focused_table_with_filter() -> None:
    """Test generate_focused_table with filter function."""
    info = {
        "db1": {"feature1": True},
        "db2": {"feature1": False},
    }
    
    table, excluded = generate_focused_table(
        info,
        feature_keys=["feature1"],
        column_labels=["Feature 1"],
        filter_fn=lambda db_info: db_info["feature1"],
    )
    
    assert "| db1 | True |" in table
    assert "db2" not in table
    assert excluded == ["db2"]


def test_generate_focused_table_preserve_order() -> None:
    """Test generate_focused_table preserves order when requested."""
    info = {
        "zebra": {"feature1": True},
        "alpha": {"feature1": False},
    }
    
    table, _ = generate_focused_table(
        info,
        feature_keys=["feature1"],
        column_labels=["Feature 1"],
        preserve_order=True,
    )
    
    # Should preserve insertion order
    lines = table.split("\n")
    assert "zebra" in lines[2]
    assert "alpha" in lines[3]


def test_calculate_support_level_not_supported() -> None:
    """Test calculate_support_level returns 'Not supported' when no features supported."""
    db_info = {"feature1": False, "feature2": False}
    assert calculate_support_level(db_info, ["feature1", "feature2"]) == "Not supported"


def test_calculate_support_level_supported() -> None:
    """Test calculate_support_level returns 'Supported' when all features supported."""
    db_info = {"feature1": True, "feature2": True}
    assert calculate_support_level(db_info, ["feature1", "feature2"]) == "Supported"


def test_calculate_support_level_partial() -> None:
    """Test calculate_support_level returns 'Partial' when some features supported."""
    db_info = {"feature1": True, "feature2": False}
    assert calculate_support_level(db_info, ["feature1", "feature2"]) == "Partial"


def test_calculate_support_level_time_grains() -> None:
    """Test calculate_support_level with time grain features."""
    db_info = {
        "time_grains": {"SECOND": True, "MINUTE": False, "HOUR": True}
    }
    assert calculate_support_level(db_info, ["time_grains.SECOND", "time_grains.MINUTE"]) == "Partial"


def test_infer_category_aws() -> None:
    """Test infer_category detects AWS databases."""
    assert infer_category("Amazon Redshift") == "CLOUD_AWS"
    assert infer_category("aws Athena") == "CLOUD_AWS"


def test_infer_category_gcp() -> None:
    """Test infer_category detects GCP databases."""
    assert infer_category("Google BigQuery") == "CLOUD_GCP"
    assert infer_category("bigquery") == "CLOUD_GCP"


def test_infer_category_azure() -> None:
    """Test infer_category detects Azure databases."""
    assert infer_category("Azure SQL") == "CLOUD_AZURE"
    assert infer_category("microsoft sql server") == "CLOUD_AZURE"


def test_infer_category_traditional_rdbms() -> None:
    """Test infer_category detects traditional RDBMS."""
    assert infer_category("PostgreSQL") == "TRADITIONAL_RDBMS"
    assert infer_category("MySQL") == "TRADITIONAL_RDBMS"
    assert infer_category("SQLite") == "TRADITIONAL_RDBMS"


def test_infer_category_other() -> None:
    """Test infer_category returns OTHER for unknown databases."""
    assert infer_category("Unknown Database") == "OTHER"


def test_get_documentation_metadata_with_spec_metadata() -> None:
    """Test get_documentation_metadata uses spec metadata when available."""
    class SpecWithMetadata(BaseEngineSpec):
        engine = "test"
        metadata = {
            "pypi_packages": ["test-package"],
            "connection_string": "test://",
        }
    
    result = get_documentation_metadata(SpecWithMetadata, "Test DB")
    
    assert result["pypi_packages"] == ["test-package"]
    # Category should be inferred when not in metadata
    assert result["category"] == "OTHER"


def test_get_documentation_metadata_fallback() -> None:
    """Test get_documentation_metadata uses fallback when no metadata."""
    class SpecWithoutMetadata(BaseEngineSpec):
        engine = "test"
        sqlalchemy_uri_placeholder = "test://"
    
    result = get_documentation_metadata(SpecWithoutMetadata, "Test DB")
    
    assert result["pypi_packages"] == []
    assert result["connection_string"] == "test://"
    assert result["category"] == "OTHER"  # Fallback from infer_category


def test_get_documentation_metadata_inferred_category() -> None:
    """Test get_documentation_metadata infers category when not in metadata."""
    class SpecWithPartialMetadata(BaseEngineSpec):
        engine = "postgresql"
        metadata = {"pypi_packages": ["psycopg2"]}
    
    result = get_documentation_metadata(SpecWithPartialMetadata, "PostgreSQL")
    
    assert result["category"] == "TRADITIONAL_RDBMS"
