from typing import Callable

from redis import ConnectionPool, Redis

from .cache_element import CacheDateTime, CacheElement, CacheElementSingleType
from .cacheable import (
    DictCacheable,
    DictCacheType,
    DictStringCacheable,
    ListCacheable,
    ListCacheType,
    StringCacheable
)
from .decorators import CacheValue


class RedisCache(Redis):
    """Subclass of :class:`Redis` that provides function decorators.

    Decorate a function with a wrapper that does two things:
        1. Cache the return value of the function.
        2. If cached value exists, return it instead of calling the function.

    Examples:
        Decorate a function that returns a string:
            .. code-block:: python

                @cache.cache_string(get_cache_key=lambda arg: f'object:{arg}')
                def expensive_fetch_operation(arg) -> str:
                    ...
                    return computed_value

        Use :meth:`cache_key` of decorated function to set :meth:`get_cache_key`:
    """
    def init(self, url):
        self.connection_pool = ConnectionPool.from_url(url)

    def cache_value(self, cache_element: 'CacheElement', get_cache_key: Callable[..., str] = None):
        """Decorate a function to automatically cache its return value.

        Args:
            cache_element (CacheElement): Instance used to get and set cache value.
            get_cache_key (Callable): Function that returns name of cache value.
                Accepts the same arguments as the decorated function.

        Tips:
            You can use the cache_key method of the decorated function to decorate
            a function (with same args) that returns the cache key.
            e.g.,

            .. code-block:: python

                @cache.cache_string()
                def get_some_value(arg):
                    return DB.fetch(arg)

                @get_some_value.cache_key
                def get_some_value(arg):
                    return f'model-{arg}'
        """
        def decorator(func):
            return CacheValue(self, func, cache_element, get_cache_key)

        return decorator

    def cache_string(self, get_cache_key: Callable[..., str] = None):
        """Decorate a function to store a string."""
        return self.cache_value(
            CacheElementSingleType[str](cacheable=StringCacheable()),
            get_cache_key,
        )

    def cache_dict(self, get_cache_key: Callable[..., str] = None):
        """Decorate a function to store a dictionary {str: str}."""
        return self.cache_value(
            CacheElementSingleType[DictCacheType](cacheable=DictCacheable()),
            get_cache_key,
        )

    def cache_dict_string(self, dict_key: str, get_cache_key=None):
        """Decorate a function to store a specific key inside a cached hash."""
        return self.cache_value(
            CacheElementSingleType[str](cacheable=DictStringCacheable()),
            get_cache_key,
        )

    def cache_datetime(self, get_cache_key: Callable[..., str] = None):
        """Decorate a function to store a datetime."""
        return self.cache_value(CacheDateTime(), get_cache_key)

    def cache_list(self, get_cache_key: Callable[..., str] = None):
        """Decorate a function to store a list of strings."""
        return self.cache_value(
            CacheElementSingleType[ListCacheType](cacheable=ListCacheable()),
            get_cache_key,
        )
