"""Fixtures for your integration tests (Section 4 of the assignment).

Your integration tests assemble the REAL repository and service on a
REAL SQLite database file -- inside the test process. Suggested fixtures
(write them here):

  - a connection to a new database file in pytest's `tmp_path`, with
    db.create_schema() applied and a few students and courses added
    through the repository (or with db.seed());
  - a RegistrationRepository on that connection;
  - a fake notifier: a small class of your own that records every
    send_confirmation / send_rejection call in a list, so a test can
    check what was sent;
  - a RegistrationService built from the three.
"""

import pytest

import db
from repository import RegistrationRepository
from service import RegistrationService


class FakeNotifier:
    """Records every notification instead of sending it."""

    def __init__(self):
        self.sent = []

    def send_confirmation(self, student_id, course_code, fee):
        self.sent.append(("confirmation", student_id, course_code, fee))

    def send_rejection(self, student_id, course_code, reason):
        self.sent.append(("rejection", student_id, course_code, reason))


@pytest.fixture
def connection(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    db.create_schema(conn)
    repo = RegistrationRepository(conn)
    with conn:
        repo.add_course("C1", "Course One", 3, 2)   # 2 seats
        repo.add_course("C2", "Course Two", 4, 1)   # 1 seat
        repo.add_student("A", "Student A")
        repo.add_student("B", "Student B")
        repo.add_student("C", "Student C")
    yield conn
    conn.close()


@pytest.fixture
def repository(connection):
    return RegistrationRepository(connection)


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
def service(connection, repository, notifier):
    return RegistrationService(connection, repository, notifier)
