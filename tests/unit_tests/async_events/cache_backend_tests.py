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

from typing import Any, cast
from unittest import mock

import redis

from superset.async_events.cache_backend import (
    RedisCacheBackend,
    RedisSentinelCacheBackend,
    RedisStreamCommandsMixin,
)


class _Backend(RedisStreamCommandsMixin):
    pass


def _make_backend() -> tuple[_Backend, mock.Mock]:
    backend = _Backend()
    cache = mock.Mock()
    backend._cache = cast("redis.Redis[Any]", cache)
    return backend, cache


def test_backends_share_mixin() -> None:
    assert issubclass(RedisCacheBackend, RedisStreamCommandsMixin)
    assert issubclass(RedisSentinelCacheBackend, RedisStreamCommandsMixin)
    assert RedisCacheBackend.MAX_EVENT_COUNT == 100
    assert RedisSentinelCacheBackend.MAX_EVENT_COUNT == 100


def test_set_delete_publish_pubsub_delegate() -> None:
    backend, cache = _make_backend()
    backend.set("k", "v", ex=1, px=2, nx=True, xx=False)
    cache.set.assert_called_once_with("k", "v", ex=1, px=2, nx=True, xx=False)

    backend.delete("a", "b")
    cache.delete.assert_called_once_with("a", "b")

    backend.publish("chan", "msg")
    cache.publish.assert_called_once_with("chan", "msg")

    backend.pubsub()
    cache.pubsub.assert_called_once_with()


def test_xadd_delegates() -> None:
    backend, cache = _make_backend()
    backend.xadd("stream", {"a": "1"}, event_id="5-0", maxlen=10)
    cache.xadd.assert_called_once_with("stream", {"a": "1"}, "5-0", 10)


def test_xrange_defaults_to_max_event_count() -> None:
    backend, cache = _make_backend()
    backend.xrange("stream")
    cache.xrange.assert_called_once_with(
        "stream", "-", "+", RedisStreamCommandsMixin.MAX_EVENT_COUNT
    )


def test_xrange_respects_explicit_count() -> None:
    backend, cache = _make_backend()
    backend.xrange("stream", start="1", end="2", count=7)
    cache.xrange.assert_called_once_with("stream", "1", "2", 7)
