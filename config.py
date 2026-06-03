# -*- coding: utf-8 -*-
"""
Configuration for PetCare Web Application
"""

# SQL Server Configuration
# Update these values for your SQL Server instance
DB_CONFIG = {
    "server": "localhost",  # SQL Server instance name/IP
    "database": "petcare",  # Database name
    "uid": "sa",  # SQL Server username
    "pwd": "YourPassword123",  # SQL Server password
    "driver": "{ODBC Driver 17 for SQL Server}",  # ODBC driver
    "trusted_connection": False,  # Set to True for Windows Authentication
}

# For Windows Authentication (trusted_connection=True):
# DB_CONFIG = {
#     "server": "localhost",
#     "database": "petcare",
#     "driver": "{ODBC Driver 17 for SQL Server}",
#     "trusted_connection": True,
# }

# Web Server Configuration
HOST = "127.0.0.1"
PORT = 8000
