from asyncio import run
from pickle import dumps
from pickle import loads

from aioredis import from_url
from aioredis import Redis

from magnit_calc.models import CalcRequest
from magnit_calc.models import Operands
from magnit_calc.models import TaskDone
from magnit_calc.models import TaskFailed
from magnit_calc.models import TaskNew
from magnit_calc.config import settings


operands = {
    Operands.ADD: lambda *x: x[0] + x[1],
    Operands.SUB: lambda *x: x[0] - x[1],
    Operands.MUL: lambda *x: x[0] * x[1],
    Operands.DIV: lambda *x: float(x[0]) / x[1],
}


def calc(calc_request: CalcRequest) -> float:
    return operands[calc_request.operand](calc_request.x, calc_request.y)


async def worker(
        redis: Redis,
        queue_key: str,
        result_key: str,
        fail_key: str,
) -> None:
    while True:
        _, task_pickled = await redis.brpop(queue_key)
        task: TaskNew = loads(task_pickled)
        try:
            await redis.hset(
                result_key,
                task.id_.bytes,
                dumps(TaskDone.from_task_new(task, calc(task.calc_request))),
            )
        except Exception as err:  # pylint: disable=broad-except
            await redis.hset(
                fail_key,
                task.id_.bytes,
                dumps(TaskFailed.from_task_new(task, str(err))),
            )


def main() -> None:  # pragma: no cover
    redis = from_url(settings.redis_url)
    run(worker(
        redis,
        settings.queue_key,
        settings.result_key,
        settings.fail_key,
    ))
