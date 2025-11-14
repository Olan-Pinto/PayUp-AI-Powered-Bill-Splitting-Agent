# 💰 PayUp - AI-Powered Bill Splitting Agent

**Split bills effortlessly with AI-powered OCR and intelligent expense calculation.**

---

## 🎯 What is PayUp?

PayUp uses Google Gemini AI to automatically read bills, extract items and prices, and calculate fair splits between multiple people. Upload a photo of any restaurant bill, specify how to split it, and get instant results with detailed breakdowns.

---

## ✨ Features

### 🤖 AI-Powered Processing
- **Smart OCR** - Extracts text from bill images using Google Gemini Vision API
- **Intelligent Parsing** - Automatically identifies items, prices, tax, and tips
- **Flexible Splitting** - Equal splits, custom percentages, or item-based division
- **Real-time Progress** - Live WebSocket updates during processing

### 💼 User Experience
- **Google OAuth** - Secure authentication
- **Bill History** - Access previously processed bills
- **Download Bills** - Save results for later
- **Responsive Design** - Works on desktop and mobile

### 🏗️ Architecture
- **Async Processing** - Background tasks with Celery
- **Cloud Storage** - Google Cloud Storage for bill images
- **Scalable** - Deployable on Google Cloud Run
- **Real-time** - WebSocket connections for live updates

---

## 🚀 Quick Start

### How to Use PayUp

1. **Sign in with Google** - Secure OAuth authentication
2. **Upload a bill image** - Restaurant receipt, grocery bill, etc.
3. **Choose split method:**
   - "Split equally among 3 people"
   - "Person A pays for items 1-3, Person B pays for the rest"
   - "Split 60-40 between Person A and Person B"
4. **Watch real-time progress** - See AI process your bill in real-time
5. **View detailed breakdown** - Get per-person totals with tax and tip included

---

## 💻 Local Development

### Branch Structure

This project uses two separate branches to keep concerns separated:

- **`main` branch** - Contains all Docker and Docker Compose configuration for local development
- **`deployment` branch** - Contains all Cloud Run deployment configuration

This separation ensures that local development setup and production deployment code don't intermingle.

### Prerequisites

- **Docker** & **Docker Compose**
- **Python 3.11+**
- **Node.js 20+**
- **Google Cloud** account (for Gemini API)
- **Supabase** account (for authentication)

### 1. Clone Repository

```bash
git clone https://github.com/Olan-Pinto/PayUp-AI-Powered-Bill-Splitting-Agent.git
cd PayUp-AI-Powered-Bill-Splitting-Agent

# For local development (Docker setup)
git checkout main

# For deployment to Cloud Run
git checkout deployment
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
# AI
GEMINI_API_KEY=your_gemini_api_key

# Authentication
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
GOOGLE_REDIRECT_URL=http://localhost:8000/auth/google/callback

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/payup

# Services (Docker)
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/0
REDIS_URL=redis://redis:6379/0

# Storage
GCS_BUCKET_NAME=uploaded_bills
UPLOADS_DIR=/tmp/uploads

# Security
JWT_SECRET=your_secret_key_here
```

### 3. Run with Docker Compose

```bash
# Start all services
docker-compose up --build

# Services will be available at:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### 4. Access the Application

1. Open **http://localhost:5173**
2. Sign in with Google
3. Upload a bill and start splitting!

---

## 🏗️ Architecture

### System Overview

```
React Frontend (Port 5173)
         │
         │ HTTP/WebSocket
         ▼
   FastAPI API (Port 8000) ──────▶ Redis (Sessions)
         │
         ├──────▶ PostgreSQL (Database)
         │
         ├──────▶ RabbitMQ (Task Queue)
         │
         ├──────▶ Celery Worker (Background Processing)
         │
         └──────▶ Google Cloud (Gemini AI + Storage)
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | React 18 + Vite | User interface |
| **Backend** | FastAPI | REST API |
| **Worker** | Celery | Async bill processing |
| **Database** | PostgreSQL | Store bill data |
| **Cache** | Redis | Sessions & task results |
| **Queue** | RabbitMQ | Task distribution |
| **AI** | Google Gemini | OCR & text analysis |
| **Storage** | Google Cloud Storage | Bill images |
| **Auth** | Supabase | User authentication |

---

## 📂 Project Structure

```
PayUp-AI-Powered-Bill-Splitting-Agent/
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── pages/            # Page components
│   │   ├── lib/              # Utilities
│   │   └── config.js         # API configuration
│   └── Dockerfile
│
├── backend/
│   ├── main.py               # FastAPI app
│   ├── auth.py               # Authentication
│   ├── bill_splitting_agent.py  # AI processing
│   ├── models.py             # Database models
│   └── database.py           # Database config
│
├── docker-compose.yml         # Local development
└── README.md
```

---

## 🔌 API Endpoints

### Authentication
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - OAuth callback
- `POST /auth/verify` - Verify access token
- `POST /auth/logout` - Logout user

### Bill Processing
- `POST /process-bill` - Upload and process bill
- `GET /bill/{bill_id}` - Get bill details
- `GET /bill/{bill_id}/download` - Download bill image
- `GET /bill/{bill_id}/view` - View bill image
- `WS /ws/progress/{bill_id}` - Real-time progress updates

**Full API documentation available at:** http://localhost:8000/docs

---

## 🎨 How It Works

### Processing Flow

**1. Upload**  
User uploads a bill image through the frontend.

**2. Queue**  
FastAPI uploads the image to Google Cloud Storage and queues a processing task.

**3. Process**  
Celery worker picks up the task:
- Downloads image from GCS
- Uses Google Gemini to extract text (OCR)
- Parses items, prices, tax, and tip
- Calculates split based on user instructions

**4. Save**  
Results are saved to PostgreSQL database.

**5. Display**  
Frontend receives real-time updates via WebSocket and displays the split breakdown.

---

## 🌐 Deployment

### Branch Information

**Important:** All deployment configuration is in the `deployment` branch to keep it separate from local development setup.

```bash
# Switch to deployment branch
git checkout deployment
```

### Production Architecture

The application can be deployed on **Google Cloud Run** with:
- **Frontend & Backend:** Separate Cloud Run services
- **Redis:** Redis Cloud (free tier available)
- **RabbitMQ:** CloudAMQP (free tier available)
- **Database:** Supabase PostgreSQL
- **Celery Worker:** Local machine or VM (connects to cloud services)

### Prerequisites for Deployment

#### 1. Set up Cloud Services

**Redis Cloud:**
- Sign up at https://redis.io/try-free/
- Create a free database
- Get connection URL: `redis://default:PASSWORD@host:port`

**CloudAMQP:**
- Sign up at https://www.cloudamqp.com/
- Create a free "Lemur" instance
- Get AMQP URL: `amqps://user:pass@host/vhost`

**Supabase:**
- Create a project at https://supabase.com
- Get database connection string from Settings → Database
- Enable Google OAuth in Authentication → Providers

**Google Cloud:**
- Create a project in Google Cloud Console
- Enable Gemini API
- Create API key
- Create a GCS bucket: `gsutil mb -l us-central1 gs://your-bucket-name`

#### 2. Deploy Backend to Cloud Run

**Make sure you're on the `deployment` branch:**
```bash
git checkout deployment
```

Then deploy:

```bash
# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage.googleapis.com

# Deploy backend
gcloud run deploy payup-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300
```

Add environment variables in Cloud Run console:
- `GEMINI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `DATABASE_URL`
- `GCS_BUCKET_NAME`
- `JWT_SECRET`
- `GOOGLE_REDIRECT_URL` (your Cloud Run backend URL + `/auth/google/callback`)

#### 3. Deploy Frontend to Cloud Run

```bash
cd frontend

gcloud run deploy payup-frontend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi
```

Add environment variable:
- `VITE_API_URL` (your Cloud Run backend URL)

Or update `frontend/src/config.js` with your backend URL.

#### 4. Configure Supabase Redirect URLs

Add these to Supabase → Authentication → URL Configuration:
- `http://localhost:8000/auth/google/callback` (local dev)
- `https://your-backend-url/auth/google/callback` (production)

#### 5. Run Celery Worker

The worker can run on your local machine or a VM:

```bash
# Set environment variables
export REDIS_URL=redis://default:PASSWORD@host:port
export CELERY_BROKER_URL=amqps://user:pass@host/vhost
export CELERY_RESULT_BACKEND=redis://default:PASSWORD@host:port
export DATABASE_URL=postgresql://...
export GEMINI_API_KEY=your_key
export GCS_BUCKET_NAME=your_bucket

# Authenticate with Google Cloud (for GCS access)
gcloud auth application-default login

# Start worker
python -m celery -A main.celery_app worker --loglevel=info --pool=solo
```

---

## 🛠️ Development Commands

### Backend Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
python -m celery -A main.celery_app worker --loglevel=info --pool=solo
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

### Docker Commands

```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Remove everything including volumes
docker-compose down -v
```

---

## 🔧 Configuration

### Supabase Setup

1. Create a project at https://supabase.com
2. Go to **Settings → Database** and copy connection string
3. Go to **Authentication → Providers**
4. Enable **Google** provider
5. Add redirect URLs:
   - `http://localhost:8000/auth/google/callback`
   - Production backend URL + `/auth/google/callback`

### Google Cloud Setup

1. Create a project in **Google Cloud Console**
2. Enable **Gemini API** (Vertex AI API)
3. Create an **API key**
4. Create a **GCS bucket** for bill storage:
   ```bash
   gsutil mb -l us-central1 gs://your-bucket-name
   ```
5. For local development with GCS:
   ```bash
   gcloud auth application-default login
   ```

---

## 💡 Usage Examples

### Equal Split
```
Instruction: "Split equally among 3 people"
Input: $100 bill
Result: Each person pays $33.33
```

### Item-Based Split
```
Instruction: "Person A ordered items 1-3, Person B ordered items 4-6"
Result: Split based on individual items plus proportional tax/tip
```

### Percentage Split
```
Instruction: "Split 60-40 between Person A and Person B"
Input: $100 bill
Result: Person A pays $60, Person B pays $40
```

### Custom Instructions
```
Instruction: "Person A pays for all drinks, split the rest equally"
Result: Custom calculation based on AI interpretation
```

---

## 🧪 Testing

### Test Bill Processing Locally

```bash
# Start all services
docker-compose up

# In another terminal, test the API
curl -X POST http://localhost:8000/process-bill \
  -F "file=@test_bill.jpg" \
  -F "instruction=Split equally among 2 people"
```

### Test with Different Bill Types

- Restaurant receipts
- Grocery bills
- Bar tabs
- Service invoices
- Delivery orders

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Commit: `git commit -m 'Add feature'`
5. Push: `git push origin feature-name`
6. Submit a pull request

---



## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Gemini API](https://ai.google.dev/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [React Documentation](https://react.dev/)
- [Docker Documentation](https://docs.docker.com/)
- [Google Cloud Run](https://cloud.google.com/run/docs)

---

<div align="center">


</div>