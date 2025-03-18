/**
 * First Time Setup Handler
 */
class SetupManager {
    constructor(app) {
        this.app = app;
        this.modal = document.getElementById('first-time-setup-modal');
        this.providerSelect = document.getElementById('setup-llm-provider');
        this.apiKeySetup = document.getElementById('api-key-setup');
        this.ollamaSetup = document.getElementById('ollama-setup');
        this.saveButton = document.getElementById('save-setup');
        
        this.init();
    }
    
    init() {
        // Set up event listeners
        this.providerSelect.addEventListener('change', () => this.handleProviderChange());
        this.saveButton.addEventListener('click', () => this.saveSetup());
        
        // Load available models when provider changes
        this.providerSelect.addEventListener('change', () => this.loadAvailableModels());
    }
    
    show() {
        this.modal.style.display = 'block';
        this.handleProviderChange(); // Set initial state
        this.loadAvailableModels(); // Load initial models
    }
    
    hide() {
        this.modal.style.display = 'none';
    }
    
    handleProviderChange() {
        const provider = this.providerSelect.value;
        
        // Show/hide API key input
        this.apiKeySetup.style.display = provider === 'ollama' ? 'none' : 'block';
        this.ollamaSetup.style.display = provider === 'ollama' ? 'block' : 'none';
        
        // Update model dropdowns based on provider
        this.loadAvailableModels();
    }
    
    async loadAvailableModels() {
        const provider = this.providerSelect.value;
        const modelsContainer = document.getElementById('available-models');
        const characterSelects = document.querySelectorAll('.character-model');
        
        try {
            // Get available models from the API
            const response = await fetch(`/api/settings/llm/models?provider=${provider}`);
            if (!response.ok) throw new Error('Failed to fetch models');
            
            const data = await response.json();
            const models = data.models || [];
            
            // Update model dropdowns for each character
            characterSelects.forEach(select => {
                select.innerHTML = models.map(model => 
                    `<option value="${model}">${model}</option>`
                ).join('');
                
                // Select a default model based on character
                const character = select.dataset.character;
                if (character === 'mia') {
                    // For Mia, prefer a general-purpose model
                    const defaultModel = this.findBestDefaultModel(models, provider);
                    if (defaultModel) select.value = defaultModel;
                }
            });
            
        } catch (error) {
            console.error('Error loading models:', error);
            modelsContainer.innerHTML = '<p class="error">Failed to load available models. Please check your connection and try again.</p>';
        }
    }
    
    findBestDefaultModel(models, provider) {
        // Define preferred models for each provider
        const preferences = {
            ollama: ['mistral', 'llama2', 'neural-chat'],
            openai: ['gpt-3.5-turbo', 'gpt-4'],
            anthropic: ['claude-instant-1', 'claude-2']
        };
        
        // Find the first available preferred model
        const preferred = preferences[provider] || [];
        return models.find(model => preferred.includes(model)) || models[0];
    }
    
    async saveSetup() {
        const provider = this.providerSelect.value;
        const apiKey = document.getElementById('setup-api-key').value;
        const characterModels = {};
        
        // Collect selected models for each character
        document.querySelectorAll('.character-model').forEach(select => {
            characterModels[select.dataset.character] = select.value;
        });
        
        try {
            // Save provider configuration
            const configResponse = await fetch('/api/settings/llm/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider,
                    api_key: apiKey,
                    default_model: characterModels.mia // Use Mia's model as the default
                })
            });
            
            if (!configResponse.ok) throw new Error('Failed to save LLM configuration');
            
            // Update character models
            for (const [character, model] of Object.entries(characterModels)) {
                const charResponse = await fetch(`/api/characters/default-${character}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model,
                        llm_provider: provider
                    })
                });
                
                if (!charResponse.ok) throw new Error(`Failed to update ${character}`);
            }
            
            // Hide setup and reload characters
            this.hide();
            this.app.loadCharacters();
            
        } catch (error) {
            console.error('Error saving setup:', error);
            this.app.showError('Failed to save setup configuration');
        }
    }
}

// Export the class
window.SetupManager = SetupManager; 