import mysql.connector, os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify , Blueprint, session
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin, login_required
import datetime
from datetime import datetime, timedelta
from turbo_flask import Turbo
import math 


app = Flask(__name__)
app.config['TURBO_USE_CDN'] = True
turbo = Turbo(app)
profile_bp = Blueprint('profile', __name__)


app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem to persist session data
app.config['SESSION_PERMANENT'] = True
app.secret_key = os.urandom(24)  # Generates a random 24-byte secret key
app.config['SESSION_COOKIE_NAME'] = 'your_session_cookie'
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
    def __init__(self, id, username, isadmin):     # Zar: added isadmin
        self.id = id
        self.username = username
        self.isadmin = isadmin    # Zar: added isadmin

    @property
    def IsAdmin(self):
        return self.isadmin


# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Fetch results as dictionaries
    cursor.execute("SELECT * FROM User WHERE UserID = %s AND IsActive = 1", (user_id,))  # Zar: added IsActive
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return User(user['UserID'], user['Username'], user['IsAdmin']) if user else None   # Zar: added isadmin



# Rana: route to home page
@app.route('/')
def home():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    yesterday = (datetime.now() - timedelta(days=1)).date()

    # Count total users who submitted feedback yesterday
    cursor.execute("""
        SELECT COUNT(DISTINCT UserID) AS total_users 
        FROM EmojiFeedback 
        WHERE Date(SubmissionDate) = %s
    """, (yesterday,))
    total_users = cursor.fetchone()['total_users']

    # Count how many users submitted each emoji rating
    cursor.execute("""
        SELECT EmojiRating, COUNT(*) AS count 
        FROM EmojiFeedback 
        WHERE Date(SubmissionDate) = %s 
        GROUP BY EmojiRating
    """, (yesterday,))
    
    emoji_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # Default values
    for row in cursor.fetchall():
        emoji_counts[row['EmojiRating']] = row['count']

    cursor.close()
    conn.close()

    return render_template('index.html', data={'total_users': total_users, 'emoji_counts': emoji_counts})



# Rana: Function to check if user is locked out
def is_user_locked(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT failed_attempts, lockout_time FROM FailedAttempts WHERE UserID = %s", (user_id,))
    record = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if record:
        failed_attempts = record['failed_attempts']
        lockout_time = record['lockout_time']
        
        if failed_attempts >= 5 and lockout_time and datetime.now() < lockout_time:
            return True, lockout_time  # User is locked out
    return False, None


# Rana: route to log in to account
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
 
        # Fetch user details
        cursor.execute("SELECT * FROM User WHERE Username = %s AND IsActive = 1", (username,)) #Zar : added IsActive
 
        user = cursor.fetchone()
        
 
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('login'))
        
        user_id = user['UserID']

        # Check if user is locked out
        locked, lockout_time = is_user_locked(user_id)
        if locked:
            flash(f"Too many failed attempts. Try again at {lockout_time.strftime('%I:%M %p')}.", "danger")
            return redirect(url_for('login'))
        
        if user['Password'] == password:
            # Successful login, reset failed attempts
            cursor.execute("DELETE FROM FailedAttempts WHERE UserID = %s", (user_id,))
            conn.commit()
            
            login_user(User(user['UserID'], user['Username'], user['IsAdmin']))   # Zar: added isadmin
            cursor.close()
            conn.close()
 
            return redirect(url_for('home'))
        else:
            # Wrong password
            cursor.execute("SELECT failed_attempts FROM FailedAttempts WHERE UserID = %s", (user_id,))
            record = cursor.fetchone()
            
            if record:
                failed_attempts = record['failed_attempts'] + 1
                if failed_attempts >= 5:
                    lockout_time = datetime.now() + timedelta(minutes=5)
                    cursor.execute("UPDATE FailedAttempts SET failed_attempts = %s, lockout_time = %s WHERE UserID = %s",
                                   (failed_attempts, lockout_time, user_id))
                    flash("Too many failed attempts. You are locked out for 5 minutes.", "danger")
                else:
                    cursor.execute("UPDATE FailedAttempts SET failed_attempts = %s WHERE UserID = %s",
                                   (failed_attempts, user_id))
                    flash("Incorrect password.", "danger")
            else:
                cursor.execute("INSERT INTO FailedAttempts (UserID, failed_attempts, lockout_time) VALUES (%s, %s, NULL)",
                               (user_id, 1))
                flash("Incorrect password.", "danger")

            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('login'))
    
    return render_template('login.html')


# Rana: route to log out 
@app.route('/logout')
def logout():
    if current_user.is_authenticated:

        # Jacob: edited to allow users to log out after already rating - can change or keep previous rating for the day 
        if request.args.get('direct_logout') == 'true':  # Added this condition for logging out without changing rating for exisiting users (see feedback_options.html)
            logout_user()  # Log the user out
            return render_template('message.html', message="You have been logged out.")
        user_id = current_user.id
        submission_date = datetime.now().date()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if feedback already exists for today
        cursor.execute(
            "SELECT * FROM EmojiFeedback WHERE UserID = %s AND DATE(SubmissionDate) = %s",
            (user_id, submission_date)
        )
        
        # Fetch the result before closing the cursor
        existing_feedback = cursor.fetchone() 


        # Process the result
        if existing_feedback:
            emoji_map = {1: "😞", 2: "🙁", 3: "😐", 4: "🙂", 5: "😁"} #stores emojis into values to show on the frontend
            selected_emoji = emoji_map.get(existing_feedback['EmojiRating'], "😐")

            cursor.fetchall()
            cursor.close()
            conn.close()

            return render_template(
                'feedback_options.html',
                selected_emoji=selected_emoji
            )
        else:
            cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('logout.html') #no existing feedback then fill out for the first time
           
    return redirect(url_for('login'))


# Rana: Route to daily emoji rating
@app.route('/rate_day', methods=['POST'])
def rate_day():
    if current_user.is_authenticated:
        user_id = current_user.id
        submission_date = datetime.now().date()
        new_rating = int(request.form['rating'])
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Jacob: edited to solve error and check for existing feedback
        cursor.execute(
            "SELECT * FROM EmojiFeedback WHERE UserID = %s AND DATE(SubmissionDate) = %s",
            (user_id, submission_date)
        )
        existing_feedback = cursor.fetchone()

        cursor.fetchall()

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
            
            # Zar : Updating 3 point for Rating Day                                      
            cursor.execute(
                "UPDATE User SET Points = Points + 3  WHERE UserID = %s", (user_id,)
            )

            # Rana : Saving action for Point History
            cursor.execute("""
                INSERT INTO PointsHistory (UserID, Points, Action, ActionDate) 
                VALUES (%s, %s, %s, %s)
            """, (user_id, 3, "Rated the day",  datetime.now()))
 

        conn.commit()

        cursor.close()
        conn.close()

        logout_user()
        return render_template('message.html', message="You have been logged out.")

    return redirect(url_for('login'))


# Rana: Route to profile 
@app.route('/my_profile', methods=['GET', 'POST'])
@login_required
def my_profile():
    user_id = current_user.id  # Use Flask-Login's current_user

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Use dictionary=True to get column names

    # Fetch username and user statistics in a single query
    query = """
        SELECT 
            u.Username,
            u.Points,  
            COUNT(DISTINCT e.FeedbackID) AS EmojiCount,
            COUNT(DISTINCT v.VoteID) AS VoteCount,
            COUNT(DISTINCT s.SuggestionID) AS SuggestionCount
        FROM User u
        LEFT JOIN EmojiFeedback e ON u.UserID = e.UserID
        LEFT JOIN Vote v ON u.UserID = v.UserID
        LEFT JOIN Suggestion s ON u.UserID = s.UserID
        WHERE u.UserID = %s;
    """

    cursor.execute(query, (user_id,))
    user_data = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'profile/my_profile.html', 
        username=user_data["Username"],
        points=user_data["Points"],
        emoji_count=user_data["EmojiCount"],
        vote_count=user_data["VoteCount"],
        suggestion_count=user_data["SuggestionCount"]
    )



# Rana: route to my ratings in profile
@app.route('/my_ratings')
@login_required
def my_ratings():
    user_id = current_user.id  # Use Flask-Login's current_user

    conn = get_db_connection()

    # Use the first cursor to fetch today's reaction
    cursor1 = conn.cursor(dictionary=True)
    cursor1.execute(
        "SELECT emojirating, submissiondate FROM EmojiFeedback WHERE userID = %s AND DATE(submissiondate) = CURDATE()",
        (user_id,))
    todays_reaction = cursor1.fetchone()
    cursor1.fetchall()
    cursor1.close()  # Close the first cursor after use

    # Use the second cursor to fetch all reactions
    cursor2 = conn.cursor(dictionary=True)
    cursor2.execute("SELECT emojirating, submissiondate FROM EmojiFeedback WHERE userID = %s", (user_id,))
    all_reactions = cursor2.fetchall()
    all_reactions = sorted(all_reactions, key=lambda x: x['submissiondate'], reverse=True)
    cursor2.fetchall()
    cursor2.close()  # Close the second cursor after use

    # Close the connection
    conn.close()
    return render_template('profile/my_ratings.html', todays_reaction=todays_reaction, all_reactions=all_reactions)


# Rana: route to my points in profile
@app.route('/my_points')
@login_required
def my_points():
    user_id = current_user.id  # Get current user ID

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
            SELECT PointID, Points, Action, ActionDate 
            FROM PointsHistory
            WHERE UserID = %s
            ORDER BY ActionDate DESC
        """, (user_id,))
        
    points_data = cursor.fetchall()

    # Calculate total points
    total_points = sum(item['Points'] for item in points_data)

    points_data = sorted(
        points_data, 
        key=lambda x: (
            x['ActionDate'].replace(tzinfo=None) if isinstance(x['ActionDate'], datetime) else x['ActionDate']
        ),
        reverse=True  # Reverse to get the most recent on top
    )

    cursor.close()
    conn.close()
    return render_template('profile/my_points.html', points_data=points_data, total_points=total_points)


# Rana: route to my suggestions in profile
@app.route('/my_suggestions')
@login_required
def my_suggestions():
    user_id = current_user.id  # Use Flask-Login's current_user

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Use dictionary=True to get column names

    # Get filter parameters from the request, if any
    suggestion_filter = request.args.get('suggestion_filter', '')  # Default to empty string
    suggestion_keyword = request.args.get('suggestion_keyword', '')  # Keyword search for filtering suggestions

    # Base query for fetching suggestions
    suggestion_query = """
        SELECT 
            s.suggestionID, s.Description, s.Comments, s.createdDate, s.netVotes, 
            s.positiveVote, s.negativeVote, 
            (SELECT st.StatusName 
            FROM Status st 
            WHERE s.NetVotes >= st.Threshold 
            ORDER BY st.Threshold DESC 
            LIMIT 1) AS StatusName
        FROM Suggestion s
        WHERE s.userID = %s
    """
    params = [user_id]

    # Apply filters based on the selected filter option
    if suggestion_filter == 'today':
        suggestion_query += " AND DATE(s.createdDate) = CURDATE()"
    elif suggestion_filter == 'last_week':
        suggestion_query += " AND s.createdDate >= CURDATE() - INTERVAL 7 DAY"
    elif suggestion_filter == 'recent_to_oldest':
        suggestion_query += " ORDER BY s.createdDate DESC"
    elif suggestion_filter == 'oldest_to_recent':
        suggestion_query += " ORDER BY s.createdDate ASC"
    elif suggestion_filter == 'highest_net_votes':
        suggestion_query += " ORDER BY s.netVotes DESC"
    elif suggestion_filter == 'lowest_net_votes':
        suggestion_query += " ORDER BY s.netVotes ASC"
    elif suggestion_filter == 'keyword' and suggestion_keyword:
        suggestion_query += " AND s.description LIKE %s"
        params.append(f'%{suggestion_keyword}%')  # Add the parameter only if keyword filter is used

    # Default to sorting by createdDate DESC (most recent first) if no filter is selected
    if not suggestion_filter:
        suggestion_query += " ORDER BY s.createdDate DESC"
    
    cursor.execute("SELECT COUNT(*) FROM Suggestion WHERE userID = %s", (user_id,))
    total_suggestions = cursor.fetchone()["COUNT(*)"]  # Get the total count of user's suggestions

    cursor.execute(suggestion_query, tuple(params))  # Execute the query after modifying the string and params
    
    suggestions = cursor.fetchall()


    cursor.close()  # Close the cursor after use
    conn.close()  # Close the connection
    return render_template('profile/my_suggestions.html', suggestions=suggestions, total_suggestions=total_suggestions,
                           suggestion_filter=suggestion_filter, suggestion_keyword=suggestion_keyword)


# Rana: route to my votes in profile
@app.route('/my_votes')
@login_required
def my_votes():
    user_id = current_user.id  # Use Flask-Login's current_user

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Use dictionary=True to get column names

    vote_filter = request.args.get('vote_filter', '')  # Default to empty string
    vote_keyword = request.args.get('vote_keyword', '')  # Keyword search for filtering votes

    # Build dynamic query for filtering votes given
    vote_query = """
        SELECT v.voteType, v.suggestionID, v.VotedDate, 
            s.description, s.userID, s.CreatedDate, s.suggestionID, s.Comments,
            (SELECT st.StatusName 
            FROM Status st 
            WHERE s.NetVotes >= st.Threshold 
            ORDER BY st.Threshold DESC 
            LIMIT 1) AS StatusName 
        FROM Vote v
        JOIN Suggestion s ON v.suggestionID = s.suggestionID
        WHERE v.userID = %s
    """

    # Parameters for the query
    vote_params = [user_id]  

    # Apply vote filters
    if vote_filter == 'today':
        vote_query += " AND DATE(v.VotedDate) = CURDATE()"
    elif vote_filter == 'last_week':
        vote_query += " AND v.VotedDate >= CURDATE() - INTERVAL 7 DAY"
    elif vote_filter == 'recent_to_oldest':
        vote_query += " ORDER BY v.VotedDate DESC"
    elif vote_filter == 'oldest_to_recent':
        vote_query += " ORDER BY v.VotedDate ASC"
    elif vote_filter == 'yes':
        vote_query += " AND v.voteType = 1"
    elif vote_filter == 'no':
        vote_query += " AND v.voteType = 0"
    elif vote_filter == 'keyword' and vote_keyword:
        vote_query += " AND s.description LIKE %s"
        vote_params.append(f'%{vote_keyword}%')  # Add the parameter only if keyword filter is used

    # Default to sorting by VotedDate DESC (most recent first) if no filter is selected
    if not vote_filter:
        vote_query += " ORDER BY v.VotedDate DESC"

    cursor.execute("SELECT COUNT(*) FROM Vote WHERE userID = %s", (user_id,))
    total_votes = cursor.fetchone()["COUNT(*)"]  # Get the total count of user's suggestions

    # Execute vote query
    cursor.execute(vote_query, tuple(vote_params))  # Pass parameters as a tuple
    votes_given = cursor.fetchall()

    cursor.close()  # Close the cursor after use
    conn.close()  # Close the connection

    return render_template('profile/my_votes.html', vote_filter=vote_filter, total_votes=total_votes,
                           vote_keyword=vote_keyword, votes_given=votes_given)


# Rana: route to my account in profile
@app.route('/my_account')
@login_required  # Ensure only logged-in users can access
def my_account():
    user_id = current_user.id  

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  

    cursor.execute("SELECT username FROM User WHERE UserID = %s", (user_id,))
    user = cursor.fetchone()  # Fetch the user's username

    cursor.close()
    conn.close()

    return render_template('profile/my_account.html', user=user) 


# Rana: route to change password in my account 
@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    user_id = current_user.id  

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    print(f"Current Password: {current_password}")  # Debugging
    print(f"New Password: {new_password}")  # Debugging
    print(f"Confirm Password: {confirm_password}")  # Debugging

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the current password (plain text)
    cursor.execute("SELECT Password FROM User WHERE UserID = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        flash("User not found.", "error")
        return redirect(url_for('my_account'))

    # Check if the current password matches the one in the database (no hashing)
    if user['Password'] != current_password:
        flash("Current password is incorrect.", "error")
        return redirect(url_for('my_account'))

    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for('my_account'))

    # Update the password (plain text)
    cursor.execute("UPDATE User SET Password = %s WHERE UserID = %s", (new_password, current_user.id))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Password updated successfully.", "success")
    return redirect(url_for('my_account'))


# Zar: route to render the user management
@app.route('/user_management', methods=['GET'])
@login_required
def user_management():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of suggestions per page
        offset = (page - 1) * per_page  # Calculate offset

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get total number of suggestions
        cursor.execute("SELECT COUNT(*) AS total FROM User")
        total_users = cursor.fetchone()['total']
        total_pages = (total_users + per_page - 1) // per_page  # Calculate total pages

        # Fetch suggestions with pagination
        query = """
                SELECT *, CASE  WHEN IsActive = 1 THEN 'Active' 
                                ELSE 'Deactivated' 
                          END AS Status 
                FROM User 
                ORDER BY IsActive DESC, UserName ASC
                LIMIT %s OFFSET %s
                """
        cursor.execute(query, (per_page, offset))
        users = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('user_management.html', users=users, page=page, total_pages=total_pages)
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500
     

# Zar: route to update the user details
@app.route('/update', methods=['POST'])
def update_user():
    data = request.get_json()
    user_id = data.get('id')
    username = data.get('username')
    password = data.get('password')
     
    if not user_id or not username or not password:
        return jsonify({"status": "error", "message": "Missing Data."}), 400

    # update to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "UPDATE User SET username = %s , password = %s WHERE UserID = %s", (username,password,user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "User updated successfully!"}), 201
    
    except Exception as e:
        # Log the error
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500
    

# Zar: route to deactivate the user
@app.route('/deactivate', methods=['POST'])
def deactivate_user():
    data = request.get_json()
    user_id = data.get('id')

     # update to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('UPDATE User SET IsActive = 0 WHERE UserID = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "User is deactivated successfully!"}), 201 
    
    except Exception as e:
        # Log the error
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500


# Zar: route to reactivate the user
@app.route('/reactivate', methods=['POST'])
def reactivate_user():
    data = request.get_json()
    user_id = data.get('id')

     # update to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('UPDATE User SET IsActive = 1 WHERE UserID = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "User is deactivated successfully!"}), 201 
    
    except Exception as e:
        # Log the error
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500    
 

# Zar: route to render the create account form
@app.route('/createaccount', methods=['GET'])
def createaccount_form():
    return render_template('createaccount.html')


# Zar: route to create a new user
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
        cursor.execute("INSERT INTO User (Username, Password) VALUES (%s, %s)", (username, password))
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


# Zar: route to render the suggestions form
@app.route('/suggestion', methods=['GET'])
@login_required
def suggestion_form():
    user_id = current_user.id  # Use Flask-Login's current_user

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Suggestion WHERE userID=%s", (user_id,))
        suggestions = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('suggestion.html', suggestions=suggestions)
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500
     

# Zar: route to suggestions
@app.route('/suggestion', methods=['POST'])
@login_required
def add_suggestion():
    data = request.form
    user_id = current_user.id
    description = data.get("Description")
 
    comments = data.get("Comments")  
 
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) 
      
        # Insert suggestion    
        query = """
                INSERT INTO Suggestion (UserID, Description, Comments, CreatedDate)
                VALUES (%s, %s, %s, %s)
                """
        cursor.execute(query, (user_id, description, comments, datetime.now()))
         
        # Zar : Updating 5 points for Posting Suggestion                                      
        cursor.execute(
            "UPDATE User SET Points = Points + 5  WHERE UserID = %s", (user_id,)
        )
        
        # Rana : Saving action for Point History
        cursor.execute("""
            INSERT INTO PointsHistory (UserID, Points, Action, ActionDate) 
            VALUES (%s, %s, %s, %s)
        """, (user_id, 5, "Posted a suggestion",  datetime.now()))
 
        conn.commit()
        cursor.close()
        conn.close()
    
        return jsonify({"message": "Suggestion added successfully"}), 200
    except Exception as e:
        # Log the error
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


# Zar: function to delete a suggestion
@app.route('/delete_suggestion', methods=['POST'])
def del_suggestion(user_id=None):
    #user_id = current_user.id
    suggestion_id = request.form.get('SuggestionID')

    if not suggestion_id:
        return jsonify({"error": "SuggestionID is required"}), 400

    try:
        conn = get_db_connection()
 
        cursor = conn.cursor(dictionary=True)

        # Get the suggestion's creation date and UserID
        cursor.execute("""
            SELECT CreatedDate, UserID
            FROM Suggestion
            WHERE SuggestionID = %s
        """, (suggestion_id,))
        suggestion = cursor.fetchone()

        if suggestion:
            user_id = suggestion["UserID"]

            # Check if there are any votes associated with the suggestion
            cursor.execute("""
                SELECT COUNT(*) AS vote_count
                FROM Vote
                WHERE SuggestionID = %s
            """, (suggestion_id,))
            vote_count = cursor.fetchone()['vote_count']

            if vote_count > 0:
                # If votes exist, return an error message
                return jsonify({"error": "Suggestion cannot be deleted because it has been voted on."}), 400


            # Delete the suggestion itself
            cursor.execute("""
                DELETE FROM Suggestion
                WHERE SuggestionID = %s
            """, (suggestion_id,))
             
            # Zar : Updating 5 points of deduction for deleting suggestion (ensuring they don’t go below 0)
            cursor.execute(
                "UPDATE User SET Points = GREATEST(Points - 5, 0) WHERE UserID = %s", (user_id,)
            )

            # Rana : Saving action for Point History
            cursor.execute("""
                INSERT INTO PointsHistory (UserID, Points, Action, ActionDate) 
                VALUES (%s, %s, %s, %s)
            """, (user_id, -5, "Deleted a suggestion", datetime.now()))
            
            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({"message": "Suggestion deleted successfully"}), 200
        else:
            return jsonify({"error": "Suggestion not found"}), 404

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while trying to delete the suggestion."}), 500


# Zar: route to render the user management
@app.route('/managesuggestion', methods=['GET'])
@login_required
def managesuggestion():
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of suggestions per page
        offset = (page - 1) * per_page  # Calculate offset

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get total number of suggestions
        cursor.execute("SELECT COUNT(*) AS total FROM Suggestion")
        total_suggestions = cursor.fetchone()['total']
        total_pages = (total_suggestions + per_page - 1) // per_page  # Calculate total pages

        # Fetch suggestions with pagination
        query = """
                SELECT Sug.*, Usr.Username, Usr.IsActive 
                FROM Suggestion as Sug
                INNER JOIN User as Usr ON Sug.UserID = Usr.UserID
                ORDER BY Sug.CreatedDate DESC
                LIMIT %s OFFSET %s
                """
        cursor.execute(query, (per_page, offset))
        suggestions = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('managesuggestion.html', suggestions=suggestions, page=page, total_pages=total_pages)
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500
     
# Zar: function to delete a suggestion 
@app.route('/del_suggestion_admin', methods=['POST'])
@login_required
def del_suggestion_admin():
    return del_suggestion(user_id=current_user.id)


#Jacob - Function to View all Suggestions (where we will do voting) and order them based on filter
# TODO: ADD Voting System into this route and reformat each suggestion box to look nicer (Maybe Don't use a table, we'll discuss possible alternatives)
from flask import request, render_template
import math

@app.route('/voting_view')
@login_required
def voting_view():
    filter_type = request.args.get('filter', 'newest')
    page = request.args.get('page', 1, type=int)  # Get page number from query params
    per_page = 15  # Suggestions per page
    user_id = current_user.id  # Get logged-in user's ID

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Calculate vote totals & determine status
    query = """
        WITH VoteSummary AS (
            SELECT 
                s.SuggestionID,
                s.Description,
                s.Comments,
                s.CreatedDate,
                COALESCE(SUM(CASE WHEN v.VoteType = 1 THEN 1 ELSE 0 END), 0) AS PositiveVote,
                COALESCE(SUM(CASE WHEN v.VoteType = 0 THEN 1 ELSE 0 END), 0) AS NegativeVote,
                (COALESCE(SUM(CASE WHEN v.VoteType = 1 THEN 1 ELSE 0 END), 0) - 
                 COALESCE(SUM(CASE WHEN v.VoteType = 0 THEN 1 ELSE 0 END), 0)) AS NetVotes,
                (COALESCE(SUM(CASE WHEN v.VoteType = 1 THEN 1 ELSE 0 END), 0) + 
                 COALESCE(SUM(CASE WHEN v.VoteType = 0 THEN 1 ELSE 0 END), 0)) AS TotalVotes
            FROM Suggestion s
            LEFT JOIN Vote v ON s.SuggestionID = v.SuggestionID
            GROUP BY s.SuggestionID
        )
        SELECT 
            vs.SuggestionID,
            vs.Description,
            vs.Comments,
            vs.CreatedDate,
            vs.PositiveVote,
            vs.NegativeVote,
            vs.NetVotes,
            vs.TotalVotes,
            (SELECT StatusName FROM Status st WHERE vs.NetVotes >= st.Threshold ORDER BY st.Threshold DESC LIMIT 1) AS StatusName,
            (SELECT VoteType FROM Vote WHERE UserID = %s AND SuggestionID = vs.SuggestionID LIMIT 1) AS UserVote
        FROM VoteSummary vs
    """

    # Apply filters
    if filter_type == 'newest':
        query += " ORDER BY vs.CreatedDate DESC"
    elif filter_type == 'trending':
        query += " ORDER BY vs.TotalVotes DESC"
    elif filter_type == 'status':
        query += " ORDER BY FIELD(StatusName, 'Implemented', 'Possible', 'Even', 'Unlikely'), vs.NetVotes DESC"

    cursor.execute(query, (user_id,))
    all_suggestions = cursor.fetchall()

    # Pagination logic
    total_suggestions = len(all_suggestions)
    total_pages = math.ceil(total_suggestions / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    suggestions = all_suggestions[start:end]

    cursor.close()
    conn.close()

    return render_template("voting_view.html", 
                           suggestions=suggestions, 
                           filter_type=filter_type, 
                           page=page, 
                           total_pages=total_pages)



# Jacob: Route to handle voting
# Rana: some changes to update Suggestion table as well
# Zar: updating points for voting
@app.route('/vote', methods=['POST'])
@login_required
def vote():
    suggestion_id = request.form.get('suggestion_id')
    vote_type = request.form.get('vote_type')

    if not suggestion_id or vote_type not in ['upvote', 'downvote']:
        return jsonify({'error': 'Invalid request'}), 400

    user_id = current_user.id
    vote_value = 1 if vote_type == 'upvote' else 0  # 1 for upvote, 0 for downvote

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        # Check if the user already voted
        cursor.execute("SELECT VoteType FROM Vote WHERE UserID = %s AND SuggestionID = %s", (user_id, suggestion_id))
        existing_vote = cursor.fetchone()

        if existing_vote:
            previous_vote = existing_vote['VoteType']
            if previous_vote != vote_value:
                # Remove previous vote count before updating
                update_suggestion_query = """
                    UPDATE Suggestion
                    SET 
                        PositiveVote = PositiveVote - IF(%s = 1, 1, 0),
                        NegativeVote = NegativeVote - IF(%s = 0, 1, 0),
                        NetVotes = NetVotes - IF(%s = 1, 1, -1)
                    WHERE SuggestionID = %s
                """
                cursor.execute(update_suggestion_query, (previous_vote, previous_vote, previous_vote, suggestion_id))

            # Update the vote
            cursor.execute(
                "UPDATE Vote SET VoteType = %s WHERE UserID = %s AND SuggestionID = %s",
                (vote_value, user_id, suggestion_id)
            )
        else:
            # Insert new vote
            cursor.execute(
                "INSERT INTO Vote (UserID, SuggestionID, VoteType) VALUES (%s, %s, %s)",
                (user_id, suggestion_id, vote_value)
            )
            
            # Zar: Updating 1 point for Voting                                       
            cursor.execute("UPDATE User SET Points = Points + 1  WHERE UserID = %s", (user_id,))

            # Rana: Saving action for Point History
            cursor.execute("""
                INSERT INTO PointsHistory (UserID, Points, Action, ActionDate) 
                VALUES (%s, %s, %s, %s)
            """, (user_id, 1, "Voted on a suggestion",  datetime.now()))

            # Get the user who owns the suggestion
            cursor.execute("SELECT UserID FROM Suggestion WHERE SuggestionID = %s", (suggestion_id,))
            suggestion_user = cursor.fetchone()

            if suggestion_user:
                receiving_userid = suggestion_user['UserID']

                # Zar: Updating 1 point for Receiving Vote 
                cursor.execute("UPDATE User SET Points = Points + 1 WHERE UserID = %s", (receiving_userid,))

                # Rana: Saving action for Point History
                cursor.execute("""
                    INSERT INTO PointsHistory (UserID, Points, Action, ActionDate) 
                    VALUES (%s, %s, %s, %s)
                """, (receiving_userid, 1, "Received a vote", datetime.now()))

        conn.commit()
        # Update the Suggestion table with new vote counts
        update_suggestion_query = """
            UPDATE Suggestion
            SET 
                PositiveVote = PositiveVote + IF(%s = 1, 1, 0),
                NegativeVote = NegativeVote + IF(%s = 0, 1, 0),
                NetVotes = (PositiveVote + IF(%s = 1, 1, 0)) - (NegativeVote + IF(%s = 0, 1, 0))
            WHERE SuggestionID = %s
        """
        cursor.execute(update_suggestion_query, (vote_value, vote_value, vote_value, vote_value, suggestion_id))

        # Fetch updated vote counts
        cursor.execute(
            "SELECT PositiveVote, NegativeVote, NetVotes FROM Suggestion WHERE SuggestionID = %s",
            (suggestion_id,)
        )
        vote_counts = cursor.fetchone()

        # Fetch the updated status
        cursor.execute(
            """
            SELECT StatusName FROM Status
            WHERE Threshold <= %s
            ORDER BY Threshold DESC
            LIMIT 1
            """,
            (vote_counts['NetVotes'],)
        )
        status = cursor.fetchone()
        new_status = status['StatusName'] if status else "Unknown"

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({
        'new_upvotes': vote_counts['PositiveVote'] or 0,
        'new_downvotes': vote_counts['NegativeVote'] or 0,
        'net_votes': vote_counts['NetVotes'] or 0,
        'new_status': new_status
    })


# Jayla: Leaderboard route
@app.route('/leaderboard')
def leaderboard():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT UserID, Username, Points FROM User ORDER BY Points DESC LIMIT 10")
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('leaderboard.html', users=users)


# Jayla: JSON API route for Leaderboard
@app.route('/leaderboard-data')
def leaderboard_data():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT UserID, Username, Points FROM User ORDER BY Points DESC LIMIT 10")
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(users)


if __name__ == '__main__':
    app.run(debug=True)