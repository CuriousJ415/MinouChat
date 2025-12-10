# MiaChat Document & RAG System Testing Guide

## 🚀 Quick Start Testing

### 1. Start the System
```bash
# Install new dependencies first
pip install -r requirements.txt

# Start MiaChat
./start.sh
# or
docker compose up -d
```

### 2. Access the Interface
- Open http://localhost:8080
- Login or register an account
- Navigate to **Dashboard** → **Manage Documents**

## 📋 Manual Testing Scenarios

### Scenario 1: Document Upload & Processing
**Expected User Experience:**
1. **Upload Documents**
   - Go to `/documents` page
   - Drag & drop or click to upload files
   - See upload progress and success messages
   - Documents appear in "Your Documents" section

2. **Supported Formats Test**
   - Upload a PDF document
   - Upload a Word document (.docx)
   - Upload an Excel spreadsheet (.xlsx)
   - Upload a text file (.txt)
   - All should process successfully and show "completed" status

3. **Processing Status**
   - Newly uploaded docs show "processing" → "completed"
   - Failed docs show "failed" status with retry option

### Scenario 2: Document Search
**Expected User Experience:**
1. **Vector Search**
   - Upload a document with specific content
   - Use search box to find relevant passages
   - See similarity scores and highlighted excerpts
   - Results should be semantically relevant, not just keyword matches

2. **Search Quality Test**
   - Search for concepts, not exact phrases
   - Example: Upload a business plan, search "revenue strategy"
   - Should find relevant sections even if exact phrase isn't used

### Scenario 3: RAG-Enhanced Conversations
**Expected User Experience:**
1. **Document-Aware Chat**
   - Upload a document (e.g., company policy, personal notes)
   - Go to `/chat` and start conversation with any character
   - Ask questions related to uploaded content
   - Character should reference document information in responses

2. **Source Citations**
   - Character responses should mention document sources
   - Look for phrases like "Based on your document..." or "According to..."
   - Response metadata should show `document_context_used: true`

3. **Cross-Character Awareness**
   - Upload document while chatting with Sage
   - Switch to Mia (Personal Assistant)
   - Ask about same topic - Mia should also have access to document

### Scenario 4: Document Management
**Expected User Experience:**
1. **View Document Content**
   - Click "..." menu on any document
   - Select "View Content" 
   - See extracted text in modal popup

2. **Delete Documents**
   - Delete a document
   - Verify it's removed from list
   - Verify it no longer appears in search or chat context

3. **Statistics Updates**
   - Upload/delete documents
   - Statistics panel should update automatically
   - Shows total docs, processed count, file size

## 🔍 Testing Different File Types

### PDF Testing
- Upload a research paper or report
- Test text extraction quality
- Verify page boundaries are preserved

### Excel/CSV Testing  
- Upload spreadsheet with data
- Test if column headers and data are extracted
- Search for specific data points

### Word Document Testing
- Upload document with tables and formatting
- Verify text and table content extraction
- Test with different Word versions (.doc vs .docx)

## 🤖 Expected Character Behaviors

### Sage (Coach) with Documents
- Should integrate business documents into coaching advice
- Reference specific metrics, strategies from uploaded files
- Provide context-aware recommendations

### Mia (Personal Assistant) with Documents
- Should help organize and reference personal documents
- Assist with task management based on uploaded schedules
- Provide summaries of document content

## 🚨 Error Scenarios to Test

### File Upload Errors
- Try uploading unsupported format (e.g., .exe file)
- Upload file larger than 50MB
- Upload corrupted file

### Processing Failures
- Monitor for documents stuck in "processing" status
- Test reprocess functionality for failed documents

### Search Edge Cases
- Search with very short queries
- Search for content that doesn't exist
- Search with special characters

## 📊 Performance Expectations

### Upload Performance
- Small files (< 1MB): Process within 10 seconds
- Medium files (1-10MB): Process within 30 seconds
- Large files (10-50MB): Process within 2 minutes

### Search Performance
- Search queries should return results within 2 seconds
- Should handle up to 100 documents efficiently

### Chat Response Time
- RAG-enhanced responses: 3-10 seconds (depending on model)
- Should be only 1-2 seconds slower than non-RAG responses

## 🎯 Success Criteria

### ✅ Document Upload Success
- [ ] All supported formats upload successfully
- [ ] Processing completes without errors
- [ ] Extracted text is readable and complete
- [ ] File metadata is captured correctly

### ✅ Search Functionality Success  
- [ ] Semantic search finds relevant content
- [ ] Similarity scores are reasonable (> 0.3 for good matches)
- [ ] Search results include proper context
- [ ] No search results for irrelevant queries

### ✅ RAG Integration Success
- [ ] Character responses include document context
- [ ] Sources are properly cited
- [ ] Context remains relevant to conversation
- [ ] All characters can access user documents

### ✅ User Interface Success
- [ ] Upload progress shows correctly
- [ ] Document list updates in real-time
- [ ] Statistics reflect current state
- [ ] Error messages are clear and helpful

## 🐛 Common Issues & Troubleshooting

### "Processing Failed" Status
- Check Docker logs: `docker compose logs -f`
- Verify dependencies are installed
- Try reprocessing the document

### Search Returns No Results
- Check if documents finished processing
- Verify FAISS index was created
- Try rebuilding index: `/api/documents/admin/rebuild-index`

### Characters Don't Reference Documents
- Verify `use_documents: true` in chat request
- Check if documents contain relevant content
- Look for similarity threshold issues

### Slow Performance
- Check Docker resources (CPU/Memory)
- Monitor embedding model loading time
- Consider smaller models for faster processing

## 📈 Advanced Testing

### Load Testing
- Upload 50+ documents simultaneously
- Test search with large document corpus
- Monitor memory usage during processing

### Accuracy Testing
- Create documents with known content
- Ask specific questions and verify accuracy
- Test edge cases (very technical content, multiple languages)

### Integration Testing
- Test with different LLM providers (Ollama vs cloud)
- Verify privacy modes work correctly
- Test with various model configurations