import gradio as gr
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import sqlite3
import pandas as pd

# Initialize tokenizer and model
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-0.5B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Coder-0.5B-Instruct")
model.to(device)
print("Model loaded to", model.device)

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


def nL_to_sql(question: str) -> str:
    """
    Converts a natural language query to a SQL query using an LLM.
    """    
    # Prepare the input for the T5 model
    SYSTEM_PROMPT = f'''
    Database schema: {schema}

    Convert natural language query into a SQL query. Simply respond with the SQL query and nothing else.
    For example:
    Question: Find all album titles
    Query: FROM albums SELECT title
    '''
    input_text = f'''
    Question: {question}
    Query: '''
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": input_text}]
    
    # Encode the input
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    
    # Generate the SQL query
    outputs = model.generate(**inputs,
                             max_new_tokens=200)
    
    # Decode the output
    sql_query = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    print(sql_query)
    return sql_query

def execute_query(sql_query: str):
    """
    Executes a SQL query on the database and returns the result.
    """
    db_path = uploaded_filepath
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(sql_query, conn)
        return df
    except Exception as e:
        return pd.DataFrame()

def process_input(natural_language_query):
    """
    Processes the natural language query, generates SQL, and executes it.
    """
    sql_query = nL_to_sql(natural_language_query)
    result = execute_query(sql_query)
    return sql_query, result

def upload_db(file_obj) -> pd.DataFrame:
    global uploaded_filepath
    if file_obj is None:
        return pd.DataFrame()
    uploaded_filepath = file_obj.name if file_obj.name.split(".")[-1] == "db" else DEFAULT_DB_FILEPATH
    updated_db_df = get_db_schema(uploaded_filepath)
    return updated_db_df

# Create the Gradio interface
DEFAULT_DB_FILEPATH = "northwind.db"
uploaded_filepath = DEFAULT_DB_FILEPATH
schema = ""
with gr.Blocks() as demo:
    title = gr.HTML("<h1>Natural Language to SQL Query</h1>")
    description = gr.HTML("<p>Upload a database (.db) file, or use a sample database provided. Enter a query in natural language, and the app will generate and execute the corresponding SQL query.</p>")
    db_upload_button = gr.UploadButton(label="Upload DB file",
                                file_count="single")
    db_schema_df = gr.DataFrame(value=get_db_schema(uploaded_filepath),
                                label="DB Schema")
    query_input = gr.Textbox(lines=5, label="Enter your query in natural language")
    query_submit_button = gr.Button(value="Submit")
    generated_query = gr.Textbox(label="Generated SQL Query")
    query_result = gr.DataFrame(label="Query Result")

    # Listeners
    db_upload_button.upload(
        fn=upload_db,
        inputs=db_upload_button,
        outputs=db_schema_df
    )
    query_submit_button.click(
        fn=process_input,
        inputs=query_input,
        outputs=[
            generated_query,
            query_result
        ]
    )

if __name__ == "__main__":
    demo.launch()
