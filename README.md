![badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/mtbrock/a4b117f575fe24d0555e1bee9e682013/raw/pytest-coverage__master.json)

# Redis Decorators
Redis cache decorators for automatically caching function return values in Python.

## Get Started
### Install
```
pip install redis_decorators
```

### Initialize
The main class, `RedisCaching`, will initialize Redis for you.
```
from redis_decorators import RedisCaching

caching = RedisCaching('redis://redis:6379')
cache = caching.get_cache()  # Redis instance
```

## Usage
The simplest way to start caching return values is to use one of the `RedisCaching.cache_*`
decorators. The cache key is generated automatically based on the function name and arguments.
```python
@caching.cache_string()
def my_string_function(arg1, arg2):
    # ... do some calculation
    return 'my_value'
```

### Calculate Cache Key
If you want to have control over how cache keys are calculated, you can specify `get_cache_key`
in the following ways:

#### Lambda function
```python
@caching.cache_string(get_cache_key=lambda arg1: return f'{arg1}-cache-key')
def my_string_function(arg1):
    return 'my_value'
```

#### Separate function definition
The decorator returns a wrapper that allows you to define additional properties:
```python
@caching.cache_string()
def my_string_function(arg1):
    return 'my_value'

# The cache key function gets the same arguments as the value function.
@my_string_function.cache_key
def my_string_function_cache_key(arg1):
    return f'{arg1}-cache-key
```

### Key Expiration
You can define an expiration time in seconds or with a `datetime.timedelta`, similar to how you
would define the cache key calculation:
```python
# Define a static expiration time with expire_in kwarg:
@caching.cache_string(expire_in=60)  # Cache key expires in 60 seconds.
def my_string_function(arg1):
    return 'my_value'

# Calculate expiration time with a function:
@caching.cache_string()
def my_string_function(arg1):
    return 'my_value'

@my_string_function.expire_in
def my_string_function_expire_in(arg1):
    # ... calculate seconds or a timedelta
    return datetime.now() - some_other_datetime
```

## Included Value Types
There are decorators already defined for various common datatypes.

| Decorator | Wrapped Function Return Type | Redis Set Function | Redis Get Function |
| --------- | ---------------------------- | ------------------ | ------------------ |
| `RedisCaching.cache_str` | `str` | `set` | `get` |
| `RedisCaching.cache_dict_str` | `str` | `hset` | `hget` |
| `RedisCaching.cache_dict` | `dict` | `hset` | `hgetall` |
| `RedisCaching.cache_list` | `list` | `rpush` | `lrange` |

You can see how the various datatypes are stored and fetched in [cacheable.py](redis_decorators/cacheable.py).

### Special Decorators
All decorators accept the same arguments except for the following:

- #### RedisCaching.cache_dict_str
This decorator stores a value inside a cached dictionary (a redis hash).
**Usage**
```python
@caching.cache_dict_string(dict_key='foo', get_cache_key=lambda arg1: return f'{arg1}-cache-key')
def my_nested_value(arg1):
    return "bar"
```
In the above example, calling `my_nested_value('hello')` results in a cached hash with key `hello-cache-key` and value `{ 'foo': 'bar' }.

## Custom Data Types
You can cache and retrieve any arbitrary data type as long as it can be serialized/transformed into a type that redis supports.

### Examples
#### Cache a `decimal.Decimal`
This example serializes `Decimal` objects to strings and coerces fetched values back into `Decimal` objects.

```python
# Define a custom `CacheElement`
class CacheDecimal(CacheElement[Decimal, str]):
    cacheable: Cacheable[str] = StringCacheable()

    def load(self, value: str) -> Decimal:
        return Decimal(value)

    def dump(self, value: Decimal) -> str:
        return str(value)

# Use the custom CacheElement with RedisCaching.cache_value
@caching.cache_value(CacheDecimal())
def my_decimal_function(arg1):
    return Decimal('1.234')
```

#### Cache your own serializable type
If you have a custom data type that is serializable, you can define a custom `CacheElement` to cache it.

```python
class MyObject:
    def serialize(self):
        # return a string representation

    @classmethod
    def from_str(cls, value):
        # parse value and return a new instance


class CacheMyObject(CacheElement[MyObject, str]):
    cacheable: Cacheable[str] = StringCacheable()

    def load(self, value: str) -> MyObject:
        return Decimal.from_str(value)

    def dump(self, value: MyObject) -> str:
        return value.serialize()

# Use the custom CacheElement with RedisCaching.cache_value
@caching.cache_value(CacheMyObject())
def my_decimal_function(arg1):
    return MyObject()
```

Note the underlying `Cacheable` in these examples is `StringCacheable`. If you want to store your object as a different type,
you can use other `Cacheable` classes to do so. For example, to store your object as a dictionary, you would
use the `DictCacheable` instead of `StringCacheable`. With `DictCacheable`, the `load` function would take
a `dict` object as the `value` argument and return your object type; the `dump` function would take your
object type as the `value` argument and return a `dict`.

See [cacheable.py](redis_decorators/cacheable.py) and [cache_element.py](redis_decorators/cache_element.py) for examples of
`Cacheable` and `CacheElement`, respectively.

## Advanced Usage
### Deferred Init
If your redis config is not available at the time `RedisCaching` is initialized, you can defer initialization using `RedisCaching.init`.
This use case is common when using web frameworks like Flask or Pyramid, where you may have modules that use cache decorators that get
imported before your app configuration is initialized.

You can create a `RedisCaching` instance without providing a URL or redis config and use decorators throughout your code base. The cache functions
will get registered before the connection to redis is made.

#### Example
Create an instance of `RedisCaching` in, for instance, `extensions.py`:
```python
from redis_decorators import RedisCaching
caching = RedisCaching()
```

Use the cache decorators wherever you need to:
```python
from extensions import caching

@caching.cache_string()
def my_cached_string_function():
    # ...
```

Initialize your `RedisCaching` instance after your config has been initialized:
```python
from extensions import caching

def app():
    # initialize app and config, visit view modules, etc.
    caching.init(app.config.REDIS_URL, **app.config.REDIS_CONFIG)
```
