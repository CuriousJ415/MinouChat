document.addEventListener('DOMContentLoaded', function() {
    const messagesContainer = document.getElementById('messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const characterSelect = document.getElementById('character-select');
    const switchButton = document.getElementById('switch-btn');
    const themeSwitch = document.getElementById('theme-switch');
    
    // Theme switching
    themeSwitch.addEventListener('change', function() {
        if (this.checked) {
            document.body.classList.remove('light-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.add('light-theme');
            localStorage.setItem('theme', 'light');
        }
    });
    
    // Load saved theme preference
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        themeSwitch.checked = false;
    } else {
        document.body.classList.remove('light-theme');
        themeSwitch.checked = true;
    }
    
    // Send message function
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, 'user');
        userInput.value = '';
        
        try {
            const response = await fetch('/api/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }),
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            
            // Add AI response to chat
            const characterName = data.character || 'System';
            addMessage(data.response, 'ai', characterName);
            
            // Update character selector if needed
            if (data.current_character && characterSelect.value !== data.current_character) {
                characterSelect.value = data.current_character;
            }
            
        } catch (error) {
            console.error('Error:', error);
            addMessage('Error: Could not connect to server', 'ai', 'System');
        }
    }
    
    // Add message to chat
    function addMessage(text, sender, characterName = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');
        
        if (sender === 'ai' && characterName) {
            const nameSpan = document.createElement('div');
            nameSpan.classList.add('character-name');
            nameSpan.textContent = characterName;
            messageDiv.appendChild(nameSpan);
        }
        
        const content = document.createTextNode(text);
        messageDiv.appendChild(content);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Switch character
    switchButton.addEventListener('click', async function() {
        const selectedCharacter = characterSelect.value;
        addMessage(`/switch ${selectedCharacter}`, 'user');
        
        try {
            const response = await fetch('/api/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: `/switch ${selectedCharacter}` }),
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            addMessage(data.response, 'ai', 'System');
            
        } catch (error) {
            console.error('Error:', error);
            addMessage('Error: Could not connect to server', 'ai', 'System');
        }
    });
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});