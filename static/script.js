document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const deepSearchBtn = document.getElementById('deep-search-btn');
    const depthSelect = document.getElementById('depth-select');

    // Initialize deep search state
    let deepSearchActive = false;

    // Toggle deep search state when button is clicked
    deepSearchBtn.addEventListener('click', () => {
        deepSearchActive = !deepSearchActive;
        deepSearchBtn.classList.toggle('active', deepSearchActive);
    });

    let waitingForResponse = false; 
    const sessionId = generateSessionId();

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (waitingForResponse) {
            console.warn("Still waiting for the previous response.");
            return;
        }

        const message = userInput.value.trim(); 
        if (!message) return;

        appendMessage('user', message); 
        userInput.value = '';

        const thinkingElement = appendMessage('assistant', `<img src="/static/images/thinking.gif" alt="Thinking..." style="width: 70px; height: 70px;" />`);
        waitingForResponse = true;  

        const depth = parseInt(depthSelect.value, 10);

        try {
            const response = await fetch('/run-agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    session_chat_history: getChatHistory(),
                    user_id: 'user123',
                    deepsearch: deepSearchActive,
                    depth: depth
                }),
            });

            if (response.ok) {
                const contentType = response.headers.get("content-type");

                if (contentType && contentType.includes("application/pdf")) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'deep_search_output.pdf';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    updateMessageContent(thinkingElement, 'PDF generated. It should start downloading shortly.');
                } else if (contentType && contentType.includes("application/json")) {
                    const data = await response.json();
                    updateMessageContent(thinkingElement, data.assistant);
                } else {
                    const text = await response.text();
                    updateMessageContent(thinkingElement, text);
                }
            } else {
                const errorData = await response.json();
                updateMessageContent(thinkingElement, `Error: ${errorData.error}`);
                console.error('Backend Error:', errorData.error);
            }
        } catch (error) {
            updateMessageContent(thinkingElement, `Error: ${error.message}`);
            console.error('Fetch Error:', error);
        }

        waitingForResponse = false;
    });

    function appendMessage(role, message) {
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

    function updateMessageContent(msgElement, newContent) {
        if (newContent) {
            const containsHTML = /<[a-z][\s\S]*>/i.test(newContent);
            let cleanHtml;
            if (containsHTML) {
                cleanHtml = DOMPurify.sanitize(newContent);
            } else {
                const rawHtml = marked.parse(newContent);
                cleanHtml = DOMPurify.sanitize(rawHtml);
            }
            msgElement.innerHTML = cleanHtml;
        } else {
            msgElement.textContent = "No message received.";
        }
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
});
