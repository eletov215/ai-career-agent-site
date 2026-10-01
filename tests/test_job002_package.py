from scripts.check_job002_package import validate


def test_job002_package_guard():
    assert validate()==[]
