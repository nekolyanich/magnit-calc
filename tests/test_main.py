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
    hget_values = []
    hkeys_args = []

    async def rpush(self, queue_key: str, task: bytes) -> None:
        self.queue_key = queue_key
        self.task_new = task

    async def hget(self, name: str, key: str) -> bytes:
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
    def test_register(self, cr: CalcRequest) -> None:
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            response = client.post("/register", data=cr.json())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(redis_stub.queue_key, settings.queue_key)
            task_new_got = loads(redis_stub.task_new)
            self.assertIsInstance(task_new_got, TaskNew)
            uuid_got = UUID(response.json())
            self.assertEqual(task_new_got.id_, uuid_got)
            self.assertEqual(task_new_got.calc_request, cr)

    @given(from_type(TaskDone))
    def test_result_done(self, td: TaskDone) -> None:
        assume(isfinite(td.result))
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            redis_stub.hget_args = []
            redis_stub.hget_values = [dumps(td)]
            response = client.get(f"/task/{td.id_}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                redis_stub.hget_args,
                [(settings.result_key, td.id_.bytes)],
            )
            self.assertEqual(response.json(), td.result)

    @given(from_type(TaskFailed))
    def test_result_fail(self, tf: TaskFailed) -> None:
        with TestClient(app) as client:
            redis_stub: RedisStub = client.app.state.redis
            redis_stub.hget_args = []
            redis_stub.hget_values = [dumps(tf), None]
            response = client.get(f"/task/{tf.id_}")
            self.assertEqual(response.status_code, 200)
            self.assertSetEqual(
                set(redis_stub.hget_args),
                set([
                    (settings.result_key, tf.id_.bytes),
                    (settings.fail_key, tf.id_.bytes),
                ]),
            )
            self.assertEqual(
                response.json(),
                TaskErrorMsg(msg=tf.error),
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
