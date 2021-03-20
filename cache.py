from typing import Any, Dict, TypeVar, Generic, List
from dataclasses import dataclass
from functools import partial, update_wrapper

import redis

T = TypeVar("T")


@dataclass
class Cacheable(Generic[T]):
    key: T

    def dump_and_store(self, client: redis.Redis, value: T):
        self.store(client, self.dump(value))

    def store(self, client: redis.Redis, value: T):
        client.set(self.key, value)

    def get_value(self, client: redis.Redis) -> bytes:
        return client.get(self.key)

    def retrieve(self, client: redis.Redis) -> T:
        value = self.get_value(client)
        if value is None:
            return value

        return self.load(value)

    def dump(self, value: T) -> T:
        return value

    def load(self, value: T) -> T:
        return value


@dataclass
class CacheString(Cacheable[str]):
    def load(self, value: bytes) -> T:
        return value.decode("utf-8")


@dataclass
class CacheDictString(CacheString):
    dict_key: str

    def __new__(cls, dict_attribute_name=None, *args, **kwargs):
        if dict_attribute_name is not None:
            def make_cacheable(key):
                return cls(key=key, dict_key=dict_attribute_name)

            return make_cacheable

        return super().__new__(cls)

    def store(self, client: redis.Redis, value: str):
        client.hset(self.key, self.dict_key, value)

    def get_value(self, client: redis.Redis):
        return client.hget(self.key, self.dict_key)


@dataclass
class CacheDict(Cacheable[Dict[str, str]]):
    def store(self, client: redis.Redis, value: Dict[str, str]):
        client.hmset(self.key, value)

    def get_value(self, client: redis.Redis) -> Dict[str, str]:
        return client.hgetall(self.key)


@dataclass
class CacheList(Cacheable[List[str]]):
    def store(self, client: redis.Redis, value: List[str]):
        # There is no command to replace an entire list.
        client.delete(self.key)
        client.lpush(self.key, value)

    def get_value(self, client: redis.Redis):
        return client.lrange(self.key, 0, -1)


class RedisCache(redis.Redis):
    def init(self, url):
        self.connection_pool = redis.ConnectionPool.from_url(url)

    def cache_value(self, get_cache_key=None, make_cacheable=CacheString):
        """Decorate a function to automatically cache its return value.

        Stores/retrieves string values by default. To use other data-types,
        provide make_cacheable.

        get_cache_key can be defined in one of two ways:
            1. Pass it as an argument to this function.
            2. Use the cache_key method of the decorated function to decorate
               a function (with same args) that returns the cache key.
               e.g.,

               @cache.cache_value()
               def get_some_value(arg):
                   return DB.fetch(arg)

               @get_some_value.cache_key
               def get_some_value(arg):
                   return f"model-{arg}"

        make_cacheable should be a subclass of Cacheable.
        """
        client = self

        class _CacheValue:
            def __init__(self, func, get_cache_key, make_cacheable):
                self.func = func
                self.get_cache_key = get_cache_key
                self.make_cacheable = make_cacheable
                update_wrapper(self, func)

            def __call__(self, *args, **kwargs):
                cache_key = self._get_cache_key(*args, **kwargs)
                cacheable = self.make_cacheable(key=cache_key)
                value = cacheable.retrieve(client)

                if value is None:
                    value = self.func(*args, **kwargs)
                    cacheable.store(client, value)

                return value

            def __get__(self, instance, owner):
                return partial(self, instance)

            def cache_key(self, func):
                self.get_cache_key = func
                update_wrapper(self, func)
                return self

            def _get_cache_key(self, *args, **kwargs):
                if not self.get_cache_key:
                    raise ValueError("cache_value: must define get_cache_key.")

                return self.get_cache_key(*args, **kwargs)

        def decorator(func):
            return _CacheValue(func, get_cache_key, make_cacheable)

        return decorator

    def cache_string(self, get_cache_key=None):
        """Decorate a function to store a string."""
        return self.cache_value(get_cache_key=get_cache_key, make_cacheable=CacheString)

    def cache_dict_string(self, dict_key, get_cache_key=None):
        """Decorate a function to store a specific key inside a cached hash."""
        return self.cache_value(
            get_cache_key=get_cache_key,
            make_cacheable=CacheDictString(dict_key),
        )
