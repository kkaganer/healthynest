from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, Any
import os
from healthynest_plannetv2 import start_new_meal_plan, resume_meal_plan_workflow, get_workflow_status

# Security setup
security = HTTPBearer()
API_KEY = os.getenv("API_KEY", "healthynest-secret-key-2025")

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify the API key from Authorization header.
    Expected format: Authorization: Bearer <API_KEY>
    """
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

app = FastAPI(
    title="HealthyNest Meal Planner API", 
    version="1.0.0",
    description="A Human-in-the-Loop (HITL) meal planning service using LangGraph workflows",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Pydantic models for request bodies
class StartPlanRequest(BaseModel):
    user_id: str = Field(..., description="UUID of the user requesting the meal plan", example="1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format", example="2025-06-10")
    days_to_generate: int = Field(..., description="Number of days to plan meals for", example=3, ge=1, le=14)
    plan_description: str = Field(..., description="Natural language description of attendees and meal schedule", example="Plan for kristina. robin joins kristina for lunch on Monday and Tuesday. max joins kristina for dinner on Tuesday only.")

class ResumePlanRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID of the paused workflow", example="meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488")
    user_input: Dict[str, Any] = Field(..., description="User's confirmation or modifications", example={"confirmed_calendar": {"Monday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina"]}}})

class WorkflowStatusRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID of the workflow to check", example="meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488")

@app.get("/")
async def root():
    """
    Root endpoint with API information and authentication guide.
    This endpoint is public and doesn't require authentication.
    """
    return {
        "message": "HealthyNest Meal Planner API",
        "version": "1.0.0",
        "description": "Human-in-the-Loop meal planning with LangGraph workflows",
        "authentication": {
            "type": "Bearer Token",
            "header": "Authorization: Bearer <API_KEY>",
            "api_key": "Contact administrator for API key"
        },
        "endpoints": {
            "start_plan": "POST /start_plan - Start a new meal planning workflow (requires auth)",
            "resume_plan": "POST /resume_plan - Resume a paused workflow with user input (requires auth)", 
            "workflow_status": "POST /workflow_status - Check workflow status (requires auth)",
            "health": "GET /healthz - Health check (public)",
            "docs": "GET /docs - Interactive API documentation (public)",
            "documentation": "GET /api-docs - Complete API documentation (public)"
        },
        "quick_start": {
            "step_1": "Get API key from administrator",
            "step_2": "POST /start_plan with Authorization: Bearer <API_KEY>",
            "step_3": "Follow HITL workflow as documented"
        }
    }

@app.get("/healthz")
@app.get("/healthz/", include_in_schema=False)
async def health_check():
    """
    Health check endpoint for Cloud Run and monitoring systems.
    This endpoint is public and doesn't require authentication.
    """
    return {"status": "healthy", "service": "healthynest-planner", "version": "1.0.0"}

@app.get("/api-docs")
async def api_documentation():
    """
    Complete API documentation with examples and workflow details.
    This endpoint is public and doesn't require authentication.
    """
    return {
        "title": "HealthyNest Meal Planner API Documentation",
        "version": "1.0.0",
        "description": "Complete documentation for the Human-in-the-Loop meal planning service",
        "base_url": "https://healthynest-planner-105939838979.europe-west1.run.app",
        "authentication": {
            "type": "Bearer Token",
            "description": "All workflow endpoints require authentication",
            "header_format": "Authorization: Bearer <API_KEY>",
            "api_key": "healthynest-secret-key-2025",
            "note": "Include the Authorization header in all authenticated requests"
        },
        "workflow_overview": {
            "description": "The meal planning process follows a Human-in-the-Loop (HITL) pattern with two pause points",
            "steps": [
                "1. User starts workflow with meal planning request (authenticated)",
                "2. LLM generates attendee calendar from natural language description",
                "3. WORKFLOW PAUSES - User confirms/modifies calendar (authenticated)",
                "4. System generates recipes for each meal slot",
                "5. WORKFLOW PAUSES - User reviews/modifies complete meal plan (authenticated)",
                "6. System saves finalized plan to database and completes workflow"
            ]
        },
        "endpoints": {
            "/start_plan": {
                "method": "POST",
                "description": "Initiates a new meal planning workflow",
                "authentication": "Required",
                "url": "https://healthynest-planner-105939838979.europe-west1.run.app/start_plan",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer healthynest-secret-key-2025"
                },
                "request_body": {
                    "user_id": "UUID of the user (string, required)",
                    "start_date": "Start date in YYYY-MM-DD format (string, required)",
                    "days_to_generate": "Number of days to plan, 1-14 (integer, required)",
                    "plan_description": "Natural language meal schedule description (string, required)"
                },
                "example_request": {
                    "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
                    "start_date": "2025-06-10",
                    "days_to_generate": 3,
                    "plan_description": "Plan for kristina. robin joins kristina for lunch on Monday and Tuesday. max joins kristina for dinner on Tuesday only."
                },
                "example_response": {
                    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
                    "status": "paused",
                    "hitl_step_required": "confirm_calendar",
                    "hitl_data_for_ui": {
                        "calendar": {
                            "Monday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina"]},
                            "Tuesday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina", "max"]},
                            "Wednesday": {"breakfast": ["kristina"], "lunch": ["kristina"], "dinner": ["kristina"]}
                        }
                    },
                    "error_message": None
                },
                "curl_example": "curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/start_plan -H 'Content-Type: application/json' -H 'Authorization: Bearer healthynest-secret-key-2025' -d '{\"user_id\":\"1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5\",\"start_date\":\"2025-06-10\",\"days_to_generate\":3,\"plan_description\":\"Plan for kristina. robin joins for lunch Monday and Tuesday.\"}'"
            },
            "/resume_plan": {
                "method": "POST",
                "description": "Resumes a paused workflow with user input/confirmation",
                "authentication": "Required",
                "url": "https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer healthynest-secret-key-2025"
                },
                "request_body": {
                    "thread_id": "Thread ID from previous response (string, required)",
                    "user_input": "User confirmation/modifications (object, required)"
                },
                "example_request_calendar_confirmation": {
                    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
                    "user_input": {
                        "confirmed_calendar": {
                            "Monday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina"]},
                            "Tuesday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina", "max"]},
                            "Wednesday": {"breakfast": ["kristina"], "lunch": ["kristina"], "dinner": ["kristina"]}
                        }
                    }
                },
                "example_request_plan_approval": {
                    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
                    "user_input": {
                        "confirmed_plan": "Array of meal plan items (or empty object for approval)"
                    }
                },
                "example_response": {
                    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
                    "status": "paused",
                    "hitl_step_required": "review_full_plan",
                    "hitl_data_for_ui": "Array of meal plan items for review",
                    "error_message": None
                },
                "curl_example": "curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan -H 'Content-Type: application/json' -H 'Authorization: Bearer healthynest-secret-key-2025' -d '{\"thread_id\":\"meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488\",\"user_input\":{\"confirmed_calendar\":{\"Monday\":{\"breakfast\":[\"kristina\"],\"lunch\":[\"kristina\",\"robin\"],\"dinner\":[\"kristina\"]}}}}'"
            },
            "/workflow_status": {
                "method": "POST",
                "description": "Checks the current status of a workflow",
                "authentication": "Required",
                "url": "https://healthynest-planner-105939838979.europe-west1.run.app/workflow_status",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer healthynest-secret-key-2025"
                },
                "request_body": {
                    "thread_id": "Thread ID to check (string, required)"
                },
                "example_request": {
                    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488"
                },
                "example_response": {
                    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
                    "status": "paused",
                    "hitl_step_required": "confirm_calendar",
                    "hitl_data_for_ui": "Data structure for UI interaction",
                    "error_message": None
                },
                "curl_example": "curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/workflow_status -H 'Content-Type: application/json' -H 'Authorization: Bearer healthynest-secret-key-2025' -d '{\"thread_id\":\"meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488\"}'"
            }
        },
        "workflow_states": {
            "running": "Workflow is actively processing",
            "paused": "Workflow is waiting for user input at HITL point",
            "completed": "Workflow has finished successfully",
            "error": "Workflow encountered an error",
            "running_modifications": "Workflow is processing recipe modifications"
        },
        "hitl_steps": {
            "confirm_calendar": {
                "description": "User needs to confirm/modify the generated attendee calendar",
                "expected_input": "confirmed_calendar object with day names as keys"
            },
            "review_full_plan": {
                "description": "User needs to review/approve the complete meal plan",
                "expected_input": "confirmed_plan array or approval confirmation"
            }
        },
        "error_handling": {
            "http_status_codes": {
                "200": "Success",
                "401": "Unauthorized - Invalid or missing API key",
                "500": "Internal server error - check error_message in response"
            },
            "common_errors": [
                "Invalid or missing Authorization header",
                "Invalid thread_id - workflow not found",
                "Missing required fields in request body",
                "Database connection errors",
                "LLM API rate limiting"
            ]
        },
        "deployment_info": {
            "platform": "Google Cloud Run",
            "region": "europe-west1",
            "url": "https://healthynest-planner-105939838979.europe-west1.run.app",
            "security": "Bearer token authentication required for workflow endpoints"
        },
        "database": {
            "backend": "Supabase",
            "tables": ["MealPlans", "MealPlanEntries", "MealPlanRecipes", "MealPlanEntryParticipants"],
            "persistence": "All meal plans and recipes saved automatically on workflow completion"
        }
    }

@app.post("/start_plan")
async def start_plan(request: StartPlanRequest, api_key: str = Depends(verify_api_key)):
    """
    Initiates a new meal planning workflow.
    
    Requires Authentication: Bearer token in Authorization header
    
    This endpoint creates a new LangGraph workflow instance that:
    1. Processes the natural language meal description
    2. Generates an attendee calendar using LLM
    3. Pauses for user confirmation (HITL)
    4. Continues with recipe selection and meal planning
    5. Pauses for final plan review (HITL)
    6. Saves completed plan to database
    
    Returns a thread_id for tracking the workflow and any immediate HITL data.
    """
    try:
        result = start_new_meal_plan(
            user_id=request.user_id,
            start_date=request.start_date,
            days_to_generate=request.days_to_generate,
            plan_description=request.plan_description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume_plan")
async def resume_plan(request: ResumePlanRequest, api_key: str = Depends(verify_api_key)):
    """
    Resumes a paused meal planning workflow with user input.
    
    Requires Authentication: Bearer token in Authorization header
    
    Use this endpoint to:
    - Confirm/modify attendee calendar at first HITL pause
    - Approve/modify final meal plan at second HITL pause
    
    The workflow will continue from where it paused and may pause again
    at the next HITL point or complete if this was the final step.
    """
    try:
        result = resume_meal_plan_workflow(
            thread_id=request.thread_id,
            user_input=request.user_input
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow_status")
async def workflow_status(request: WorkflowStatusRequest, api_key: str = Depends(verify_api_key)):
    """
    Gets the current status of a workflow.
    
    Requires Authentication: Bearer token in Authorization header
    
    Use this endpoint to check:
    - Current workflow state (running, paused, completed, error)
    - What HITL step is required (if any)
    - Available data for UI interaction
    - Any error messages
    """
    try:
        result = get_workflow_status(request.thread_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))