/**
 * MiaAI Client-side Application
 * Handles UI interaction, character management, and API communication
 */

class App {
    constructor() {
        // Initialize properties
        this.characters = [];
        this.selectedCharacter = null;
        this.chatManager = null;
        this.documentManager = null;
        this.settings = {
            llmProvider: 'ollama',
            model: 'mistral',
            apiKey: ''
        };
        this.usingDocumentContext = false;

        // DOM elements
        this.characterList = document.getElementById('character-list');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.documentButton = document.getElementById('document-button');
        this.clearChatButton = document.getElementById('clear-chat-button');
        this.recallConversationButton = document.getElementById('recall-conversation-button');
        this.searchMemoriesButton = document.getElementById('search-memories-button');
        this.documentContextIndicator = document.getElementById('document-context-indicator');
        this.characterLlmProviderSelect = document.getElementById('character-llm-provider');
        this.characterModelSelect = document.getElementById('character-model');
        this.characterApiKeyInput = document.getElementById('character-api-key');
        this.settingsLlmProviderSelect = document.getElementById('settings-llm-provider');
        this.settingsModelSelect = document.getElementById('settings-model');
        this.settingsApiKeyInput = document.getElementById('settings-api-key');

        // Buttons
        this.addCharacterBtn = document.getElementById('add-character-btn');
        this.createCharacterBtn = document.getElementById('create-character-btn');
        this.settingsBtn = document.getElementById('settings-btn');
        this.saveSettingsBtn = document.getElementById('save-settings-btn');
        this.restoreDefaultsBtn = document.getElementById('restore-defaults-btn');

        // Modals
        this.createCharacterModal = document.getElementById('create-character-modal');
        this.characterSettingsModal = document.getElementById('character-settings-modal');
        this.settingsModal = document.getElementById('settings-modal');

        // Bind event listeners
        this.bindEventListeners();

        // Initialize Chat Manager
        this.chatManager = new ChatManager(this);

        // Initialize Document Manager
        this.documentManager = new DocumentManager(this);

        // Load characters and settings
        this.loadCharacters();
        this.loadSettings();
    }
    
    bindEventListeners() {
        // Character management
        if (this.addCharacterBtn) {
            this.addCharacterBtn.addEventListener('click', () => this.showNewCharacterModal());
        }
        if (this.restoreDefaultsBtn) {
            this.restoreDefaultsBtn.addEventListener('click', () => this.restoreDefaultCharacters());
        }
        
        // Chat actions
        if (this.settingsBtn) {
            this.settingsBtn.addEventListener('click', () => this.showSettingsModal());
        }
        
        // Memory actions
        if (this.searchMemoriesButton) {
            this.searchMemoriesButton.addEventListener('click', () => this.openMemorySearchModal());
        }
        
        // LLM provider change in character settings
        const settingsLlmProvider = document.getElementById('settings-llm-provider');
        const settingsModel = document.getElementById('settings-model');
        if (settingsLlmProvider && settingsModel) {
            settingsLlmProvider.addEventListener('change', () => {
                // Add a loading placeholder
                settingsModel.innerHTML = '<option value="">Loading models...</option>';
                
                // Load models for the selected provider
                loadModelsForProvider(settingsLlmProvider.value, settingsModel);
            });
        }
        
        // Message sending
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        // Modal handling
        const closeButtons = document.querySelectorAll('.close-btn');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.closeModals());
        });
        
        // New character form
        const newCharacterForm = document.getElementById('new-character-form');
        if (newCharacterForm) {
            newCharacterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createCharacter(new FormData(newCharacterForm));
            });
        }
        
        // Character settings form
        const characterSettingsForm = document.getElementById('character-settings-form');
        if (characterSettingsForm) {
            characterSettingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.updateCharacterSettings(new FormData(characterSettingsForm));
            });
            
            // Reset memory button
            const resetMemoryButton = document.getElementById('reset-memory-button');
            if (resetMemoryButton) {
                resetMemoryButton.addEventListener('click', () => this.resetCharacterMemory());
            }
        }
        
        // Close modals when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModals();
            }
        });
    }
    
    loadCharacters() {
        fetch('/api/characters')
            .then(response => response.json())
            .then(data => {
                this.characters = data;
                this.renderCharacterList();
            })
            .catch(error => {
                console.error('Error loading characters:', error);
                this.showError('Failed to load characters');
            });
    }
    
    renderCharacterList() {
        this.characterList.innerHTML = '';
        
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
                    <button class="character-settings-button" title="Settings">
                        <i class="fas fa-cog"></i>
                    </button>
                </div>
            `;
            
            // Add click event to select character
            characterElement.addEventListener('click', (e) => {
                // Don't select if clicking the settings button
                if (!e.target.closest('.character-settings-button')) {
                    this.selectCharacter(character);
                }
            });
            
            // Add click event for settings button
            const settingsButton = characterElement.querySelector('.character-settings-button');
            if (settingsButton) {
                settingsButton.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.showCharacterSettings(character);
                });
            }
            
            this.characterList.appendChild(characterElement);
        });
    }
    
    selectCharacter(character) {
        this.selectedCharacter = character;
        
        // Update UI
        document.querySelectorAll('.character-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const selectedItem = this.characterList.querySelector(`[data-id="${character.id}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        // Update chat header
        const chatHeader = document.querySelector('.chat-header');
        if (chatHeader) {
            const chatPlaceholder = chatHeader.querySelector('.chat-placeholder');
            if (chatPlaceholder) {
                chatPlaceholder.innerHTML = `
                    <div class="chat-avatar">${character.name.charAt(0)}</div>
                    <div class="chat-info">
                        <div class="chat-name">${character.name}</div>
                        <div class="chat-role">${character.role}</div>
                    </div>
                `;
            }
        }
        
        // Enable chat input and buttons
        if (this.messageInput) {
            this.messageInput.disabled = false;
            this.messageInput.placeholder = `Message ${character.name}...`;
            this.messageInput.focus(); // Add focus to show cursor
        }
        
        // Enable buttons
        if (this.sendButton) {
            this.sendButton.disabled = false;
        }
        if (this.documentButton) {
            this.documentButton.disabled = false;
        }
        if (this.clearChatButton) {
            this.clearChatButton.disabled = false;
        }
        if (this.recallConversationButton) {
            this.recallConversationButton.disabled = false;
        }
        if (this.searchMemoriesButton) {
            this.searchMemoriesButton.disabled = false;
        }
        
        // Load chat history
        if (this.chatManager) {
            this.chatManager.loadChatHistory(character.id);
        }
        
        // Update document manager
        if (this.documentManager) {
            this.documentManager.updateUIForSelectedCharacter();
        }
    }
    
    showNewCharacterModal() {
        const modal = document.getElementById('new-character-modal');
        modal.style.display = 'block';
    }
    
    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }
    
    createCharacter(formData) {
        const character = {
            name: formData.get('name'),
            role: formData.get('role'),
            personality: formData.get('personality'),
            backstory: formData.get('backstory'),
            system_prompt: formData.get('system_prompt'),
            llm_provider: formData.get('llm_provider'),
            model: formData.get('model'),
            temperature: parseFloat(formData.get('temperature')),
            top_p: parseFloat(formData.get('top_p')),
            repeat_penalty: parseFloat(formData.get('repeat_penalty')),
            top_k: parseInt(formData.get('top_k'))
        };
        
        fetch('/api/characters', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(character)
        })
        .then(response => response.json())
        .then(data => {
            this.closeModals();
            this.loadCharacters();
            this.selectCharacter(data);
        })
        .catch(error => {
            console.error('Error creating character:', error);
            this.showError('Failed to create character');
        });
    }
    
    restoreDefaultCharacters() {
        if (!confirm('This will restore the default characters. Continue?')) {
            return;
        }
        
        fetch('/api/characters/restore-defaults', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            this.characters = data;
            this.renderCharacterList();
        })
        .catch(error => {
            console.error('Error restoring default characters:', error);
            this.showError('Failed to restore default characters');
        });
    }
    
    showCharacterSettings(character) {
        // Set form values
        const form = document.getElementById('character-settings-form');
        if (form) {
            const llmProvider = form.querySelector('#settings-llm-provider');
            const model = form.querySelector('#settings-model');
            const temperature = form.querySelector('#settings-temperature');
            const topP = form.querySelector('#settings-top-p');
            const repeatPenalty = form.querySelector('#settings-repeat-penalty');
            const topK = form.querySelector('#settings-top-k');
            
            // Set values from character
            if (llmProvider) llmProvider.value = character.llm_provider || 'ollama';
            
            // Load models for the selected provider
            if (llmProvider && model) {
                // Add a loading placeholder
                model.innerHTML = '<option value="">Loading models...</option>';
                
                // Load models for the selected provider
                loadModelsForProvider(llmProvider.value, model).then(() => {
                    // Set the model value after models are loaded
                    model.value = character.model || 'mistral';
                });
            }
            
            if (temperature) {
                temperature.value = character.temperature || 0.7;
                document.getElementById('settings-temperature-value').textContent = temperature.value;
            }
            if (topP) {
                topP.value = character.top_p || 0.9;
                document.getElementById('settings-top-p-value').textContent = topP.value;
            }
            if (repeatPenalty) {
                repeatPenalty.value = character.repeat_penalty || 1.1;
                document.getElementById('settings-repeat-penalty-value').textContent = repeatPenalty.value;
            }
            if (topK) {
                topK.value = character.top_k || 40;
                document.getElementById('settings-top-k-value').textContent = topK.value;
            }
            
            // Store the character ID
            form.dataset.characterId = character.id;
        }
        
        // Show the modal
        const modal = document.getElementById('character-settings-modal');
        if (modal) modal.style.display = 'block';
    }
    
    updateCharacterSettings(formData) {
        const form = document.getElementById('character-settings-form');
        const characterId = form.dataset.characterId;
        
        if (!characterId) {
            this.showError('Character ID not found');
            return;
        }
        
        const settings = {
            llm_provider: formData.get('llm_provider'),
            model: formData.get('model'),
            temperature: parseFloat(formData.get('temperature')),
            top_p: parseFloat(formData.get('top_p')),
            repeat_penalty: parseFloat(formData.get('repeat_penalty')),
            top_k: parseInt(formData.get('top_k'))
        };
        
        fetch(`/api/characters/${characterId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        })
        .then(response => response.json())
        .then(data => {
            this.closeModals();
            this.loadCharacters();
            this.showNotification('Character settings updated');
        })
        .catch(error => {
            console.error('Error updating character settings:', error);
            this.showError('Failed to update character settings');
        });
    }
    
    resetCharacterMemory() {
        const form = document.getElementById('character-settings-form');
        const characterId = form.dataset.characterId;
        
        if (!characterId) {
            this.showError('Character ID not found');
            return;
        }
        
        if (!confirm('This will COMPLETELY reset all memories for this character including long-term memories. This cannot be undone. Continue?')) {
            return;
        }
        
        fetch(`/api/characters/${characterId}/reset_memories`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.closeModals();
                this.showNotification('Character memory has been completely reset');
                
                // Reload chat history if this is the selected character
                if (this.selectedCharacter && this.selectedCharacter.id === characterId) {
                    this.chatManager.loadChatHistory(characterId);
                }
            } else {
                this.showError(data.error || 'Failed to reset memory');
            }
        })
        .catch(error => {
            console.error('Error resetting memory:', error);
            this.showError('Failed to reset memory');
        });
    }
    
    showSettingsModal() {
        const modal = document.getElementById('settings-modal');
        modal.style.display = 'block';
    }
    
    loadSettings() {
        // Implementation of loadSettings method
    }
    
    showNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification success-notification';
        
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-check-circle"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    showError(message) {
        const errorToast = document.getElementById('error-toast');
        const errorMessage = document.getElementById('error-message');
        
        errorMessage.textContent = message;
        errorToast.classList.add('show');
        
        setTimeout(() => {
            errorToast.classList.remove('show');
        }, 3000);
    }

    sendMessageToAPI(message) {
        if (!this.selectedCharacter) {
            this.showError('Please select a character first');
            return;
        }

        this.chatManager.showTypingIndicator();

        // Check if this character has documents
        this.checkForCharacterDocuments(this.selectedCharacter.id)
            .then(hasDocuments => {
                // Show document context indicator if using documents
                if (hasDocuments) {
                    this.usingDocumentContext = true;
                    if (this.documentContextIndicator) {
                        this.documentContextIndicator.style.display = 'flex';
                        this.documentContextIndicator.title = `Using document context for ${this.selectedCharacter.name}`;
                    }
                }
                
                const payload = {
                    character_id: this.selectedCharacter.id,
                    message: message,
                    use_documents: hasDocuments, // Only use documents if they exist
                    context_type: 'full' // Request the LLM to use full context including documents
                };

                console.log("Sending message with payload:", payload);

                // Create a timeout for the request
                const timeoutPromise = new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Request timed out after 30 seconds')), 30000)
                );

                // Main fetch request
                const fetchPromise = fetch(`/api/chat/send`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                })
                .then(response => {
                    console.log("Response status:", response.status);
                    // Try to get the response body even if it's an error
                    return response.text().then(text => {
                        console.log("Raw response:", text);
                        
                        try {
                            // Try to parse as JSON
                            const data = JSON.parse(text);
                            
                            // Check if it's an error response
                            if (!response.ok) {
                                // Format Ollama connection error in a more user-friendly way
                                if (data.error && data.error.includes("Failed to connect to Ollama")) {
                                    throw new Error("Could not connect to the AI service. Please check if Ollama is running.");
                                }
                                throw new Error(`Server error: ${data.error || response.statusText}`);
                            }
                            
                            return data;
                        } catch (e) {
                            console.error("Error parsing JSON:", e);
                            // If parsing failed, throw with the raw text
                            if (!response.ok) {
                                // Format connection error in a more user-friendly way
                                if (text.includes("Failed to connect to Ollama") || text.includes("HTTPConnectionPool")) {
                                    throw new Error("Could not connect to the AI service. Please check if Ollama is running.");
                                }
                                throw new Error(`Server error (${response.status}): ${text}`);
                            }
                            throw new Error(`Invalid JSON response: ${text}`);
                        }
                    });
                });

                // Race between the fetch and the timeout
                Promise.race([fetchPromise, timeoutPromise])
                    .then(data => {
                        console.log("Response data:", data);
                        this.chatManager.hideTypingIndicator();
                        if (!data.success) {
                            this.showError(data.error || 'Unknown error');
                            return;
                        }
                        this.chatManager.displayMessage('assistant', data.response);
                    })
                    .catch(error => {
                        console.error('Error sending message:', error);
                        this.chatManager.hideTypingIndicator();
                        
                        // Show a more user-friendly error message
                        let errorMessage = error.message;
                        if (errorMessage.includes("Failed to fetch") || 
                            errorMessage.includes("NetworkError") ||
                            errorMessage.includes("network") ||
                            errorMessage.includes("HTTPConnectionPool")) {
                            errorMessage = "Connection to AI service failed. Please make sure Ollama is running.";
                        }
                        
                        this.showError('Failed to send message: ' + errorMessage);
                    });
            });
    }

    // Add method to check if character has documents
    async checkForCharacterDocuments(characterId) {
        try {
            const response = await fetch(`/api/documents/character/${characterId}`);
            
            if (!response.ok) {
                console.error(`Failed to check documents: ${response.status}`);
                return false;
            }
            
            const data = await response.json();
            return data.documents && data.documents.length > 0;
        } catch (error) {
            console.error('Error checking for character documents:', error);
            return false;
        }
    }

    // Add sendMessage method to handle sending messages
    sendMessage() {
        if (!this.selectedCharacter) {
            this.showError('Please select a character first');
            return;
        }
        
        const messageText = this.messageInput.value.trim();
        if (!messageText) {
            return; // Don't send empty messages
        }
        
        // Display user message
        this.chatManager.displayMessage('user', messageText);
        
        // Clear input
        this.messageInput.value = '';
        
        // Send message to API
        this.sendMessageToAPI(messageText);
    }

    // Add memory search methods
    openMemorySearchModal() {
        if (!this.selectedCharacter) {
            this.showError('Please select a character first');
            return;
        }
        
        // Get the modal and form
        const modal = document.getElementById('memory-search-modal');
        const form = document.getElementById('memory-search-form');
        const resultsContainer = document.getElementById('search-results-container');
        
        if (!modal || !form) {
            console.error('Memory search modal or form not found');
            return;
        }
        
        // Clear previous results
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
        
        // Clear the form
        form.reset();
        
        // Show the modal
        modal.style.display = 'block';
        
        // Add form submission handler
        form.onsubmit = (e) => {
            e.preventDefault();
            const query = document.getElementById('memory-search-query').value.trim();
            if (query) {
                this.searchMemories(query);
            }
        };
    }
    
    async searchMemories(query) {
        if (!this.selectedCharacter) {
            this.showError('Please select a character first');
            return;
        }
        
        // Get the results container
        const resultsContainer = document.getElementById('search-results-container');
        if (!resultsContainer) return;
        
        // Show loading state
        resultsContainer.innerHTML = '<div class="loading">Searching memories...</div>';
        
        try {
            console.log(`Searching memories for character ${this.selectedCharacter.id} with query: ${query}`);
            
            // Make API request
            const response = await fetch(`/api/chat/direct-search/${this.selectedCharacter.id}?q=${encodeURIComponent(query)}`);
            
            console.log(`Search response status: ${response.status}`);
            
            // Handle non-successful response
            if (!response.ok) {
                let errorMessage = `Search failed: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData && errorData.error) {
                        errorMessage = errorData.error;
                    }
                } catch (e) {
                    console.error('Error parsing error response:', e);
                }
                
                resultsContainer.innerHTML = `<div class="error">Error: ${errorMessage}</div>`;
                return;
            }
            
            // Parse JSON response
            const data = await response.json();
            console.log('Search results:', data);
            
            // Display results
            if (data.success === false) {
                resultsContainer.innerHTML = `<div class="error">${data.error || 'Search failed'}</div>`;
                return;
            }
            
            if (!data.results || data.results.length === 0) {
                resultsContainer.innerHTML = '<div class="no-results">No memories found</div>';
                return;
            }
            
            // Display results
            let html = '<div class="search-results">';
            data.results.forEach(result => {
                // Format the score percentage (handling both 'score' and 'relevance' properties)
                const score = result.score !== undefined ? result.score : (result.relevance || 0);
                const scorePercent = Math.round(parseFloat(score) * 100);
                
                html += `
                    <div class="memory-item">
                        <div class="memory-content">${result.content}</div>
                        <div class="memory-meta">
                            <span class="memory-score">Relevance: ${scorePercent}%</span>
                            ${result.timestamp ? `<span class="memory-time">${result.timestamp}</span>` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            
            resultsContainer.innerHTML = html;
        } catch (error) {
            console.error('Error searching memories:', error);
            resultsContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        }
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Create and initialize the app
    window.app = new App();
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
});

// Provider change handlers
function handleLlmProviderChange(providerSelect, modelSelect, apiKeyInput) {
    const provider = providerSelect.value;
    
    // Show/hide API key field based on provider
    if (provider === 'ollama') {
        apiKeyInput.parentElement.style.display = 'none';
    } else {
        apiKeyInput.parentElement.style.display = 'block';
    }
    
    // Update models for the selected provider
    loadModelsForProvider(provider, modelSelect);
}

// Load models for the selected provider
async function loadModelsForProvider(provider, modelSelect) {
    // Clear current options except the loading placeholder
    while (modelSelect.options.length > 1) {
        modelSelect.remove(1);
    }
    
    try {
        console.log(`Loading models for provider: ${provider}`);
        const response = await fetch(`/api/settings/llm/models?provider=${provider}`);
        
        if (!response.ok) {
            throw new Error(`Failed to load models: ${response.status}`);
        }
        
        const data = await response.json();
        console.log(`Received models:`, data);
        
        // Remove loading placeholder
        if (modelSelect.options.length > 0) {
            modelSelect.remove(0);
        }
        
        // Check if the response has the expected format
        if (data.success && Array.isArray(data.models)) {
            // Add models to dropdown
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
            
            // If no models were returned, show a message
            if (data.models.length === 0) {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No models available';
                modelSelect.appendChild(option);
            }
        } else {
            throw new Error('Invalid response format');
        }
        
        return true; // Return success
    } catch (error) {
        console.error('Error loading models:', error);
        
        // Show error option
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Failed to load models';
        modelSelect.appendChild(option);
        
        return false; // Return failure
    }
} 