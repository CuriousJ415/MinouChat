/**
 * MiaAI Client-side Application
 * Handles UI interaction, character management, and API communication
 */

class MiaAIApp {
    constructor() {
        // UI Elements
        this.characterList = document.getElementById('character-list');
        this.chatHeader = document.getElementById('chat-header');
        this.chatMessages = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.newCharacterButton = document.getElementById('new-character-button');
        this.characterModal = document.getElementById('character-modal');
        this.characterForm = document.getElementById('character-form');
        this.closeModalButton = document.getElementById('close-modal');
        this.memorySearchModal = document.getElementById('memory-search-modal');
        this.memorySearchForm = document.getElementById('memory-search-form');
        this.memorySearchResults = document.getElementById('memory-search-results');
        this.closeMemoryModalButton = document.getElementById('close-memory-modal');
        this.errorToast = document.getElementById('error-toast');
        this.errorMessage = document.getElementById('error-message');
        this.closeErrorButton = document.getElementById('close-error');
        this.deleteCharacterButton = document.getElementById('delete-character-button');
        this.clearMemoryButton = document.getElementById('clear-memory-button');
        
        // State
        this.characters = [];
        this.selectedCharacter = null;
        this.editingCharacter = null;
        
        // Initialize chat manager
        this.chatManager = new ChatManager(this);
        
        // Initialize the application
        this.init();
    }
    
    init() {
        // Set up event listeners
        this.newCharacterButton.addEventListener('click', () => this.openCharacterModal());
        this.closeModalButton.addEventListener('click', () => this.closeCharacterModal());
        this.characterForm.addEventListener('submit', (e) => this.saveCharacter(e));
        this.deleteCharacterButton.addEventListener('click', () => {
            if (this.editingCharacter) {
                this.deleteCharacter(this.editingCharacter.id);
            }
        });
        this.clearMemoryButton.addEventListener('click', () => {
            if (this.editingCharacter) {
                this.clearCharacterMemory(this.editingCharacter.id);
            }
        });
        this.closeMemoryModalButton.addEventListener('click', () => this.closeMemorySearchModal());
        this.memorySearchForm.addEventListener('submit', (e) => this.searchMemories(e));
        this.closeErrorButton.addEventListener('click', () => this.hideError());
        
        // Restore defaults button
        document.getElementById('restore-defaults-button').addEventListener('click', () => this.restoreDefaultCharacters());
        
        // Ensure the message input and send button are disabled initially
        document.getElementById('message-input').disabled = true;
        document.getElementById('send-button').disabled = true;
        
        // Load characters
        this.loadCharacters();
        
        // Close modals when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === this.characterModal) {
                this.closeCharacterModal();
            }
            if (e.target === this.memorySearchModal) {
                this.closeMemorySearchModal();
            }
        });
    }
    
    loadCharacters() {
        fetch('/api/characters/')
            .then(response => response.json())
            .then(data => {
                console.log('Characters loaded:', data);
                // The API returns an array directly, not wrapped in a characters object
                this.characters = Array.isArray(data) ? data : data.characters || [];
                this.renderCharacterList();
            })
            .catch(error => {
                console.error('Error loading characters:', error);
                this.showError('Failed to load characters');
            });
    }
    
    renderCharacterList() {
        // Clear the list
        this.characterList.innerHTML = '';
        
        // Add each character
        this.characters.forEach(character => {
            const characterElement = document.createElement('div');
            characterElement.className = 'character-item';
            characterElement.dataset.id = character.id;
            
            if (this.selectedCharacter && this.selectedCharacter.id === character.id) {
                characterElement.classList.add('selected');
            }
            
            characterElement.innerHTML = `
                <div class="character-avatar">${character.name.charAt(0)}</div>
                <div class="character-info">
                    <div class="character-name">${character.name}</div>
                    <div class="character-role">${character.role}</div>
                </div>
                <div class="character-actions">
                    <button class="character-action-button history-button" title="Show recent conversation" data-id="${character.id}">
                        <i class="fas fa-comments"></i>
                    </button>
                    <button class="character-action-button edit-button" title="Edit ${character.name}" data-id="${character.id}">
                        <i class="fas fa-edit"></i>
                    </button>
                </div>
            `;
            
            // Add history button functionality
            const historyButton = characterElement.querySelector('.history-button');
            historyButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showHistoryPreview(character.id, character.name);
            });
            
            // Add edit button functionality
            const editButton = characterElement.querySelector('.edit-button');
            editButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openCharacterModal(character);
            });
            
            // Add click event to the character item itself for selection
            characterElement.addEventListener('click', () => {
                this.selectCharacter(character);
            });
            
            this.characterList.appendChild(characterElement);
        });
    }
    
    // Add a new method to show history preview
    showHistoryPreview(characterId, characterName) {
        // Fetch recent messages (last 3)
        fetch(`/api/chat/${characterId}/history?limit=3`)
            .then(response => response.json())
            .then(data => {
                // Check if there are any conversation messages
                if (!data.conversations || data.conversations.length === 0 || 
                    !data.conversations[0].messages || data.conversations[0].messages.length === 0) {
                    this.showError('No conversation history available');
                    return;
                }
                
                // Get the messages
                const messages = data.conversations[0].messages;
                
                // Create the preview element
                const previewElement = document.createElement('div');
                previewElement.className = 'history-preview';
                
                // Add preview header
                previewElement.innerHTML = `
                    <div class="history-preview-header">
                        <h3>Recent conversation with ${characterName}</h3>
                        <button class="close-preview">&times;</button>
                    </div>
                    <div class="history-preview-content"></div>
                `;
                
                // Add messages to preview content
                const contentElement = previewElement.querySelector('.history-preview-content');
                
                // Show last 3 messages or all if less than 3
                const recentMessages = messages.slice(-3);
                recentMessages.forEach(msg => {
                    const messageElement = document.createElement('div');
                    messageElement.className = `preview-message ${msg.role}`;
                    
                    let sender = msg.role === 'user' ? 'You' : characterName;
                    
                    messageElement.innerHTML = `
                        <div class="preview-message-header">${sender}</div>
                        <div class="preview-message-content">${this.chatManager.formatMessageContent(msg.content)}</div>
                    `;
                    
                    contentElement.appendChild(messageElement);
                });
                
                // Add close functionality
                previewElement.querySelector('.close-preview').addEventListener('click', () => {
                    if (previewElement.parentNode) {
                        previewElement.parentNode.removeChild(previewElement);
                    }
                });
                
                // Add to chat messages container at the top
                const messagesContainer = document.getElementById('chat-messages');
                messagesContainer.insertBefore(previewElement, messagesContainer.firstChild);
                
                // Auto-dismiss after 20 seconds
                setTimeout(() => {
                    if (previewElement.parentNode) {
                        previewElement.parentNode.removeChild(previewElement);
                    }
                }, 20000);
            })
            .catch(error => {
                console.error('Error loading history preview:', error);
                this.showError('Could not load conversation history');
            });
    }
    
    selectCharacter(character) {
        this.selectedCharacter = character;
        
        // Update UI
        document.querySelectorAll('.character-item').forEach(item => {
            item.classList.remove('selected');
            if (item.dataset.id === character.id.toString()) {
                item.classList.add('selected');
            }
        });
        
        // Update chat header
        this.chatHeader.innerHTML = `
            <div class="chat-avatar">${character.name.charAt(0)}</div>
            <div class="chat-info">
                <div class="chat-name">${character.name}</div>
                <div class="chat-role">${character.role}</div>
            </div>
        `;
        
        // Enable chat input and send button
        document.getElementById('message-input').disabled = false;
        document.getElementById('send-button').disabled = false;
        
        // Load chat history
        this.chatManager.loadChatHistory(character.id);
    }
    
    openCharacterModal(character = null) {
        // Store the editing character
        this.editingCharacter = character;
        
        // Reset form
        this.characterForm.reset();
        
        // Set form title
        document.getElementById('character-modal-title').textContent = character ? 'Edit Character' : 'Create New Character';
        
        // Fill form if editing
        if (character) {
            document.getElementById('character-id').value = character.id;
            document.getElementById('character-name').value = character.name;
            document.getElementById('character-role').value = character.role;
            document.getElementById('character-personality').value = character.personality || '';
            document.getElementById('character-backstory').value = character.backstory || '';
            document.getElementById('character-system-prompt').value = character.system_prompt || '';
            
            // Set LLM provider and model
            const llmProviderSelect = document.getElementById('character-llm-provider');
            llmProviderSelect.value = character.llm_provider || 'ollama';
            document.getElementById('character-model').value = character.model || 'mistral';
            
            // Check if this is a default character (based on ID prefix 'default-')
            const isDefaultCharacter = character.id.startsWith('default-');
            
            // Show delete button for non-default characters
            document.getElementById('delete-character-button').style.display = isDefaultCharacter ? 'none' : 'block';
            if (!isDefaultCharacter) {
                document.getElementById('delete-character-button').onclick = () => this.deleteCharacter(character.id);
            }
            
            // Clear memory button is always available for existing characters
            document.getElementById('clear-memory-button').style.display = 'block';
        } else {
            // New character - hide delete and clear memory buttons
            document.getElementById('delete-character-button').style.display = 'none';
            document.getElementById('clear-memory-button').style.display = 'none';
        }
        
        // Fetch available models for the selected provider
        this.fetchAndPopulateModels();
        
        // Add event listener to provider dropdown to update models when changed
        const providerSelect = document.getElementById('character-llm-provider');
        providerSelect.addEventListener('change', () => this.fetchAndPopulateModels());
        
        // Show modal
        this.characterModal.classList.add('active');
    }
    
    async fetchAndPopulateModels() {
        try {
            const provider = document.getElementById('character-llm-provider').value;
            const modelContainer = document.getElementById('character-model-container');
            
            // Show loading indicator
            modelContainer.innerHTML = '<select id="character-model" disabled><option>Loading models...</option></select>';
            
            // Fetch models from server
            const response = await fetch(`/api/settings/llm/models?provider=${provider}`);
            if (!response.ok) {
                throw new Error('Failed to fetch models');
            }
            
            const data = await response.json();
            
            // Create select dropdown
            let modelSelect = '<select id="character-model" required>';
            if (data.models && data.models.length > 0) {
                data.models.forEach(model => {
                    modelSelect += `<option value="${model}">${model}</option>`;
                });
            } else {
                modelSelect += '<option value="">No models available</option>';
            }
            modelSelect += '</select>';
            
            // Update the container
            modelContainer.innerHTML = modelSelect;
            
            // If editing a character, set the model
            if (this.editingCharacter && this.editingCharacter.model) {
                const selectElement = document.getElementById('character-model');
                // Try to find the model in the options
                const modelExists = Array.from(selectElement.options).some(option => option.value === this.editingCharacter.model);
                
                if (modelExists) {
                    selectElement.value = this.editingCharacter.model;
                } else if (selectElement.options.length > 0) {
                    // Add the model if it doesn't exist in the list but is set for the character
                    const option = document.createElement('option');
                    option.value = this.editingCharacter.model;
                    option.text = `${this.editingCharacter.model} (not found locally)`;
                    selectElement.add(option, 0);
                    selectElement.value = this.editingCharacter.model;
                }
            }
        } catch (error) {
            console.error('Error fetching models:', error);
            // Fallback to text input
            document.getElementById('character-model-container').innerHTML = 
                '<input type="text" id="character-model" placeholder="e.g. mistral, llama2, gpt-4, claude-3" required>';
                
            // If editing, set the model value
            if (this.editingCharacter && this.editingCharacter.model) {
                document.getElementById('character-model').value = this.editingCharacter.model;
            }
        }
    }
    
    closeCharacterModal() {
        this.characterModal.classList.remove('active');
        this.editingCharacter = null;
    }
    
    saveCharacter(event) {
        event.preventDefault();
        
        const characterId = document.getElementById('character-id').value;
        const isNewCharacter = !characterId;
        
        const characterData = {
            name: document.getElementById('character-name').value,
            role: document.getElementById('character-role').value,
            personality: document.getElementById('character-personality').value,
            backstory: document.getElementById('character-backstory').value,
            system_prompt: document.getElementById('character-system-prompt').value,
            llm_provider: document.getElementById('character-llm-provider').value,
            model: document.getElementById('character-model').value
        };
        
        const url = isNewCharacter ? '/api/characters' : `/api/characters/${characterId}`;
        const method = isNewCharacter ? 'POST' : 'PUT';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(characterData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.closeCharacterModal();
                this.loadCharacters();
                
                // Select the new/edited character
                if (isNewCharacter && data.character) {
                    this.selectCharacter(data.character);
                } else if (!isNewCharacter) {
                    // Update the selected character if it was edited
                    if (this.selectedCharacter && this.selectedCharacter.id === parseInt(characterId)) {
                        this.selectCharacter({...this.selectedCharacter, ...characterData, id: parseInt(characterId)});
                    }
                }
            } else {
                this.showError(data.error || 'Failed to save character');
            }
        })
        .catch(error => {
            console.error('Error saving character:', error);
            this.showError('Failed to save character');
        });
    }
    
    deleteCharacter(characterId) {
        if (!confirm('Are you sure you want to delete this character? This action cannot be undone.')) {
            return;
        }
        
        fetch(`/api/characters/${characterId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.closeCharacterModal();
                
                // If the deleted character was selected, clear the chat
                if (this.selectedCharacter && this.selectedCharacter.id === characterId) {
                    this.selectedCharacter = null;
                    this.chatHeader.innerHTML = '<div class="chat-placeholder">Select a character to start chatting</div>';
                    this.chatMessages.innerHTML = '';
                }
                
                this.loadCharacters();
            } else {
                this.showError(data.error || 'Failed to delete character');
            }
        })
        .catch(error => {
            console.error('Error deleting character:', error);
            this.showError('Failed to delete character');
        });
    }
    
    sendMessageToAPI(message) {
        if (!this.selectedCharacter) {
            this.showError('Please select a character first');
            return;
        }
        
        fetch(`/api/chat/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                character_id: this.selectedCharacter.id,
                message: message 
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide typing indicator
            this.chatManager.hideTypingIndicator();
            
            if (data.success) {
                // Display AI response
                this.chatManager.displayMessage('ai', data.response);
            } else {
                this.showError(data.error || 'Failed to get response');
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
            this.chatManager.hideTypingIndicator();
            this.showError('Failed to get response');
        });
    }
    
    openMemorySearchModal() {
        if (!this.selectedCharacter) {
            this.showError('Please select a character first');
            return;
        }
        
        // Reset form and results
        this.memorySearchForm.reset();
        this.memorySearchResults.innerHTML = '';
        
        // Show modal
        this.memorySearchModal.style.display = 'flex';
    }
    
    closeMemorySearchModal() {
        this.memorySearchModal.style.display = 'none';
    }
    
    searchMemories(event) {
        event.preventDefault();
        
        const query = document.getElementById('memory-search-query').value;
        
        if (!query || !this.selectedCharacter) {
            return;
        }
        
        fetch(`/api/chat/${this.selectedCharacter.id}/search?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                this.memorySearchResults.innerHTML = '';
                
                if (data.results && data.results.length > 0) {
                    data.results.forEach(memory => {
                        const memoryElement = document.createElement('div');
                        memoryElement.className = 'memory-result';
                        
                        memoryElement.innerHTML = `
                            <div class="memory-content">${memory.content}</div>
                            <div class="memory-metadata">
                                <span class="memory-date">${new Date(memory.timestamp).toLocaleString()}</span>
                                <span class="memory-score">Score: ${memory.score.toFixed(2)}</span>
                            </div>
                        `;
                        
                        this.memorySearchResults.appendChild(memoryElement);
                    });
                } else {
                    this.memorySearchResults.innerHTML = '<div class="no-results">No memories found</div>';
                }
            })
            .catch(error => {
                console.error('Error searching memories:', error);
                this.showError('Failed to search memories');
            });
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorToast.classList.add('show');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideError();
        }, 5000);
    }
    
    hideError() {
        this.errorToast.classList.remove('show');
    }
    
    // Add a new method to clear character memory
    clearCharacterMemory(characterId) {
        if (!confirm("This will clear all conversation history for this character. Continue?")) {
            return;
        }
        
        fetch(`/api/chat/${characterId}/clear`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Character memory cleared:', characterId);
                // Show success message
                this.showNotification('Conversation history cleared successfully!');
                // Close the modal
                this.closeCharacterModal();
                
                // If this character is currently selected, reload the chat
                if (this.selectedCharacter && this.selectedCharacter.id === characterId) {
                    this.chatManager.loadChatHistory(characterId);
                }
            } else {
                throw new Error(data.error || 'Failed to clear memory');
            }
        })
        .catch(error => {
            console.error('Error clearing memory:', error);
            this.showError('Failed to clear conversation history');
        });
    }
    
    restoreDefaultCharacters() {
        if (!confirm("This will restore all default characters to their original settings. Continue?")) {
            return;
        }
        
        fetch('/api/characters/restore-defaults', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Default characters restored:', data.restored);
                // Show success message
                this.showNotification('Default characters restored successfully!');
                // Reload characters to update the UI
                this.loadCharacters();
            } else {
                throw new Error(data.error || 'Failed to restore defaults');
            }
        })
        .catch(error => {
            console.error('Error restoring defaults:', error);
            this.showError('Failed to restore default characters');
        });
    }
    
    showNotification(message, duration = 3000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification success-notification';
        
        const content = document.createElement('div');
        content.className = 'notification-content';
        
        const icon = document.createElement('i');
        icon.className = 'fas fa-check-circle';
        
        content.appendChild(icon);
        content.appendChild(document.createTextNode(message));
        
        notification.appendChild(content);
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after duration
        setTimeout(() => {
            if (notification.parentNode === document.body) {
                document.body.removeChild(notification);
            }
        }, duration);
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.app = new MiaAIApp();
}); 