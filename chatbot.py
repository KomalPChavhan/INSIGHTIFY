import os
import streamlit as st
from langchain.chains import create_sql_query_chain
from langchain_google_genai import GoogleGenerativeAI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, IntegrityError
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

# Additional imports for few-shots
from langchain.chains.sql_database.prompt import PROMPT_SUFFIX
from langchain.prompts import SemanticSimilarityExampleSelector
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.prompts.prompt import PromptTemplate
from langchain.prompts import FewShotPromptTemplate


# Load environment variables
load_dotenv()

# Few-shot examples
few_shots = [
    {
        "Question": "How many t-shirts do we have left for Nike in XS size and white color?",
        "SQLQuery": "SELECT sum(stock_quantity) FROM t_shirts WHERE brand = 'Nike' AND color = 'White' AND size = 'XS'",
    },
    {
        "Question": "How much is the price of the inventory for all small size t-shirts?",
        "SQLQuery": "SELECT SUM(price * stock_quantity) AS total_inventory_value FROM t_shirts WHERE size = 'S';",
    },
    { 
        "Question": "How many total white color Levi's shirt I have?",
        "SQLQuery": "SELECT sum(stock_quantity) AS Total White Levi's FROM t_shirts WHERE color = 'White' AND brand = 'Levi';",
    },

    {
        "Question": "How many black t-shirts do we have in stock in size M?",
        "SQLQuery": "SELECT SUM(stock_quantity) FROM t_shirts WHERE color = 'Black' AND size = 'M';;",
    },
     {
        "Question": "How many white color Levi's shirt I have?",
        "SQLQuery": "SELECT SUM(stock_quantity) FROM t_shirts WHERE color = 'white' AND brand = 'Levi';;",
    },
    {
        "Question": "Which brand offers the most affordable T-shirts?",
        "SQLQuery": "SELECT brand FROM t_shirts GROUP BY brand ORDER BY MIN(price) LIMIT 1;;",
    },
    {
        "Question": "List all unique sizes available for each brand.",
        "SQLQuery": "SELECT brand, GROUP_CONCAT(DISTINCT size) AS available_sizes FROM t_shirts GROUP BY brand;",
    },
    {
        "Question": "Which T-shirts are available in both S and M sizes?",
        "SQLQuery": "SELECT t_shirt_id,brand FROM t_shirts WHERE size IN ('S', 'M');",
    },
    {
        "Question": "show count of  all white tshirts",
        "SQLQuery": "SELECT SUM(stock_quantity) FROM t_shirts WHERE color = 'White';",
    },
    {
        "Question": "show count of  all black t shirts of nike brand",
        "SQLQuery": "SELECT SUM(stock_quantity) FROM t_shirts WHERE color = 'black' AND brand='Nike';",
    },
    {
        "Question": "How many T-shirts were sold on 2023-09-15?",
        "SQLQuery": "SELECT SUM(quantity_sold) AS total_sold FROM sales WHERE sale_date = '2023-09-15';",
    },

    {
        "Question": "What is the average price of T-shirts sold by brand for each size?",
        "SQLQuery": "SELECT brand, size, AVG(price) AS avg_price FROM sales GROUP BY brand, size;",
    },
    {
        "Question": "Which color of T-shirt has the least stock in inventory?",
        "SQLQuery": "SELECT color, SUM(stock_quantity) AS total_stock FROM t_shirts GROUP BY color ORDER BY total_stock ASC LIMIT 1;",
    },
    {
        "Question": "How many T-shirts with sizes S and M were sold by the Adidas brand?",
        "SQLQuery": "SELECT SUM(quantity_sold) FROM sales WHERE brand = 'Adidas' AND size IN ('S', 'M');",
    },
    {
        "Question": "Find the percentage of sales for each brand.",
        "SQLQuery": "SELECT brand, SUM(total_sales) * 100.0 / (SELECT SUM(total_sales) FROM sales) AS sales_percentage FROM sales GROUP BY brand;",
    },
    {
        "Question": "Which size of Levi's T-shirts has the highest stock in inventory?",
        "SQLQuery": "SELECT size, MAX(stock_quantity) AS max_stock FROM t_shirts WHERE brand = 'Levi' GROUP BY size ORDER BY max_stock DESC LIMIT 1;",
    },

]

# Database connection parameters
db_user = "root"
db_password = "komal**27"
db_host = "localhost"
db_name = "atliq_tshirts"

# Create SQLAlchemy engine and SQLDatabase
engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")
db = SQLDatabase(engine, sample_rows_in_table_info=3)

# Initialize LLM
llm = GoogleGenerativeAI(model="gemini-pro", google_api_key="AIzaSyCevmB7autUYUBg5SCrzH65j4jpwv19xfQ")

# Few-shots integration
embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
to_vectorize = [" ".join(example.values()) for example in few_shots]
vectorstore = Chroma.from_texts(to_vectorize, embeddings, metadatas=few_shots)

# Example selector
example_selector = SemanticSimilarityExampleSelector(
    vectorstore=vectorstore,
    k=2  # Number of examples to include
)

# Few-shot prompt
mysql_prompt = """You are a MySQL expert. Given an input question, first create a syntactically correct MySQL query to run, then look at the results of the query and return the answer to the input question.
Unless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results using the LIMIT clause as per MySQL. You can order the results to return the most informative data in the database.
Never query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in backticks (`) to denote them as delimited identifiers.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
Pay attention to use CURDATE() function to get the current date, if the question involves "today".

Use the following format:

Question: Question here
SQLQuery: Query to run with no pre-amble

No pre-amble.
"""

example_prompt = PromptTemplate(
    input_variables=["Question", "SQLQuery",],
    template="\nQuestion: {Question}\nSQLQuery: {SQLQuery}",
)

few_shot_prompt = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=example_prompt,
    prefix=mysql_prompt,
    suffix=PROMPT_SUFFIX,
    input_variables=["input", "table_info", "top_k"], #These variables are used in the prefix and suffix
)
chain = create_sql_query_chain(llm, db, prompt=few_shot_prompt)

# Streamlit UI


# Modular Function: Execute SQL Query
def execute_generated_query(question):
    try:
        response = chain.invoke({"question": question})
        query = response.strip("sql\n").strip("\n")
        return query
    except Exception as e:
        st.error(f"Error generating query: {e}")
        return None



# Sidebar feature selection
option = st.sidebar.selectbox("Choose an action:", ["Insightify Chatbot", "Record New Arrivals", "Log Sales Transactions", "View Data Visualization"])

# 1. Feature: Ask a Question
if option == "Insightify Chatbot":
    st.title("Insightify Chatbot 👕")
    question = st.text_input("Enter your question:")
    if st.button("Execute"):
        query = execute_generated_query(question)
        if query:
            st.write("Generated SQL Query:")
            st.code(query, language="sql")
            try:
                result = db.run(query)
                st.write("Query Result:")
                st.write(result)
            except ProgrammingError as e:
                st.error(f"Error executing query: {e}")


# 2. Feature: Add a T-shirt
elif option == "Record New Arrivals":
    st.subheader("Record New Arrivals")

    # Initialize session state for managing form reset
    if "reset_form" not in st.session_state:
        st.session_state.reset_form = False

    if "success_message" not in st.session_state:
        st.session_state.success_message = ""

    # Form for adding new T-shirt
    with st.form("add_tshirt_form", clear_on_submit=True):
        brand = st.text_input("Brand", value="" if st.session_state.reset_form else "")
        color = st.text_input("Color", value="" if st.session_state.reset_form else "")
        size = st.selectbox("Size", ["XS", "S", "M", "L", "XL"])
        price = st.number_input("Price", min_value=1)
        stock_quantity = st.number_input("Stock Quantity", min_value=1)

        submitted = st.form_submit_button("Submit")
        
        if submitted:
            try:
                with engine.connect() as conn:
                    # Check if a T-shirt with these properties already exists
                    check_query = text("""
                        SELECT t_shirt_id, stock_quantity FROM t_shirts 
                        WHERE brand = :brand AND color = :color AND size = :size AND price = :price
                    """)
                    result = conn.execute(check_query, {
                        "brand": brand, "color": color, "size": size, "price": price
                    }).fetchone()

                    if result:
                        # Existing T-shirt found; update stock
                        t_shirt_id, existing_stock = result
                        update_query = text("""
                            UPDATE t_shirts SET stock_quantity = stock_quantity + :new_stock 
                            WHERE t_shirt_id = :t_shirt_id
                        """)
                        conn.execute(update_query, {
                            "new_stock": stock_quantity, "t_shirt_id": t_shirt_id
                        })
                        conn.commit()
                        st.session_state.success_message = f"Updated stock for T-shirt ID {t_shirt_id}. New stock: {existing_stock + stock_quantity}."
                    else:
                        # New T-shirt; insert into database
                        insert_query = text("""
                            INSERT INTO t_shirts (brand, color, size, price, stock_quantity)
                            VALUES (:brand, :color, :size, :price, :stock_quantity)
                        """)
                        conn.execute(insert_query, {
                            "brand": brand, "color": color, "size": size, 
                            "price": price, "stock_quantity": stock_quantity
                        })
                        conn.commit()
                        st.session_state.success_message = "New T-shirt added successfully!"

                # Reset the form for a new entry
                st.session_state.reset_form = True

            except IntegrityError as e:
                st.error(f"Integrity Error: {e}")
            except Exception as e:
                st.error(f"Error: {e}")

    # Display success message if present
    if st.session_state.success_message:
        st.success(st.session_state.success_message)
        st.session_state.success_message = ""

    # "Add Another" button to reset form
    if st.session_state.reset_form:
        if st.button("Add Another"):
            st.session_state.reset_form = False




# 3. Feature: Remove a T-shirt
elif option == "Log Sales Transactions":
    st.subheader("Log Sales Transactions")
    
    # Input for T-shirt ID
    t_shirt_id = st.text_input("Enter the T-shirt ID:")
    
    # Input for quantity to remove
    remove_quantity = st.number_input("Enter the quantity to Sell:", min_value=1, step=1)

    # Button to execute the removal
    if st.button("Sell"):
        try:
            with engine.connect() as conn:
                # Check if the T-shirt ID exists and retrieve the stock quantity
                check_query = text("SELECT stock_quantity FROM t_shirts WHERE t_shirt_id = :t_shirt_id")
                result = conn.execute(check_query, {"t_shirt_id": t_shirt_id}).fetchone()

                if result:
                    stock_quantity = result[0]
                    if remove_quantity > stock_quantity:
                        st.error("The quantity to remove exceeds the available stock.")
                    else:
                        if remove_quantity == stock_quantity:
                            # Remove the T-shirt if all stock is to be removed
                            delete_query = text("DELETE FROM t_shirts WHERE t_shirt_id = :t_shirt_id")
                            conn.execute(delete_query, {"t_shirt_id": t_shirt_id})
                            st.success(f"T-shirt ID {t_shirt_id} removed successfully!")
                        else:
                            # Reduce the stock quantity
                            update_query = text(
                                "UPDATE t_shirts SET stock_quantity = stock_quantity - :remove_quantity WHERE t_shirt_id = :t_shirt_id"
                            )
                            conn.execute(update_query, {"remove_quantity": remove_quantity, "t_shirt_id": t_shirt_id})
                            st.success(f"Reduced stock quantity for T-shirt ID {t_shirt_id} by {remove_quantity}. Remaining stock: {stock_quantity - remove_quantity}.")
                else:
                    st.warning("T-shirt ID not found.")
                conn.commit()
        except Exception as e:
            st.error(f"Error: {e}")


elif option == "View Data Visualization":
        try:
            with open("data_visualization.py", encoding="utf-8") as f:
                exec(f.read())
        except UnicodeDecodeError as e:
            print(f"Encoding issue: {e}")

