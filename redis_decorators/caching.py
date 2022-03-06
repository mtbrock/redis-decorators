from datetime import timedelta
from functools import partial, update_wrapper
from typing import Any, Callable, Optional, Union

from redis import Redis

from .cache_element import CacheDateTime, CacheElement, CacheElementSingleType
from .cacheable import (
    DictCacheable,
    DictCacheType,
    DictStringCacheable,
    ListCacheable,
    ListCacheType,
    StringCacheable,
)


class RedisCaching:
    """Provides decorators for automatic caching."""

    cache_cls = Redis
    _cache_instances = {}

    def __init__(self, url=None, **kwargs):
        self._default_cache_kwargs = {"decode_responses": True, "socket_timeout": 15}
        self.init(url, **kwargs)

    def init(self, url, **kwargs):
        self._url = url
        self._cache_kwargs = {
            **self._default_cache_kwargs,
            **kwargs,
        }

    def get_cache(self) -> Redis:
        if self._url in self._cache_instances:
            return self._cache_instances.get(self._url)

        cache = self.cache_cls.from_url(self._url, **self._cache_kwargs)
        self._cache_instances[self._url] = cache
        return cache

    def delete(self, cache_key: str):
        self.get_cache().delete(cache_key)

    def cache_value(
        self,
        cache_element: CacheElement,
        get_cache_key: Callable[..., str] = None,
        expire_in: Union[int, timedelta] = None,
    ):
        """Decorate a function to automatically cache its return value.

        Wrapper does two things:
            1. If cached value does not exist, cache the return value of the function.
            2. If cached value exists, return it instead of calling the function.

        Args:
            cache_element (CacheElement): Instance used to get and set cache value.
            get_cache_key (Callable): Function that returns name of cache value.
                Accepts the same arguments as the decorated function.
            expire_in (Union[int, timedelta]): Number of seconds until this key
                expires after being set. Can be a datetime.timedelta object.

        Examples:
            Decorate a function that returns a string:
                .. code-block:: python

                    @cache.cache_string(get_cache_key=lambda arg: f'object:{arg}')
                    def expensive_fetch_operation(arg) -> str:
                        ...
                        return computed_value

            Use `cache_key` of decorated function to set `get_cache_key`:
                .. code-block:: python

                    @cache.cache_string()
                    def expensive_fetch_operation(arg) -> str:
                        ...
                        return computed_value

                    @expensive_fetch_operation.cache_key
                    def expensive_fetch_operation_cache_key(arg) -> str:
                        ...
                        return computed_value
        """

        def decorator(func):
            return CacheValueWrapper(
                self, func, cache_element, get_cache_key, expire_in
            )

        return decorator

    def cache_string(self, get_cache_key: Callable[..., str] = None, **kwargs):
        """Decorate a function to store a string."""
        return self.cache_value(
            CacheElementSingleType[str](cacheable=StringCacheable()),
            get_cache_key,
            **kwargs,
        )

    def cache_dict(self, get_cache_key: Callable[..., str] = None, **kwargs):
        """Decorate a function to store a dictionary {str: str}."""
        return self.cache_value(
            CacheElementSingleType[DictCacheType](cacheable=DictCacheable()),
            get_cache_key,
            **kwargs,
        )

    def cache_dict_string(self, dict_key: str, get_cache_key=None, **kwargs):
        """Decorate a function to store a specific key inside a cached hash."""
        return self.cache_value(
            CacheElementSingleType[str](cacheable=DictStringCacheable(dict_key)),
            get_cache_key,
            **kwargs,
        )

    def cache_list(self, get_cache_key: Callable[..., str] = None, **kwargs):
        """Decorate a function to store a list of strings."""
        return self.cache_value(
            CacheElementSingleType[ListCacheType](cacheable=ListCacheable()),
            get_cache_key,
            **kwargs,
        )

    def cache_datetime(self, get_cache_key: Callable[..., str] = None, **kwargs):
        """Decorate a function to store a datetime."""
        return self.cache_value(CacheDateTime(), get_cache_key, **kwargs)


class CacheValueWrapper:
    def __init__(
        self,
        caching: RedisCaching,
        func: Callable,
        cache_element: CacheElement,
        get_cache_key: Optional[Callable[..., str]] = None,
        expire_in: Union[int, timedelta] = None,
    ):
        self._caching = caching
        self._func = func
        self._cache_element = cache_element
        self._get_cache_key = get_cache_key
        self._expire_in = expire_in
        update_wrapper(self, func)

    def __call__(self, *args: Any, **kwargs: Any):
        cache_key = self._calculate_cache_key(*args, **kwargs)
        value = self._cache_element.get_value(self._caching.get_cache(), cache_key)

        if value is None:
            client = self._caching.get_cache()
            value = self._func(*args, **kwargs)
            self._cache_element.set_value(client, cache_key, value)
            expire_in = self._calculate_expire_in(value, *args, **kwargs)

            if expire_in:
                client.expire(cache_key, expire_in)

        return value

    def __get__(self, instance, owner):
        return partial(self, instance)

    def cache_key(self, func):
        self._get_cache_key = func
        return func

    def expire_in(self, func):
        self._expire_in = func
        return func

    def _calculate_expire_in(self, value, *args, **kwargs):
        if callable(self._expire_in):
            kwargs["value"] = value
            return self._expire_in(*args, **kwargs)

        return self._expire_in

    def _calculate_cache_key(self, *args: Any, **kwargs: Any):
        if self._get_cache_key is None:
            arg_str = ':'.join([self._func.__name__, *[str(arg) for arg in args], str(kwargs)])
            return ":".join(["redis_decorators", arg_str])

        return self._get_cache_key(*args, **kwargs)


def build_redis_url(host, password, db, use_secure=True):

    prefix = "rediss" if use_secure else "redis"

    if password:
        url = f"{prefix}://:{password}@{host}"
    else:
        url = f"{prefix}://{host}"

    if db:
        url = f"{url}/{db}"

    return url
