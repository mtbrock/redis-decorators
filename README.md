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
@caching.cache_string(get_cache_key = lambda arg1: return f'{arg1}-cache-key')
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
