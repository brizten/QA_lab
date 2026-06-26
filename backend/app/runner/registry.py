from app.runner.base import BaseTestCase


class TestRegistry:
    def __init__(self) -> None:
        self._tests: dict[str, type[BaseTestCase]] = {}

    def register(self, test_class: type[BaseTestCase]) -> type[BaseTestCase]:
        test = test_class()
        if not test.code:
            raise ValueError("Test case code must not be empty")

        existing = self._tests.get(test.code)
        if existing is not None and existing is not test_class:
            raise ValueError(f"Test case code is already registered: {test.code}")

        self._tests[test.code] = test_class
        return test_class

    def get_test_by_code(self, code: str) -> BaseTestCase | None:
        test_class = self._tests.get(code)
        if test_class is None:
            return None
        return test_class()

    def list_codes(self) -> list[str]:
        return sorted(self._tests)


registry = TestRegistry()


def get_test_by_code(code: str) -> BaseTestCase | None:
    return registry.get_test_by_code(code)


def register_builtin_tests() -> None:
    from app.runner.tests.cards.issue_virtual_card import IssueVirtualCardTest
    from app.runner.tests.k2.create_payment import CreatePaymentTest

    registry.register(IssueVirtualCardTest)
    registry.register(CreatePaymentTest)


register_builtin_tests()
