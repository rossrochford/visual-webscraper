import os
import uuid

import trio
from trio_redis import Redis as _TrioRedisClient
from redis.client import list_or_args as redis_list_or_args


REDIS_HOSTNAME = os.environ.get('REDIS_HOSTNAME', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))


class TrioRedisClient(_TrioRedisClient):
    # note: clients must be created using an 'async with' block

    def __init__(self, addr=b"127.0.0.1", port=6379, host=None):
        if host:  # in case wrong argument name used
            addr = host
        super(TrioRedisClient, self).__init__(addr=addr, port=port)
        # every process-queue pair needs a unique list key
        self.q_list_keys = {}
        self.cli_lock = trio.Lock()

    async def brpoplpush(self, src, dst, timeout=0):
        if timeout is None:
            timeout = 0
        async with self.cli_lock:
            return await self.conn.process_command(b'BRPOPLPUSH', src, dst, timeout)

    async def blpop(self, keys, timeout=0):
        if timeout is None:
            timeout = 0
        keys = redis_list_or_args(keys, None)
        keys.append(timeout)
        async with self.cli_lock:
            return await self.conn.process_command(b'BLPOP', *keys)

    async def hgetall(self, *args, **kwargs):
        async with self.cli_lock:
            return super(TrioRedisClient, self).hgetall(*args, **kwargs)

    async def hmset(self, *args, **kwargs):
        async with self.cli_lock:
            return super(TrioRedisClient, self).hmset(*args, **kwargs)

    async def hmget(self, *args, **kwargs):
        async with self.cli_lock:
            return super(TrioRedisClient, self).hmget(*args, **kwargs)

    async def queue_push(self, q_name, msg_string):
        async with self.cli_lock:
            await self.lpush(q_name, msg_string)

    async def queue_pop(self, q_name):

        if q_name not in self.q_list_keys:
            list_key = 'wrk-' + q_name + uuid.uuid4().hex[:6]
            self.q_list_keys[q_name] = list_key

        await self.brpoplpush(q_name, self.q_list_keys[q_name])
        _, result = await self.blpop(self.q_list_keys[q_name])

        return result.decode()


async def main():
    import random
    async with TrioRedisClient(addr=REDIS_HOSTNAME.encode(), port=REDIS_PORT) as redis_cli:
        while True:
            result = await redis_cli.queue_pop('my-queue')
            print(result)
            if random.randint(0, 10) == 9:
                print('requeueing')
                await redis_cli.queue_push('my-queue', result)


if __name__ == '__main__':
    trio.run(main)
