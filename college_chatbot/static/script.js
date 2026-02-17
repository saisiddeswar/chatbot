const chatBody = document.getElementById('chat-body');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

let chatHistory = []; // Local history state

// ----------------------------------------------------
// FETCH POPULAR QUESTIONS
// ----------------------------------------------------
async function loadPopularQuestions() {
    try {
        const response = await fetch('/stats/top');
        if (response.ok) {
            const data = await response.json();
            if (data.questions && data.questions.length > 0) {
                renderSuggestions(data.questions);
            }
        }
    } catch (error) {
        console.warn("Failed to load popular questions:", error);
    }
}

function renderSuggestions(questions) {
    // Find the first bot message (welcome message)
    const welcomeMsg = chatBody.querySelector('.bot-message .message-content');
    if (!welcomeMsg) return;

    // Create container
    const container = document.createElement('div');
    container.className = 'suggestion-container';

    questions.forEach(q => {
        const chip = document.createElement('div');
        chip.className = 'suggestion-chip';
        chip.textContent = q;
        chip.onclick = (e) => {
            // Prevent default just in case
            e.preventDefault();

            // Set input value
            userInput.value = q;

            // Manually trigger the submit event on the form if possible, OR just call sendMessage
            // Calling sendMessage with a mock event is cleaner
            const mockEvent = { preventDefault: () => { } };
            sendMessage(mockEvent);
        };
        container.appendChild(chip);
    });

    // Append after welcome text
    welcomeMsg.appendChild(document.createElement('br'));
    welcomeMsg.appendChild(document.createElement('br'));
    // Or prefer appending OUTSIDE the bubble? 
    // Usually chips look better outside or just below.
    // Let's append inside for now as "options", 
    // OR create a new "system" message.

    // Let's append to the message content for simplicity
    const label = document.createElement('div');
    label.style.fontSize = '0.85em';
    label.style.color = '#666';
    label.style.marginBottom = '6px';
    label.innerText = "Popular questions:";

    welcomeMsg.appendChild(label);
    welcomeMsg.appendChild(container);
}

// Load on start
document.addEventListener('DOMContentLoaded', loadPopularQuestions);


function appendMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');

    // Convert newlines to breaks and basic markdown formatting
    // For a simple bot, we might just replace \n with <br>
    // A robust solution would use a markdown parser library like marked.js
    let formattedText = text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    messageDiv.innerHTML = `
        <div class="message-content">${formattedText}</div>
    `;

    chatBody.appendChild(messageDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-indicator';
    loadingDiv.classList.add('loading-dots');
    loadingDiv.innerHTML = `
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
    `;
    chatBody.appendChild(loadingDiv);
    chatBody.scrollTop = chatBody.scrollHeight;

    sendBtn.disabled = true;
    userInput.disabled = true;
}

function hideLoading() {
    const loadingDiv = document.getElementById('loading-indicator');
    if (loadingDiv) {
        loadingDiv.remove();
    }
    sendBtn.disabled = false;
    userInput.disabled = false;
    userInput.focus();
}

async function sendMessage(event) {
    if (event) event.preventDefault();

    const text = userInput.value.trim();
    if (!text) return;

    // 1. Add User Message
    appendMessage('user', text);
    userInput.value = '';

    // 2. Show Loading
    showLoading();

    try {
        // 3. Call API
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: text,
                history: chatHistory
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        const botResponse = data.response;

        // 4. Update History
        chatHistory.push([text, botResponse]);

        // 5. Add Bot Message
        hideLoading();
        appendMessage('bot', botResponse);

    } catch (error) {
        console.error('Error:', error);
        hideLoading();
        appendMessage('bot', '⚠️ Sorry, something went wrong. Please check your connection or try again later.');
    }
}
