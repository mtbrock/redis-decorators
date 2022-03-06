from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List
from unittest import mock

import pytest

from redis_decorators import build_redis_url

now = datetime.utcnow()
NOVAL = object()


@dataclass
class DecoratorFunctionTestConfig:
    decorator_name: str
    cache_get: str
    cache_set: str
    return_value: str
    get_value: str
    set_value: str

    extra_decorator_kwargs: Dict = field(default_factory=dict)
    extra_get_args: List = field(default_factory=list)
    extra_set_args: List = field(default_factory=list)
    extra_set_kwargs: List = field(default_factory=dict)


class DecoratedFunction:
    function: Callable
    get_cache_key: Callable
    inner_mock: mock.Mock


@pytest.mark.parametrize(
    "config",
    [
        DecoratorFunctionTestConfig(
            decorator_name="cache_string",
            cache_get="get",
            cache_set="set",
            return_value="string-value",
            get_value="string-value",
            set_value="string-value",
        ),
        DecoratorFunctionTestConfig(
            decorator_name="cache_dict",
            cache_get="hgetall",
            cache_set="hset",
            return_value={"hash": "value"},
            get_value={"hash": "value"},
            set_value=NOVAL,
            extra_set_kwargs={"mapping": {"hash": "value"}},
        ),
        DecoratorFunctionTestConfig(
            decorator_name="cache_dict_string",
            cache_get="hget",
            cache_set="hset",
            return_value="string-value",
            get_value="string-value",
            set_value="dict-key",
            extra_decorator_kwargs=dict(dict_key="dict-key"),
            extra_get_args=["dict-key"],
            extra_set_args=["string-value"],
        ),
        DecoratorFunctionTestConfig(
            decorator_name="cache_list",
            cache_get="lrange",
            cache_set="rpush",
            return_value=["list", "value"],
            get_value=["list", "value"],
            set_value="list",
            extra_get_args=[0, -1],
            extra_set_args=["value"],
        ),
        DecoratorFunctionTestConfig(
            decorator_name="cache_datetime",
            cache_get="get",
            cache_set="set",
            return_value=now,
            get_value=now.isoformat(),
            set_value=now.isoformat(),
        ),
    ],
)
class TestRedisCachingDecorators:
    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def setup_cls(cls, testing_redis_caching):
        cls.caching = testing_redis_caching()
        cls.cache = cls.caching.get_cache()

    @pytest.fixture(scope="function", autouse=True)
    def setup_config(self, config):
        for key in self.cache.scan_iter('*'):
            self.cache.delete(key)

        self.value_decorator = getattr(self.caching, config.decorator_name)
        self.wrapped_function = mock.Mock()
        self.get_cache_key = mock.Mock(return_value="cache-key")

    def mock_cache(self, cache, methods, side_effects):
        return mock.patch.multiple(
            cache,
            **{
                method: mock.Mock(side_effect=side_effect)
                for method, side_effect in zip(methods, side_effects)
            },
        )

    def test_get_cache_key_not_defined(self, config):
        cache_key = 'redis_decorators:decorated_function:123:abc:{}'
        assert cache_key not in self.cache

        @self.value_decorator(**config.extra_decorator_kwargs)
        def decorated_function(arg1, arg2):
            return config.return_value

        decorated_function("123", "abc")
        assert cache_key in self.cache

    def test_function_declaration(self, config):
        @self.value_decorator(
            get_cache_key=self.get_cache_key, **config.extra_decorator_kwargs
        )
        def decorated_function(arg1, arg2):
            self.wrapped_function(arg1, arg2)
            return config.return_value

        self._test_decorated_function(
            config, decorated_function, self.get_cache_key, self.wrapped_function
        )

    def test_function_declaration__with_cache_key_decorator(self, config):
        @self.value_decorator(**config.extra_decorator_kwargs)
        def decorated_function(arg1, arg2):
            self.wrapped_function(arg1, arg2)
            return config.return_value

        @decorated_function.cache_key
        def decorated_function_cache_key(arg1, arg2):
            return self.get_cache_key(arg1, arg2)

        self._test_decorated_function(
            config, decorated_function, self.get_cache_key, self.wrapped_function
        )

    def test_class_declaration(self, config):
        wrapped_function = self.wrapped_function

        # If the decorated function is in a class, get_cache_key takes self.
        # Not sure how/if I should get around that.
        def get_cache_key(_, arg1, arg2):
            return self.get_cache_key(arg1, arg2)

        class MyClass:
            @self.value_decorator(
                get_cache_key=get_cache_key, **config.extra_decorator_kwargs
            )
            def decorated_function(self, arg1, arg2):
                wrapped_function(arg1, arg2)
                return config.return_value

        instance = MyClass()
        self._test_decorated_function(
            config,
            lambda *args, **kwargs: instance.decorated_function(*args, **kwargs),
            self.get_cache_key,
            self.wrapped_function,
        )

    def test_class_declaration__with_cache_key_decorator(self, config):
        wrapped_function = self.wrapped_function
        get_cache_key = self.get_cache_key

        class MyClass:
            @self.value_decorator(
                get_cache_key=get_cache_key, **config.extra_decorator_kwargs
            )
            def decorated_function(self, arg1, arg2):
                wrapped_function(arg1, arg2)
                return config.return_value

            @decorated_function.cache_key
            def decorated_function_cache_key(self, arg1, arg2):
                return get_cache_key(arg1, arg2)

        instance = MyClass()
        self._test_decorated_function(
            config,
            lambda *args, **kwargs: instance.decorated_function(*args, **kwargs),
            self.get_cache_key,
            self.wrapped_function,
        )

    def _test_decorated_function(
        self, config, decorated_function, get_cache_key, wrapped_function
    ):
        cache_get_function = getattr(self.cache, config.cache_get)
        cache_set_function = getattr(self.cache, config.cache_set)
        with self.mock_cache(
            self.cache,
            [config.cache_get, config.cache_set],
            [cache_get_function, cache_set_function],
        ):
            cache_get_mocked = getattr(self.cache, config.cache_get)
            cache_set_mocked = getattr(self.cache, config.cache_set)
            # Value has not been stored yet.
            assert "cache-key" not in self.cache

            # 1. Cache returns None because value does not exist.
            # 2. Wrapped function is called to get value.
            # 3. Value is stored.
            returned = decorated_function("123", "abc")
            assert returned == config.return_value
            assert "cache-key" in self.cache
            wrapped_function.assert_called_once_with("123", "abc")
            get_cache_key.assert_called_once_with("123", "abc")
            cache_get_mocked.assert_called_once_with(
                "cache-key", *config.extra_get_args
            )
            set_args = []
            if config.set_value is not NOVAL:
                set_args.append(config.set_value)

            cache_set_mocked.assert_called_once_with(
                "cache-key",
                *set_args,
                *config.extra_set_args,
                **config.extra_set_kwargs,
            )

            wrapped_function.reset_mock()
            get_cache_key.reset_mock()
            cache_get_mocked.reset_mock()
            cache_set_mocked.reset_mock()

            # 1. Value is fetched from cache.
            # 2. Wrapped function is not called.
            returned = decorated_function("123", "abc")
            assert returned == config.return_value
            wrapped_function.assert_not_called()
            get_cache_key.assert_called_once_with("123", "abc")
            cache_get_mocked.assert_called_once_with(
                "cache-key", *config.extra_get_args
            )
            cache_set_mocked.assert_not_called()

    def test_expiration(self):
        cache = self.caching.get_cache()
        key = "cache-key"
        value = "return-value-that-expires"

        def get_cache_key(arg1):
            return key

        @self.caching.cache_string(
            get_cache_key=get_cache_key, expire_in=timedelta(seconds=12)
        )
        def decorated_function(arg1):
            return value

        assert cache.ttl(key) == -2
        return_value = decorated_function(123)
        assert cache.ttl(key) == 12
        assert key in cache
        assert return_value == value

    def test_expire_in_decorator(self):
        cache = self.caching.get_cache()
        key = "cache-key"
        value = "return-value-that-expires"

        def get_cache_key(arg1):
            return key

        @self.caching.cache_string(
            get_cache_key=get_cache_key, expire_in=timedelta(seconds=1)
        )
        def decorated_function(arg1):
            return value

        @decorated_function.expire_in
        def value_expires_in(arg12, value):
            return 15

        assert cache.ttl(key) == -2
        return_value = decorated_function(123)
        assert cache.ttl(key) == 15
        assert key in cache
        assert return_value == value


def test_build_redis_url():
    assert build_redis_url("redis:6379", None, None) == "rediss://redis:6379"
    assert build_redis_url("redis:6379", "pass", None) == "rediss://:pass@redis:6379"
    assert build_redis_url("redis:6379", "pass", 2) == "rediss://:pass@redis:6379/2"
    assert (
        build_redis_url("redis:6379", "pass", 2, False) == "redis://:pass@redis:6379/2"
    )
