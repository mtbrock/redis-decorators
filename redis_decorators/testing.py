import fakeredis


class FakeRedis(fakeredis.FakeRedis):
    @classmethod
    def from_url(cls, url: str, **kwargs):
        return cls(**kwargs)
