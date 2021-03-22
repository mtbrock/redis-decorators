from unittest import mock

import pytest

_cache_data = {}


class _MockCache:
    def __init__(self, data):
        self.data = data

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):  # noqa
        self.data[key] = value.encode()

    def hget(self, key, dict_key):
        value = self.data.get(key, {})
        return value.get(dict_key)

    def hset(self, key, dict_key, value):
        dict_value = self.data.get(key, {})
        dict_value[dict_key] = value.encode()
        self.data[key] = dict_value


class MockCache:
    def __init__(self, data):
        self.data = data

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):  # noqa
        self.data[key] = value.encode()

    def hget(self, key, dict_key):
        value = self.data.get(key, {})
        return value.get(dict_key)

    def hset(self, key, dict_key, value):
        dict_value = self.data.get(key, {})
        dict_value[dict_key] = value.encode()
        self.data[key] = dict_value


class CacheValueClass:
    @cache.cache_value()
    def get_cache_value(self, arg):
        return "cached_cls_value"

    @get_cache_value.cache_key
    def get_cache_value(self, arg):
        return f"cached_cls_key-{arg}"

    @cache.cache_dict_string("dict-key")
    def get_cache_dict_value(self, arg):
        return "cached_dict_value"

    @get_cache_dict_value.cache_key
    def get_cache_dict_value(self, arg):
        return f"cached_dict_key-{arg}"


class TestCache:
    @pytest.fixture(autouse=True, scope="function")
    def mock_cache(self):
        self.cache_data = {}
        mock_cache = MockCache(self.cache_data)
        with mock.patch.multiple(
            cache,
            **{
                "get": mock.Mock(side_effect=mock_cache.get),
                "set": mock.Mock(side_effect=mock_cache.set),
                "hget": mock.Mock(side_effect=mock_cache.hget),
                "hset": mock.Mock(side_effect=mock_cache.hset),
            },
        ):
            self.cache = cache
            yield

    def test_cache_value_decorator(self):
        obj = CacheValueClass()
        key = "cached_cls_key-123"
        cache_value = "cached_cls_value"

        assert key not in self.cache_data

        # Verify value is not retrieved from cache but gets stored in cache.
        return_value = obj.get_cache_value("123")
        self.cache.get.assert_called_once_with(key)
        self.cache.set.assert_called_once_with(key, cache_value)
        assert return_value == cache_value
        assert self.cache_data[key] == cache_value.encode()

        # Change value in cache and verify it is retrieved.
        self.cache.get.reset_mock()
        self.cache.set.reset_mock()
        new_value = "new_cached_value"
        self.cache_data[key] = new_value.encode()

        return_value = obj.get_cache_value("123")
        self.cache.get.assert_called_once_with(key)
        self.cache.set.assert_not_called()
        assert return_value == new_value
        assert self.cache_data[key] == new_value.encode()

    def test_cache_dict_decorator(self):
        obj = CacheValueClass()
        key = "cached_dict_key-555"
        dict_key = "dict-key"
        cache_value = "cached_dict_value"
        cached_dict = {dict_key: cache_value.encode()}

        assert key not in self.cache_data

        # Verify value is not retrieved from cache but gets stored in cache.
        return_value = obj.get_cache_dict_value("555")
        self.cache.hget.assert_called_once_with(key, dict_key)
        self.cache.hset.assert_called_once_with(key, dict_key, cache_value)
        assert return_value == cache_value
        assert self.cache_data[key] == cached_dict

        # Change value in cache and verify it is retrieved.
        self.cache.hget.reset_mock()
        self.cache.hset.reset_mock()
        new_value = "new_cached_value"
        new_cached_dict = {dict_key: new_value.encode()}
        self.cache_data[key] = new_cached_dict

        return_value = obj.get_cache_dict_value("555")
        self.cache.hget.assert_called_once_with(key, dict_key)
        self.cache.hset.assert_not_called()
        assert return_value == new_value
        assert self.cache_data[key] == new_cached_dict
