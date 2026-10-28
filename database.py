
import os

import pyodbc
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    server = os.getenv("DB_SERVER", "TTPL02")
    database = os.getenv("DB_NAME", "ItsybitsyDB")
    driver = os.getenv(
        "DB_DRIVER",
        "SQL Server Native Client 11.0"
    )
    trusted = os.getenv(
        "DB_TRUSTED_CONNECTION", "yes"
    ).lower() == "yes"
    encrypt = os.getenv(
        "DB_ENCRYPT", "no"
    ).lower()

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Encrypt={encrypt};"
    )

    if trusted:
        connection_string += "Trusted_Connection=yes;"
    else:
        connection_string += (
            f"UID={os.getenv('DB_USER')};"
            f"PWD={os.getenv('DB_PASSWORD')};"
        )

    return pyodbc.connect(
        connection_string,
        timeout=10
    )


def test_connection():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT DB_NAME() AS database_name"
        )
        row = cursor.fetchone()
        return row[0]
    finally:
        connection.close()
