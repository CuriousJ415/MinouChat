/**
 * MinouChat Onboarding Manager
 * Handles welcome wizard and contextual hints for new users
 */

const OnboardingManager = {
  STORAGE_KEY: 'minouchat-onboarding-complete',
  HINTS_KEY: 'minouchat-hints-dismissed',

  currentStep: 0,
  totalSteps: 3,
  selectedPersonaId: null,
  personas: [],

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

      case 2:
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
