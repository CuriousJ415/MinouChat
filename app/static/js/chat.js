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
        // Set up event listeners
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.clearButton.addEventListener('click', () => this.clearChat());
        this.searchButton.addEventListener('click', () => this.app.openMemorySearchModal());
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
        messageElement.className = `message ${role}${isMemory ? ' memory' : ''}`;
        
        // Format the message content (handle markdown, code, etc.)
        const formattedContent = this.formatMessageContent(content);
        
        // Add memory badge if it's a memory
        let memoryBadge = '';
        if (isMemory) {
            memoryBadge = '<span class="memory-badge">Memory</span>';
        }
        
        messageElement.innerHTML = `
            ${memoryBadge}
            <div class="message-content">${formattedContent}</div>
        `;
        
        this.messageContainer.appendChild(messageElement);
        
        // Scroll to bottom
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
        // Remove all messages from the screen
        while (this.messageContainer.firstChild) {
            this.messageContainer.removeChild(this.messageContainer.firstChild);
        }

        // Add a notification that the chat was cleared but history is preserved
        const notification = document.createElement('div');
        notification.className = 'chat-notification';
        
        const content = document.createElement('div');
        content.className = 'notification-content';
        
        const icon = document.createElement('i');
        icon.className = 'fas fa-info-circle';
        
        content.appendChild(icon);
        content.appendChild(document.createTextNode('Chat screen cleared. Conversation history is preserved.'));
        
        notification.appendChild(content);
        this.messageContainer.appendChild(notification);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            if (notification.parentNode === this.messageContainer) {
                this.messageContainer.removeChild(notification);
            }
        }, 5000);
    }
    
    loadChatHistory(characterId) {
        fetch(`/api/chat/${characterId}/history`)
            .then(response => response.json())
            .then(data => {
                // Clear existing messages
                while (this.messageContainer.firstChild) {
                    this.messageContainer.removeChild(this.messageContainer.firstChild);
                }
                
                // Display messages
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        this.displayMessage(msg.role, msg.content);
                    });
                } else {
                    // Show welcome message
                    const character = this.app.selectedCharacter;
                    if (character) {
                        const welcomeMessage = `Hello! I'm ${character.name}, ${character.role}. How can I help you today?`;
                        this.displayMessage('ai', welcomeMessage);
                    }
                }
            })
            .catch(error => {
                console.error('Error loading chat history:', error);
                this.app.showError('Failed to load chat history');
            });
    }
}

// Export the ChatManager class
window.ChatManager = ChatManager; 