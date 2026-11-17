"""Integration tests (Section 4 of the assignment).

Mark every test in this file with the `integration` marker, e.g.

    pytestmark = pytest.mark.integration

Modules are importable directly (see pyproject.toml), e.g.

    import db
    from repository import RegistrationRepository
    from service import RegistrationService
    from errors import CourseFull, AlreadyEnrolled, NotEligible
"""

# TODO: implement your tests here.

import sqlite3

import pytest

from errors import AlreadyEnrolled, CourseFull

pytestmark = pytest.mark.integration


def seats(repository, code):
    return repository.get_course(code)["seats_taken"]


def enrolled(connection, code):
    rows = connection.execute("SELECT student_id FROM enrollments WHERE course_code = ?", (code,))
    return {row[0] for row in rows}


def test_take_seat_capacity_boundary(connection, repository):
    """REQ-2"""
    with connection:
        assert repository.take_seat("C1")
        assert repository.take_seat("C1")
        assert not repository.take_seat("C1")
    assert seats(repository, "C1") == 2


def test_duplicate_enrollment_rejected(connection, repository):
    """REQ-3"""
    with connection:
        repository.add_enrollment("A", "C1")
    with pytest.raises(sqlite3.IntegrityError), connection:
        repository.add_enrollment("A", "C1")
    assert enrolled(connection, "C1") == {"A"}


def test_current_credits(connection, repository):
    """REQ-1"""
    with connection:
        repository.add_enrollment("A", "C1")
        repository.add_enrollment("A", "C2")
        repository.add_enrollment("B", "C1")
    assert repository.current_credits("A") == 7
    assert repository.current_credits("C") == 0


def test_failed_transaction_leaves_nothing(connection, repository):
    """REQ-2"""
    with pytest.raises(sqlite3.IntegrityError), connection:
        repository.take_seat("C1")
        repository.add_enrollment("X", "C1")
    assert seats(repository, "C1") == 0
    assert enrolled(connection, "C1") == set()


def test_enroll_success(connection, repository, service, notifier):
    """REQ-1, REQ-2, REQ-4, REQ-5"""
    service.enroll("A", "C1")
    assert enrolled(connection, "C1") == {"A"}
    assert seats(repository, "C1") == 1
    assert notifier.sent == [("confirmation", "A", "C1", 300.0)]


def test_enroll_full_course(connection, repository, service, notifier):
    """REQ-2, REQ-5"""
    service.enroll("A", "C2")
    with pytest.raises(CourseFull):
        service.enroll("B", "C2")
    assert enrolled(connection, "C2") == {"A"}
    assert notifier.sent[-1] == ("rejection", "B", "C2", "course is full")


def test_enroll_duplicate(connection, repository, service, notifier):
    """REQ-3, REQ-5"""
    service.enroll("A", "C1")
    with pytest.raises(AlreadyEnrolled):
        service.enroll("A", "C1")
    assert seats(repository, "C1") == 1
    assert len(notifier.sent) == 1


@pytest.mark.xfail(strict=True, reason="remove_enrollment() deletes by course_code only, "
                   "so withdrawing one student removes every student's enrollment")
def test_withdraw_removes_only_that_student(connection, service):
    """REQ-6"""
    service.enroll("A", "C1")
    service.enroll("B", "C1")
    service.withdraw("A", "C1")
    assert enrolled(connection, "C1") == {"B"}
