from typing import Any

from app.runner.base import BaseTestCase
from app.runner.context import TestContext


class CreatePaymentTest(BaseTestCase):
    code = "k2.create_payment"
    name = "Create K2 payment"
    module = "k2"
    input_schema = {
        "type": "object",
        "required": ["amount", "currency", "receiver"],
        "properties": {
            "amount": {"type": "number"},
            "currency": {"type": "string"},
            "receiver": {"type": "string"},
            "force_fail": {"type": "boolean"},
        },
    }

    def run(self, context: TestContext) -> dict[str, Any]:
        with context.step("Validate input parameters", request_json=context.params) as step:
            amount = context.params.get("amount")
            assert isinstance(amount, (int, float)) and amount > 0, "amount must be positive"
            assert context.params.get("currency"), "currency is required"
            assert context.params.get("receiver"), "receiver is required"
            step.save_response_json({"message": "Input parameters are valid"})

        with context.step(
            "Mock create payment",
            request_json={
                "amount": context.params["amount"],
                "currency": context.params["currency"],
                "receiver": context.params["receiver"],
            },
        ) as step:
            payment = {
                "payment_id": f"payment-{context.test_run_id}",
                "amount": context.params["amount"],
                "currency": context.params["currency"],
                "receiver": context.params["receiver"],
                "status": "CREATED",
            }
            step.save_response_json(payment)

        with context.step(
            "Mock check payment status",
            request_json={"payment_id": payment["payment_id"]},
        ) as step:
            if context.params.get("force_fail") is True:
                raise AssertionError("Forced failure for testing")
            payment["status"] = "COMPLETED"
            step.save_response_json({"payment_id": payment["payment_id"], "status": payment["status"]})

        with context.step("Validate payment status", request_json=payment) as step:
            assert payment["status"] == "COMPLETED", "Payment status must be COMPLETED"
            step.save_response_json({"status": payment["status"]})

        return {
            "message": "Payment created successfully",
            "payment_id": payment["payment_id"],
            "payment_status": payment["status"],
        }
