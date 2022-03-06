from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Generic, List, Optional, TypeVar

from redis import Redis

StoreType = TypeVar("StoreType")
ListCacheType = List[str]
DictCacheType = Dict[str, str]


class Cacheable(Generic[StoreType], ABC):
    """Performs caching store and fetch operations for a specific type.

    Subclass to define how to handle a specific type.
    """

    @abstractmethod
    def store(self, client: Redis, key: str, value: StoreType) -> None:
        """Store a value in cache.

        Args:
            client (Redis): Cache to store in.
            key (str): Name of cache value.
            value (StoreType): Value to store.

        Returns:
            None
        """
        pass  # pragma: nocover

    @abstractmethod
    def fetch(self, client: Redis, key: str) -> Optional[StoreType]:
        """Fetch a value from cache.

        Args:
            client (Redis): Cache to fetch from.
            key (str): Name of cache value.

        Returns:
            StoreType or None: Value fetched from cache or None if no value exists.
        """
        pass  # pragma: nocover


class StringCacheable(Cacheable[str]):
    def store(self, client: Redis, key: str, value: str):
        client.set(key, value)

    def fetch(self, client: Redis, key: str) -> Optional[str]:
        return client.get(key)


@dataclass
class DictStringCacheable(Cacheable[str]):
    """
    Attributes:
        dict_key (str): Name of hash value.
    """

    dict_key: str

    def store(self, client: Redis, key: str, value: str):
        client.hset(key, self.dict_key, value)

    def fetch(self, client: Redis, key: str) -> Optional[str]:
        return client.hget(key, self.dict_key)


class DictCacheable(Cacheable[DictCacheType]):
    def store(self, client: Redis, key: str, value: DictCacheType):
        client.hset(key, mapping=value)

    def fetch(self, client: Redis, key: str) -> Optional[DictCacheType]:
        return client.hgetall(key) or None


class ListCacheable(Cacheable[ListCacheType]):
    def store(self, client: Redis, key: str, value: ListCacheType):
        client.delete(key)
        client.rpush(key, *value)

    def fetch(self, client: Redis, key: str) -> Optional[ListCacheType]:
        return client.lrange(key, 0, -1) or None
