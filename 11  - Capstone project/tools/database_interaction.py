from logging import Logger
from sqlite3 import Connection
import sqlite3
import logging


class DatabaseInteraction:
    def __init__(self, logger: Logger, connection: sqlite3.Connection):
        self.logger = logger
        self.connection = connection

    def get_db_schema(self):
        tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = self.connection.execute(tables_query).fetchall()
        self.logger.info(tables)
        schema = {}
        for table in tables:
            table_name = table[0]
            schema_query = f"PRAGMA table_info('{table_name}');"
            schema[table_name] = [column[1] for column in self.connection.execute(schema_query).fetchall()]

        formatted_output = []
        for table, columns in schema.items():
            formatted_output.append(f"Table: {table}")
            formatted_output.append(f"Columns: {', '.join(columns)}")
        return "\n".join(formatted_output)

    def fetch_from_db(self, query):
        """Function to query SQLite database with provided SQL query."""
        try:
            results = self.connection.execute(query).fetchall()
            return results
        except Exception as e:
            raise Exception(f"SQL error: {e}")