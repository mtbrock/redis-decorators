from functools import partial, update_wrapper
from typing import Any, Callable, Optional

from redis import Redis

from .cache_element import CacheElement


class CacheValue():
    def __init__(
        self,
        client: Redis,
        func: Callable,
        cache_element: CacheElement,
        get_cache_key: Optional[Callable[..., str]],
    ):
        self.client = client
        self.func = func
        self.cache_element = cache_element
        self.get_cache_key = get_cache_key
        update_wrapper(self, func)

    def __call__(self, *args: Any, **kwargs: Any):
        cache_key = self._get_cache_key(*args, **kwargs)
        value = self.cache_element.get_value(self.client, cache_key)

        if value is None:
            value = self.func(*args, **kwargs)
            self.cache_element.set_value(self.client, cache_key, value)

        return value

    def __get__(self, instance, owner):
        return partial(self, instance)

    def cache_key(self, func):
        self.get_cache_key = func
        update_wrapper(self, func)
        return self

    def _get_cache_key(self, *args: Any, **kwargs: Any):
        if not self.get_cache_key:
            raise ValueError('cache_value: must define get_cache_key.')

        return self.get_cache_key(*args, **kwargs)
