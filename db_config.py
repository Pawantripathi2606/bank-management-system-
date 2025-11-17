import mysql.connector
import streamlit as st
import time
from mysql.connector import Error

# Configuration for retries
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds

@st.cache_resource
def connect():
    """
    Establishes and caches the MySQL database connection with retry logic.
    Retries up to MAX_RETRIES times if connection initially fails.
    The process is now silent in the UI.
    """
    
    for attempt in range(MAX_RETRIES):
        try:
            # NOTE: Using the credentials from your original file. Double-check these!
            db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="Pawan123@",
                database="bank_system"
            )
            
            if db.is_connected():
                # Success is silent now, just return the connection
                return db
            
        except Error as err:
            # Errors are only printed to the terminal console, not the Streamlit UI
            print(f"DEBUG: DB Connection attempt {attempt + 1}/{MAX_RETRIES} failed: {err}")
            
            # If this is not the last attempt, wait before retrying
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                # If all attempts fail, halt the app with a silent st.stop()
                st.error(" Failed to establish database connection after multiple retries. Please check your MySQL server and credentials.")
                st.stop()
    
    # This line should ideally not be reached, but ensures a final stop if loop somehow exits.
    st.stop()