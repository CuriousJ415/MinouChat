// Model Management UI
class ModelManager {
    constructor() {
        this.modelSelect = document.getElementById('model-select');
        this.modelStatus = document.getElementById('model-status');
        this.testConnectionBtn = document.getElementById('test-connection-btn');
        this.initializeEventListeners();
        this.loadModels();
    }

    initializeEventListeners() {
        if (this.modelSelect) {
            this.modelSelect.addEventListener('change', () => this.switchModel());
        }
        if (this.testConnectionBtn) {
            this.testConnectionBtn.addEventListener('click', () => this.testConnection());
        }
    }

    async loadModels() {
        try {
            const response = await fetch('/api/models/list');
            const data = await response.json();
            
            if (data.success && this.modelSelect) {
                // Clear existing options
                this.modelSelect.innerHTML = '';
                
                // Add models to select
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    this.modelSelect.appendChild(option);
                });
                
                // Load current model
                await this.loadCurrentModel();
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.updateStatus('Error loading models', 'error');
        }
    }

    async loadCurrentModel() {
        try {
            const response = await fetch('/api/models/current');
            const data = await response.json();
            
            if (data.success && this.modelSelect) {
                // Set current model in select
                this.modelSelect.value = data.model;
                this.updateStatus(`Current model: ${data.model}`, 'info');
            }
        } catch (error) {
            console.error('Error loading current model:', error);
            this.updateStatus('Error loading current model', 'error');
        }
    }

    async switchModel() {
        if (!this.modelSelect) return;
        
        const model = this.modelSelect.value;
        this.updateStatus('Switching model...', 'info');
        
        try {
            const response = await fetch('/api/models/switch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ model }),
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatus(`Switched to ${model}`, 'success');
            } else {
                this.updateStatus(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error switching model:', error);
            this.updateStatus('Error switching model', 'error');
        }
    }

    async testConnection() {
        this.updateStatus('Testing connection...', 'info');
        
        try {
            const response = await fetch('/api/models/test', {
                method: 'POST',
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatus(data.message, 'success');
            } else {
                this.updateStatus(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error testing connection:', error);
            this.updateStatus('Error testing connection', 'error');
        }
    }

    updateStatus(message, type = 'info') {
        if (!this.modelStatus) return;
        
        this.modelStatus.textContent = message;
        this.modelStatus.className = 'model-status';
        this.modelStatus.classList.add(`status-${type}`);
    }
}

// Initialize model manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.modelManager = new ModelManager();
}); 