# VideoIQ 🧠⚡

VideoIQ is a production-grade, local-first RAG (Retrieval-Augmented Generation) dashboard that enables content creators, marketers, and analysts to perform side-by-side performance audits of a YouTube URL (Video A) and an Instagram Reel URL (Video B). By feeding both links into the application, VideoIQ concurrently scrapes video metadata (views, likes, comments, duration, upload date, followers), retrieves or transcribes speech data (via standard APIs and local OpenAI Whisper), indexes text segments into a local persistent ChromaDB vector store, and provides a real-time, streaming AI chat interface backed by Google's Gemini 1.5 Flash.

This tool acts as your personal video optimization partner. Rather than jumping between platforms, you can instantly compare engagement metrics and ask complex comparative questions like *"Compare the hook structures of both videos in the first 5 seconds,"* *"Why did Video B get a higher engagement rate despite fewer views?"* or *"What optimization suggestions do you have for Video A's transcript?"*. VideoIQ isolates sessions dynamically, cites its claims with context-chunk indexes, and streams responses with zero lag out-of-the-box.

---

## Architecture Diagram

```
                 +-----------------------------------------+
                 |            React Frontend               |
                 |      Vite + Tailwind CSS (Port 5173)    |
                 +----+------------------------------------+
                      |                       ^
             POST URL Ingest                  | Streaming Event Stream (SSE)
                      v                       |
   +------------------+-----------------------+---------------------+
   |                      FastAPI Backend                           |
   |                       Port 8000                                |
   +--------+------------------+-----------------------+------------+
            |                  |                       |
            | yt-dlp           | HTTP Request          | local audio extraction
            v                  v                       v
     +------+------+   +-------+-------+       +-------+-------+
     |   YouTube   |   |   Apify API   |       | OpenAI Whisper|
     | Transcript  |   | (Instagram)   |       |    (tiny)     |
     +------+------+   +-------+-------+       +-------+-------+
            |                  |                       |
            +------------------+-----------------------+
                               |
                               v Text segments chunking
                 +-------------+-------------+
                 | Recursive Character       |
                 | Text Splitter (300 / 50)  |
                 +-------------+-------------+
                               |
                               v Local Embedding Generation
                 +-------------+-------------+
                 |   BAAI/bge-small-en       |
                 |   SentenceTransformers    |
                 +-------------+-------------+
                               |
                               v
                       [ ChromaDB Store ]
                       (videoiq_chunks)
                               |
                               | Context Query
                               v
                 +-------------+-------------+
                 | Gemini 1.5 Flash Streaming|
                 | System prompt + Memory    |
                 +---------------------------+
```

---

## Setup & Local Installation

### Prerequisites
1. **Python 3.10+** installed.
2. **Node.js v18+** and npm installed.
3. **ffmpeg** installed on your system PATH (required for local audio conversion and OpenAI Whisper transcription).

---

### 1. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the `.env.example` file and supply your API keys:
   ```bash
   cp .env.example .env
   ```
5. Run the backend development server using Uvicorn:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

---

### 2. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Copy the `.env.example` file:
   ```bash
   cp .env.example .env
   ```
4. Run the Vite development server:
   ```bash
   npm run dev
   ```
5. Open your browser and go to `http://localhost:5173`.

---

## Environment Variables Explained

### Backend (`backend/.env`)

| Variable | Description | Required / Optional | Default |
|---|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API Key used to access the `gemini-1.5-flash` model. | **Required** for Chat | None |
| `APIFY_TOKEN` | Apify Token used to run the `apify~instagram-reel-scraper` actor. | *Optional* (Fallback to 0 metrics if empty) | None |
| `CLIENT_URL` | The production URL of the React client (used for setting up strict CORS bounds). | Optional | `http://localhost:5173` |
| `CHROMA_PATH` | Path where local ChromaDB embeddings are saved persistently. | Optional | `./chroma_store` |

### Frontend (`frontend/.env`)

| Variable | Description | Required | Default |
|---|---|---|---|
| `VITE_API_URL` | The backend API root URL where ingest and chat endpoints reside. | **Required** | `http://localhost:8000` |

---

## Production Deployment Steps

### 1. Backend Deployment (Render)
1. Log in to [Render](https://render.com) and create a **New Web Service**.
2. Connect your GitHub repository containing the VideoIQ application.
3. Configure the following service settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add the following **Environment Variables** in Render's dashboard settings:
   - `GEMINI_API_KEY` = `[your_gemini_api_key]`
   - `APIFY_TOKEN` = `[your_apify_token]`
   - `CLIENT_URL` = `https://[your-frontend-app].vercel.app`
   - `CHROMA_PATH` = `/opt/render/project/src/chroma_store` (or create a persistent disk mount for persistent storage).
5. Deploy the service.

### 2. Frontend Deployment (Vercel)
1. Log in to [Vercel](https://vercel.com) and create a **New Project**.
2. Link your GitHub repository.
3. Choose the directory `frontend` as the **Root Directory**.
4. Configure build settings:
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Supply the frontend environment variables:
   - `VITE_API_URL` = `https://[your-render-backend-subdomain].onrender.com`
6. Deploy the project.

---

## Cost & Scalability Audit (At 1,000 creators/day)

### 1. Vector Embeddings
- **Local (BGE-small-en)**: **$0.00 / day** (runs entirely free on local CPU/Docker memory).
- **OpenAI text-embedding-3-small**: Charging `$0.02 / 1M tokens`. At 1,000 creators auditing 2 videos daily, average text count of 5,000 tokens/creator, we generate ~5,000,000 tokens. Total cost is **$0.10 / day**.
- *Decision*: BGE-small-en is highly effective for localized transcript matching and carries absolute zero running costs.

### 2. Vector Databases
- **ChromaDB Local**: **$0.00 / day** (stores persistently on localized disk volumes or within Docker).
- **Qdrant Cloud (Managed)**: Scaled server costs start at **$9.00 / month** ($0.30/day) for high availability, isolated namespaces, and hardware indices.
- *Decision*: ChromaDB local is perfect for lightweight, transactional comparative sessions that reset with every new URL submission.

### 3. LLM Costs (1,000 creators/day)
For an average turn of 5 turns per creator, representing 4,000 input tokens (including system prompts, memory history, and 4 transcript chunk contexts) and 500 output tokens:
- **Gemini 1.5 Flash**:
  - Input: `$0.075 / 1M tokens` → 1,000 × 5 × 4,000 × $0.075/1M = **$1.50 / day**
  - Output: `$0.30 / 1M tokens` → 1,000 × 5 × 500 × $0.30/1M = **$0.75 / day**
  - **Total: $2.25 / day**
- **GPT-4o-mini**:
  - Input: `$0.15 / 1M tokens` → **$3.00 / day**
  - Output: `$0.60 / 1M tokens` → **$1.50 / day**
  - **Total: $4.50 / day**
- *Decision*: Gemini 1.5 Flash offers superior value and native speed for large incoming context windows.

### 4. Scale Bottlenecks at 10,000+ daily users & Solutions
- **Whisper CPU Satiation**: transcribing 10k Reels simultaneously on a single CPU instance will cause server locks.
  - *Solution*: Offload local audio downloads and Whisper transcribing to a queuing server (Celery/Redis) backed by isolated, GPU-powered worker pools, or utilize an external API (like AssemblyAI or Deepgram).
- **Apify Rate Limits**: Scraping 10k Instagram pages directly using standard tokens will cause concurrency blocks.
  - *Solution*: Set up dedicated proxy networks, configure Apify client pools, or use specialized scraping APIs with high concurrency rates.
- **Chroma Lockups**: Running multi-thread writes on the same persistent SQLite database causes file blocks.
  - *Solution*: Migrate from Chroma persistent local client to Qdrant or Pinecone database clusters.

---

## Technical Rationale

1. **FastAPI**: Chosen for its high performance, native async support, automated OpenAPI docs generation, and ease of creating SSE event stream connections compared to Django.
2. **React + Vite**: Enables instant hot-reloading in development and builds exceptionally fast production bundles compared to CRA.
3. **ChromaDB + BGE Embeddings**: Ensures 100% free, highly efficient local vector storage. `bge-small-en` outperforms many models double its size, returning swift search comparisons.
4. **Gemini 1.5 Flash**: Selected for its massive context capacity, low latency, outstanding cost-to-performance metrics, and robust support for conversational streaming.

---

## Known Limitations
1. **Transcripts Requirement**: VideoIQ depends on YouTube having auto-generated or manual captions available. If disabled, a placeholder transcript is created.
2. **FFmpeg dependency**: If `ffmpeg` is missing on your host machine's PATH, local Whisper audio transcription for Instagram Reels will fail, leaving an empty transcription warning.
3. **Scraper dependency**: Instagram Reels metadata is scraped using Apify's actor. If Apify updates its selectors or you run out of credits, metadata counters default to 0, though transcription remains fully active.
