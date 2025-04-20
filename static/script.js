document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const sessionId = generateSessionId();
    let followUpNeeded = null;

    socket.on("follow_up_request", function(data) {  
        const serverMessage = data.message;
        followUpNeeded = "Follow-up needed: " + serverMessage;
        appendMessage('assistant', serverMessage);
    });  

    socket.on("reasoning_update", function(data) {
        appendReasoning(data.message);
    });  
      
    socket.on("agent_response", function(data) {
        if (data.session_id === sessionId) {
            if (data.content_type && data.content_type === "application/pdf") {
                const byteCharacters = atob(data.assistant);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);  
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: "application/pdf" });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'deep_search_output.pdf';
                document.body.appendChild(a);
                a.click();
                a.remove();
                appendMessage('assistant', 'PDF generated. It should start downloading shortly.');
            } else {
                appendMessage('assistant', data.assistant);
            }
        }
    });

    // Listen for evaluation request event from the backend.
    socket.on("request_evaluation", function(data) {
        if (data.session_id === sessionId) {
            // Display the star rating UI.
            displayRatingUI(data);
        }
    });

    socket.on("error", function(data) {
        if (data.session_id === sessionId) {
            appendMessage('assistant', "Error: " + data.error);
        }
    });

    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const deepSearchBtn = document.getElementById('deep-search-btn');
    const depthSelect = document.getElementById('depth-select');

    let deepSearchActive = false;
    deepSearchBtn.addEventListener('click', () => {
        deepSearchActive = !deepSearchActive;
        deepSearchBtn.classList.toggle('active', deepSearchActive);
    });

    function lastMessageIsAssistant() {
        const chatBox = document.getElementById('chat-box');
        const allMessages = chatBox.querySelectorAll('.message, .reasoning-message');
        if (allMessages.length === 0) return true;
        const lastMsg = allMessages[allMessages.length - 1];
        return lastMsg.classList.contains('assistant');
    }

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();

        if (!lastMessageIsAssistant()) {
            console.log("Submission blocked: waiting for a response or reasoning to complete.");
            return;
        }

        const message = userInput.value.trim();
        if (!message) return;
        appendMessage('user', message);
        userInput.value = '';

        if (followUpNeeded) {
            socket.emit("follow_up_response", {
                session_id: sessionId,
                message: message
            });
            followUpNeeded = null;
            return;
        }

        appendReasoning(`Reasoning...`);

        const depth = parseInt(depthSelect.value, 10);  

        socket.emit("run_agent", {
            session_id: sessionId,
            session_chat_history: getChatHistory(),
            user_id: "user123",
            deepsearch: deepSearchActive,
            depth: depth
        });
    });

    function clearReasoning() {
        const reasoningDiv = document.getElementById('reasoning-div');
        if (reasoningDiv) {
            reasoningDiv.remove();
        }
    }

    function appendMessage(role, message) {
        if (role === 'assistant') {
            clearReasoning();
        }  
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', role);
        if (message) {
            const containsHTML = /<[a-z][\s\S]*>/i.test(message);
            let cleanHtml;
            if (containsHTML) {
                cleanHtml = DOMPurify.sanitize(message);
            } else {
                const rawHtml = marked.parse(message);
                cleanHtml = DOMPurify.sanitize(rawHtml);
            }
            msgDiv.innerHTML = cleanHtml;
        } else {
            msgDiv.textContent = "No message received.";
        }
        const chatBox = document.getElementById('chat-box');
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight; 
        return msgDiv;
    }

    function appendReasoning(message) {
        let reasoningDiv = document.getElementById('reasoning-div');
        if (!reasoningDiv) {
            reasoningDiv = document.createElement('div');
            reasoningDiv.id = 'reasoning-div';
            reasoningDiv.classList.add('reasoning');
            const chatBox = document.getElementById('chat-box');
            chatBox.appendChild(reasoningDiv);
        }
    
        const reasoningLine = document.createElement('div');
        reasoningLine.classList.add('reasoning-message');
        reasoningLine.textContent = message;
        reasoningDiv.appendChild(reasoningLine);

        const chatBox = document.getElementById('chat-box');
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    function getChatHistory() {
        const messages = document.getElementById('chat-box').querySelectorAll('.message');
        const history = [];
        messages.forEach(msg => {
            const role = msg.classList.contains('user') ? 'user' : 'assistant';
            const message = role === 'user' ? msg.textContent : msg.innerText;
            history.push({ role, content: message });
        });
        if (history.length > 0 && !history[history.length - 1].content) {
            history.pop();
        }
        return history;
    }
 
    function generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9);
    }

    // Create and display the star rating UI.
    function displayRatingUI(data) {
     
        if (document.getElementById('rating-container')) return;
        
        const ratingContainer = document.createElement('div');
        ratingContainer.id = 'rating-container';
        
        const reviewText = document.createElement('div');
        reviewText.textContent = "Please rate the answer";
        reviewText.style.textAlign = 'center';
        reviewText.style.marginBottom = '5px';
        ratingContainer.appendChild(reviewText);
     
        const starRow = document.createElement('div');
        starRow.id = 'star-row';
        starRow.style.display = 'flex';
        starRow.style.justifyContent = 'center';
        starRow.style.marginBottom = '5px';
        
        for (let i = 1; i <= 5; i++) {
            const star = document.createElement('span');
            star.classList.add('star');
            star.dataset.rating = i;
            star.innerHTML = '☆';  // empty star
    
            star.addEventListener('click', () => {
                const rating = parseInt(star.dataset.rating, 10);
                socket.emit('submit_evaluation', {
                    session_id: sessionId,
                    rating: rating
                });
          
                document.querySelectorAll('#rating-container .star').forEach(s => {
                    s.innerHTML = '☆';
                });
                for (let j = 1; j <= rating; j++) {
                    document.querySelector(`#rating-container .star[data-rating="${j}"]`).innerHTML = '★';
                }
      
                setTimeout(() => {
                    ratingContainer.remove();
                }, 500);
            });
            starRow.appendChild(star);
        }
        ratingContainer.appendChild(starRow);
    
        // Append the assistant's message below the stars, if provided
        if (data && data.assistant) {
            const messageText = document.createElement('div');
            messageText.classList.add('rating-message');
            messageText.textContent = data.assistant;
            ratingContainer.appendChild(messageText);
        }
        

        document.getElementById('chat-box').appendChild(ratingContainer);
    }
    
});
