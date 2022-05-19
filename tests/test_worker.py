from asyncio import run
from pickle import dumps
from pickle import loads
from typing import cast
from unittest import TestCase
from unittest.mock import patch

from aioredis import Redis
from hypothesis import assume
from hypothesis import given
from hypothesis.strategies import from_type
from hypothesis.strategies import integers
from hypothesis.strategies import text

from magnit_calc.models import CalcRequest
from magnit_calc.models import TaskDone
from magnit_calc.models import TaskFailed
from magnit_calc.models import TaskNew
from magnit_calc.worker import calc
from magnit_calc.worker import worker


class TestCalc(TestCase):
    @given(integers(), integers())
    def test_add(self, x: int, y: int) -> None:
        self.assertEqual(
            calc(CalcRequest(x=x, y=y, operand="+")),
            x + y,
        )

    @given(integers(), integers())
    def test_sub(self, x: int, y: int) -> None:
        self.assertEqual(
            calc(CalcRequest(x=x, y=y, operand="-")),
            x - y,
        )

    @given(integers(), integers())
    def test_mul(self, x: int, y: int) -> None:
        self.assertEqual(
            calc(CalcRequest(x=x, y=y, operand="*")),
            x * y,
        )

    @given(integers(), integers())
    def test_div(self, x: int, y: int) -> None:
        assume(y != 0)
        self.assertEqual(
            calc(CalcRequest(x=x, y=y, operand="/")),
            float(x) / y,
        )


class StopWorker(Exception):
    pass


class TestWorker(TestCase):
    @given(
        from_type(TaskNew),
        text(min_size=1, max_size=10),
        text(min_size=1, max_size=10),
    )
    def test_task_done(
            self,
            task_new: TaskNew,
            queue_key: str,
            result_key: str,
    ) -> None:
        assume(task_new.calc_request.y != 0)

        class RedisStub:
            first_run = True
            hset_args: tuple[str, bytes, bytes]
            queue_name: str

            async def brpop(self, queue_name: str) -> tuple[str, bytes]:
                if not self.first_run:
                    raise StopWorker
                self.first_run = False
                self.queue_name = queue_name
                return 'key', dumps(task_new)

            async def hset(self, name: str, key: bytes, value: bytes) -> None:
                self.hset_args = name, key, value

        redis = RedisStub()
        with self.assertRaises(StopWorker):
            run(worker(
                cast(Redis, redis),
                queue_key,
                result_key,
                fail_key='does-not-matter',
            ))

        self.assertEqual(redis.queue_name, queue_key)
        got_result_key, got_task_id, got_task_done_pickled = redis.hset_args

        self.assertEqual(got_result_key, result_key)
        self.assertEqual(got_task_id, task_new.id_.bytes)
        got_task_done = loads(got_task_done_pickled)
        self.assertIsInstance(got_task_done, TaskDone)
        self.assertEqual(got_task_done.id_, task_new.id_)
        self.assertEqual(got_task_done.calc_request, task_new.calc_request)
        self.assertEqual(
            got_task_done.result,
            float(calc(task_new.calc_request)),
        )

    @given(
        from_type(TaskNew),
        text(min_size=1, max_size=10),
        text(min_size=1, max_size=10),
        text(min_size=1, max_size=10),
    )
    def test_task_fail(
            self,
            task_new: TaskNew,
            queue_key: str,
            fail_key: str,
            error_info: str,
    ) -> None:
        class RedisStub:
            first_run = True
            queue_name: str
            hset_args: tuple[str, bytes, bytes]

            async def brpop(self, queue_name):
                if not self.first_run:
                    raise StopWorker
                self.first_run = False
                self.queue_name = queue_name
                return 'key', dumps(task_new)

            async def hset(self, name: str, key: bytes, value: bytes) -> None:
                self.hset_args = name, key, value

        redis = RedisStub()
        with patch(
            "magnit_calc.worker.calc",
            side_effect=Exception(error_info),
        ):
            with self.assertRaises(StopWorker):
                run(worker(
                    cast(Redis, redis),
                    queue_key,
                    result_key="does-not-matter",
                    fail_key=fail_key,
                ))

        self.assertEqual(redis.queue_name, queue_key)
        got_fail_key, got_task_id, got_task_failed_pickled = redis.hset_args

        self.assertEqual(got_fail_key, fail_key)
        self.assertEqual(got_task_id, task_new.id_.bytes)
        got_task_failed = loads(got_task_failed_pickled)
        self.assertIsInstance(got_task_failed, TaskFailed)
        self.assertEqual(got_task_failed.id_, task_new.id_)
        self.assertEqual(got_task_failed.calc_request, task_new.calc_request)
        self.assertEqual(got_task_failed.error, error_info)
