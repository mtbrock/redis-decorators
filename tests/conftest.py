import pytest
from unittest.mock import patch

from redis_decorators import RedisCaching, FakeRedis


def pytest_addoption(parser):
    parser.addoption('--redis-url', action='store', default=None)


@pytest.fixture(scope='session')
def testing_redis_caching(pytestconfig):
    redis_url = pytestconfig.getoption('redis_url')
    if redis_url:
        def redis_caching(**kwargs):
            return RedisCaching(redis_url, **kwargs)

        return redis_caching


    class _RedisCaching(RedisCaching):
        cache_cls = FakeRedis

    return _RedisCaching
