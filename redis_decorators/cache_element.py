from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Optional, TypeVar

from redis import Redis

from .cacheable import Cacheable, StringCacheable

FetchType = TypeVar("FetchType")
StoreType = TypeVar("StoreType")


class CacheElement(Generic[FetchType, StoreType], ABC):
    """Get and set cache values.

    Attributes:
        cacheable (Cacheable): Instance used to store and fetch values.
    """

    cacheable: Cacheable[StoreType]

    def get_value(self, client: Redis, key: str) -> Optional[FetchType]:
        """Returns cached value or None if no value exists."""
        value = self.cacheable.fetch(client, key)
        if value is None:
            return None

        return self.load(value)

    def set_value(self, client: Redis, key: str, value: FetchType) -> None:
        """Set value in cache.

        Args:
            client (Redis): Cache to fetch from.
            key (str): Name of cache value.

        Returns:
            None
        """
        self.cacheable.store(client, key, self.dump(value))

    @abstractmethod
    def load(self, value: StoreType) -> FetchType:
        """Load value from cache into expected Python type."""
        pass  # pragma: nocover

    @abstractmethod
    def dump(self, value: FetchType) -> StoreType:
        """Dump value from Python type into type expected by cache."""
        pass  # pragma: nocover


@dataclass
class CacheElementSingleType(CacheElement[FetchType, FetchType]):
    """A CacheElement that fetches the same type that it stores.

    By default, values are passed to and from cache as-is, i.e. no serialization
    or deserialization is performed.

    For example, a string can be stored and fetched without modification whereas
    a datetime would need to be serialized for storage and deserialized for
    retrieval.
    """

    cacheable: Cacheable[FetchType]

    def load(self, value: FetchType) -> FetchType:
        return value

    def dump(self, value: FetchType) -> FetchType:
        return value


@dataclass
class CacheDateTime(CacheElement[datetime, str]):
    """Store and fetch datetime values with string serialization."""

    cacheable: Cacheable[str] = StringCacheable()

    def dump(self, value: datetime) -> str:
        return value.isoformat()

    def load(self, value: str) -> datetime:
        return datetime.fromisoformat(value)
