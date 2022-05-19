from pickle import dumps
from pickle import loads
from uuid import UUID
from uuid import uuid4

from aioredis import from_url
from fastapi import FastAPI

from magnit_calc.models import CalcRequest
from magnit_calc.models import Task
from magnit_calc.models import TaskErrorMsg
from magnit_calc.models import TaskNew


app = FastAPI()
redis = from_url("redis://localhost")

PREFIX = "MAGNIT"
QUEUE_KEY = PREFIX + ":NEW"
RESULT_KEY = PREFIX + ":DONE"
FAIL_KEY = PREFIX + ":FAIL"


@app.post("/register")
async def register(item: CalcRequest) -> UUID:
    task_id = uuid4()
    await redis.rpush(QUEUE_KEY, dumps(TaskNew(id_=task_id, calc_request=item)))
    return task_id


@app.get("/task/{task_id}")
async def result(task_id: UUID) -> float | TaskErrorMsg | None:
    task_id_bytes = task_id.bytes
    result_pickled = await redis.hget(RESULT_KEY, task_id_bytes)
    if result_pickled:
        return loads(result_pickled).result
    fail_pickled = await redis.hget(FAIL_KEY, task_id_bytes)
    if fail_pickled:
        return TaskErrorMsg(msg=loads(fail_pickled).error)
    return None


@app.get("/task_list")
async def task_list() -> list[Task]:
    new = await redis.lrange(QUEUE_KEY, 0, -1)
    done = await redis.hkeys(RESULT_KEY)
    fail = await redis.hkeys(FAIL_KEY)
    return {
        "new": [loads(i).id_ for i in new],
        "done": [UUID(bytes=i) for i in done],
        "fail": [UUID(bytes=i) for i in fail],
    }
