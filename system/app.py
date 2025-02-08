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


###### while user ID not in emoji feedback redirect to logout.html and if they are in emoji feedback redirect to feedback_options.html. Allow users to see previous feeback, change it if they'd like, or log off without changing.
# Log out route
@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        if request.args.get('direct_logout') == 'true':  # Added this condition for logging out without changing rating for exisiting users (see feedback_options.html)
            logout_user()  # Log the user out
            return render_template('message.html', message="You have been logged out.")
        user_id = current_user.id
        submission_date = datetime.now().date() #using just the date because SQL can't convert datetime into just date for referencing unique conditions

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM EmojiFeedback WHERE UserID = %s AND DATE(SubmissionDate) = %s",
            (user_id, submission_date)
        )
        existing_feedback = cursor.fetchone() #checking for existing feedback for a user on that specific day
        cursor.close()
        conn.close()

        if existing_feedback:
            emoji_map = {1: "😞", 2: "🙁", 3: "😐", 4: "🙂", 5: "😁"} #stores emojis into values to show on the frontend
            selected_emoji = emoji_map.get(existing_feedback['EmojiRating'], "😐")
            return render_template(
                'feedback_options.html',
                selected_emoji=selected_emoji
            )
        else:
            return render_template('logout.html') #no existing feedback then fill out for the first time
    return redirect(url_for('login'))

@app.route('/rate_day', methods=['POST'])
def rate_day():
    if current_user.is_authenticated:
        user_id = current_user.id
        submission_date = datetime.now().date()
        new_rating = int(request.form['rating'])
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check for existing feedback
        cursor.execute(
            "SELECT * FROM EmojiFeedback WHERE UserID = %s AND DATE(SubmissionDate) = %s",
            (user_id, submission_date)
        )
        existing_feedback = cursor.fetchone()

        if existing_feedback:
            # Update the existing feedback
            cursor.execute(
                "UPDATE EmojiFeedback SET EmojiRating = %s WHERE FeedbackID = %s",
                (new_rating, existing_feedback['FeedbackID'])
            )
        else:
            # Insert new feedback
            cursor.execute(
                "INSERT INTO EmojiFeedback (UserID, EmojiRating, SubmissionDate) VALUES (%s, %s, %s)",
                (user_id, new_rating, datetime.now())
            )
        conn.commit()
        cursor.close()
        conn.close()
        logout_user()
        return render_template('message.html', message="You have been logged out.")

    return redirect(url_for('login'))

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