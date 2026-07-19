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

from superset.db_engine_specs import doris, starrocks, starrocks_doris_types

SHARED_TYPES = [
    "TINYINT",
    "LARGEINT",
    "DOUBLE",
    "HLL",
    "BITMAP",
    "ARRAY",
    "MAP",
    "STRUCT",
]


def test_shared_types_reexported_are_identical() -> None:
    for name in SHARED_TYPES:
        shared = getattr(starrocks_doris_types, name)
        assert getattr(doris, name) is shared
        assert getattr(starrocks, name) is shared


def test_visit_names_match_type_name() -> None:
    for name in SHARED_TYPES:
        assert getattr(starrocks_doris_types, name).__visit_name__ == name


def test_container_python_types() -> None:
    assert starrocks_doris_types.ARRAY().python_type is list
    assert starrocks_doris_types.MAP().python_type is dict
    assert starrocks_doris_types.STRUCT().python_type is None
