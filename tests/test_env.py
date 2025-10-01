import sys


def test_python_version():
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 10), "Python >=3.10 required"
