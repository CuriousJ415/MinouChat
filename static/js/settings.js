/**
 * MiaAI Settings JavaScript
 * Handles settings page functionality including loading, testing, and saving LLM configurations
 */

class SettingsManager {
    constructor() {
        // Elements
        this.providerSelect = document.getElementById('provider');
        this.providerDetails = {
            ollama: document.getElementById('provider-details-ollama'),
            openai: document.getElementById('provider-details-openai'),
            anthropic: document.getElementById('provider-details-anthropic')
        };
        this.testButton = document.getElementById('test-connection-button');
        this.connectionStatus = document.getElementById('connection-status');
        this.llmSettingsForm = document.getElementById('llm-settings-form');
        
        // Fields
        this.ollamaApiUrl = document.getElementById('ollama-api-url');
        this.ollamaModel = document.getElementById('ollama-model');
        this.openaiApiKey = document.getElementById('openai-api-key');
        this.openaiModel = document.getElementById('openai-model');
        this.anthropicApiKey = document.getElementById('anthropic-api-key');
        this.anthropicModel = document.getElementById('anthropic-model');
        
        this.init();
    }
    
    init() {
        // Show/hide provider details based on selection
        this.providerSelect.addEventListener('change', () => this.toggleProviderDetails());
        
        // Set up event listeners
        this.testButton.addEventListener('click', () => this.testConnection());
        this.llmSettingsForm.addEventListener('submit', (e) => this.saveSettings(e));
        
        // Load settings on page load
        this.loadSettings();
    }
    
    toggleProviderDetails() {
        const selectedProvider = this.providerSelect.value;
        
        // Hide all provider details
        Object.values(this.providerDetails).forEach(el => {
            el.style.display = 'none';
        });
        
        // Show selected provider details
        this.providerDetails[selectedProvider].style.display = 'block';
    }
    
    async loadSettings() {
        try {
            const response = await fetch('/api/settings/llm');
            if (!response.ok) throw new Error('Failed to load settings');
            
            const config = await response.json();
            
            // Set provider
            if (config.provider) {
                this.providerSelect.value = config.provider;
                // Trigger change event
                this.toggleProviderDetails();
            }
            
            // Set fields
            this.ollamaApiUrl.value = config.api_url || 'http://localhost:11434/api';
            this.ollamaModel.value = config.model || 'mistral';
            
            if (config.provider === 'openai') {
                this.openaiModel.value = config.model || 'gpt-4';
                // API key is just a boolean indicating if it exists
                this.openaiApiKey.placeholder = config.api_key ? '••••••••' : 'sk-...';
            }
            
            if (config.provider === 'anthropic') {
                this.anthropicModel.value = config.model || 'claude-3-opus-20240229';
                // API key is just a boolean indicating if it exists
                this.anthropicApiKey.placeholder = config.api_key ? '••••••••' : 'sk-ant-...';
            }
        } catch (error) {
            console.error('Error loading settings:', error);
            alert('Failed to load settings. Please try again later.');
        }
    }
    
    async testConnection() {
        const provider = this.providerSelect.value;
        let config = {};
        
        // Set provider-specific config
        if (provider === 'ollama') {
            config = {
                api_url: this.ollamaApiUrl.value,
                model: this.ollamaModel.value
            };
        } else if (provider === 'openai') {
            config = {
                api_key: this.openaiApiKey.value,
                model: this.openaiModel.value
            };
        } else if (provider === 'anthropic') {
            config = {
                api_key: this.anthropicApiKey.value,
                model: this.anthropicModel.value
            };
        }
        
        // Update UI
        this.testButton.disabled = true;
        this.connectionStatus.className = 'status';
        this.connectionStatus.textContent = 'Testing connection...';
        
        try {
            const response = await fetch('/api/settings/llm/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    provider: provider,
                    config: config
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.connectionStatus.className = 'status success';
                this.connectionStatus.textContent = `Connection successful! Response: ${result.response}`;
            } else {
                this.connectionStatus.className = 'status error';
                this.connectionStatus.textContent = `Connection failed: ${result.error}`;
            }
        } catch (error) {
            this.connectionStatus.className = 'status error';
            this.connectionStatus.textContent = `Error: ${error.message}`;
        } finally {
            this.testButton.disabled = false;
        }
    }
    
    async saveSettings(event) {
        event.preventDefault();
        
        const provider = this.providerSelect.value;
        let config = {
            provider: provider
        };
        
        // Set provider-specific config
        if (provider === 'ollama') {
            config.api_url = this.ollamaApiUrl.value;
            config.model = this.ollamaModel.value;
        } else if (provider === 'openai') {
            if (this.openaiApiKey.value) {
                config.api_key = this.openaiApiKey.value;
            }
            config.model = this.openaiModel.value;
        } else if (provider === 'anthropic') {
            if (this.anthropicApiKey.value) {
                config.api_key = this.anthropicApiKey.value;
            }
            config.model = this.anthropicModel.value;
        }
        
        try {
            const response = await fetch('/api/settings/llm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Settings saved successfully!');
            } else {
                alert(`Failed to save settings: ${result.error}`);
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            alert(`Error saving settings: ${error.message}`);
        }
    }
}

// Initialize settings manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new SettingsManager();
}); 