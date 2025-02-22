import sys
print(sys.executable)

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
    suggestions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("voting_view.html", suggestions=suggestions, filter_type=filter_type)