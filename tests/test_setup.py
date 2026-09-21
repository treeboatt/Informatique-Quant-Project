"""Tests de mise en place : le package s'importe et la version de Python est la bonne."""

import sys

import lattice


def test_package_imports():
    assert lattice.__name__ == "lattice"


def test_python_version():
    assert sys.version_info >= (3, 12)
