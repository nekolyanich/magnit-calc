from math import isfinite
from pickle import dumps
from pickle import loads
from unittest import TestCase
from uuid import UUID

from fastapi.testclient import TestClient
from hypothesis import assume
from hypothesis import given
from hypothesis.strategies import from_type
from hypothesis.strategies import lists

from magnit_calc.config import settings
from magnit_calc.main import app
from magnit_calc.models import CalcRequest
from magnit_calc.models import TaskDone
from magnit_calc.models import TaskErrorMsg
from magnit_calc.models import TaskFailed
from magnit_calc.models import TaskNew


class RedisStub:
    hget_values: list[bytes | None]
    hkeys_args: list[str]
    queue_key: str
    task_new: bytes
    hget_args: list[tuple[str, str]]
    hkey_values: list[list[bytes]]
    lrange_values: list[bytes]
    lrange_args: tuple[str, int, int]

    async def rpush(self, queue_key: str, task: bytes) -> None:
        self.queue_key = queue_key
        self.task_new = task

    async def hget(self, name: str, key: str) -> bytes | None:
        self.hget_args.append((name, key))
        return self.hget_values.pop()

    async def hkeys(self, name: str) -> list[bytes]:
        self.hkeys_args.append(name)
        return self.hkey_values.pop()

    async def lrange(self, name: str, start: int, stop: int) -> list[bytes]:
        self.lrange_args = name, start, stop
        return self.lrange_values


@app.on_event('startup')
async def startup():
    app.state.redis = RedisStub()


class TestMainApp(TestCase):
    @given(from_type(CalcRequest))
    def test_register(self, calc_request: CalcRequest) -> None:
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            response = client.post("/register", data=calc_request.json())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(redis_stub.queue_key, settings.queue_key)
            task_new_got = loads(redis_stub.task_new)
            self.assertIsInstance(task_new_got, TaskNew)
            uuid_got = UUID(response.json())
            self.assertEqual(task_new_got.id_, uuid_got)
            self.assertEqual(task_new_got.calc_request, calc_request)

    @given(from_type(TaskDone))
    def test_result_done(self, task_done: TaskDone) -> None:
        assume(isfinite(task_done.result))
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            redis_stub.hget_args = []
            redis_stub.hget_values = [dumps(task_done)]
            response = client.get(f"/task/{task_done.id_}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                redis_stub.hget_args,
                [(settings.result_key, task_done.id_.bytes)],
            )
            self.assertEqual(response.json(), task_done.result)

    @given(from_type(TaskFailed))
    def test_result_fail(self, task_failed: TaskFailed) -> None:
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            redis_stub.hget_args = []
            redis_stub.hget_values = [dumps(task_failed), None]
            response = client.get(f"/task/{task_failed.id_}")
            self.assertEqual(response.status_code, 200)
            self.assertSetEqual(
                set(redis_stub.hget_args),
                set([
                    (settings.result_key, task_failed.id_.bytes),
                    (settings.fail_key, task_failed.id_.bytes),
                ]),
            )
            self.assertEqual(
                response.json(),
                TaskErrorMsg(msg=task_failed.error),
            )

    @given(from_type(UUID))
    def test_result_none(self, uuid: UUID) -> None:
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            redis_stub.hget_args = []
            redis_stub.hget_values = [None, None]
            response = client.get(f"/task/{uuid}")
            self.assertEqual(response.status_code, 200)
            self.assertSetEqual(
                set(redis_stub.hget_args),
                set([
                    (settings.result_key, uuid.bytes),
                    (settings.fail_key, uuid.bytes),
                ]),
            )
            self.assertEqual(
                response.json(),
                None,
            )

    @given(
        lists(from_type(TaskNew)),
        lists(from_type(UUID)),
        lists(from_type(UUID)),
    )
    def test_list(
            self,
            task_news: list[TaskNew],
            done_uuids: list[UUID],
            fail_uuids: list[UUID],
    ) -> None:
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            redis_stub.hkeys_args = []
            redis_stub.hkey_values = [
                [i.bytes for i in fail_uuids],
                [i.bytes for i in done_uuids],
            ]
            redis_stub.lrange_values = [dumps(i) for i in task_news]
            response = client.get("/task_list")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                redis_stub.lrange_args,
                (settings.queue_key, 0, -1),
            )
            self.assertEqual(
                set(redis_stub.hkeys_args),
                set([settings.result_key, settings.fail_key]),
            )
            self.assertDictEqual(
                response.json(),
                {
                    "new": [str(i.id_) for i in task_news],
                    "done": [str(i) for i in done_uuids],
                    "fail": [str(i) for i in fail_uuids],
                },
            )
