import sys
print(sys.executable)


{% extends "base.html" %}

{% block content %}
<head>
    <title>Voting View</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="container">
        <h1>Vote on Company Suggestions!</h1>

        <!-- Filter Dropdown -->
        <div class="filter-container">
            <label for="filter">Sort by:</label>
            <select id="filter" onchange="applyFilter()">
                <option value="newest" {% if filter_type == 'newest' %}selected{% endif %}>Newest</option>
                <option value="trending" {% if filter_type == 'trending' %}selected{% endif %}>Trending</option>
                <option value="status" {% if filter_type == 'status' %}selected{% endif %}>Status</option>
            </select>
        </div>

        <!-- Suggestions Card View -->
        <div class="card-container">
            {% for suggestion in suggestions %}
            <div class="suggestion-card" data-index="{{ loop.index0 }}" data-id="{{ suggestion.SuggestionID }}" style="position: relative;">
                <div class="card-header">
                    <p class="status-label status-{{ suggestion.StatusName | lower | replace(' ', '-') }}">
                        Status: <span id="status-{{ suggestion.SuggestionID }}">{{ suggestion.StatusName or "Unknown" }}</span>
                    </p></div>
                <div class="card-body">
                    <p><strong>Title:</strong> {{ suggestion.Description }}</p>
                    <a href="javascript:void(0);" class="view-details" data-index="{{ loop.index0 }}">
                        <weak>Click to View Details</weak>
                    </a>

                    <!-- Top Right: Date (Formatted as MM-DD-YYYY) -->
                    <span style="position: absolute; top: 5px; right: 10px; font-size: 12px; color: #666;">
                        {{ suggestion['CreatedDate'].strftime('%m/%d/%Y') }}
                        <br>
                        {{ suggestion['CreatedDate'].strftime('%I:%M %p') }}
                    </span>

                    <!-- Voting Section -->
                    <div class="vote-buttons">
                        <button class="upvote {% if suggestion.UserVote == 1 %}voted{% endif %}" 
                            id="upvote-btn-{{ suggestion.SuggestionID }}" 
                            onclick="castVote('{{ suggestion.SuggestionID }}', 'upvote')">
                            👍 <span id="upvote-{{ suggestion.SuggestionID }}">{{ suggestion.PositiveVote or 0 }}</span>
                        </button>
                        
                        <button class="downvote {% if suggestion.UserVote == 0 %}voted{% endif %}" 
                            id="downvote-btn-{{ suggestion.SuggestionID }}" 
                            onclick="castVote('{{ suggestion.SuggestionID }}', 'downvote')">
                            👎 <span id="downvote-{{ suggestion.SuggestionID }}">{{ suggestion.NegativeVote or 0 }}</span>
                        </button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Pagination Controls -->
<div class="pagination">

    <span>Page {{ page }} of {{ total_pages }}</span>
    <br><br>
    {% if page > 1 %}
        <a href="{{ url_for('voting_view', filter=filter_type, page=page-1) }}" class="page-btn">← Previous</a>
    {% endif %}
    
    {% if page < total_pages %}
        <a href="{{ url_for('voting_view', filter=filter_type, page=page+1) }}" class="page-btn">Next →</a>
    {% endif %}
    <br><br><br>

</div>


    <!-- Vote Confirmation Message -->
    <div id="vote-confirmation" class="vote-confirmation hidden">Your vote has been recorded!</div>

    <!-- Lightbox Modal -->
    <div id="suggestionModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">✖</button>
            <h2 id="modalTitle"></h2>
            <p><strong>Description:</strong> <span id="modalDescription"></p>
            <p id="modalComments"></p>
            <p><strong>Status:</strong> <span id="modalStatus"></span></p>
            <p><strong>Created Date:</strong><span id="modalDate"></span></p>

            <!-- Existing Comments Section -->
            <div id="modalCommentsSection">
                <h4>Comments:</h4>
                <ul id="modalCommentsList"></ul>
            </div>

            <!-- Comment Input Box -->
            <label for="modalComment">Your Comment (optional):</label>
            <textarea id="modalComment" placeholder="Enter your comment here..."></textarea>

            
            <!-- Voting in Lightbox -->
            <div class="modal-vote-buttons">
                <button class="upvote" onclick="castVoteFromModal('upvote')">👍 
                    <span id="modalUpvoteCount">0</span>
                </button>
                <button class="downvote" onclick="castVoteFromModal('downvote')">👎 
                    <span id="modalDownvoteCount">0</span>
                </button>
            </div>

            <div class="modal-navigation">
                <button onclick="prevSuggestion()">← Previous</button>
                <button onclick="nextSuggestion()">Next →</button>
            </div>
        </div>
    </div>

    <!-- Store JSON Data in Hidden Div -->
    <div id="suggestion-data" data-suggestions='{{ suggestions | tojson | safe }}'></div>

    <script>
        let suggestions = JSON.parse(document.getElementById("suggestion-data").dataset.suggestions);
        let currentIndex = 0;

        // Apply filter selection
        function applyFilter() {
            let selectedFilter = document.getElementById("filter").value;
            window.location.href = "/voting_view?filter=" + selectedFilter;
        }

        // Attach click event to open modal
        document.querySelectorAll(".view-details").forEach((link) => {
            link.addEventListener("click", function (event) {
                event.stopPropagation();
                let index = parseInt(link.dataset.index);
                openModal(index);
            });
        });

        function openModal(index) {
            currentIndex = index;
            updateModal();
            document.getElementById("suggestionModal").style.display = "block";
        }

        function closeModal() {
            document.getElementById("suggestionModal").style.display = "none";
        }

        function updateModal() {
            if (suggestions.length > 0) {
                let currentSuggestion = suggestions[currentIndex];
                document.getElementById("modalTitle").innerText = currentSuggestion.Description;
                document.getElementById("modalDescription").innerText = (currentSuggestion.SuggestionComments || "None");
                document.getElementById("modalStatus").innerText = currentSuggestion.StatusName || "Unknown";
                document.getElementById("modalUpvoteCount").innerText = currentSuggestion.PositiveVote || 0;
                document.getElementById("modalDownvoteCount").innerText = currentSuggestion.NegativeVote || 0;
                document.getElementById("modalDate").innerText =" " + currentSuggestion.CreatedDate;
                // Get modal vote buttons
                const modalUpvote = document.querySelector(".modal-vote-buttons .upvote");
                const modalDownvote = document.querySelector(".modal-vote-buttons .downvote");

                // Reset previous highlight
                modalUpvote.classList.remove("votedyes", "voted");
                modalDownvote.classList.remove("votedno", "voted");

                // Retrieve user's previous vote
                let votedType = currentSuggestion.UserVote;
                if (votedType === 1) {
                    modalUpvote.classList.add("votedyes", "voted");
                } else if (votedType === 0) {
                    modalDownvote.classList.add("votedno", "voted");
                }

                // Apply highlighting to the modal buttons if a previous vote exists
                if (votedType === 'upvote') {
                    modalUpvote.classList.add("votedyes", "voted");
                } else if (votedType === 'downvote') {
                    modalDownvote.classList.add("votedno", "voted");
                }
                // Update Comments Section
                let commentsList = document.getElementById("modalCommentsList");
                commentsList.innerHTML = ""; // Clear previous comments

                if (currentSuggestion.VoteComments && currentSuggestion.VoteComments.length > 0) {
                    currentSuggestion.VoteComments.forEach(comment => {
                        let commentItem = document.createElement("li");
                        commentItem.innerHTML = `<strong>Anonymous:</strong> ${comment.Comment}`;
                        commentsList.appendChild(commentItem);
                    });
                } else {
                    commentsList.innerHTML = "<li>No comments yet.</li>";
                }
            }

            // Submit a new comment
            function submitComment() {
                let suggestionId = suggestions[currentIndex].SuggestionID;
                let comment = document.getElementById("modalComment").value.trim();

                if (!comment) {
                    alert("Comment cannot be empty.");
                    return;
                }

                fetch('/vote', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: new URLSearchParams({
                        'suggestion_id': suggestionId,
                        'vote_type': suggestions[currentIndex].UserVote === 1 ? 'upvote' : 'downvote',
                        'comment': comment ? comment : suggestions[currentIndex].UserComment
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log("Vote API Response:", data); // Debugging line
                    if (data.error) {
                        alert("Error: " + data.error);
                        return;
                    }

                    // Assuming the API returns a success status
                    localStorage.setItem("voteSuccess", "true"); // Set flag to true
                    console.log("Vote success flag set to:", localStorage.getItem("voteSuccess"));


                    // Fetch the updated comments from response
                    let updatedComments = data.updated_comments;

                    // Update the JavaScript object storing suggestions
                    suggestions[currentIndex].VoteComments = updatedComments;

                    // Update UI to reflect new comments
                    let commentsList = document.getElementById("modalCommentsList");
                    commentsList.innerHTML = ""; // Clear old comments

                    updatedComments.forEach(commentObj => {
                        let commentItem = document.createElement("li");
                        commentItem.innerHTML = `<strong>${commentObj.UserName}:</strong> ${commentObj.Comment}`;
                        commentsList.appendChild(commentItem);
                    });

                    // Clear comment input and hide button
                    document.getElementById("modalComment").value = "";
                })
                .catch(error => console.error('Error:', error));
            }
        }

        function prevSuggestion() {
            if (currentIndex > 0) {
                currentIndex--;
                updateModal();
            }
        }

        function nextSuggestion() {
            if (currentIndex < suggestions.length - 1) {
                currentIndex++;
                updateModal();
            }
        }

            // Function to vote
            function castVote(suggestionId, voteType) {
                let commentBox = document.getElementById("modalComment");
                let comment = commentBox ? commentBox.value.trim() : "";

                // Ensure we keep the existing comment if the user hasn't entered a new one
                if (!comment && suggestions[currentIndex].UserComment) {
                    comment = suggestions[currentIndex].UserComment;
                }

            let requestBody = new URLSearchParams({
                'suggestion_id': suggestionId,
                'vote_type': voteType
            });

            // Only include the comment if the user has entered one
            if (comment) {
                requestBody.append('comment', comment);
            }

            fetch('/vote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: requestBody
            })
            .then(response => response.json())
            .then(data => {
                console.log("Vote API Response:", data); // Debugging line
                if (data.error) {
                    alert("Error: " + data.error);
                    return;
                }

                localStorage.setItem("voteSuccess", "true"); // Set flag to true
                
                // Update UI instantly
                // document.getElementById(`upvote-${suggestionId}`).innerText = data.new_upvotes;
                // document.getElementById(`downvote-${suggestionId}`).innerText = data.new_downvotes;
                // document.getElementById(`status-${suggestionId}`).innerText = data.new_status;

                // Get buttons in both card and modal
                const upvoteButton = document.getElementById(`upvote-btn-${suggestionId}`);
                const downvoteButton = document.getElementById(`downvote-btn-${suggestionId}`);
                const modalUpvote = document.querySelector(`.modal-vote-buttons .upvote`);
                const modalDownvote = document.querySelector(`.modal-vote-buttons .downvote`);

                // Reset all vote buttons before applying a new vote
                upvoteButton.classList.remove("votedyes", "voted");
                downvoteButton.classList.remove("votedno", "voted");
                modalUpvote.classList.remove("votedyes", "voted");
                modalDownvote.classList.remove("votedno", "voted");

                // Apply the new highlight to the selected vote
                if (voteType === 'upvote') {
                    upvoteButton.classList.add("votedyes", "voted");
                    modalUpvote.classList.add("votedyes", "voted");
                } else if (voteType === 'downvote') {
                    downvoteButton.classList.add("votedno", "voted");
                    modalDownvote.classList.add("votedno", "voted");
                }

                // Update the comments list to reflect the latest comments
                let commentsList = document.getElementById("modalCommentsList");
                commentsList.innerHTML = ""; // Clear previous comments

                if (data.updated_comments.length > 0) {
                    data.updated_comments.forEach(commentObj => {
                        let commentItem = document.createElement("li");
                        commentItem.innerHTML = `<strong>${commentObj.UserName}:</strong> ${commentObj.Comment}`;
                        commentsList.appendChild(commentItem);
                    });
                } else {
                    commentsList.innerHTML = "<li>No comments yet.</li>";
                }

                // If the user entered a comment, clear the input field
                if (comment) {
                    document.getElementById("modalComment").value = "";
                }

                // Store the modal index before refresh
                localStorage.setItem("openModalIndex", currentIndex);

                // Show confirmation message
                let confirmation = document.getElementById("vote-confirmation");
                confirmation.classList.remove("hidden");


                // Reload after 300 ms
                setTimeout(() => {
                    location.reload();
                }, 300);
            })
            .catch(error => console.error('Error:', error));
        }

        function castVoteFromModal(voteType) {
            let suggestionId = suggestions[currentIndex].SuggestionID;
            localStorage.setItem("openModalIndex", currentIndex);
            castVote(suggestionId, voteType);
        }

        // Highlight user's previous vote
        document.addEventListener("DOMContentLoaded", function () {
            if (localStorage.getItem("voteSuccess") === "true") {
                let confirmation = document.getElementById("vote-confirmation");
                confirmation.classList.remove("vote-confirmation-hidden");
                confirmation.classList.add("vote-confirmation-visible");

                // Keep message visible for 1.5 seconds, then hide it
                setTimeout(() => {
                    confirmation.classList.add("hidden");
                    localStorage.removeItem("voteSuccess"); // Clear flag
                }, 1500);
            }
            
            document.querySelectorAll(".suggestion-card").forEach((card) => {
                let suggestionId = card.dataset.id;
                let suggestion = suggestions.find(s => s.SuggestionID == suggestionId);
                
                if (suggestion && suggestion.UserVote !== null) {
                    if (suggestion.UserVote == 1) {
                        document.getElementById(`upvote-btn-${suggestionId}`).classList.add("votedyes", "voted");
                    } else if (suggestion.UserVote == 0) {
                        document.getElementById(`downvote-btn-${suggestionId}`).classList.add("votedno", "voted");
                    }
                }
                });
            });
                
            document.addEventListener("DOMContentLoaded", function () {
                // Check if we should reopen a modal
                let savedIndex = localStorage.getItem("openModalIndex");

                if (localStorage.getItem("voteSuccess") === "true" && savedIndex !== null) {

                    let confirmation = document.getElementById("vote-confirmation");
                    confirmation.classList.remove("vote-confirmation-hidden");
                    confirmation.classList.add("vote-confirmation-visible");

                    // Keep message visible for 1.5 seconds, then hide it
                    setTimeout(() => {
                        confirmation.classList.add("hidden");
                        localStorage.removeItem("voteSuccess"); // Clear flag
                    }, 1500);
                    openModal(parseInt(savedIndex));
                    localStorage.removeItem("openModalIndex"); // Clear it after reopening
                }
            });
    </script>
</body>
{% endblock %}