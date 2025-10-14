import streamlit as st
from passlib.hash import pbkdf2_sha256
from db_connector import get_db_connection
import mysql.connector

st.set_page_config(layout="wide")

def login_user(email, password):
    """Verifies user credentials against the database using email."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and pbkdf2_sha256.verify(password, user['password_hash']):
            # Combine first and last name for display
            user['full_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            return user
    return None

def register_user(first_name, last_name, email, password):
    """Hashes password and creates a new user with the default 'user' role."""
    password_hash = pbkdf2_sha256.hash(password)
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Note: The `users` table in the new schema doesn't have `username`. Using email for login.
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, password_hash, role) VALUES (%s, %s, %s, %s, 'user')",
                (first_name, last_name, email, password_hash)
            )
            conn.commit()
            return True
        except mysql.connector.Error as err:
            if err.errno == 1062: # Duplicate entry for email
                st.error(f"Registration failed: An account with the email '{email}' already exists.")
            else:
                st.error(f"A database error occurred: {err}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

def main():
    """Main function to run the Streamlit app."""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None

    if st.session_state.get('logged_in'):
        st.sidebar.success(f"Logged in as {st.session_state['user_info']['full_name']}")
        st.sidebar.write(f"Role: {st.session_state['user_info']['role']}")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.write("# Welcome to the Timesheet Application!")
        st.write("Please select a dashboard from the sidebar.")

    else:
        st.title("Timesheet Application")
        login_tab, register_tab = st.tabs(["Login", "Register"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                
                if submitted:
                    user = login_user(email, password)
                    if user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = user
                        st.rerun()
                    else:
                        st.error("Invalid email or password")

        with register_tab:
            with st.form("register_form", clear_on_submit=True):
                st.subheader("Create a New Account")
                reg_first_name = st.text_input("First Name*")
                reg_last_name = st.text_input("Last Name*")
                reg_email = st.text_input("Email*")
                reg_password = st.text_input("Password*", type="password")
                reg_password_confirm = st.text_input("Confirm Password*", type="password")
                
                register_submitted = st.form_submit_button("Register")

                if register_submitted:
                    if not all([reg_first_name, reg_last_name, reg_email, reg_password, reg_password_confirm]):
                        st.warning("Please fill out all required fields marked with *.")
                    elif reg_password != reg_password_confirm:
                        st.error("Passwords do not match.")
                    else:
                        if register_user(reg_first_name, reg_last_name, reg_email, reg_password):
                            st.success("Registration successful! You can now log in.")

if __name__ == "__main__":
    main()

