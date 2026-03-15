# OnboardAI — Product Requirements Document

## 1. Overview

### 1.1 Product Summary

OnboardAI is an AI-powered employee onboarding assistant that lets companies upload internal documents (handbooks, SOPs, process docs) and provides new hires with a chat interface to ask natural language questions and receive accurate, cited answers grounded in those documents.

### 1.2 Problem Statement

New employees spend their first weeks digging through scattered documents trying to understand company processes, tools, and policies. Answers are buried in PDFs, Word docs, and wiki pages. The result: slow ramp-up, repetitive questions to managers, and frustration on all sides.

### 1.3 Solution

A RAG (Retrieval-Augmented Generation) application that ingests company documents, indexes them semantically, and serves a chat interface where users can ask questions and get instant, accurate answers with citations pointing back to the source material.

### 1.4 Target Users

- **Admins:** Upload and manage the document corpus. Could be HR, ops, or team leads.
- **New Hires:** Ask questions about company processes, policies, tools, and culture.

### 1.5 Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React + Vite + Tailwind CSS | Fast dev, component-based, easy to deploy |
| Backend | Python / FastAPI | Best AI/ML ecosystem, async support, auto-generated docs |
| Embeddings | OpenAI `text-embedding-3-small` | Cheap ($0.02/1M tokens), high quality, 1536 dimensions |
| LLM | OpenAI `gpt-4o-mini` | Cheapest capable model ($0.15/$0.60 per 1M tokens) |
| Vector Store | ChromaDB (local) | Zero infrastructure, free, good enough for demo/small scale |
| File Storage | Local filesystem | Simple for v1; can swap to S3 later |

---

## 2. Architecture & Technical Spec

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│                                                             │
│   React Frontend (Vite + Tailwind)                          │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐             │
│   │ Upload   │  │ Chat     │  │ Source        │             │
│   │ Panel    │  │ Interface│  │ Viewer        │             │
│   └──────────┘  └──────────┘  └──────────────┘             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST (JSON)
┌────────────────────────▼────────────────────────────────────┐
│                      API LAYER                              │
│                                                             │
│   FastAPI Server                                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐             │
│   │ /ingest  │  │ /query   │  │ /documents   │             │
│   └──────────┘  └──────────┘  └──────────────┘             │
└────────┬───────────────┬───────────────┬────────────────────┘
         │               │               │
┌────────▼───────┐ ┌─────▼──────┐ ┌──────▼───────────────────┐
│  PROCESSING    │ │  RETRIEVAL │ │  EXTERNAL APIs           │
│                │ │            │ │                           │
│  Doc Processor │ │  ChromaDB  │ │  OpenAI Embeddings API   │
│  Text Chunker  │ │  (local)   │ │  OpenAI Chat API         │
└────────────────┘ └────────────┘ └───────────────────────────┘
```

### 2.2 Project Structure

```
onboard-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app, CORS, lifespan
│   │   ├── config.py              # Settings from .env
│   │   ├── models.py              # Pydantic request/response models
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ingest.py          # POST /api/ingest
│   │   │   ├── query.py           # POST /api/query
│   │   │   └── documents.py       # GET /api/documents, DELETE
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── document_processor.py
│   │   │   ├── chunker.py
│   │   │   ├── embeddings.py
│   │   │   ├── vector_store.py
│   │   │   ├── retriever.py
│   │   │   └── generator.py
│   │   └── utils/
│   │       └── file_helpers.py
│   ├── uploads/                   # Uploaded files stored here
│   ├── chroma_data/               # ChromaDB persistence
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── ChatMessage.jsx
│   │   │   ├── UploadPanel.jsx
│   │   │   ├── DocumentList.jsx
│   │   │   ├── SourceCard.jsx
│   │   │   ├── SuggestedQuestions.jsx
│   │   │   └── Layout.jsx
│   │   ├── hooks/
│   │   │   ├── useChat.js
│   │   │   └── useDocuments.js
│   │   ├── services/
│   │   │   └── api.js
│   │   └── styles/
│   │       └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── PRD.md
└── README.md
```

### 2.3 Data Flows

#### Document Ingestion Flow

1. User uploads file(s) via the Upload Panel (PDF, DOCX, MD, TXT)
2. Frontend sends `POST /api/ingest` with multipart form data
3. Backend saves the original file to `uploads/` directory
4. Document Processor extracts raw text based on file type
5. Chunker splits text into overlapping chunks with metadata
6. Embeddings service sends chunks to OpenAI API, receives vectors
7. Vector Store writes chunks + vectors + metadata to ChromaDB
8. Backend responds with ingestion summary (chunk count, doc ID)

#### Query Flow

1. User types a question in the Chat Interface
2. Frontend sends `POST /api/query` with question + conversation history
3. Backend embeds the question via OpenAI Embeddings API
4. Retriever performs similarity search in ChromaDB (top-k chunks)
5. Retriever filters results below relevance threshold
6. Generator builds a prompt with: system instructions, retrieved chunks, conversation history, and the question
7. Generator calls OpenAI Chat API and receives the answer
8. Backend responds with the answer + source citations
9. Frontend renders the answer with clickable source references

### 2.4 Configuration

All configuration is loaded from environment variables via a `.env` file.

```
OPENAI_API_KEY=sk-...              # Required
CHROMA_PERSIST_DIR=./chroma_data   # Where ChromaDB stores data
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini
CHUNK_SIZE=500                     # Target chunk size in characters
CHUNK_OVERLAP=50                   # Overlap between chunks in characters
TOP_K=5                            # Number of chunks to retrieve per query
RELEVANCE_THRESHOLD=0.3            # Minimum cosine similarity score (0-1)
UPLOAD_DIR=./uploads               # Where original files are stored
MAX_FILE_SIZE_MB=20                # Maximum upload file size
```

---

## 3. Data Models & Schemas

### 3.1 Internal Data Models

#### ProcessedDocument

Represents a document after text extraction, before chunking.

```python
@dataclass
class ProcessedDocument:
    text: str               # Full extracted text
    metadata: dict          # filename, file_type, page_count, word_count, char_count
```

#### Chunk

A single chunk of text ready for embedding and storage.

```python
@dataclass
class Chunk:
    id: str                 # Unique ID: "{doc_id}_chunk_{index}"
    text: str               # The chunk content
    doc_id: str             # Parent document ID
    chunk_index: int        # Position in original document (0-based)
    metadata: dict          # filename, file_type, section_header (if detected),
                            # char_start, char_end
```

#### RetrievedChunk

A chunk returned from similarity search, with its relevance score.

```python
@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float            # Cosine similarity score (0.0 - 1.0)
```

#### QueryResult

The final response returned to the frontend after answer generation.

```python
@dataclass
class QueryResult:
    answer: str             # Generated answer text
    sources: list[Source]   # List of source citations
    query: str              # Original question (echoed back)
```

#### Source

A citation reference attached to an answer.

```python
@dataclass
class Source:
    doc_id: str
    filename: str
    chunk_text: str         # The relevant chunk text
    score: float            # Relevance score
    section: str | None     # Section header if detected
```

### 3.2 Pydantic API Models

#### Request Models

```python
class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    word_count: int
    message: str

class QueryRequest(BaseModel):
    question: str
    conversation_history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]

class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]

class SourceResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_text: str
    score: float
    section: str | None = None

class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    word_count: int
    uploaded_at: str        # ISO 8601 timestamp

class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total_count: int
```

### 3.3 ChromaDB Schema

ChromaDB stores each chunk as a record with:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique chunk ID (`{doc_id}_chunk_{index}`) |
| `embedding` | float[] | 1536-dimensional vector from OpenAI |
| `document` | string | The chunk text content |
| `metadata` | dict | `doc_id`, `filename`, `file_type`, `chunk_index`, `section`, `char_start`, `char_end`, `uploaded_at` |

---

## 4. API Contract

### 4.1 Base URL

```
http://localhost:8000/api
```

### 4.2 Endpoints

#### POST /api/ingest

Upload and process one or more documents.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `files` — one or more files (PDF, DOCX, MD, TXT)
- Max file size: 20MB per file

**Response (200):**
```json
{
  "results": [
    {
      "doc_id": "a1b2c3d4",
      "filename": "employee_handbook.pdf",
      "chunk_count": 47,
      "word_count": 8523,
      "message": "Successfully processed and indexed"
    }
  ]
}
```

**Error Responses:**
- `400`: Unsupported file type
- `413`: File too large
- `500`: Processing or embedding failure

---

#### POST /api/query

Ask a question against the indexed documents.

**Request:**
```json
{
  "question": "What is the PTO policy?",
  "conversation_history": [
    {"role": "user", "content": "Tell me about benefits"},
    {"role": "assistant", "content": "Acme Corp offers health insurance..."}
  ]
}
```

**Response (200):**
```json
{
  "answer": "Full-time employees receive 20 days of PTO per year, accruing at 1.67 days per month. Unused PTO carries over up to 10 days. Requests should be submitted at least 2 weeks in advance through BambooHR.",
  "sources": [
    {
      "doc_id": "a1b2c3d4",
      "filename": "employee_handbook.pdf",
      "chunk_text": "Full-time employees receive 20 days of PTO per year...",
      "score": 0.92,
      "section": "Working Hours & PTO"
    }
  ]
}
```

**Error Responses:**
- `400`: Empty question
- `404`: No documents indexed yet
- `500`: Embedding or LLM failure

---

#### GET /api/documents

List all indexed documents.

**Response (200):**
```json
{
  "documents": [
    {
      "doc_id": "a1b2c3d4",
      "filename": "employee_handbook.pdf",
      "file_type": ".pdf",
      "chunk_count": 47,
      "word_count": 8523,
      "uploaded_at": "2026-03-11T10:30:00Z"
    }
  ],
  "total_count": 1
}
```

---

#### DELETE /api/documents/{doc_id}

Remove a document and all its chunks from the index.

**Response (200):**
```json
{
  "message": "Document removed",
  "doc_id": "a1b2c3d4",
  "chunks_removed": 47
}
```

**Error Responses:**
- `404`: Document not found

---

#### GET /api/suggested-questions

Get contextual starter questions based on indexed documents.

**Response (200):**
```json
{
  "questions": [
    {"text": "What is the PTO policy?", "topic": "HR / PTO"},
    {"text": "How do deployments work?", "topic": "Engineering"},
    {"text": "What tools do I need on day one?", "topic": "Tools & Access"},
    {"text": "How do I set up the VPN?", "topic": "Tools & Access"}
  ]
}
```

---

## 5. Feature Requirements & Acceptance Criteria

### 5.1 Document Ingestion

**FR-1: Multi-format file upload**

Users can upload PDF, DOCX, MD, and TXT files.

| Acceptance Criteria |
|---|
| Upload panel accepts drag-and-drop and click-to-browse |
| PDF text is extracted with pdfplumber, preserving page structure |
| DOCX text is extracted via python-docx, capturing all paragraphs |
| MD and TXT are read as raw text |
| Unsupported file types show a clear error message in the UI |
| Files over 20MB are rejected with an error before upload begins |

**FR-2: Intelligent text chunking**

Extracted text is split into semantic chunks suitable for embedding.

| Acceptance Criteria |
|---|
| Chunks target ~500 characters with 50 character overlap |
| Chunker splits on paragraph boundaries first, then sentence boundaries, then word boundaries as fallback |
| Each chunk retains metadata: parent doc ID, chunk index, filename, detected section header |
| Section headers (markdown `#` or document headings) are detected and attached to subsequent chunks |
| No chunk is empty or whitespace-only |

**FR-3: Vector indexing**

Chunks are embedded and stored in ChromaDB for retrieval.

| Acceptance Criteria |
|---|
| Each chunk is embedded using OpenAI `text-embedding-3-small` (1536 dimensions) |
| Embeddings and metadata are stored in a persistent ChromaDB collection |
| Duplicate documents (same filename) are re-indexed: old chunks are removed before new ones are added |
| Ingestion progress is communicated to the frontend (file accepted → processing → complete) |

### 5.2 Query & Retrieval

**FR-4: Natural language questions**

Users can ask questions in plain English and receive grounded answers.

| Acceptance Criteria |
|---|
| User question is embedded using the same model as document chunks |
| Retriever returns top-5 most similar chunks from ChromaDB |
| Chunks below the relevance threshold (cosine similarity < 0.3) are filtered out |
| If no chunks pass the threshold, the response says "I couldn't find relevant information in the uploaded documents" |

**FR-5: Answer generation with citations**

The LLM generates an answer grounded in retrieved context and cites its sources.

| Acceptance Criteria |
|---|
| The LLM prompt includes: system instructions, retrieved chunks with source labels, conversation history (last 5 turns), and the user question |
| The system prompt instructs the model to only answer based on provided context and to cite sources by label |
| Each answer includes a `sources` array with filename, chunk text, similarity score, and section (if detected) |
| If the model cannot answer from the context, it responds with a clear "I don't have enough information" message rather than hallucinating |

**FR-6: Conversation memory**

The chat supports multi-turn conversations with context from prior turns.

| Acceptance Criteria |
|---|
| The frontend sends the last 5 conversation turns with each query |
| Follow-up questions like "tell me more about that" or "what about the deductible?" resolve correctly using conversation context |
| Conversation history is stored in frontend state (not persisted on backend) |
| Users can start a new conversation (clear history) with a button |

### 5.3 Document Management

**FR-7: Document list**

Users can see all indexed documents.

| Acceptance Criteria |
|---|
| GET /api/documents returns all documents with metadata |
| UI displays document name, type icon, word count, chunk count, and upload date |
| List updates automatically after a successful upload |

**FR-8: Document removal**

Users can remove a document and its chunks from the index.

| Acceptance Criteria |
|---|
| DELETE /api/documents/{doc_id} removes the document record and all associated chunks from ChromaDB |
| Original uploaded file is also deleted from the filesystem |
| UI confirms deletion with a confirmation dialog before proceeding |
| Document list updates after deletion |

### 5.4 Onboarding-Specific Features

**FR-9: Suggested starter questions**

New users see suggested questions to get started.

| Acceptance Criteria |
|---|
| When the chat is empty (no messages), display 4-6 clickable suggested questions |
| Suggested questions are contextual — generated from the indexed document topics, not hardcoded |
| Backend endpoint GET /api/suggested-questions returns questions based on indexed content |
| Clicking a suggestion populates the chat input and submits it |
| Suggestions disappear once the first message is sent |

**FR-10: Topic categories**

Documents are loosely categorized by topic for easier browsing.

| Acceptance Criteria |
|---|
| Topics are inferred from section headers during ingestion (e.g., "Benefits", "Engineering", "Tools & Access") |
| Sidebar or tag display shows available topics |
| Clicking a topic filters suggested questions or scopes the search (stretch goal) |

---

## 6. UI/UX Specification

### 6.1 Design Direction

**Aesthetic:** Clean, professional, approachable. Think modern internal tool — not consumer flashy, not enterprise dull. A design that says "this company has its act together."

**Color Palette:**
- Primary: Deep navy (`#1a2332`) — trustworthy, professional
- Accent: Warm amber/gold (`#f0a030`) — approachable, highlights
- Background: Off-white (`#f8f7f4`) — warm, easy on the eyes
- Surface: White (`#ffffff`) — cards, chat bubbles
- Text: Dark charcoal (`#2d2d2d`) — readable
- Muted: Gray (`#8c8c8c`) — secondary text, timestamps

**Typography:**
- Headings: A clean sans-serif with personality (DM Sans, Outfit, or Satoshi)
- Body: Readable and neutral (IBM Plex Sans, Source Sans 3)
- Code/filenames: Monospace (JetBrains Mono, Fira Code)

### 6.2 Layout

The app uses a two-panel layout on desktop, collapsible on mobile.

```
┌─────────────────────────────────────────────────────────────┐
│  🧭 OnboardAI              [New Chat]    [Upload Docs]  │
├──────────────────┬──────────────────────────────────────────┤
│                  │                                      │
│  SIDEBAR         │  MAIN CHAT AREA                     │
│  (280px)         │                                      │
│                  │  ┌────────────────────────────────┐  │
│  📄 Documents    │  │  Suggested Questions           │  │
│  ─────────────   │  │  (shown when chat is empty)    │  │
│  handbook.pdf    │  │                                │  │
│  eng_process.md  │  │  "What's the PTO policy?"     │  │
│  benefits.docx   │  │  "How do deployments work?"   │  │
│                  │  │  "What tools do I need?"       │  │
│  🏷️ Topics      │  │  "How do I set up VPN?"        │  │
│  ─────────────   │  └────────────────────────────────┘  │
│  Benefits        │                                      │
│  Engineering     │  ┌────────────────────────────────┐  │
│  Tools           │  │  💬 Chat messages go here      │  │
│  HR / PTO        │  │                                │  │
│                  │  │  USER: What's the PTO policy?  │  │
│                  │  │                                │  │
│                  │  │  AI: Full-time employees       │  │
│                  │  │  receive 20 days...            │  │
│                  │  │                                │  │
│                  │  │  📎 Sources:                   │  │
│                  │  │  handbook.pdf — "Working Hours" │  │
│                  │  │                                │  │
│                  │  └────────────────────────────────┘  │
│                  │                                      │
│                  │  ┌────────────────────────────────┐  │
│                  │  │ Ask a question...      [Send]  │  │
│                  │  └────────────────────────────────┘  │
└──────────────────┴──────────────────────────────────────┘
```

### 6.3 Component Specifications

#### Layout (Layout.jsx)

- Full viewport height, flex row
- Sidebar: 280px fixed width, collapsible on screens < 768px via hamburger menu
- Main area: flex-grow, contains chat interface
- Top bar: app name/logo left, action buttons right

#### Upload Panel (UploadPanel.jsx)

- Triggered by "Upload Docs" button in top bar → opens a modal overlay
- Drag-and-drop zone with dashed border, icon, and "Drop files here or click to browse"
- Shows file type badges: PDF, DOCX, MD, TXT
- Displays upload progress: file name → "Processing..." → "✓ 47 chunks indexed"
- Supports multiple files in a single upload
- Error states: "Unsupported file type", "File too large (max 20MB)"
- Close modal after all files finish, or allow user to dismiss

#### Document List (DocumentList.jsx)

- Lives in the sidebar under "Documents" heading
- Each document shows: file type icon, filename (truncated if long), chunk count badge
- Hover state reveals a delete icon (trash)
- Delete click shows a small confirmation tooltip: "Remove this document?" [Yes] [No]
- Empty state: "No documents uploaded yet. Upload your first doc to get started."

#### Chat Interface (ChatInterface.jsx)

- Scrollable message area taking up remaining vertical space
- Auto-scrolls to newest message
- Input bar fixed at bottom: text input + send button
- Send on Enter key or click
- Input disabled while AI is generating (show loading indicator)
- "New Chat" button in top bar clears conversation history

#### Chat Message (ChatMessage.jsx)

- User messages: right-aligned, accent background, white text, rounded bubble
- AI messages: left-aligned, white background, dark text, rounded bubble
- AI messages include a "Sources" collapsible section at the bottom
- Loading state: pulsing dots or typing indicator while waiting for response
- Timestamp shown subtly below each message

#### Source Card (SourceCard.jsx)

- Displayed inside AI messages, collapsed by default, "📎 N sources" toggle
- Each source shows: filename, section name (if available), relevance score as a subtle bar or percentage
- Chunk text shown as a truncated preview (2-3 lines), expandable on click
- Clicking filename could highlight or scroll to that doc in sidebar (stretch goal)

#### Suggested Questions (SuggestedQuestions.jsx)

- Shown in main area when conversation is empty
- Grid of 4-6 cards, 2 columns on desktop, 1 on mobile
- Each card: question text + subtle topic tag
- Click fills input and submits
- Cards have a subtle hover animation (lift + shadow)
- Disappear once first message is sent

### 6.4 Responsive Behavior

- **Desktop (>1024px):** Full two-panel layout as shown
- **Tablet (768-1024px):** Sidebar collapses to icons, expands on hover/click
- **Mobile (<768px):** Sidebar hidden behind hamburger menu, full-width chat

### 6.5 Interaction States

| State | Visual |
|-------|--------|
| Empty chat | Suggested questions grid, welcome message |
| Uploading | Modal with progress indicators per file |
| Waiting for AI | Typing indicator (pulsing dots) in chat |
| AI response | Message appears with expand-to-reveal sources |
| Error (API down) | Toast notification: "Something went wrong. Please try again." |
| No results | AI message: "I couldn't find relevant information in the uploaded documents. Try rephrasing or uploading more docs." |
| No documents | Sidebar empty state prompts upload |

---

## 7. Agent Implementation Guide

This section is for setting up Claude Code agents to build the project.

### 7.1 Recommended Agent Split

Split the work across two Claude Code sessions running in separate terminals:

**Agent 1 — Backend**

Working directory: `onboard-ai/backend/`

Prompt context: Provide this agent with the full PRD. Its job is to build the complete FastAPI backend including all services, routes, and models.

Key instructions for the backend agent:
- Follow the project structure in Section 2.2 exactly
- Implement all services in `app/services/` as standalone modules with clean interfaces
- Implement all routes in `app/routes/` using FastAPI APIRouter
- Use Pydantic models from `app/models.py` for all request/response validation
- Write the chunker to split on paragraph boundaries first, then sentences, with configurable overlap
- The generator system prompt must instruct the LLM to answer ONLY from provided context and cite sources
- Persist ChromaDB to disk so indexed docs survive server restarts
- Add CORS middleware allowing `http://localhost:5173` (Vite default dev server)
- Include the sample_handbook.md in a `test_docs/` directory for testing
- After building, verify each endpoint works using FastAPI's auto-generated docs at `/docs`

**Agent 2 — Frontend**

Working directory: `onboard-ai/frontend/`

Prompt context: Provide this agent with the full PRD. Its job is to build the complete React frontend.

Key instructions for the frontend agent:
- Scaffold with `npm create vite@latest . -- --template react`
- Install and configure Tailwind CSS
- Follow the component structure in Section 2.2 and the UI spec in Section 6
- All API calls go through `src/services/api.js` — single source of truth for backend communication
- Use custom hooks (`useChat.js`, `useDocuments.js`) to manage state and side effects
- Chat interface must send conversation history (last 5 turns) with each query request
- Source citations should be collapsible, defaulting to collapsed
- Suggested questions disappear after first message is sent
- Upload modal supports drag-and-drop with per-file progress indicators
- Implement responsive behavior: sidebar collapses on mobile behind hamburger menu
- Use the color palette and typography from Section 6.1

### 7.2 Agent Startup Commands

```bash
# Terminal 1 — Backend Agent
cd onboard-ai/backend
claude

# Then paste or reference the PRD and say:
# "Build the complete FastAPI backend following this PRD. 
#  Start with the services layer, then models, then routes. 
#  Test each service as you go."

# Terminal 2 — Frontend Agent
cd onboard-ai/frontend
claude

# Then paste or reference the PRD and say:
# "Build the complete React frontend following this PRD. 
#  Start by scaffolding with Vite, install Tailwind, 
#  then build components following the UI spec in Section 6."
```

### 7.3 Testing Checklist

After both agents finish, verify end-to-end:

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173`

**Ingestion tests:**
- [ ] Upload the sample handbook markdown file
- [ ] Upload a PDF (any PDF you have handy)
- [ ] Verify document appears in sidebar with chunk count
- [ ] Upload a .jpg or unsupported file → should show error

**Query tests:**
- [ ] Ask "What is the PTO policy?" → should cite handbook, mention 20 days
- [ ] Ask "How do I set up the VPN?" → should give WireGuard steps
- [ ] Ask "What's the 401k match?" → should mention 4% match
- [ ] Ask a follow-up: "What's the vesting schedule?" → should use conversation context
- [ ] Ask something not in docs: "What's the dress code?" → should say it can't find info

**Document management tests:**
- [ ] Delete a document → confirm it's removed from sidebar
- [ ] Ask a question that was only in the deleted doc → should no longer find results

**UI tests:**
- [ ] Suggested questions show on empty chat
- [ ] Suggestions disappear after first message
- [ ] Source citations expand/collapse
- [ ] Mobile responsive: sidebar hides behind menu
- [ ] "New Chat" clears conversation

---

## 8. User Journey: Supabase Demo → Upload Your Own

The pre-loaded Supabase docs serve as a hook — the goal is to get users to upload their own knowledge base. The UX should guide this progression:

### 8.1 First Visit Flow

1. **Landing state:** Chat is empty. Header shows "Exploring: Supabase Docs (pre-loaded)". Starter questions are visible.
2. **Explore phase:** User clicks starter questions, asks follow-ups, sees how citations work. This builds trust in the tool.
3. **Nudge:** After the user's **3rd query**, show a subtle banner above the chat input:
   > "Liking this? Try it with your own docs — upload a handbook, wiki, or any PDF."
   > [Upload Your Docs →]
4. **Upload phase:** Clicking the CTA opens the upload modal. After successful upload, the knowledge base selector switches to show the user's docs alongside (or instead of) Supabase.
5. **Sticky value:** Once they've uploaded and queried their own docs, the app has demonstrated real value they can't get elsewhere.

### 8.2 Knowledge Base Selector

Add a dropdown or toggle in the header that lets users choose which knowledge base to query:
- **All Documents** — searches everything (Supabase + uploaded)
- **Supabase Docs** — pre-loaded only
- **My Documents** — user uploads only

This keeps the Supabase demo intact while letting users focus on their own content.

### 8.3 Upload CTA Component

A dismissable banner that appears after 3 queries. Design:
```
┌─────────────────────────────────────────────────────────────┐
│ 📄  Try it with your own docs — upload a handbook, wiki,    │
│     or any PDF and start asking questions.  [Upload →]  [✕] │
└─────────────────────────────────────────────────────────────┘
```

If dismissed, don't show again for the session. If they upload, don't show again at all.

---

## 9. Deployment

### 9.1 Architecture for Production

Vercel is ideal for the React frontend but **cannot run ChromaDB or long-lived Python processes**. The backend needs a persistent server.

**Deployment plan:**
| Component | Host | Why |
|-----------|------|-----|
| Frontend (React) | **Vercel** | Free tier, instant deploys, your existing workflow |
| Backend (FastAPI) | **Render** | Free tier, supports Python, persistent filesystem for ChromaDB |
| ChromaDB data | Render filesystem | Persisted on the backend server |

### 9.2 Render Backend Setup

Render's free tier gives you:
- 750 hours/month (enough for always-on)
- 512MB RAM (sufficient for ChromaDB with Supabase docs)
- Persistent disk available on paid tier ($7/mo) — or re-ingest on each deploy on free tier

**Files needed for Render:**

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`backend/render.yaml` (optional, for Blueprint deploys):
```yaml
services:
  - type: web
    name: onboard-ai-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port 8000
    envVars:
      - key: OPENAI_API_KEY
        sync: false
```

### 9.3 Vercel Frontend Setup

The React frontend deploys to Vercel as-is. One config change needed:

`frontend/vite.config.js` needs a proxy for local dev, and the production API URL should come from an env var:

```javascript
// frontend/src/api/client.js
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

Set `VITE_API_URL` in Vercel's environment variables to your Render backend URL (e.g., `https://onboard-ai-api.onrender.com`).

### 9.4 Deployment Steps (after local testing passes)

1. **Push to GitHub** — create a repo `onboard-ai`
2. **Deploy backend to Render:**
   - Connect GitHub repo
   - Set root directory to `backend/`
   - Add env var: `OPENAI_API_KEY`
   - Deploy → get the backend URL
3. **Deploy frontend to Vercel:**
   - Connect same GitHub repo
   - Set root directory to `frontend/`
   - Add env var: `VITE_API_URL=https://your-render-url.onrender.com`
   - Deploy
4. **Run ingestion** (one-time): SSH into Render or run locally pointing at the Render backend to populate Supabase docs
5. **Test live:** Open Vercel URL, verify chat works

### 9.5 CORS Configuration

The FastAPI backend must allow requests from the Vercel frontend domain. Update `main.py`:

```python
origins = [
    "http://localhost:5173",          # local dev
    "https://onboard-ai.vercel.app",  # production (update with actual URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 9.6 Cost Estimate (Production)

| Item | Monthly Cost |
|------|-------------|
| Vercel (frontend) | Free |
| Render (backend, free tier) | Free |
| OpenAI API (assuming ~500 queries/month) | ~$0.50 |
| **Total** | **~$0.50/month** |

If traffic grows and you need persistent ChromaDB (no re-ingest on Render restarts), upgrade Render to Starter ($7/mo) for persistent disk.
