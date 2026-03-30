"""
Pytest configuration and shared fixtures for P2P gRPC Chat tests.
"""

import socket

import pytest


@pytest.fixture(scope="session")
def free_port():
    """
    Get a free port for testing.

    Returns:
        int: A free port number
    """
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
