"""
scripts/_03_generate_synthetic.py
==================================
Importable wrapper around the synthetic data generator.
Tests import this module; the actual script is 03_generate_synthetic_data.py.
"""
# Re-export the generator function for pytest
from scripts.generate_synthetic_core import generate_synthetic_incidents  # noqa: F401
