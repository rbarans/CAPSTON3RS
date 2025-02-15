import mysql.connector, os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify , Blueprint, session
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin, login_required
from datetime import datetime


app = Flask(__name__)
profile_bp = Blueprint('profile', __name__)


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


# Rana: route to home page
@app.route('/')
def home():
    return render_template('index.html')


# Rana: route to log in to account
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


# Rana: route to log out of account 
@app.route('/logout')
def logout():
    if current_user.is_authenticated:

        # Jacob: edited to allow users to log out after already rating - can change or keep previous rating for the day 
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


@app.route('/profile')
@login_required
def profile():
    user_id = current_user.id  # Use Flask-Login's current_user

    # Get filter parameters from the request
    suggestion_filter = request.args.get('suggestion_filter', '')  # Default to empty string
    keyword = request.args.get('keyword', '')  # Keyword search for filtering suggestions
    vote_filter = request.args.get('vote_filter', '')  # Default to empty string
    vote_keyword = request.args.get('vote_keyword', '')  # Keyword search for filtering suggestions


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Use dictionary=True to get column names

    # Fetch total points
    cursor.execute("SELECT points FROM User WHERE userID = %s", (user_id,))
    user = cursor.fetchone()
    total_points = user['points'] if user else 0

    # Build dynamic query for filtering suggestions
    suggestion_query = """
        SELECT 
            description, createdDate, netVotes, userID,
            (SELECT COUNT(*) FROM Vote WHERE suggestionID = Suggestion.suggestionID AND voteType = 1) AS positiveVotes,
            (SELECT COUNT(*) FROM Vote WHERE suggestionID = Suggestion.suggestionID AND voteType = 0) AS negativeVotes
        FROM Suggestion 
        WHERE userID = %s

    """
 # Apply filters based on the selected filter option
    if suggestion_filter == 'today':
        suggestion_query += " AND DATE(createdDate) = CURDATE()"
    elif suggestion_filter == 'yesterday':
        suggestion_query += " AND DATE(createdDate) = CURDATE() - INTERVAL 1 DAY"
    elif suggestion_filter == 'last_week':
        suggestion_query += " AND createdDate >= CURDATE() - INTERVAL 7 DAY"
    elif suggestion_filter == 'highest_net_votes':
        suggestion_query += " ORDER BY netVotes DESC"
    elif suggestion_filter == 'lowest_net_votes':
        suggestion_query += " ORDER BY netVotes ASC"
    elif suggestion_filter == 'keyword' and keyword:
        suggestion_query += " AND description LIKE %s"
        cursor.execute(suggestion_query, (user_id, f'%{keyword}%'))
        suggestions = cursor.fetchall()
        cursor.close()  # Close the cursor after use
        conn.close()
        return render_template(
            'profile.html',
            total_points=total_points,
            suggestions=suggestions,
            keyword=keyword,
            suggestion_filter=suggestion_filter
        )

    # Execute the query and fetch the results
    if suggestion_filter != 'keyword':
        cursor.execute(suggestion_query, (user_id,))
    suggestions = cursor.fetchall()

    # Fetch today's emoji reaction (if any)
    cursor.execute(
        "SELECT emojirating, submissiondate FROM EmojiFeedback WHERE userID = %s AND DATE(submissiondate) = CURDATE()",
        (user_id,))
    todays_reaction = cursor.fetchone()

    # Fetch emoji reactions from the past week, excluding today's reaction
    cursor.execute(
        "SELECT emojirating, submissiondate FROM EmojiFeedback WHERE userID = %s AND submissiondate >= CURDATE() - INTERVAL 7 DAY AND DATE(submissiondate) < CURDATE()",
        (user_id,))
    last_week_reactions = cursor.fetchall()

    # Build dynamic query for filtering votes given
    vote_query = """
        SELECT v.voteType, v.suggestionID, v.VotedDate, s.description, s.userID, s.CreatedDate 
        FROM Vote v
        JOIN Suggestion s ON v.suggestionID = s.suggestionID
        WHERE v.userID = %s
    """
# Apply vote filters
    if vote_filter == 'today':
        vote_query += " AND DATE(v.VotedDate) = CURDATE()"
    elif vote_filter == 'yesterday':
        vote_query += " AND DATE(v.VotedDate) = CURDATE() - INTERVAL 1 DAY"
    elif vote_filter == 'last_week':
        vote_query += " AND v.VotedDate >= CURDATE() - INTERVAL 7 DAY"
    elif vote_filter == 'yes':
        vote_query += " AND v.voteType = 1"
    elif vote_filter == 'no':
        vote_query += " AND v.voteType = 0"
    elif vote_filter == 'keyword' and vote_keyword:
        vote_query += " AND s.description LIKE %s"
        cursor.execute(vote_query, (user_id, f'%{vote_keyword}%'))
        votes_given = cursor.fetchall()
        cursor.close()  # Close the cursor after use
        conn.close()
        return render_template(
            'profile.html',
            total_points=total_points,
            suggestions=suggestions,
            vote_filter=vote_filter,
            vote_keyword=vote_keyword,
            votes_given=votes_given
        )

    # Execute vote query
    if vote_filter != 'keyword':
        cursor.execute(vote_query, (user_id,))
    votes_given = cursor.fetchall()

    cursor.close()  # Close the cursor after use
    conn.close()

    return render_template(
        'profile.html',
        total_points=total_points,
        todays_reaction=todays_reaction,
        last_week_reactions=last_week_reactions,
        suggestions=suggestions,
        vote_filter=vote_filter,
        vote_keyword=vote_keyword,
        votes_given=votes_given
    )



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
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

   # if not user_id or not description:
   #     return jsonify({"error": user_id}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor() 

        query = """
                INSERT INTO Suggestion (UserID, Description, Comments, CreatedDate)
                VALUES (%s, %s, %s, %s)
                """
        cursor.execute(query, (user_id, description, comments, created_date))
        conn.commit()
        cursor.close()
        conn.close()
    
        return jsonify({"message": "Suggestion added successfully"}), 200
    except Exception as e:
        # Log the error
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


# Zar: function to update a suggestion
def update_suggestion(suggestion_id, description=None, comments=None):
    query = "UPDATE Suggestion SET "
    updates = []
    params = []
    
    if description is not None:
        updates.append("Description = %s")
        params.append(description)
    if comments is not None:
        updates.append("Comments = %s")
        params.append(comments)

    query += ", ".join(updates) + " WHERE SuggestionID = %s"
    params.append(suggestion_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    cursor.close()
    conn.close()


# Zar: function to delete a suggestion
@app.route('/delete_suggestion', methods=['POST'])
def del_suggestion():
    suggestion_id = request.form.get('SuggestionID')
    if not suggestion_id:
        return jsonify({"error": "SuggestionID is required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Suggestion WHERE SuggestionID = %s", (suggestion_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Suggestion deleted successfully"}), 200
    except Exception as e:
        print(f"Error: {e}")
        #return jsonify({"error": str(e)}), 500
        return jsonify({"error": "The suggestion has been voted on and can no longer be deleted."}), 500
    

#Jacob - Function to View all Suggestions (where we will do voting) and order them based on filter
# TODO: ADD Voting System into this route and reformat each suggestion box to look nicer (Maybe Don't use a table, we'll discuss possible alternatives)
@app.route('/voting_view')
@login_required
def voting_view():
    filter_type = request.args.get('filter', 'newest')
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
                 COALESCE(SUM(CASE WHEN v.VoteType = 0 THEN 1 ELSE 0 END), 0)) AS NetVotes
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
            (SELECT StatusName FROM Status st WHERE vs.NetVotes >= st.Threshold ORDER BY st.Threshold DESC LIMIT 1) AS StatusName,
            (SELECT VoteType FROM Vote WHERE UserID = %s AND SuggestionID = vs.SuggestionID LIMIT 1) AS UserVote
        FROM VoteSummary vs
    """

    # Apply filters
    if filter_type == 'newest':
        query += " ORDER BY vs.CreatedDate DESC"
    elif filter_type == 'trending':
        query += " ORDER BY vs.NetVotes DESC"
    elif filter_type == 'status':
        query += " ORDER BY FIELD(StatusName, 'Implemented', 'Possible', 'Even', 'Unlikely')"

    cursor.execute(query, (user_id,))
    suggestions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("voting_view.html", suggestions=suggestions, filter_type=filter_type)


# Route to handle voting
@app.route('/vote', methods=['POST'])
@login_required
def vote():
    suggestion_id = request.form.get('suggestion_id')
    vote_type = request.form.get('vote_type')

    if not suggestion_id or vote_type not in ['upvote', 'downvote']:
        return jsonify({'error': 'Invalid request'}), 400

    user_id = current_user.id
    vote_value = 1 if vote_type == 'upvote' else 0  # Assigning 0 for downvotes

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if user already voted
    cursor.execute("SELECT * FROM Vote WHERE UserID = %s AND SuggestionID = %s", (user_id, suggestion_id))
    existing_vote = cursor.fetchone()

    if existing_vote:
        cursor.execute(
            "UPDATE Vote SET VoteType = %s WHERE UserID = %s AND SuggestionID = %s",
            (vote_value, user_id, suggestion_id)
        )
    else:
        cursor.execute(
            "INSERT INTO Vote (UserID, SuggestionID, VoteType) VALUES (%s, %s, %s)",
            (user_id, suggestion_id, vote_value)
        )

    conn.commit()

    # Fetch updated vote counts
    cursor.execute(
        "SELECT SUM(CASE WHEN VoteType = 1 THEN 1 ELSE 0 END) AS PositiveVote, "
        "SUM(CASE WHEN VoteType = 0 THEN 1 ELSE 0 END) AS NegativeVote "
        "FROM Vote WHERE SuggestionID = %s",
        (suggestion_id,)
    )
    vote_counts = cursor.fetchone()

    # Fetch the updated status
    cursor.execute(
        """
        SELECT StatusName FROM Status
        WHERE Threshold <= (
            SELECT (SUM(CASE WHEN VoteType = 1 THEN 1 ELSE 0 END) - 
                    SUM(CASE WHEN VoteType = 0 THEN 1 ELSE 0 END))
            FROM Vote WHERE SuggestionID = %s
        )
        ORDER BY Threshold DESC
        LIMIT 1
        """,
        (suggestion_id,)
    )
    status = cursor.fetchone()
    new_status = status['StatusName'] if status else "Unknown"

    # Update status in Suggestion table
    cursor.execute(
        "UPDATE Suggestion SET StatusID = (SELECT StatusID FROM Status WHERE StatusName = %s LIMIT 1) WHERE SuggestionID = %s",
        (new_status, suggestion_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        'new_upvotes': vote_counts['PositiveVote'] or 0,
        'new_downvotes': vote_counts['NegativeVote'] or 0,
        'new_status': new_status
    })
  
if __name__ == '__main__':
    app.run(debug=True)