/**
 * Document management system for MIAAI
 * Handles document upload, listing, preview, and operations
 */

class DocumentManager {
    constructor(app) {
        this.app = app;
        this.documents = [];
        this.currentDocument = null;
        
        // DOM elements
        this.documentManagerModal = document.getElementById('document-manager-modal');
        this.documentPreviewModal = document.getElementById('document-preview-modal');
        this.documentUploadForm = document.getElementById('document-upload-form');
        this.documentCharacterSelect = document.getElementById('document-character');
        this.documentFilterCharacter = document.getElementById('document-filter-character');
        this.documentSearchInput = document.getElementById('document-search');
        this.documentList = document.getElementById('document-list');
        this.documentPreviewTitle = document.getElementById('document-preview-title');
        this.documentPreviewContent = document.getElementById('document-preview-content');
        this.documentExtractBtn = document.getElementById('document-extract-btn');
        this.documentSummarizeBtn = document.getElementById('document-summarize-btn');
        this.documentDeleteBtn = document.getElementById('document-delete-btn');
        this.documentButton = app.documentButton;
        
        // Tab elements
        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
        
        // Bind events
        this.bindEvents();
        
        // Initialize
        this.populateCharacterDropdowns();
    }
    
    bindEvents() {
        // Open document manager modal with the document button
        if (this.documentButton) {
            this.documentButton.addEventListener('click', () => {
                this.showModal(this.documentManagerModal);
                this.loadDocuments();
            });
        }
        
        // Close buttons for modals
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.hideModal(e.target.closest('.modal'));
            });
        });
        
        // Tab switching
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });
        
        // Document upload form submission
        this.documentUploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadDocument();
        });
        
        // Document filter change
        this.documentFilterCharacter.addEventListener('change', () => {
            this.filterDocuments();
        });
        
        // Document search
        this.documentSearchInput.addEventListener('input', () => {
            this.filterDocuments();
        });
        
        // Document actions
        this.documentExtractBtn.addEventListener('click', () => {
            this.extractToMemory();
        });
        
        this.documentSummarizeBtn.addEventListener('click', () => {
            this.summarizeDocument();
        });
        
        this.documentDeleteBtn.addEventListener('click', () => {
            this.deleteDocument();
        });
    }
    
    populateCharacterDropdowns() {
        // Clear existing options
        while (this.documentCharacterSelect.options.length > 1) {
            this.documentCharacterSelect.remove(1);
        }
        
        while (this.documentFilterCharacter.options.length > 1) {
            this.documentFilterCharacter.remove(1);
        }
        
        // Add options for each character
        if (this.app.characters) {
            this.app.characters.forEach(character => {
                // For document upload
                const uploadOption = document.createElement('option');
                uploadOption.value = character.id;
                uploadOption.textContent = character.name;
                this.documentCharacterSelect.appendChild(uploadOption);
                
                // For document filter
                const filterOption = document.createElement('option');
                filterOption.value = character.id;
                filterOption.textContent = character.name;
                this.documentFilterCharacter.appendChild(filterOption);
            });
        }
    }
    
    showModal(modal) {
        modal.style.display = 'block';
    }
    
    hideModal(modal) {
        modal.style.display = 'none';
    }
    
    switchTab(tabName) {
        // Update tab buttons
        this.tabBtns.forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Update tab contents
        this.tabContents.forEach(content => {
            if (content.id === `${tabName}-tab`) {
                content.style.display = 'block';
            } else {
                content.style.display = 'none';
            }
        });
    }
    
    async loadDocuments() {
        try {
            const response = await fetch('/api/documents');
            
            if (!response.ok) {
                throw new Error(`Failed to load documents: ${response.status}`);
            }
            
            const data = await response.json();
            this.documents = data;
            this.renderDocumentList();
        } catch (error) {
            console.error('Error loading documents:', error);
            this.showError('Failed to load documents. Please try again.');
        }
    }
    
    renderDocumentList() {
        // Clear the list
        this.documentList.innerHTML = '';
        
        // Filter documents based on current filters
        const filteredDocs = this.filterDocumentsData();
        
        if (filteredDocs.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state';
            emptyState.textContent = 'No documents found';
            this.documentList.appendChild(emptyState);
            return;
        }
        
        // Add each document to the list
        filteredDocs.forEach(doc => {
            const docItem = document.createElement('div');
            docItem.className = 'document-item';
            docItem.dataset.id = doc.id;
            
            // Determine icon based on file type
            let iconClass = 'fas fa-file';
            if (doc.doc_type === 'pdf') {
                iconClass = 'fas fa-file-pdf';
            } else if (doc.doc_type === 'txt') {
                iconClass = 'fas fa-file-alt';
            } else if (doc.doc_type === 'md') {
                iconClass = 'fas fa-file-code';
            } else if (doc.doc_type === 'docx') {
                iconClass = 'fas fa-file-word';
            }
            
            // Get character name if associated
            let characterName = 'None';
            if (doc.character_id) {
                const character = this.app.characters.find(c => c.id === doc.character_id);
                if (character) {
                    characterName = character.name;
                }
            }
            
            // Format date
            const uploadDate = new Date(doc.upload_date).toLocaleDateString();
            
            docItem.innerHTML = `
                <div class="document-icon">
                    <i class="${iconClass}"></i>
                </div>
                <div class="document-details">
                    <div class="document-name">${doc.filename}</div>
                    <div class="document-meta">
                        <span>${doc.doc_type.toUpperCase()}</span> • 
                        <span>Character: ${characterName}</span> • 
                        <span>Uploaded: ${uploadDate}</span>
                    </div>
                </div>
            `;
            
            // Add click event to preview document
            docItem.addEventListener('click', () => {
                this.previewDocument(doc.id);
            });
            
            this.documentList.appendChild(docItem);
        });
    }
    
    filterDocumentsData() {
        const characterFilter = this.documentFilterCharacter.value;
        const searchFilter = this.documentSearchInput.value.toLowerCase();
        
        return this.documents.filter(doc => {
            // Apply character filter
            if (characterFilter && doc.character_id !== characterFilter) {
                return false;
            }
            
            // Apply search filter
            if (searchFilter && !doc.filename.toLowerCase().includes(searchFilter)) {
                return false;
            }
            
            return true;
        });
    }
    
    filterDocuments() {
        this.renderDocumentList();
    }
    
    async uploadDocument() {
        // Get form data
        const formData = new FormData(this.documentUploadForm);
        
        // Debug logging
        console.log("Uploading document...");
        console.log("Form data entries:");
        for (let [key, value] of formData.entries()) {
            console.log(`${key}: ${value instanceof File ? value.name : value}`);
        }
        
        try {
            // Show loading state
            this.documentUploadForm.querySelector('button[type="submit"]').disabled = true;
            this.documentUploadForm.querySelector('button[type="submit"]').textContent = 'Uploading...';
            
            // The API endpoint is just /api/documents
            console.log("Sending request to /api/documents");
            const response = await fetch('/api/documents', {
                method: 'POST',
                body: formData
            });
            
            console.log("Response status:", response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                throw new Error(`Upload failed: ${response.status} - ${errorText}`);
            }
            
            const result = await response.json();
            console.log("Upload successful, result:", result);
            
            // Reset form
            this.documentUploadForm.reset();
            
            // Show success message with instructions
            const characterId = formData.get('character_id');
            let message = 'Document uploaded successfully.';
            
            if (characterId) {
                // Find character name
                const character = this.app.characters.find(c => c.id === characterId);
                if (character) {
                    message += ` The document is now available to ${character.name}. You can ask questions about the document in your chat.`;
                } else {
                    message += ` The document is now associated with your character. You can ask questions about the document in your chat.`;
                }
            } else {
                message += ' To use this document, you need to extract it to a character\'s memory.';
            }
            
            this.showSuccess(message);
            
            // Refresh document list
            this.loadDocuments();
            
            // Switch to library tab
            this.switchTab('library');
        } catch (error) {
            console.error('Error uploading document:', error);
            this.showError('Failed to upload document: ' + error.message);
        } finally {
            // Reset button state
            this.documentUploadForm.querySelector('button[type="submit"]').disabled = false;
            this.documentUploadForm.querySelector('button[type="submit"]').textContent = 'Upload Document';
        }
    }
    
    async previewDocument(documentId) {
        try {
            const response = await fetch(`/api/documents/${documentId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load document: ${response.status}`);
            }
            
            const document = await response.json();
            this.currentDocument = document;
            
            // Set document title
            this.documentPreviewTitle.textContent = document.filename;
            
            // Set document content
            if (document.text_content) {
                // Wrap in pre tag to preserve formatting
                this.documentPreviewContent.innerHTML = `<pre>${document.text_content}</pre>`;
            } else {
                this.documentPreviewContent.textContent = 'Content preview not available';
            }
            
            // Show preview modal
            this.showModal(this.documentPreviewModal);
            
            // Enable/disable extract button based on whether a character is selected
            this.documentExtractBtn.disabled = !this.app.selectedCharacter;
        } catch (error) {
            console.error('Error previewing document:', error);
            this.showError('Failed to load document preview. Please try again.');
        }
    }
    
    async extractToMemory() {
        if (!this.currentDocument || !this.app.selectedCharacter) {
            this.showError('Please select a character before extracting to memory');
            return;
        }
        
        try {
            // Show loading state
            this.documentExtractBtn.disabled = true;
            this.documentExtractBtn.textContent = 'Extracting...';
            
            const docId = this.currentDocument.id;
            const charId = this.app.selectedCharacter.id;
            
            console.log(`Extracting document ${docId} to memory for character ${charId}`);
            
            // Use the new simpler endpoint with JSON payload
            const response = await fetch('/api/documents/extract-memory', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_id: docId,
                    character_id: charId
                })
            });
            
            // Log raw response for debugging
            const responseText = await response.text();
            console.log("Extract response text:", responseText);
            
            let result;
            try {
                result = JSON.parse(responseText);
                console.log("Parsed response:", result);
            } catch (e) {
                console.error("Failed to parse JSON:", e);
                result = { success: false, error: "Invalid response format" };
            }
            
            if (response.ok && result.success) {
                this.showSuccess('Document extracted to memory successfully. You can now ask questions about this document in chat.');
                this.hideModal(this.documentPreviewModal);
            } else {
                const errorMsg = result.error || `Failed to extract document (${response.status})`;
                throw new Error(errorMsg);
            }
        } catch (error) {
            console.error('Error extracting to memory:', error);
            this.showError(error.message || 'Failed to extract to memory');
        } finally {
            // Reset button state
            this.documentExtractBtn.disabled = false;
            this.documentExtractBtn.textContent = 'Extract to Memory';
        }
    }
    
    async summarizeDocument() {
        if (!this.currentDocument) {
            return;
        }
        
        try {
            // Disable button and show loading state
            this.documentSummarizeBtn.disabled = true;
            this.documentSummarizeBtn.textContent = 'Summarizing...';
            
            const docId = this.currentDocument.id;
            const charId = this.app.selectedCharacter ? this.app.selectedCharacter.id : '';
            
            console.log(`Summarizing document ${docId} for character ${charId || 'none'}`);
            
            // Use the new simpler endpoint with JSON payload
            const response = await fetch('/api/documents/summarize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_id: docId,
                    character_id: charId
                })
            });
            
            // Log raw response for debugging
            const responseText = await response.text();
            console.log("Summary response text:", responseText);
            
            let result;
            try {
                result = JSON.parse(responseText);
                console.log("Parsed summary response:", result);
            } catch (e) {
                console.error("Failed to parse summary JSON:", e);
                result = { success: false, error: "Invalid response format" };
            }
            
            if (response.ok && result.success && result.summary) {
                // Get the summary text
                const summary = String(result.summary);
                
                // Sanitize the summary for display by escaping HTML and converting newlines
                const sanitizedSummary = summary
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;')
                    .replace(/\n/g, '<br>');
                    
                this.documentPreviewContent.innerHTML = `<div class="summary-content">${sanitizedSummary}</div>`;
                this.showSuccess('Document summarized successfully');
            } else {
                const errorMsg = result.error || `Failed to summarize document (${response.status})`;
                this.documentPreviewContent.textContent = 'Failed to generate summary: ' + errorMsg;
                throw new Error(errorMsg);
            }
        } catch (error) {
            console.error('Error summarizing document:', error);
            this.showError(error.message || 'Failed to summarize document');
        } finally {
            // Reset button state
            this.documentSummarizeBtn.disabled = false;
            this.documentSummarizeBtn.textContent = 'Summarize with AI';
        }
    }
    
    async deleteDocument() {
        if (!this.currentDocument) {
            return;
        }
        
        if (!confirm(`Are you sure you want to delete "${this.currentDocument.filename}"?`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/documents/${this.currentDocument.id}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`Failed to delete document: ${response.status}`);
            }
            
            this.showSuccess('Document deleted successfully');
            
            // Close the preview modal
            this.hideModal(this.documentPreviewModal);
            
            // Refresh document list
            this.loadDocuments();
        } catch (error) {
            console.error('Error deleting document:', error);
            this.showError('Failed to delete document. Please try again.');
        }
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    showToast(message, type) {
        const toast = document.getElementById(`${type}-toast`);
        const messageElement = document.getElementById(`${type}-message`);
        
        messageElement.textContent = message;
        toast.style.opacity = '1';
        
        // Success messages stay visible longer
        const displayTime = type === 'success' ? 5000 : 3000;
        
        setTimeout(() => {
            toast.style.opacity = '0';
        }, displayTime);
    }
    
    // Update the selectCharacter method to enable the document button
    updateUIForSelectedCharacter() {
        if (this.documentButton && this.app.selectedCharacter) {
            this.documentButton.disabled = false;
        }
    }
}

// Do not initialize here - will be initialized from main app.js 