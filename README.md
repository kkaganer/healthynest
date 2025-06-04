# HealthyNest LangGraph Meal Planner

angGraph-based meal planning application with Human-in-the-Loop (HITL) capabilities, deployed on Google Cloud Run.

## Deployment

The URL may change if you redeploy on Google Cloud Run.

current URL = https://healthynest-planner-105939838979.europe-west1.run.app

**Live Service**: `https://healthynest-planner-105939838979.europe-west1.run.app`

**API Documentation**: `https://healthynest-planner-105939838979.europe-west1.run.app/docs`


## 🎯 Features

### ✅ Human-in-the-Loop (HITL) Workflow
- **Pause & Resume**: Workflow pauses at designated checkpoints for user input
- **State Persistence**: Complete state management with thread-based isolation
- **Dynamic Input**: Accepts natural language scheduling descriptions
- **Multi-step Confirmation**: User can review and modify generated calendars and meal plans

### ✅ Production Deployment
- **Google Cloud Run**: Scalable serverless deployment
- **HTTPS Webhooks**: Secure API endpoints for workflow management
- **Environment Configuration**: Proper secret management
- **Health Monitoring**: Built-in health checks and logging

### ✅ Database Integration
- **Supabase Backend**: Complete meal plan persistence
- **User Management**: Multi-user support with dietary preferences
- **Recipe Database**: Intelligent recipe selection based on dietary needs

## 🔗 API Endpoints

### Start New Meal Plan
```bash
POST /start_plan
Content-Type: application/json

{
  "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
  "start_date": "2025-06-10",
  "days_to_generate": 2,
  "plan_description": "Plan for kristina. robin joins for lunch on Monday and Tuesday."
}
```

### Resume Paused Workflow
```bash
POST /resume_plan
Content-Type: application/json

{
  "thread_id": "meal_plan_USER_ID_TIMESTAMP",
  "user_input": {
    "confirmed_calendar": {
      "Monday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina"]}
    }
  }
}
```

### Check Workflow Status
```bash
POST /workflow_status
Content-Type: application/json

{
  "thread_id": "meal_plan_USER_ID_TIMESTAMP"
}
```

### Other Endpoints
- `GET /` - API information
- `GET /docs` - Interactive API documentation
- `GET /healthz` - Health check

## 🛠️ Development

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Access API at http://localhost:8080
```

### Docker Build
```bash
# Build container
docker build -t healthynest-planner .

# Run container
docker run -p 8080:8080 --env-file .env healthynest-planner
```

### Cloud Deployment
```bash
# Deploy to Google Cloud Run
gcloud run deploy healthynest-planner \
  --source . \
  --platform managed \
  --region europe-west1 \
  --set-env-vars SUPABASE_URL='...',SUPABASE_KEY='...',SPOONACULAR_API_KEY='...',GOOGLE_API_KEY='...'
```


## 📊 Architecture

### LangGraph Workflow
1. **Get Plan Request** - Parse initial scheduling description
2. **Create Meal Plan Shell** - Initialize database record
3. **Generate Attendee Calendar** - LLM creates meal schedule
4. **Present Calendar for Confirmation** - HITL pause point
5. **Process Confirmed Calendar** - Handle user modifications
6. **Recipe Selection Loop** - For each meal slot:
   - Get candidate recipes based on dietary needs
   - LLM intelligent selection
   - Store draft plan item
7. **Present Full Plan for Review** - HITL pause point
8. **Save Finalized Plan** - Persist to database

### State Management
- **Thread-based Isolation**: Each workflow has unique thread ID
- **MemorySaver Checkpointer**: LangGraph state persistence
- **HITL Interrupt Points**: Workflow pauses at designated nodes
- **User Input Integration**: External input merged into workflow state
