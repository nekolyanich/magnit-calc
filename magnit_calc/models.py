from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field
from typing_extensions import Annotated


class TaskErrorMsg(BaseModel):
    error: Literal["task_error"] = "task_error"
    msg: str


class Operands(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"


class CalcRequest(BaseModel):
    x: int
    y: int
    operand: Operands


class TaskNew(BaseModel):
    type_: Literal["new"] = "new"
    id_: UUID
    calc_request: CalcRequest


class TaskDone(BaseModel):
    type_: Literal["done"] = "done"
    id_: UUID
    calc_request: CalcRequest
    result: float

    @classmethod
    def from_task_new(cls, task_new: TaskNew, result: float) -> 'TaskDone':
        return cls(
            id_=task_new.id_,
            calc_request=task_new.calc_request,
            result=result,
        )


class TaskFailed(BaseModel):
    type_: Literal["failed"] = "failed"
    id_: UUID
    calc_request: CalcRequest
    error: str

    @classmethod
    def from_task_new(cls, task_new: TaskNew, error: str) -> 'TaskFailed':
        return cls(
            id_=task_new.id_,
            calc_request=task_new.calc_request,
            error=error,
        )


Task = Annotated[TaskNew | TaskDone | TaskFailed, Field(discriminator='type_')]
