import openai
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float

def generate_schema(df):
    schema = ""
    for col in df.columns:
        dtype = str(df[col].dtype)
        schema += f"{col} ({dtype}), "
    return schema.rstrip(', ')

def construct_prompt(natural_language_query, schema):
    prompt = f"""
You are an AI assistant that converts natural language to SQL queries.

Here is the database schema:
Table: data
Columns:
{schema}

Generate a SQL query for the following request:
"{natural_language_query}"

Only provide the SQL query.
    """
    return prompt

def generate_sql_query(natural_language_query, schema):
    prompt = construct_prompt(natural_language_query, schema)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Use 'gpt-4' if available
        messages=[
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0,
    )
    sql_query = response.choices[0].message["content"].strip()
    return sql_query

def create_database_table(df, engine):
    metadata = MetaData()

    columns = []
    for col in df.columns:
        dtype = df[col].dtype
        if dtype == 'int64':
            col_type = Integer
        elif dtype == 'float64':
            col_type = Float
        else:
            col_type = String

        columns.append(Column(col, col_type))

    data_table = Table('data', metadata, *columns)
    metadata.create_all(engine)

    return data_table

def execute_sql_query(engine, sql_query):
    try:
        # Print SQL query for debugging
        print(f"Executing SQL query: {sql_query}")

        # Execute query
        result_df = pd.read_sql_query(sql_query, con=engine)
        return result_df, None  # Return result and no error
    except Exception as e:
        # Simplify the error message
        error_message = str(e).split(':')[-1].strip()
        if 'no such table' in error_message.lower():
            error_message = "The query could not find the specified table."
        elif 'syntax error' in error_message.lower():
            error_message = "The query has a syntax error."
        else:
            error_message = "An error occurred while executing the query."

        return None, error_message

def main():
    # Initialize session state for conversation history and other settings
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "current_query" not in st.session_state:
        st.session_state["current_query"] = ""

    st.title("CSV Data Query Chatbot")

    # Sidebar for OpenAI API key and file upload
    st.sidebar.header("OpenAI API Key")
    openai_api_key = st.sidebar.text_input("Enter your OpenAI API key:", type="password", placeholder="Your OpenAI API Key")
    st.sidebar.header("Upload CSV File")
    uploaded_file = st.sidebar.file_uploader("Upload your CSV file", type=["csv"])

    # Display file upload results and process file if uploaded
    if uploaded_file:
        df = pd.read_csv(uploaded_file)

        # Correct column names if necessary
        df.columns = [
            "Page title and screen name", "Country", "Views", 
            "Users", "Views per user", "Average engagement time", 
            "Event count", "Key events"
        ]
        
        # Create an in-memory SQLite database and table
        engine = create_engine('sqlite://', echo=False)
        create_database_table(df, engine)
        df.to_sql('data', con=engine, index=False, if_exists='replace')

        # Show a preview of the database (ignoring the first 8 rows)
        st.subheader("Database Preview")
        preview_df = df.iloc[8:]  # Ignore the first 8 rows
        st.dataframe(preview_df)

        # Chat container with history on top and input at the bottom
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        # Display conversation history in normal order
        for entry in st.session_state["history"]:
            st.markdown(f'<div class="chat-bubble user-bubble">{entry["query"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-bubble ai-bubble"><strong>Generated SQL Query:</strong><br><pre><code class="sql">{entry["sql_query"]}</code></pre></div>', unsafe_allow_html=True)
            if entry["table"]:
                st.markdown(f'<div class="chat-bubble ai-bubble"><strong>Result:</strong><br>{entry["table"]}</div>', unsafe_allow_html=True)
            elif entry["response"]:
                st.markdown(f'<div class="chat-bubble ai-bubble"><strong>Result:</strong><br>{entry["response"]}</div>', unsafe_allow_html=True)

        # End of chat container
        st.markdown('</div>', unsafe_allow_html=True)

        # Input box and submit button below chat history
        user_query = st.text_area("Type your query here:", st.session_state["current_query"])

        if openai_api_key:
            openai.api_key = openai_api_key  # Set the API key

            # Use a single submit button and handle its action correctly
            if st.button("Submit Query"):
                # Check for new query and clear history if necessary
                if st.session_state["current_query"] != user_query:
                    st.session_state["current_query"] = user_query
                    with st.spinner('Generating SQL query...'):
                        schema = generate_schema(df)  # Use the entire dataset
                        sql_query = generate_sql_query(user_query, schema)

                        # Execute the SQL query
                        with st.spinner('Executing SQL query...'):
                            result, error = execute_sql_query(engine, sql_query)

                        # Format the result based on whether it should be a table or simple text
                        if result is not None:
                            if result.empty:
                                response_text = "The query executed successfully but returned no results."
                                table_html = ""  # No table to display
                            else:
                                # Check if the user asked for a table
                                if 'table' in user_query.lower():
                                    table_html = result.to_html(index=False)
                                    response_text = ""
                                else:
                                    response_text = result.to_string(index=False)
                                    table_html = ""
                        else:
                            response_text = f"Error: {error}"
                            table_html = ""  # No table to display

                        # Add the query, SQL query, and response to history
                        st.session_state["history"].append({
                            "query": user_query,
                            "sql_query": f"{sql_query}",
                            "response": response_text,
                            "table": table_html
                        })
                else:
                    st.warning("Please enter a new query to proceed.")
        else:
            st.warning("Please enter your OpenAI API key to proceed.")

if __name__ == "__main__":
    main()


# import openai
# import pandas as pd
# import streamlit as st
# from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float

# def generate_schema(df):
#     schema = ""
#     for col in df.columns:
#         dtype = str(df[col].dtype)
#         schema += f"{col} ({dtype}), "
#     return schema.rstrip(', ')

# def construct_prompt(natural_language_query, schema):
#     prompt = f"""
# You are an AI assistant that converts natural language to SQL queries.

# Here is the database schema:
# Table: data
# Columns:
# {schema}

# Generate a SQL query for the following request:
# "{natural_language_query}"

# Only provide the SQL query.
#     """
#     return prompt

# def generate_sql_query(natural_language_query, schema):
#     prompt = construct_prompt(natural_language_query, schema)
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",  # Use 'gpt-4' if available
#         messages=[
#             {"role": "system", "content": "You are an AI assistant."},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=150,
#         temperature=0,
#     )
#     sql_query = response.choices[0].message["content"].strip()
#     return sql_query

# def create_database_table(df, engine):
#     metadata = MetaData()

#     columns = []
#     for col in df.columns:
#         dtype = df[col].dtype
#         if dtype == 'int64':
#             col_type = Integer
#         elif dtype == 'float64':
#             col_type = Float
#         else:
#             col_type = String

#         columns.append(Column(col, col_type))

#     data_table = Table('data', metadata, *columns)
#     metadata.create_all(engine)

#     return data_table

# def execute_sql_query(engine, sql_query):
#     try:
#         # Print SQL query for debugging
#         print(f"Executing SQL query: {sql_query}")

#         # Execute query
#         result_df = pd.read_sql_query(sql_query, con=engine)
#         return result_df
#     except Exception as e:
#         return f"Error executing SQL query: {e}"

# def main():
#     # Initialize session state for conversation history
#     if "history" not in st.session_state:
#         st.session_state["history"] = []
#     if "current_query" not in st.session_state:
#         st.session_state["current_query"] = ""

#     # Custom CSS for ChatGPT-style interface with reduced history height
#     st.markdown("""
#         <style>
#         .stApp {
#             background-color: #2b2b2b;
#             color: #e0e0e0;
#             font-family: 'Arial', sans-serif;
#             padding-top: 20px;
#         }
#         .chat-container {
#             max-width: 700px;
#             margin: auto;
#             overflow-y: auto;
#             display: flex;
#             flex-direction: column; /* Display messages from top to bottom */
#         }
#         .chat-bubble {
#             padding: 15px;
#             border-radius: 10px;
#             margin-bottom: 10px;
#             box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
#         }
#         .user-bubble {
#             background-color: #3b3b3b;
#             text-align: right;
#             border-bottom-right-radius: 0;
#             color: #ffffff;
#         }
#         .ai-bubble {
#             background-color: #444444;
#             text-align: left;
#             border-bottom-left-radius: 0;
#             color: #dcdcdc;
#         }
#         .stTextArea textarea {
#             background-color: #3b3b3b;
#             color: #ffffff;
#             border-radius: 5px;
#             border: 1px solid #444;
#         }
#         .stButton button {
#             background-color: #1a73e8;
#             color: #ffffff;
#             border: none;
#             border-radius: 5px;
#             padding: 8px 16px;
#             cursor: pointer;
#             transition: background-color 0.3s;
#         }
#         .stButton button:hover {
#             background-color: #166ad1;
#         }
#         </style>
#     """, unsafe_allow_html=True)

#     st.title("CSV Data Query Chatbot")

#     # Sidebar for OpenAI API key
#     st.sidebar.header("OpenAI API Key")
#     openai_api_key = st.sidebar.text_input("Enter your OpenAI API key:", type="password", placeholder="Your OpenAI API Key")

#     # File uploader
#     uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

#     if uploaded_file:
#         df = pd.read_csv(uploaded_file)

#         # Correct column names if necessary
#         df.columns = [
#             "Page title and screen name", "Country", "Views", 
#             "Users", "Views per user", "Average engagement time", 
#             "Event count", "Key events"
#         ]
        
#         # Create an in-memory SQLite database and table
#         engine = create_engine('sqlite://', echo=False)
#         data_table = create_database_table(df, engine)
#         df.to_sql('data', con=engine, index=False, if_exists='replace')

#         # Chat container with history on top and input at the bottom
#         st.markdown('<div class="chat-container">', unsafe_allow_html=True)

#         # Display conversation history in normal order
#         for entry in st.session_state["history"]:
#             st.markdown(f'<div class="chat-bubble user-bubble">{entry["query"]}</div>', unsafe_allow_html=True)
#             st.markdown(f'<div class="chat-bubble ai-bubble"><strong>Generated SQL Query:</strong><br><pre><code class="sql">{entry["sql_query"]}</code></pre></div>', unsafe_allow_html=True)
#             st.markdown(f'<div class="chat-bubble ai-bubble"><strong>Result:</strong><br>{entry["response"]}</div>', unsafe_allow_html=True)

#         # End of chat container
#         st.markdown('</div>', unsafe_allow_html=True)

#         # Input box and submit button below chat history
#         user_query = st.text_area("Type your query here:", st.session_state["current_query"])

#         if openai_api_key:
#             openai.api_key = openai_api_key  # Set the API key

#             if st.button("Submit Query"):
#                 # Check for new query and clear history if necessary
#                 if st.session_state["current_query"] != user_query:
#                     st.session_state["current_query"] = user_query
#                     with st.spinner('Generating SQL query...'):
#                         schema = generate_schema(df)  # Use the entire dataset
#                         sql_query = generate_sql_query(user_query, schema)

#                         # Execute the SQL query
#                         with st.spinner('Executing SQL query...'):
#                             result = execute_sql_query(engine, sql_query)

#                         # Format the result as text without triple quotes
#                         if isinstance(result, pd.DataFrame) and not result.empty:
#                             response_text = result.to_string(index=False)
#                         elif isinstance(result, pd.DataFrame) and result.empty:
#                             response_text = "The query executed successfully but returned no results."
#                         else:
#                             response_text = result

#                         # Add the query, SQL query, and response to history
#                         st.session_state["history"].append({
#                             "query": user_query,
#                             "sql_query": f"{sql_query}",
#                             "response": response_text
#                         })
#                 else:
#                     st.warning("Please enter a new query to proceed.")
#         else:
#             st.warning("Please enter your OpenAI API key to proceed.")

# if __name__ == "__main__":
#     main()

