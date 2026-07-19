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
from marshmallow import Schema, ValidationError

from superset.themes.schemas import (
    BaseThemeSchema,
    ThemePostSchema,
    ThemePutSchema,
)
from superset.utils import json


@pytest.mark.parametrize("schema_cls", [ThemePostSchema, ThemePutSchema])
def test_theme_schemas_share_base(schema_cls: type[Schema]) -> None:
    assert issubclass(schema_cls, BaseThemeSchema)
    fields = schema_cls().fields
    assert set(fields) == {"theme_name", "json_data"}


@pytest.mark.parametrize("schema_cls", [ThemePostSchema, ThemePutSchema])
def test_blank_theme_name_rejected(schema_cls: type[Schema]) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema_cls().load({"theme_name": "   ", "json_data": json.dumps({})})
    assert "theme_name" in excinfo.value.messages


@pytest.mark.parametrize("schema_cls", [ThemePostSchema, ThemePutSchema])
def test_invalid_json_rejected(schema_cls: type[Schema]) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema_cls().load({"theme_name": "t", "json_data": "{not json"})
    assert "json_data" in excinfo.value.messages


@pytest.mark.parametrize("schema_cls", [ThemePostSchema, ThemePutSchema])
def test_sanitized_json_written_back(schema_cls: type[Schema]) -> None:
    result = schema_cls().load(
        {
            "theme_name": "t",
            "json_data": json.dumps(
                {"token": {"brandSpinnerUrl": "javascript:alert('xss')"}}
            ),
        }
    )
    assert json.loads(result["json_data"])["token"]["brandSpinnerUrl"] == ""
