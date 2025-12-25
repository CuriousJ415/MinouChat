/**
 * MinouChat Onboarding Manager
 * Handles welcome wizard and contextual hints for new users
 */

const OnboardingManager = {
  STORAGE_KEY: 'minouchat-onboarding-complete',
  HINTS_KEY: 'minouchat-hints-dismissed',
  LLM_CONFIGURED_KEY: 'minouchat-llm-configured',

  currentStep: 0,
  totalSteps: 4,  // Welcome, LLM Config, Persona Selection, Completion
  selectedPersonaId: null,
  personas: [],

  // LLM Configuration State
  selectedProvider: null,
  llmConfigured: false,

  /**
   * Initialize the onboarding system
   * @param {Object} options - Configuration options
   */
  init(options = {}) {
    this.personas = options.personas || [];
    this.isFirstLogin = options.isFirstLogin || false;
    this.username = options.username || 'there';

    // Check if we should show onboarding
    if (this.shouldShowOnboarding()) {
      this.show();
    }

    // Initialize contextual hints
    this.initHints();
  },

  /**
   * Check if onboarding should be shown
   * @returns {boolean}
   */
  shouldShowOnboarding() {
    // Show if explicitly marked as first login or not completed
    if (this.isFirstLogin) return true;
    return !localStorage.getItem(this.STORAGE_KEY);
  },

  /**
   * Mark onboarding as complete
   */
  markComplete() {
    localStorage.setItem(this.STORAGE_KEY, 'true');
  },

  /**
   * Reset onboarding (can be triggered from settings)
   */
  reset() {
    localStorage.removeItem(this.STORAGE_KEY);
    localStorage.removeItem(this.HINTS_KEY);
  },

  /**
   * Show the onboarding wizard
   */
  show() {
    this.currentStep = 0;
    this.createModal();
    this.renderStep();
    this.openModal();
  },

  /**
   * Hide the onboarding wizard
   */
  hide() {
    this.closeModal();
    this.markComplete();
  },

  /**
   * Skip onboarding
   */
  skip() {
    this.hide();
  },

  /**
   * Go to next step
   */
  nextStep() {
    if (this.currentStep < this.totalSteps - 1) {
      this.currentStep++;
      this.renderStep();
    } else {
      this.complete();
    }
  },

  /**
   * Go to previous step
   */
  prevStep() {
    if (this.currentStep > 0) {
      this.currentStep--;
      this.renderStep();
    }
  },

  /**
   * Complete onboarding and redirect to chat
   */
  complete() {
    this.hide();
    if (this.selectedPersonaId) {
      window.location.href = `/chat?character_id=${this.selectedPersonaId}`;
    }
  },

  /**
   * Create the modal DOM elements
   */
  createModal() {
    // Remove existing modal if present
    const existing = document.getElementById('onboarding-modal');
    if (existing) existing.remove();

    // Create backdrop
    const backdrop = document.createElement('div');
    backdrop.id = 'onboarding-backdrop';
    backdrop.className = 'modal-backdrop';
    backdrop.onclick = () => {}; // Don't close on backdrop click

    // Create modal
    const modal = document.createElement('div');
    modal.id = 'onboarding-modal';
    modal.className = 'modal';
    modal.style.maxWidth = '600px';
    modal.innerHTML = `
      <div class="modal-header">
        <h3 class="modal-title">Welcome to MinouChat</h3>
        <button class="modal-close" onclick="OnboardingManager.skip()" title="Skip">
          <svg viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div class="modal-body" id="onboarding-content">
        <!-- Content rendered here -->
      </div>
      <div class="modal-footer" id="onboarding-footer">
        <!-- Footer rendered here -->
      </div>
    `;

    document.body.appendChild(backdrop);
    document.body.appendChild(modal);
  },

  /**
   * Render the current step content
   */
  renderStep() {
    const content = document.getElementById('onboarding-content');
    const footer = document.getElementById('onboarding-footer');

    // Update step indicators
    const stepsHtml = this.renderStepIndicators();

    switch (this.currentStep) {
      case 0:
        // Welcome Step
        content.innerHTML = `
          ${stepsHtml}
          <div class="wizard-content">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--text-primary)" stroke-width="1" style="margin-bottom: var(--space-4)">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <h2 class="wizard-title">Welcome, ${this.escapeHtml(this.username)}!</h2>
            <p class="wizard-description">
              MinouChat is your private AI assistant platform. Create personalized AI personas,
              chat with context from your documents, and keep your conversations private.
            </p>
          </div>
        `;
        footer.innerHTML = `
          <span class="skip-link" onclick="OnboardingManager.skip()">Skip setup</span>
          <button class="btn btn-primary" onclick="OnboardingManager.nextStep()">
            Get Started
          </button>
        `;
        break;

      case 1:
        // LLM Configuration Step (NEW)
        content.innerHTML = `
          ${stepsHtml}
          <div class="wizard-content">
            <h2 class="wizard-title">Configure Your AI</h2>
            <p class="wizard-description">
              Choose an AI provider to power your conversations. You'll need an API key.
            </p>
            <div class="provider-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3); margin-top: var(--space-4); text-align: left;">
              ${this.renderProviderCards()}
            </div>
            <div id="llm-api-key-section" style="display: ${this.selectedProvider ? 'block' : 'none'}; margin-top: var(--space-4);">
              <div class="form-group">
                <label class="form-label">API Key for <span id="selected-provider-name">${this.selectedProvider || ''}</span></label>
                <div style="display: flex; gap: var(--space-2);">
                  <input type="password" class="form-input" id="onboarding-api-key" placeholder="Enter your API key" style="flex: 1;">
                  <button class="btn btn-secondary" onclick="OnboardingManager.testApiKey()" id="test-key-btn">
                    Test
                  </button>
                </div>
              </div>
              <div id="api-test-result" style="margin-top: var(--space-2); font-size: var(--text-sm);"></div>
            </div>
            <p class="text-sm text-muted" style="margin-top: var(--space-4);">
              Don't have an API key? <a href="https://openrouter.ai/keys" target="_blank" style="color: var(--pop-primary);">Get one from OpenRouter</a> (recommended)
            </p>
          </div>
        `;
        footer.innerHTML = `
          <button class="btn btn-secondary" onclick="OnboardingManager.prevStep()">Back</button>
          <button class="btn btn-primary" onclick="OnboardingManager.nextStep()" id="llm-next-btn" ${!this.llmConfigured ? 'disabled' : ''}>
            Continue
          </button>
        `;
        break;

      case 2:
        // Persona Selection Step
        content.innerHTML = `
          ${stepsHtml}
          <div class="wizard-content">
            <h2 class="wizard-title">Choose a Persona</h2>
            <p class="wizard-description">
              Select an AI persona to start chatting with. You can create your own later.
            </p>
            <div class="persona-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--space-4); margin-top: var(--space-6); text-align: left;">
              ${this.renderPersonaCards()}
            </div>
          </div>
        `;
        footer.innerHTML = `
          <button class="btn btn-secondary" onclick="OnboardingManager.prevStep()">Back</button>
          <button class="btn btn-primary" onclick="OnboardingManager.nextStep()" ${!this.selectedPersonaId ? 'disabled' : ''}>
            Continue
          </button>
        `;
        break;

      case 3:
        // Completion Step
        const persona = this.personas.find(p => p.id === this.selectedPersonaId);
        content.innerHTML = `
          ${stepsHtml}
          <div class="wizard-content">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--pop-success)" stroke-width="1" style="margin-bottom: var(--space-4)">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <h2 class="wizard-title">You're All Set!</h2>
            <p class="wizard-description">
              ${persona ? `Start chatting with <strong>${this.escapeHtml(persona.name)}</strong>. You can switch personas anytime from the sidebar.` : 'Click below to start chatting.'}
            </p>
            <div style="margin-top: var(--space-4);">
              <p class="text-sm text-muted">Quick tips:</p>
              <ul style="text-align: left; color: var(--text-secondary); font-size: var(--text-sm); margin: var(--space-2) 0; padding-left: var(--space-6);">
                <li>Upload documents to give your AI context</li>
                <li>Create custom personas from the Personas page</li>
                <li>Your conversations stay private on your device</li>
              </ul>
            </div>
          </div>
        `;
        footer.innerHTML = `
          <button class="btn btn-secondary" onclick="OnboardingManager.prevStep()">Back</button>
          <button class="btn btn-pop" onclick="OnboardingManager.complete()">
            Start Chatting
          </button>
        `;
        break;
    }
  },

  /**
   * Render provider selection cards
   */
  renderProviderCards() {
    const providers = [
      { id: 'openrouter', name: 'OpenRouter', desc: '100+ models', recommended: true },
      { id: 'openai', name: 'OpenAI', desc: 'GPT-4, GPT-4o' },
      { id: 'anthropic', name: 'Anthropic', desc: 'Claude 3.5' }
    ];

    return providers.map(p => {
      const isSelected = this.selectedProvider === p.id;
      return `
        <div class="card card-clickable provider-card ${isSelected ? 'selected' : ''}"
             onclick="OnboardingManager.selectProvider('${p.id}')"
             style="padding: var(--space-3); text-align: center; cursor: pointer; ${isSelected ? 'border-color: var(--pop-primary);' : ''}">
          <div style="font-weight: 500; margin-bottom: 4px;">${p.name}</div>
          <div class="text-sm text-muted">${p.desc}</div>
          ${p.recommended ? '<div style="font-size: 10px; color: var(--pop-primary); margin-top: 4px;">Recommended</div>' : ''}
        </div>
      `;
    }).join('');
  },

  /**
   * Select an LLM provider
   */
  selectProvider(providerId) {
    this.selectedProvider = providerId;
    this.llmConfigured = false;  // Reset until API key is tested
    this.renderStep();
  },

  /**
   * Test API key with selected provider
   */
  async testApiKey() {
    const apiKey = document.getElementById('onboarding-api-key').value.trim();
    const resultEl = document.getElementById('api-test-result');
    const testBtn = document.getElementById('test-key-btn');
    const nextBtn = document.getElementById('llm-next-btn');

    if (!apiKey) {
      resultEl.innerHTML = '<span style="color: var(--pop-danger);">Please enter an API key</span>';
      return;
    }

    testBtn.disabled = true;
    testBtn.textContent = 'Testing...';
    resultEl.innerHTML = '<span style="color: var(--text-muted);">Connecting...</span>';

    try {
      const response = await fetch('/api/settings/llm/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: this.selectedProvider,
          config: { api_key: apiKey }
        })
      });

      const result = await response.json();

      if (result.success) {
        this.llmConfigured = true;
        resultEl.innerHTML = '<span style="color: var(--pop-success);">Connected successfully!</span>';
        nextBtn.disabled = false;

        // Save the configuration
        await this.saveLLMConfig(apiKey);
      } else {
        resultEl.innerHTML = `<span style="color: var(--pop-danger);">Failed: ${result.message || 'Connection error'}</span>`;
        nextBtn.disabled = true;
      }
    } catch (e) {
      console.error('API test error:', e);
      resultEl.innerHTML = '<span style="color: var(--pop-danger);">Connection error. Please try again.</span>';
      nextBtn.disabled = true;
    }

    testBtn.disabled = false;
    testBtn.textContent = 'Test';
  },

  /**
   * Save LLM configuration
   */
  async saveLLMConfig(apiKey) {
    try {
      const credentials = {};
      credentials[`${this.selectedProvider}_api_key`] = apiKey;

      await fetch('/api/settings/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: this.selectedProvider,
          ...credentials
        })
      });

      localStorage.setItem(this.LLM_CONFIGURED_KEY, 'true');
    } catch (e) {
      console.error('Failed to save LLM config:', e);
    }
  },

  /**
   * Render step indicator dots
   */
  renderStepIndicators() {
    let html = '<div class="wizard-steps">';
    for (let i = 0; i < this.totalSteps; i++) {
      const classes = ['wizard-step'];
      if (i < this.currentStep) classes.push('completed');
      if (i === this.currentStep) classes.push('active');
      html += `<div class="${classes.join(' ')}"></div>`;
    }
    html += '</div>';
    return html;
  },

  /**
   * Render persona selection cards
   */
  renderPersonaCards() {
    if (!this.personas || this.personas.length === 0) {
      return '<p class="text-muted text-center">No personas available. You can create one later.</p>';
    }

    // Show only first 4 personas
    const displayPersonas = this.personas.slice(0, 4);

    return displayPersonas.map(persona => {
      const isSelected = this.selectedPersonaId === persona.id;
      return `
        <div class="card card-clickable ${isSelected ? 'selected' : ''}"
             onclick="OnboardingManager.selectPersona('${persona.id}')"
             style="padding: var(--space-4); ${isSelected ? 'border-color: var(--pop-primary);' : ''}">
          <div class="card-title" style="font-size: var(--text-base);">${this.escapeHtml(persona.name)}</div>
          <div class="text-sm text-muted">${this.escapeHtml(persona.category || 'General')}</div>
          <p class="text-sm text-secondary mt-2" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            ${this.escapeHtml(persona.personality || '').substring(0, 80)}...
          </p>
        </div>
      `;
    }).join('');
  },

  /**
   * Select a persona
   */
  selectPersona(personaId) {
    this.selectedPersonaId = personaId;
    this.renderStep(); // Re-render to update selection
  },

  /**
   * Open the modal
   */
  openModal() {
    const backdrop = document.getElementById('onboarding-backdrop');
    const modal = document.getElementById('onboarding-modal');
    if (backdrop) backdrop.classList.add('show');
    if (modal) modal.classList.add('show');
    document.body.style.overflow = 'hidden';
  },

  /**
   * Close the modal
   */
  closeModal() {
    const backdrop = document.getElementById('onboarding-backdrop');
    const modal = document.getElementById('onboarding-modal');
    if (backdrop) backdrop.classList.remove('show');
    if (modal) modal.classList.remove('show');
    document.body.style.overflow = '';

    // Remove after animation
    setTimeout(() => {
      if (backdrop) backdrop.remove();
      if (modal) modal.remove();
    }, 300);
  },

  /**
   * Initialize contextual hints
   */
  initHints() {
    const dismissed = JSON.parse(localStorage.getItem(this.HINTS_KEY) || '[]');

    // Show hints that haven't been dismissed
    document.querySelectorAll('[data-hint]').forEach(element => {
      const hintId = element.dataset.hint;
      if (!dismissed.includes(hintId)) {
        this.showHint(element, hintId);
      }
    });
  },

  /**
   * Show a contextual hint
   */
  showHint(element, hintId) {
    const hintText = element.dataset.hintText || '';
    if (!hintText) return;

    const hint = document.createElement('div');
    hint.className = 'hint-tooltip';
    hint.innerHTML = `
      <span>${this.escapeHtml(hintText)}</span>
      <button class="hint-dismiss" onclick="OnboardingManager.dismissHint('${hintId}', this.parentElement)">Got it</button>
    `;

    // Position hint
    hint.style.cssText = `
      position: absolute;
      background: var(--bg-inverse);
      color: var(--text-inverse);
      padding: var(--space-2) var(--space-3);
      border-radius: var(--radius-md);
      font-size: var(--text-sm);
      z-index: 1000;
      display: flex;
      align-items: center;
      gap: var(--space-2);
      white-space: nowrap;
      animation: fadeIn 0.3s ease;
    `;

    element.style.position = 'relative';
    element.appendChild(hint);
  },

  /**
   * Dismiss a hint
   */
  dismissHint(hintId, element) {
    const dismissed = JSON.parse(localStorage.getItem(this.HINTS_KEY) || '[]');
    if (!dismissed.includes(hintId)) {
      dismissed.push(hintId);
      localStorage.setItem(this.HINTS_KEY, JSON.stringify(dismissed));
    }
    if (element) element.remove();
  },

  /**
   * Escape HTML for safe rendering
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
};

// Add hint dismiss button styles
const hintStyles = document.createElement('style');
hintStyles.textContent = `
  .hint-dismiss {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.3);
    color: inherit;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
  }
  .hint-dismiss:hover {
    background: rgba(255,255,255,0.1);
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .card.selected {
    border-color: var(--pop-primary) !important;
    background: rgba(59, 130, 246, 0.05);
  }
`;
document.head.appendChild(hintStyles);

// Export for use in other scripts
window.OnboardingManager = OnboardingManager;
