import sqlite3
import pandas as pd

def get_db_schema(db_path: str) -> pd.DataFrame:
    """Retrieves the database schema, saves it as a global schema string and returns it as a DataFrame."""
    conn = sqlite3.connect(db_path)
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    tables_df = pd.read_sql_query(query, conn)
    conn.close()

    db_schema_df = pd.DataFrame()
    for table_name in tables_df["name"]:
        db_schema_df = pd.concat([db_schema_df, get_table_schema(db_path, table_name)],
                  axis=1)

    return db_schema_df.fillna("")

def get_table_schema(db_path: str, table_name: str) -> pd.Series:
    """Retrieves the schema (columns) for a specified table."""
    global schema
    conn = sqlite3.connect(db_path)
    query = f"PRAGMA table_info('{table_name}');"
    column_df = pd.read_sql_query(query, conn)
    conn.close()
    column_df = column_df.rename(columns={"name": table_name})
    table_schema = f"Table: {table_name}\\n"
    for col in column_df[table_name]:
        table_schema += f"  Column: {col}\\n"
    schema += table_schema
    return column_df[table_name]

def get_table_schema_string(db_path: str, table_name) -> str:
    """
    Extracts the table schema (name and columns) as a string.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        schema = ""
        for table_name in tables:
            table_name = table_name[0]
            schema += f"Table: {table_name}\\n"
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                schema += f"  Column: {col[1]} ({col[2]})\\n"
    return schema