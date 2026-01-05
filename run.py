import gradio as gr
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import sqlite3
import pandas as pd
from db_tools import get_db_schema
from config import schema

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

def execute_query(sql_query: str) -> pd.DataFrame:
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

def process_input(natural_language_query: str) -> tuple[str, pd.DataFrame]:
    """
    Processes the natural language query, generates SQL, and executes it.
    """
    sql_query = nL_to_sql(natural_language_query)
    result = execute_query(sql_query)
    return sql_query, result

def upload_db(file_obj) -> pd.DataFrame:
    """
    Updates file path of user-uploaded database file, and returns the schema (tables and columns) as a DataFrame.
    """
    global uploaded_filepath
    if file_obj is None:
        return pd.DataFrame()
    uploaded_filepath = file_obj.name if file_obj.name.split(".")[-1] == "db" else DEFAULT_DB_FILEPATH
    updated_db_df = get_db_schema(uploaded_filepath)
    return updated_db_df

# Create the Gradio interface
DEFAULT_DB_FILEPATH = "northwind.db"
uploaded_filepath = DEFAULT_DB_FILEPATH

with gr.Blocks() as demo:
    title = gr.HTML("<h1>Natural Language to SQL Query</h1>")
    description = gr.HTML("<p>Upload a database (.db) file, or use a sample database provided. Enter a query in natural language, and the app will generate and execute the corresponding SQL query.</p>")
    db_upload_button = gr.UploadButton(label="Upload DB file",
                                file_count="single")
    db_schema_df = gr.Dataframe(value=get_db_schema(uploaded_filepath),
                                label="DB Schema",
                                max_height=200)
    with gr.Row():
        with gr.Column():
            query_input = gr.Textbox(lines=5, label="Enter your query in natural language")
            query_submit_button = gr.Button(value="Submit")
        with gr.Column():
            generated_query = gr.Textbox(label="Generated SQL Query")
            query_result = gr.Dataframe(label="Query Result",
                                        max_height=200)

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
