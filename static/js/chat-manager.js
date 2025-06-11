/**
 * ChatManager
 * Handles chat interactions, message sending, and history management
 */
class ChatManager {
    constructor(app) {
        this.app = app;
        this.chatMessages = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.clearChatButton = document.getElementById('clear-chat-button');
        this.recallConversationButton = document.getElementById('recall-conversation-button');
        this.searchMemoriesButton = document.getElementById('search-memories-button');
        this.isTyping = false;
        
        // Initialize event listeners
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Clear chat button
        if (this.clearChatButton) {
            this.clearChatButton.addEventListener('click', () => this.clearChatWindow());
        }
        
        // Search memories button
        if (this.searchMemoriesButton) {
            this.searchMemoriesButton.addEventListener('click', () => this.openMemorySearchModal());
        }
    }
    
    clearChatWindow() {
        // Clear only the chat messages display without affecting history or memory
        if (!this.chatMessages) return;
        
        // Save a reference to typing indicator if it exists
        const typingIndicator = this.chatMessages.querySelector('.typing-indicator');
        
        // Clear the chat window
        this.chatMessages.innerHTML = '';
        
        // Re-add typing indicator if it existed
        if (typingIndicator) {
            this.chatMessages.appendChild(typingIndicator);
        }
        
        // Show empty state message
        this.showEmptyState();
    }
    
    showEmptyState() {
        if (!this.chatMessages) return;
        
        // Only show empty state if there are no messages
        if (this.chatMessages.children.length === 0 || 
            (this.chatMessages.children.length === 1 && this.chatMessages.querySelector('.typing-indicator'))) {
            
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state';
            emptyState.innerHTML = `
                <p>No messages yet. Start a conversation!</p>
            `;
            
            // Add at beginning of chat messages
            this.chatMessages.insertBefore(emptyState, this.chatMessages.firstChild);
        }
    }
    
    loadChatHistory(characterId) {
        if (!characterId) return;
        
        // Clear current chat display
        if (this.chatMessages) {
            this.chatMessages.innerHTML = '';
        }
        
        // Show loading indicator
        this.showLoading();
        
        // Fetch chat history from API
        fetch(`/api/chat/${characterId}/history`)
            .then(response => response.json())
            .then(data => {
                this.hideLoading();
                
                if (data.success && data.messages) {
                    // Display messages
                    data.messages.forEach(msg => {
                        this.addMessageToChat(msg.role === 'user', msg.content);
                    });
                    
                    // Scroll to bottom
                    this.scrollToBottom();
                } else {
                    // Show empty state if no messages
                    this.showEmptyState();
                }
            })
            .catch(error => {
                console.error('Error loading chat history:', error);
                this.hideLoading();
                this.showEmptyState();
            });
    }
    
    showLoading() {
        if (!this.chatMessages) return;
        
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'loading-indicator';
        loadingIndicator.innerHTML = '<div class="spinner"></div><p>Loading...</p>';
        this.chatMessages.appendChild(loadingIndicator);
    }
    
    hideLoading() {
        if (!this.chatMessages) return;
        
        const loadingIndicator = this.chatMessages.querySelector('.loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }
    
    addMessageToChat(isUser, content) {
        if (!this.chatMessages) return;
        
        // Remove empty state if present
        const emptyState = this.chatMessages.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = isUser ? 'message user-message' : 'message assistant-message';
        
        // Format content with markdown if it's not from user
        if (!isUser) {
            // Simple markdown-like formatting
            content = content
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>');
        }
        
        messageElement.innerHTML = `
            <div class="message-content">${content}</div>
        `;
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        if (!this.chatMessages) return;
        
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    clearConversation(characterId) {
        if (!characterId) return;
        
        if (!confirm('This will clear the conversation history. Continue?')) {
            return;
        }
        
        fetch(`/api/chat/${characterId}/clear`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear chat display
                this.clearChatWindow();
                this.app.showNotification('Conversation cleared');
            } else {
                this.app.showError(data.error || 'Failed to clear conversation');
            }
        })
        .catch(error => {
            console.error('Error clearing conversation:', error);
            this.app.showError('Failed to clear conversation');
        });
    }
    
    openMemorySearchModal() {
        const characterId = this.app.selectedCharacter?.id;
        if (!characterId) {
            this.app.showError('No character selected');
            return;
        }
        
        // Get the modal
        const modal = document.getElementById('memory-search-modal');
        if (!modal) return;
        
        // Clear previous results
        const resultsContainer = document.getElementById('search-results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
        
        // Clear search input
        const searchInput = document.getElementById('memory-search-query');
        if (searchInput) {
            searchInput.value = '';
        }
        
        // Set character ID on form
        const form = document.getElementById('memory-search-form');
        if (form) {
            form.dataset.characterId = characterId;
            
            // Add submit event listener if not already added
            if (!form.dataset.listenerAdded) {
                form.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.searchMemories();
                });
                form.dataset.listenerAdded = 'true';
            }
        }
        
        // Show the modal
        modal.style.display = 'block';
    }
    
    searchMemories() {
        const form = document.getElementById('memory-search-form');
        const characterId = form?.dataset.characterId;
        const searchInput = document.getElementById('memory-search-query');
        const query = searchInput?.value.trim();
        
        if (!characterId) {
            this.app.showError('No character selected');
            return;
        }
        
        if (!query) {
            this.app.showError('Please enter a search query');
            return;
        }
        
        const resultsContainer = document.getElementById('search-results-container');
        if (!resultsContainer) return;
        
        // Show loading state
        resultsContainer.innerHTML = '<div class="loading">Searching memories...</div>';
        
        // Call API to search memories
        fetch(`/api/chat/search/${characterId}?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.memories) {
                    if (data.memories.length === 0) {
                        resultsContainer.innerHTML = '<div class="no-results">No memories found</div>';
                        return;
                    }
                    
                    // Clear results container
                    resultsContainer.innerHTML = '';
                    
                    // Add each memory to results
                    data.memories.forEach(memory => {
                        const memoryElement = document.createElement('div');
                        memoryElement.className = 'memory-item';
                        
                        // Format the memory content
                        memoryElement.innerHTML = `
                            <div class="memory-content">${memory.content}</div>
                            <div class="memory-meta">
                                <span class="memory-date">${new Date(memory.created_at).toLocaleString()}</span>
                                <span class="memory-score">Score: ${memory.score.toFixed(2)}</span>
                                <button class="forget-btn" data-memory-id="${memory.id}">Forget</button>
                            </div>
                        `;
                        
                        resultsContainer.appendChild(memoryElement);
                        
                        // Add event listener to forget button
                        const forgetBtn = memoryElement.querySelector('.forget-btn');
                        if (forgetBtn) {
                            forgetBtn.addEventListener('click', () => {
                                this.forgetMemory(characterId, memory.content);
                            });
                        }
                    });
                } else {
                    resultsContainer.innerHTML = `<div class="error">${data.error || 'Failed to search memories'}</div>`;
                }
            })
            .catch(error => {
                console.error('Error searching memories:', error);
                resultsContainer.innerHTML = '<div class="error">Error searching memories</div>';
            });
    }
    
    forgetMemory(characterId, content) {
        if (!characterId || !content) return;
        
        if (!confirm('Are you sure you want to forget this memory?')) {
            return;
        }
        
        fetch(`/api/chat/forget/${characterId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: content })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.app.showNotification('Memory forgotten');
                
                // Refresh search results
                this.searchMemories();
            } else {
                this.app.showError(data.error || 'Failed to forget memory');
            }
        })
        .catch(error => {
            console.error('Error forgetting memory:', error);
            this.app.showError('Failed to forget memory');
        });
    }
} 