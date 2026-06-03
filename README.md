VideoIQ 

VideoIQ is a production-grade, and deployed RAG chatbot (Retrieval-Augmented Generation) dashboard that enables content creators, marketers, and analysts to perform side-by-side performance audits of a YouTube URL (Video A) and an Instagram Reel URL (Video B). By feeding both links into the application, VideoIQ concurrently scrapes video metadata (views, likes, comments, duration, upload date, followers), retrieves or transcribes speech data via standard APIs indexes text segments into a local persistent ChromaDB vector store, and provides a real-time, streaming AI chat interface backed by Google's Gemini.

This tool acts as our personal video optimization partne instead of jumping between platforms, we can instantly compare the engagement stats and ask and see and analyse complex comparative questions like , "Compare the hook structures of both videos in the first 5 seconds,",  "Why did Video B get a higher engagement rate despite fewer views?" or "What optimization suggestions do you have for Video A's transcript?",  VideoIQ isolates sessions dynamically, cites its claims with context-chunk indexes, and streams responses with zero lag out-of-the-box. There are few most common question added to the chatbot Ui so it'll be easy to ask them quickly instead of just typing them.

---

Architecture Diagram

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
   +--------+----------------------------------------+--------------+
            |                                        |                       
            |YouTube Data API v3                     | HTTP Request          
            v                                        v                       
     +------+------+                         +-------+-------+       
     |   YouTube   |                         |   Apify API   |       
     |Transcript api|                        | (Instagram)   |       
     +------+------+                         +-------+-------+       
            |                                        |                       
            +------------------+---------------------+
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

Setup & Local Installation

 Prerequisites
1. Python 3.10+ installed.
2. Node.js v18+ and npm installed.
3. ffmpeg installed on our system PATH .

---

1. Backend Setup(for local host)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
    PowerShell:
   .\venv\Scripts\Activate.ps1
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

2. Frontend Setup(for local host)

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
5. Open the browser and go to `http://localhost:5173` (maybe differnt if that port is busy or used by another source)

---

 Environment Variables Explaination

 Backend (`backend/.env`)

| Variable | Description | Required / Optional | Default |
|---|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API Key used to access the gemini-1.5-flash model. 
| `YOUTUBE_API_KEY` | Google API key with YouTube Data API v3 enabled. Used for YouTube title, channel, views, likes, comments, duration, and upload date, Required for YouTube metrics 
| `APIFY_TOKEN` | Apify Token used to run the apify~instagram-reel-scraper actor. | *Optional* (Fallback to 0 metrics if empty) 
| `CLIENT_URL` | The production URL of the React client (used for setting up stricst CORS bounds). 
| `CHROMA_PATH` | Path where local ChromaDB embeddings are saved. | 

 Frontend (`frontend/.env`)

| Variable | Description | Required | Default |
|---|---|---|---|
| `VITE_API_URL` | The backend API root URL where ingest and chat endpoints are. 

---

 Production Deployment Steps

1. Backend Deployment (Render)
1. Log in to [Render](https://render.com) and create a New Web Service.
2. Connected my GitHub repo containing the VideoIQ files with it.
3. Configure the following service settings:
   - Environment: `Python`
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add the following Environment Variables in Render's dashboard settings:
   - GEMINI_API_KEY = [your_gemini_api_key]
   - YOUTUBE_API_KEY = [your_google_api_key_with_youtube_data_api_v3_enabled]
   - APIFY_TOKEN` = [your_apify_token]
   - CLIENT_URL = https://[your-frontend-app].vercel.app
   - CHROMA_PATH = /opt/render/project/src/chroma_store (or create a persistent disk mount for persistent storage)
5. Deploy the service.

2. Frontend Deployment (Vercel)
1. Log in to [Vercel](https://vercel.com) and created a New Project.
2. Link your GitHub repository.
3. Choose the directory frontend as the Root Directory.
4. Configure build settings:
   - Framework Preset: Vite
   - Build Command: npm run build
   - Output Directory: dist
5. Supply the frontend environment variables:
   - VITE_API_URL = https://[your-render-backend-subdomain].onrender.com
6. Deploy the project.

---

Cost & Scalability Audit (At 1,000 creators/day)

1. Vector Embeddings
- Local (BGE-small-en): it's free (runs entirely free on local CPU/Docker memory).
- OpenAI text-embedding-3-small**: Charging $0.02 / 1M tokens. At 1,000 creators auditing 2 videos daily, average text count of 5,000 tokens/creator, we generate ~5,000,000 tokens. Total cost is $0.10 / day
- Decision: BGE-small-en is highly effective for localized transcript matching and carries absolute zero running costs.

2. Vector Databases
- ChromaDB Local: it's free for current stats and user load (stores persistently on localized disk volumes or within Docker).
- Qdrant Cloud (Managed)**: Scaled server costs start at $9.00 / month ($0.30/day) for high availability, isolated namespaces, and hardware indices.
- Decision: ChromaDB local is perfect for lightweight, transactional comparative sessions that reset with every new URL submission.

3. LLM Costs (1,000 creators/day)
For an average turn of 5 turns per creator, representing 4,000 input tokens (including system prompts, memory history, and 4 transcript chunk contexts) and 500 output tokens:
- Gemini 1.5 Flash:
  - Input: $0.075 / 1M tokens → 1,000 × 5 × 4,000 × $0.075/1M = **$1.50 / day**
  - Output: $0.30 / 1M tokens → 1,000 × 5 × 500 × $0.30/1M = **$0.75 / day**
  - Total: $2.25 / day
- GPT-4o-mini:
  - Input: $0.15 / 1M tokens → $3.00 / day
  - Output: $0.60 / 1M tokens → $1.50 / day
  - otal: $4.50 / day
- Decision: Gemini 1.5 Flash offers great value and native speed for large incoming context windows.
- Estimated daily Gemini cost remains low because RAG only sends relevant chunks instead of full transcripts.

4. Scale Bottlenecks at 10,000+ daily users & Solutions
  - Solution: Offload local audio downloads transcribing it to a queuing server (Celery/Redis) backed by isolated, GPU-powered worker pools or utilize an external API (like AssemblyAI or Deepgram).
- Apify Rate Limits Scraping 10k Instagram pages directly using standard tokens will cause concurrency blocks.
  - Solution: Set up dedicated proxy networks, configure Apify client pools, or use specialized scraping APIs with high concurrency rates.
- Chroma Lockups: Running multi-thread writes on the same persistent SQLite database causes file blocks.
  - Solution: Migrate from Chroma persistent local client to Qdrant or Pinecone database clusters.

 Technical Rationale

1. FastAPI: Chosen for its high performance, native async support, automated OpenAPI docs generation, and ease of creating SSE event stream connections compared to Django.
2. React + Vite: Enables instant hot-reloading in development and builds exceptionally fast production bundles compared to CRA.
3. ChromaDB + BGE Embeddings**: Ensures 100% free, highly efficient local vector storage, bge-small-en outperforms many models double its size, returning swift search comparisons.
4. Gemini 1.5 Flash: Selected for its massive context capacity, low latency, outstanding cost-to-performance metrics, and robust support for conversational streaming.

---

Limitations
1. Transcripts Requirement: VideoIQ depends on YouTube having auto-generated or manual captions available. If disabled, a placeholder transcript is created.
2. FFmpeg dependency: If ffmpeg is missing on your host machine's PATH, local audio transcription for Instagram Reels will fail, leaving an empty transcription warning.
3. Scraper dependency: Instagram Reels metadata is scraped using Apify's actor. If Apify updates its selectors or you run out of credits, metadata counters default to 0, though transcription remains fully active.

Challenges Faced During Development
This project looked simple at first, but while deploying and testing it on real cloud services, several issues came up.

1. CORS Issues Between Frontend and Backend
At the beginning, the frontend hosted on Vercel was unable to communicate properly with the backend hosted on Render because of CORS restrictions. The browser was blocking requests even though both services were running correctly.
This was fixed by improving the CORS configuration and making the allowed origins more flexible.

2. Environment Variable Problems
Some of the API keys and configuration values were not being loaded correctly in production. Because of this, certain features worked locally but failed after deployment.
Extra validation and cleaning logic was added to make environment variables more reliable.

3. Embedding Model Compatibility Issues
As this project uses vector embeddings for the RAG pipeline. During deployment, different embedding models returned vectors with different dimensions, which caused ChromaDB collection errors.
After debugging the issue, the embedding pipeline was updated and standardized so all stored vectors use the same dimension.

4. YouTube Cloud Restrictions
One of the biggest problems was YouTube blocking automated requests coming from cloud providers like Render.
Libraries such as yt-dlp and youtube-transcript-api worked in some cases but often failed because YouTube detected the cloud IP and treated it as automated traffic.
To reduce failures, a multi-layer fallback system was added.

5. Gemini API Quota Limits
The project uses Gemini APIs for some AI-powered processing. During testing, quota and rate-limit errors appeared when the fallback pipeline tried to process videos.
To handle this, additional fallback logic was added so the application can still continue working even when Gemini requests fail.

6. Metadata Returning Empty Values
At one point, YouTube videos were showing:
Unknown Channel
0 Views
0 Likes
0 Comments
Although the video title and thumbnail was visible
After investigating logs, the root cause turned out to be a missing YOUTUBE_API_KEY in the deployment environment.
Once the API key was configured correctly, real metadata started loading again.

8. Deployment Debugging
A large amount of time was spent debugging differences between local development and production deployment.
Many issues only appeared after deploying to Vercel and Render, so detailed logging was added throughout the application to make troubleshooting easier.

What I Learned: This project taught me that building the feature is only half of the work. The harder part is making it reliable in production, handling API limitations, dealing with deployment issues, and creating proper fallback systems when external services fail.

Future Improvements(not the project requirments but it can be done if needed or asked to do so)
- Dedicated transcript ingestion service
- Queue-based processing using Celery + Redis
- Qdrant migration for large-scale vector storage
- Multi-user session management
- Caching layer for repeated video analysis
- Advanced analytics dashboards
