from datetime import date
from app import payments_v17

def test_calendar_recurrence_month_end_and_leap_year():
    assert payments_v17._next_occurrence(date(2024, 1, 31), 'monthly', None) == date(2024, 2, 29)
    assert payments_v17._next_occurrence(date(2024, 2, 29), 'yearly', None) == date(2025, 2, 28)

def test_payment_handling_can_be_configured_independently():
    assert payments_v17._handling('bpay', 'automatic') == 'automatic'
    assert payments_v17._handling('direct_debit', 'manual') == 'manual'

def test_automatic_due_occurrence_is_paid():
    assert payments_v17._status_for(date(2026, 8, 24), 'automatic', 3, date(2026, 8, 24)) == 'paid'
    assert payments_v17._status_for(date(2026, 8, 25), 'automatic', 3, date(2026, 8, 24)) == 'upcoming'

def test_manual_due_and_overdue_are_not_auto_paid():
    assert payments_v17._status_for(date(2026, 8, 24), 'manual', 3, date(2026, 8, 24)) == 'due'
    assert payments_v17._status_for(date(2026, 8, 23), 'manual', 3, date(2026, 8, 24)) == 'overdue'
