import mysql.connector, os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify 
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin
from datetime import datetime

app = Flask(__name__)

app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem to persist session data
app.config['SESSION_PERMANENT'] = True
app.secret_key = os.urandom(24)  # Generates a random 24-byte secret key
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# MySQL database connection function
def get_db_connection():
    conn = mysql.connector.connect(
        host='107.180.1.16',
        port= 3306,
        user='cis440springA2025team3',
        password='cis440springA2025team3',
        database='cis440springA2025team3'
    )
    return conn


# Define User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Fetch results as dictionaries
    cursor.execute("SELECT * FROM User WHERE UserID = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return User(user['UserID'], user['Username']) if user else None


@app.route('/')
def home():
    return render_template('index.html')


###### need to do error catch block if someone is going to submit more than twice in one day
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM User WHERE Username = %s AND Password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            login_user(User(user['UserID'], user['Username']))
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


###### while user ID not in emoji feedback redirect to emoji page and if they are in emoji feedback, log out
# Log out route
@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        return render_template('logout.html')
    return redirect(url_for('login'))  # Redirect to login page if not logged in


# Rate Day route
@app.route('/rate_day/<int:rating>')
def rate_day(rating):
    if current_user.is_authenticated:
        user_id = current_user.id
        submission_time = datetime.now()  # Get the current date and time

        # Save the rating and submission time to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO EmojiFeedback (UserID, EmojiRating, SubmissionDate) VALUES (%s, %s, %s)",
                       (user_id, rating, submission_time))
        conn.commit()
        cursor.close()
        conn.close()

        # Log the user out
        logout_user()

        # Redirect to the home page with a logout message
        return render_template('message.html', message="You have been logged out.")

    return redirect(url_for('login'))  # Redirect to login page if not logged in

# Route to render the create account form
@app.route('/createaccount', methods=['GET'])
def createaccount_form():
    return render_template('createaccount.html')

# Route to create a new user
@app.route('/createaccount', methods=['POST'])
def createaccount():
    data = request.form  # Get form data
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    # Save to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor() 
        cursor.execute("INSERT INTO User (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "User registered successfully!"}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Username already exists!"}), 409
    except Exception as e:
        # Log the error
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500


if __name__ == '__main__':
    app.run(debug=True)