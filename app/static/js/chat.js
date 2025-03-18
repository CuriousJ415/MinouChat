/**
 * MiaAI Chat JavaScript
 * Handles chat-specific functionality including message sending, receiving, and formatting
 */

class ChatManager {
    constructor(app) {
        this.app = app;
        this.messageContainer = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.clearButton = document.getElementById('clear-chat-button');
        this.searchButton = document.getElementById('search-memories-button');
        this.typingIndicator = document.createElement('div');
        this.typingIndicator.className = 'message ai typing-indicator';
        this.typingIndicator.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        
        this.init();
    }
    
    init() {
        // Set up event listeners for required elements
        if (this.messageInput) {
            this.messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        // Set up event listeners for optional elements
        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => this.clearChat());
        }
        
        if (this.searchButton) {
            this.searchButton.addEventListener('click', () => this.app.openMemorySearchModal());
        }
    }
    
    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // Check if a character is selected
        if (!this.app.selectedCharacter) {
            this.app.showError('Please select a character first');
            return;
        }
        
        // Display user message
        this.displayMessage('user', message);
        
        // Clear input
        this.messageInput.value = '';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Send to API
        this.app.sendMessageToAPI(message);
    }
    
    displayMessage(role, content, isMemory = false) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}`;
        messageElement.textContent = content;
        
        this.messageContainer.appendChild(messageElement);
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }
    
    formatMessageContent(content) {
        // Simple markdown-like formatting
        let formatted = content
            // Code blocks
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Bold
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            // Line breaks
            .replace(/\n/g, '<br>');
        
        return formatted;
    }
    
    showTypingIndicator() {
        this.messageContainer.appendChild(this.typingIndicator);
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }
    
    hideTypingIndicator() {
        if (this.typingIndicator.parentNode === this.messageContainer) {
            this.messageContainer.removeChild(this.typingIndicator);
        }
    }
    
    clearChat() {
        // Clear messages from the UI only, don't delete from database
        while (this.messageContainer.firstChild) {
            this.messageContainer.removeChild(this.messageContainer.firstChild);
        }
        
        // Show welcome message
        const character = this.app.selectedCharacter;
        if (character) {
            const welcomeMessage = `Chat cleared. I'm ${character.name}, ${character.role}. How can I help you today?`;
            this.displayMessage('assistant', welcomeMessage);
        }
        
        // Show notification
        this.app.showNotification('Chat cleared');
    }
    
    loadChatHistory(characterId, limit = 10, offset = 0) {
        console.log(`Loading chat history for character ${characterId} with limit=${limit}, offset=${offset}`);
        
        // Clear existing messages
        while (this.messageContainer.firstChild) {
            this.messageContainer.removeChild(this.messageContainer.firstChild);
        }
        
        // Show welcome message by default
        const character = this.app.selectedCharacter;
        if (character) {
            const welcomeMessage = `Hello! I'm ${character.name}, ${character.role}. How can I help you today?`;
            this.displayMessage('assistant', welcomeMessage);
        }
        
        // Try to load history
        fetch(`/api/chat/${characterId}/history?limit=${limit}&offset=${offset}`)
            .then(response => {
                console.log("History response status:", response.status);
                if (!response.ok) {
                    console.log("Error response:", response);
                    // Don't throw error, just return null so we keep the welcome message
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (!data) return; // If null, keep the welcome message
                
                console.log("History data:", data);
                
                // Only clear messages if we have conversations to show
                if (data.success && data.conversations && data.conversations.length > 0) {
                    // Clear the welcome message
                    while (this.messageContainer.firstChild) {
                        this.messageContainer.removeChild(this.messageContainer.firstChild);
                    }
                    
                    // Display messages
                    data.conversations.forEach(msg => {
                        this.displayMessage(
                            msg.role === 'user' ? 'user' : 'assistant', 
                            msg.content
                        );
                    });
                }
            })
            .catch(error => {
                console.error('Error loading chat history:', error);
                // We already showed the welcome message, so no need to handle the error
            });
    }
}

// Export the ChatManager class
window.ChatManager = ChatManager; 