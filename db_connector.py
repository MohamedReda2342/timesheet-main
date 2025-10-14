import streamlit as st
import mysql.connector
from mysql.connector import Error

# Database connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '2342',
    'database': 'timesheet_app'
}

# Function to create a database connection
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        st.error(f"Error connecting to MySQL Database: {e}")
        return None
