import pytest

from app import v1
from pydantic import ValidationError


def test_recurring_payload_accepts_nullable_reference_fields():
    payload = v1.RecurringExpenseCreateV1(
        name="iCloud Storage",
        amount="4.49",
        frequency="monthly",
        payment_method="not_set",
        account_id=None,
        card_id=None,
        category_id=None,
        expense_type_id=None,
        end_date=None,
        reminder_days_before=None,
    )
    assert payload.account_id is None
    assert payload.card_id is None
    assert payload.category_id is None
    assert payload.expense_type_id is None
    assert payload.end_date is None
    assert payload.reminder_days_before is None


def test_recurring_payload_rejects_invalid_reference_shapes():
    with pytest.raises(ValidationError):
        v1.RecurringExpenseCreateV1(name="Bad", account_id="")
