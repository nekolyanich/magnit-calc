from unittest import TestCase

from fastapi.testclient import TestClient
from hypothesis.strategies import from_type
from hypothesis import given

from magnit_calc.main import app
from magnit_calc.models import CalcRequest


class TestMainApp(TestCase):
    def setup_example(self) -> None:
        if hasattr(super(), 'setup_example'):
            super().setup_example()
        self.client = TestClient(app)

    @given(from_type(CalcRequest))
    def test_register(self, cr: CalcRequest) -> None:
        response = self.client.post("/register", data=cr)
