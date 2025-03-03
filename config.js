document.addEventListener('DOMContentLoaded', function() {
    const providerSelect = document.getElementById('provider-select');
    const providerForms = document.querySelectorAll('.provider-form');
    
    // Toggle provider forms based on selection
    providerSelect.addEventListener('change', function() {
        const selectedProvider = this.value;
        
        providerForms.forEach(form => {
            form.classList.remove('active');
        });
        
        document.getElementById(`${selectedProvider}-config`).classList.add('active');
    });
    
    // Load saved configuration
    loadConfiguration();
    
    // Initialize test and save buttons
    ['ollama', 'openai', 'anthropic', 'custom'].forEach(provider => {
        const testBtn = document.getElementById(`test-${provider}`);
        const saveBtn = document.getElementById(`save-${provider}`);
        
        if (testBtn) {
            testBtn.addEventListener('click', () => testConnection(provider));
        }
        
        if (saveBtn) {
            saveBtn.addEventListener('click', () => saveConfiguration(provider));
        }
    });
});

// Test connection to provider
async function testConnection(provider) {
    const resultElement = document.getElementById(`${provider}-test-result`);
    resultElement.className = 'test-result';
    resultElement.textContent = 'Testing connection...';
    
    try {
        // Get configuration for selected provider
        const config = getProviderConfig(provider);
        
        // Send test request to server
        const response = await fetch('/api/test_connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                provider: provider,
                config: config
            }),
        });
        
        const result = await response.json();
        
        if (result.success) {
            resultElement.className = 'test-result success';
            resultElement.textContent = '✓ Connection successful: ' + result.message;
        } else {
            resultElement.className = 'test-result error';
            resultElement.textContent = '✗ Connection failed: ' + result.error;
        }
    } catch (error) {
        resultElement.className = 'test-result error';
        resultElement.textContent = '✗ Test failed: ' + error.message;
    }
}

// Save configuration
async function saveConfiguration(provider) {
    const config = getProviderConfig(provider);
    config.provider = provider;
    
    try {
        const response = await fetch('/api/save_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config),
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Configuration saved successfully!');
            loadConfiguration();
        } else {
            alert('Failed to save configuration: ' + result.error);
        }
    } catch (error) {
        alert('Error saving configuration: ' + error.message);
    }
}

// Get configuration for provider
function getProviderConfig(provider) {
    switch (provider) {
        case 'ollama':
            return {
                api_url: document.getElementById('ollama-url').value,
                model: document.getElementById('ollama-model').value
            };
        case 'openai':
            return {
                api_key: document.getElementById('openai-api-key').value,
                model: document.getElementById('openai-model').value
            };
        case 'anthropic':
            return {
                api_key: document.getElementById('anthropic-api-key').value,
                model: document.getElementById('anthropic-model').value
            };
        case 'custom':
            let headers = {};
            try {
                const headersText = document.getElementById('custom-headers').value;
                if (headersText) {
                    headers = JSON.parse(headersText);
                }
            } catch (e) {
                console.error('Invalid JSON in headers');
            }
            
            return {
                api_url: document.getElementById('custom-api-url').value,
                api_key: document.getElementById('custom-api-key').value,
                model: document.getElementById('custom-model').value,
                headers: headers
            };
        default:
            return {};
    }
}

// Load current configuration
async function loadConfiguration() {
    try {
        const response = await fetch('/api/get_config');
        const config = await response.json();
        
        // Update current config display
        document.getElementById('config-provider').textContent = getProviderDisplayName(config.provider);
        document.getElementById('config-model').textContent = config.model || 'Not set';
        document.getElementById('config-url').textContent = config.api_url || 'Not applicable';
        document.getElementById('config-key').textContent = config.api_key ? '[hidden]' : 'Not set';
        
        // Set provider dropdown
        if (config.provider) {
            document.getElementById('provider-select').value = config.provider;
            // Trigger change event to show correct form
            const event = new Event('change');
            document.getElementById('provider-select').dispatchEvent(event);
        }
        
        // Fill in saved values
        switch (config.provider) {
            case 'ollama':
                document.getElementById('ollama-url').value = config.api_url || 'http://ollama:11434/api';
                document.getElementById('ollama-model').value = config.model || 'mistral';
                break;
            case 'openai':
                document.getElementById('openai-model').value = config.model || 'gpt-4o';
                // Don't set API key for security
                break;
            case 'anthropic':
                document.getElementById('anthropic-model').value = config.model || 'claude-3-5-sonnet';
                // Don't set API key for security
                break;
            case 'custom':
                document.getElementById('custom-api-url').value = config.api_url || '';
                document.getElementById('custom-model').value = config.model || '';
                // Don't set API key for security
                if (config.headers) {
                    document.getElementById('custom-headers').value = JSON.stringify(config.headers);
                }
                break;
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
    }
}

// Get display name for provider
function getProviderDisplayName(provider) {
    switch (provider) {
        case 'ollama': return 'Local Ollama';
        case 'openai': return 'OpenAI';
        case 'anthropic': return 'Anthropic Claude';
        case 'custom': return 'Custom API';
        default: return 'Unknown';
    }
}