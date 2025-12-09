import streamlit as st
import pandas as pd
from db_config import connect
import mysql.connector
import bcrypt
import time

# --- UI Layout Configuration ---
st.set_page_config(
    page_title="Bank Management System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
# Tracks if a user is currently logged in
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
# Stores the email of the logged-in user
if 'user_email' not in st.session_state:
    st.session_state.user_email = None


# --- DATABASE SETUP (User Table) ---

def create_user_table(db_connection):
    """Ensures the users table exists for login/registration with Email and Hashed Password."""
    try:
        cursor = db_connection.cursor()
        # Only saving email and password hash
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(sql)
        db_connection.commit()
    except mysql.connector.Error as err:
        st.error(f"FATAL: Error initializing user table: {err}. Check MySQL permissions and database status.")
        st.stop()


# --- AUTHENTICATION DB FUNCTIONS ---

def register_user(email, password):
    """Registers a new user and hashes the password using bcrypt."""
    db = connect()
    try:
        cursor = db.cursor()
        
        # 1. Hash the password securely
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 2. Insert into users table
        sql = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
        values = (email, hashed_password)
        cursor.execute(sql, values)
        db.commit()
        return True, "Registration successful! You can now log in."
    except mysql.connector.Error as err:
        if 'Duplicate entry' in str(err) and 'email' in str(err):
            return False, "This email is already registered."
        return False, f"Database error: {err}"


def authenticate_user(email, password):
    """Checks user email/password credentials against the database."""
    db = connect()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        
        if result:
            stored_hash = result[0].encode('utf-8')
            # Verify the entered password against the stored hash
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                return True, "Credentials verified."
            else:
                return False, "Incorrect password."
        else:
            return False, "Email not found."
    except mysql.connector.Error as err:
        return False, f"Authentication error: {err}"


# --- AUTHENTICATION UI COMPONENTS ---

def login_page():
    """Displays the single-step login and registration forms."""
    st.title("Welcome to Streamlit Bank Manager")
    st.sidebar.header("Login / Register")

    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

    with tab_login:
        st.subheader("Sign In")
        with st.form("login_form"):
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if not login_email or not login_password:
                    st.warning("Please enter email and password.")
                else:
                    success, message = authenticate_user(login_email, login_password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_email = login_email
                        st.success("Login successful!")
                        st.rerun() # Rerun to switch to the banking menu
                    else:
                        st.error(message)

    with tab_register:
        st.subheader("Create a New Account")
        with st.form("register_form"):
            reg_email = st.text_input("Email (Mandatory)", key="reg_email")
            reg_password = st.text_input("Password (Mandatory)", type="password", key="reg_password")
            
            reg_submitted = st.form_submit_button("Register Account")
            
            if reg_submitted:
                if not reg_email or not reg_password:
                    st.warning("Email and Password are required.")
                elif len(reg_password) < 6:
                    st.warning("Password must be at least 6 characters.")
                else:
                    # Note: Phone number registration is removed as requested
                    success, message = register_user(reg_email, reg_password)
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)


def logout():
    """Clears session state and reruns the app to show the login page."""
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.toast("Logged out successfully!")
    time.sleep(0.5)
    st.rerun()


# --- EXISTING BANKING FUNCTIONS (Access database for banking data) ---

def create_account_db(name, email, balance):
    """Inserts a new account into the database."""
    db = connect()
    try:
        cursor = db.cursor()
        sql = "INSERT INTO accounts (`name`, `email`, `balance`) VALUES (%s, %s, %s)"
        values = (name, email, balance)
        cursor.execute(sql, values)
        db.commit()
        connect.clear()
        return True, "Account created successfully!"
    except mysql.connector.Error as err:
        return False, f"Error creating account: {err}"

def get_all_accounts():
    """Fetches all accounts and returns as a list of dicts/tuples."""
    db = connect()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, balance FROM accounts")
        accounts = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]
        return column_names, accounts
    except mysql.connector.Error as err:
        st.error(f"Error fetching accounts: {err}")
        return [], []

def update_balance(acc_id, amount, operation):
    """Performs deposit or withdrawal."""
    db = connect()
    try:
        cursor = db.cursor()
        
        if operation == "WITHDRAW":
            cursor.execute("SELECT balance FROM accounts WHERE id = %s", (acc_id,))
            result = cursor.fetchone()
            if not result:
                return False, "Account ID not found."
            current_balance = result[0]
            if current_balance < amount:
                return False, f"INSUFFICIENT BALANCE. Current balance: ₹{current_balance:.2f}"
            sql = "UPDATE accounts SET balance = balance - %s WHERE id = %s"
        elif operation == "DEPOSIT":
            sql = "UPDATE accounts SET balance = balance + %s WHERE id = %s"
        else:
            return False, "Invalid operation type."

        cursor.execute(sql, (amount, acc_id))
        
        if cursor.rowcount == 0:
             return False, "Account ID not found or no change made."
             
        db.commit()
        connect.clear()
        
        action_word = "DEPOSITED" if operation == "DEPOSIT" else "WITHDRAWAL"
        return True, f"{action_word} successful."
        
    except mysql.connector.Error as err:
        return False, f"Transaction error: {err}"

def get_balance(acc_id):
    """Fetches name and balance for a given account ID."""
    db = connect()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT name, balance FROM accounts where id= %s", (acc_id,))
        result = cursor.fetchone()
        
        if result:
            return True, {"name": result[0], "balance": result[1]}
        else:
            return False, "ACCOUNT NOT FOUND"

    except mysql.connector.Error as err:
        return False, f"Error checking balance: {err}"

# --- Streamlit UI Components for Each Operation ---

def create_account_ui():
    """UI for creating a new bank account."""
    st.subheader(" Create New Account")
    with st.form("create_account_form"):
        name = st.text_input("Account Holder Name", key="name")
        email = st.text_input("Email Address", key="email")
        balance = st.number_input("Opening Balance (₹)", min_value=0.00, value=100.00, step=0.01, key="balance")
        submitted = st.form_submit_button("Create Account")

        if submitted:
            if not name or not email:
                st.warning("Please fill in both Name and Email.")
            elif balance <= 0:
                st.warning("Opening balance must be greater than zero.")
            else:
                success, message = create_account_db(name, email, float(balance))
                if success:
                    st.success(message)
                else:
                    st.error(message)

def view_accounts_ui():
    """UI for viewing all bank accounts."""
    st.subheader("👥 View All Accounts")
    column_names, accounts = get_all_accounts()
    if accounts:
        df = pd.DataFrame(accounts, columns=column_names)
        st.data_editor(
            df, 
            width='stretch', 
            hide_index=True,
            column_config={
                "balance": st.column_config.NumberColumn(
                    "Balance",
                    format="₹%.2f",
                )
            }
        )
    else:
        st.info("No accounts found in the database.")


def transaction_ui(operation):
    """Generic UI for Deposit and Withdraw operations."""
    st.subheader(f"{operation.title()} Money")
    form_key = f"{operation.lower()}_form"
    with st.form(form_key):
        st.info(f"Please enter the Account ID and the amount to {operation.lower()}.")
        acc_id = st.number_input("Account ID", min_value=1, step=1, key=f"{operation}_id", format="%d")
        amount = st.number_input(f"Amount to {operation.title()} (₹)", min_value=0.01, step=0.01, key=f"{operation}_amount")
        submitted = st.form_submit_button(f"Execute {operation.title()}")
        if submitted:
            if amount <= 0:
                st.warning("Amount must be greater than zero.")
            elif acc_id < 1:
                st.warning("Please enter a valid Account ID.")
            else:
                success, message = update_balance(int(acc_id), float(amount), operation.upper())
                if success:
                    st.success(message)
                    balance_success, balance_data = get_balance(int(acc_id))
                    if balance_success:
                        st.write(f"**Updated Balance for Account ID {acc_id}: ₹{balance_data['balance']:.2f}**")
                else:
                    st.error(message)


def check_balance_ui():
    """UI for checking an account's balance."""
    st.subheader("Check Account Balance")
    with st.form("check_balance_form"):
        acc_id = st.number_input("Enter Account ID", min_value=1, step=1, key="check_id", format="%d")
        submitted = st.form_submit_button("Check Balance")
        if submitted:
            if acc_id < 1:
                st.warning("Please enter a valid Account ID.")
            else:
                success, data = get_balance(int(acc_id))
                if success:
                    st.success(f"Account Holder: {data['name']}")
                    st.success(f"Current Balance: **₹{data['balance']:.2f}**")
                else:
                    st.error(data) 


# --- Main Application Logic ---

def main():
    try:
        # Step 1: Attempt to establish the connection first. 
        db_conn = connect() 
        
        # Step 2: If connection is successful, ensure the user table exists.
        create_user_table(db_conn)

        # Step 3: Run the main application logic
        if not st.session_state.logged_in:
            login_page()
        else:
            st.title("Bank Management system")
            st.sidebar.success(f"Logged in as: {st.session_state.user_email}")
            
            st.sidebar.button("Logout", on_click=logout)
            st.sidebar.markdown("---")
            st.sidebar.header("Navigation")
            
            menu_options = [
                "Create Account", 
                "View All Accounts", 
                "Deposit Money", 
                "Withdraw Money", 
                "Check Balance"
            ]
            
            choice = st.sidebar.radio("Select Operation", menu_options)
            
            st.markdown("---")

            if choice == "Create Account":
                create_account_ui()
            elif choice == "View All Accounts":
                view_accounts_ui()
            elif choice == "Deposit Money":
                transaction_ui("Deposit")
            elif choice == "Withdraw Money":
                transaction_ui("Withdraw")
            elif choice == "Check Balance":
                check_balance_ui()
            
            st.sidebar.markdown("---")
<<<<<<< HEAD
            st.sidebar.info("Developed by student")
=======
            
>>>>>>> 47c42ad51fe4e6148170efe90525c362bc488896

    except Exception as e:
        st.error("A critical error occurred during application startup.")
        st.exception(e)


if __name__ == "__main__":
    main()
