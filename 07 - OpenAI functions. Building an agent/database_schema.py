import sqlite3
from sqlite3 import Connection


def format_table_columns(schema_columns):
    formatted_output = []
    for table, columns in schema_columns.items():
        formatted_output.append(f"Table: {table}")
        formatted_output.append(f"Columns: {', '.join(columns)}")
    return "\n".join(formatted_output)


def get_db_schema(connection: sqlite3.Connection):
    tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
    tables = connection.execute(tables_query).fetchall()

    schema = {}
    columns = {}
    for table in tables:
        table_name = table[0]
        schema_query = f"PRAGMA table_info('{table_name}');"
        schema[table_name] = connection.execute(schema_query).fetchall()
        # Fetch from schema column names
        columns = {table: [column[1] for column in schema] for table, schema in schema.items()}
    return format_table_columns(columns)