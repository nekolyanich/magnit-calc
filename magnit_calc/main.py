from pickle import dumps
from pickle import loads
from uuid import UUID
from uuid import uuid4

from aioredis import from_url
from aioredis import Redis
from fastapi import FastAPI
from fastapi import Request

from magnit_calc.config import settings
from magnit_calc.models import CalcRequest
from magnit_calc.models import Task
from magnit_calc.models import TaskErrorMsg
from magnit_calc.models import TaskNew


app = FastAPI()


@app.on_event('startup')
async def startup():
    app.state.redis = from_url(settings.redis_url)


@app.post("/register")
async def register(request: Request, item: CalcRequest) -> UUID:
    redis = request.app.state.redis
    task_id = uuid4()
    await redis.rpush(
        settings.queue_key,
        dumps(TaskNew(id_=task_id, calc_request=item)),
    )
    return task_id


@app.get("/task/{task_id}")
async def result(
        request: Request,
        task_id: UUID,
) -> float | TaskErrorMsg | None:
    redis: Redis = request.app.state.redis
    task_id_bytes = task_id.bytes
    result_pickled = await redis.hget(settings.result_key, task_id_bytes)
    if result_pickled:
        return loads(result_pickled).result
    fail_pickled = await redis.hget(settings.fail_key, task_id_bytes)
    if fail_pickled:
        return TaskErrorMsg(msg=loads(fail_pickled).error)
    return None


@app.get("/task_list")
async def task_list(request: Request, ) -> list[Task]:
    redis = request.app.state.redis
    new = await redis.lrange(settings.queue_key, 0, -1)
    done = await redis.hkeys(settings.result_key)
    fail = await redis.hkeys(settings.fail_key)
    return {
        "new": [loads(i).id_ for i in new],
        "done": [UUID(bytes=i) for i in done],
        "fail": [UUID(bytes=i) for i in fail],
    }
