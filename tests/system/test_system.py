"""System tests (Section 5 of the assignment).

Mark every test in this file with the `system` marker. Use the provided
`system` fixture (tests/system/conftest.py); do not import anything from
src/ here -- a system test sees only HTTP and the outbox.
"""

# TODO: implement your tests here.

import threading

import pytest
import requests

pytestmark = pytest.mark.system

KEY = {"X-API-Key": "registrar-key"}


def seats(system, code):
    return system.get(f"/courses/{code}").json()["seats_taken"]


def test_enroll_success(system):
    """REQ-1, REQ-2, REQ-4, REQ-5, REQ-7"""
    response = system.enroll("S01", "SE413")
    assert response.status_code == 201
    assert response.json() == {"student_id": "S01", "course_code": "SE413",
                               "credits": 3, "total_credits": 3, "fee": 300.0}
    schedule = system.get("/students/S01/schedule").json()
    assert schedule["courses"][0]["code"] == "SE413"
    assert schedule["fee"] == 300.0
    assert seats(system, "SE413") == 1
    assert system.outbox() == [{"type": "confirmation", "student_id": "S01",
                                "course_code": "SE413", "fee": 300.0}]


def test_missing_prerequisite(system):
    """REQ-1, REQ-5, REQ-7"""
    response = system.enroll("S13", "SE413")
    assert response.status_code == 422
    assert response.json() == {"error": "prerequisite CIS350 not completed"}
    assert system.get("/students/S13/schedule").json()["courses"] == []
    assert seats(system, "SE413") == 0
    assert system.outbox() == [{"type": "rejection", "student_id": "S13", "course_code": "SE413",
                                "reason": "prerequisite CIS350 not completed"}]


@pytest.mark.parametrize("body", [
    '{"student_id": 1, "course_code": "SE413"}',
    '{"student_id": "S01"}',
    '["S01", "SE413"]',
    '{"student_id": "' + "S" * 10000 + '", "course_code": "SE413"}',
    '{"student_id": "S01\' OR 1=1 --", "course_code": "SE413"}',
])
def test_invalid_body_gets_400(system, body):
    """REQ-5, REQ-8"""
    response = requests.post(f"{system.url}/enrollments", data=body,
                             headers={**KEY, "Content-Type": "application/json"})
    assert response.status_code == 400
    assert "error" in response.json()
    assert seats(system, "SE413") == 0
    assert system.outbox() == []


@pytest.mark.parametrize("method, path", [
    ("POST", "/enrollments"),
    ("DELETE", "/enrollments/S14/MTH201"),
    ("GET", "/students/S01/schedule"),
    ("GET", "/courses/SE413"),
])
def test_api_key_required(system, method, path):
    """REQ-8"""
    response = requests.request(method, system.url + path)
    assert response.status_code == 401
    assert "error" in response.json()


def test_ten_students_three_seats(system):
    """REQ-2, REQ-5"""
    barrier = threading.Barrier(10)
    statuses = []

    def enroll(student_id):
        barrier.wait()
        statuses.append(requests.post(f"{system.url}/enrollments", headers=KEY, json={
            "student_id": student_id, "course_code": "SE499"}).status_code)

    threads = [threading.Thread(target=enroll, args=(f"S{n:02d}",)) for n in range(1, 11)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(statuses) == [201] * 3 + [409] * 7
    assert seats(system, "SE499") == 3
    types = [m["type"] for m in system.outbox()]
    assert types.count("confirmation") == 3
    assert types.count("rejection") == 7
