# 🚀 How to Run Your AI Astrologer API

## Prerequisites

1. **Python 3.11+** (as specified in Pipfile)
2. **PostgreSQL** database running locally or remotely
3. **Redis** server running (optional, for caching)
4. **Firebase** project setup
5. **OpenRouter API** key

## Step 1: Install Dependencies

```bash
# Install dependencies using pipenv
pipenv install

# Or if you prefer pip
pip install -r requirements.txt
```

## Step 2: Set Up Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Copy the example and fill in your values
cp .env.example .env
```

Required environment variables:

```env
# --- Application Settings ---
ENVIRONMENT=development
DEBUG=true
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# --- Database Settings (PostgreSQL) ---
DATABASE_URL=postgresql://username:password@localhost:5432/ai_astrologer_db
TEST_DATABASE_URL=postgresql://username:password@localhost:5432/ai_astrologer_test_db

# --- Firebase Settings ---
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_SERVICE_ACCOUNT_PATH=config/firebase-service-account.json

# --- OpenRouter API Settings ---
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_API_BASE=https://openrouter.ai/api/v1
OPENROUTER_MODEL=deepseek/deepseek-chat

# --- Encryption Settings ---
ENCRYPTION_SECRET_KEY=your-32-character-encryption-key-here

# --- Redis Settings (Optional) ---
REDIS_URL=redis://localhost:6379
```

## Step 3: Set Up Database

### Option A: Local PostgreSQL

1. Install PostgreSQL locally
2. Create databases:
```sql
CREATE DATABASE ai_astrologer_db;
CREATE DATABASE ai_astrologer_test_db;
```

### Option B: Use Docker

```bash
# Start PostgreSQL with Docker
docker run --name ai-astrologer-postgres \
  -e POSTGRES_USER=astrologer \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=ai_astrologer_db \
  -p 5432:5432 \
  -d postgres:15

# Create test database
docker exec -it ai-astrologer-postgres psql -U astrologer -c "CREATE DATABASE ai_astrologer_test_db;"
```

## Step 4: Set Up Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use existing one
3. Enable Authentication
4. Generate service account key:
   - Go to Project Settings > Service Accounts
   - Generate new private key
   - Save as `config/firebase-service-account.json`

## Step 5: Get OpenRouter API Key

1. Go to [OpenRouter](https://openrouter.ai/)
2. Sign up and get your API key
3. Add it to your `.env` file

## Step 6: Run the Application

### Method 1: Using pipenv (Recommended)

```bash
# Activate virtual environment
pipenv shell

# Run the application
pipenv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 2: Using uvicorn directly

```bash
# Activate virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: Using Python module

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 7: Verify the Application

1. **Check if the app is running:**
   - Open your browser and go to: http://localhost:8000
   - You should see the API documentation

2. **Check API endpoints:**
   - API docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

3. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/api/health
   ```

## Available API Endpoints

- **Health Check**: `GET /api/health`
- **User Management**: `/api/users/*`
- **Admin Panel**: `/api/admin/*`
- **Charts**: `/api/charts/*`
- **Chat**: `/api/chat/*`

## Troubleshooting

### Common Issues:

1. **Database Connection Error:**
   - Check if PostgreSQL is running
   - Verify DATABASE_URL in .env file
   - Ensure database exists

2. **Firebase Error:**
   - Check FIREBASE_PROJECT_ID
   - Verify service account file path
   - Ensure Firebase project is properly configured

3. **OpenRouter API Error:**
   - Verify OPENROUTER_API_KEY
   - Check if you have credits/access

4. **Import Errors:**
   - Make sure you're in the project root directory
   - Check if all dependencies are installed
   - Verify Python version (3.11+)

### Development Tips:

1. **Enable Debug Mode:**
   ```env
   DEBUG=true
   ENVIRONMENT=development
   ```

2. **Auto-reload on changes:**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production`
2. Set `DEBUG=false`
3. Use a production-grade ASGI server like Gunicorn with Uvicorn workers
4. Set up proper logging and monitoring
5. Use environment-specific database and Redis configurations

## Support

If you encounter any issues:
1. Check the logs in `logfile.log`
2. Verify all environment variables are set correctly
3. Ensure all external services (PostgreSQL, Redis, Firebase) are accessible
4. Check the FastAPI documentation for any API-related issues
