#!/usr/bin/env python3
"""LNG Carrier Fleet Performance Management System"""

__version__ = "1.0.0"

from .database.connection import DatabaseManager
from .database.schema import create_all_tables
