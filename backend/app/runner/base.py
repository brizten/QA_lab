from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.runner.context import TestContext


class BaseTestCase(ABC):
    code: ClassVar[str]
    name: ClassVar[str]
    module: ClassVar[str]
    input_schema: ClassVar[dict[str, Any]]

    @abstractmethod
    def run(self, context: TestContext) -> dict[str, Any] | None:
        """Execute a test case and return JSON-serializable result data."""
