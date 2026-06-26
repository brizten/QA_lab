from typing import Any

from app.runner.base import BaseTestCase
from app.runner.context import TestContext


class IssueVirtualCardTest(BaseTestCase):
    code = "cards.issue_virtual_card"
    name = "Issue virtual card"
    module = "cards"
    input_schema = {
        "type": "object",
        "required": ["iin", "product_code", "currency"],
        "properties": {
            "iin": {"type": "string"},
            "product_code": {"type": "string"},
            "currency": {"type": "string"},
            "force_fail": {"type": "boolean"},
        },
    }

    def run(self, context: TestContext) -> dict[str, Any]:
        with context.step("Validate input parameters", request_json=context.params) as step:
            assert context.params.get("iin"), "iin is required"
            assert context.params.get("product_code"), "product_code is required"
            assert context.params.get("currency"), "currency is required"
            step.save_response_json({"message": "Input parameters are valid"})

        with context.step(
            "Mock create client",
            request_json={"iin": context.params["iin"], "environment": context.environment},
        ) as step:
            client = {
                "client_id": f"client-{context.params['iin'][-4:]}",
                "iin": context.params["iin"],
            }
            step.save_response_json(client)

        with context.step(
            "Mock issue card",
            request_json={
                "client_id": client["client_id"],
                "product_code": context.params["product_code"],
                "currency": context.params["currency"],
            },
        ) as step:
            if context.params.get("force_fail") is True:
                raise AssertionError("Forced failure for testing")
            card = {
                "card_id": f"card-{context.test_run_id}",
                "client_id": client["client_id"],
                "status": "ACTIVE",
                "currency": context.params["currency"],
            }
            step.save_response_json(card)

        with context.step("Validate card status", request_json=card) as step:
            assert card["status"] == "ACTIVE", "Card status must be ACTIVE"
            step.save_response_json({"status": card["status"]})

        return {
            "message": "Virtual card issued successfully",
            "client_id": client["client_id"],
            "card_id": card["card_id"],
            "card_status": card["status"],
        }
