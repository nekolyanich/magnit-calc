from pydantic import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost"
    queue_key: str = "MAGNIT:NEW"
    result_key: str = "MAGNIT:DONE"
    fail_key: str = "MAGNIT:FAIL"


settings = Settings()
