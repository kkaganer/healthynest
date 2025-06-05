# HealthyNest Meal Planning API - Comprehensive Usage Guide

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Complete Workflow Examples](#complete-workflow-examples)
5. [HITL (Human-in-the-Loop) Patterns](#hitl-patterns)
6. [Error Handling](#error-handling)
7. [Troubleshooting](#troubleshooting)
8. [Database Integration](#database-integration)

## Overview

The HealthyNest Meal Planning API provides a Human-in-the-Loop (HITL) meal planning service using LangGraph workflows. The system generates personalized meal plans based on natural language descriptions and allows user confirmation at key decision points.

**Production URL**: `https://healthynest-planner-105939838979.europe-west1.run.app`

### Key Features
- **HITL Workflow**: Two pause points for user confirmation
- **Natural Language Processing**: LLM-powered meal plan generation
- **Multi-attendee Support**: Handle complex scheduling scenarios
- **Database Persistence**: Automatic saving to Supabase
- **Recipe Modifications**: LLM-powered recipe adaptations for dietary needs

## Authentication

All workflow endpoints require Bearer token authentication.

**API Key**: `healthynest-secret-key-2025`

### Required Headers
```http
Authorization: Bearer healthynest-secret-key-2025
Content-Type: application/json
```

### Python Example
```python
import requests

headers = {
    'Authorization': 'Bearer healthynest-secret-key-2025',
    'Content-Type': 'application/json'
}

base_url = "https://healthynest-planner-105939838979.europe-west1.run.app"
```

## API Endpoints

### 1. Public Endpoints

#### GET `/` - API Information
Returns API information and quick start guide.

```python
response = requests.get(f"{base_url}/")
print(response.json())
```

**Response Example**:
```json
{
  "message": "HealthyNest Meal Planner API",
  "version": "1.0.0",
  "description": "Human-in-the-Loop meal planning with LangGraph workflows",
  "authentication": {
    "type": "Bearer Token",
    "header": "Authorization: Bearer <API_KEY>"
  },
  "endpoints": {
    "start_plan": "POST /start_plan - Start a new meal planning workflow",
    "resume_plan": "POST /resume_plan - Resume a paused workflow",
    "workflow_status": "POST /workflow_status - Check workflow status"
  }
}
```

#### GET `/healthz` - Health Check
```python
response = requests.get(f"{base_url}/healthz")
# Returns: {"status": "healthy", "service": "healthynest-planner", "version": "1.0.0"}
```

#### GET `/api-docs` - Complete API Documentation
Returns comprehensive API documentation with examples.

### 2. Workflow Endpoints (Authentication Required)

#### POST `/start_plan` - Start New Meal Plan

Initiates a new meal planning workflow that will pause for user confirmation.

**Request Body**:
```python
payload = {
    "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",  # UUID string
    "start_date": "2025-06-10",                          # YYYY-MM-DD format
    "days_to_generate": 3,                               # 1-14 days
    "plan_description": "Plan for kristina. robin joins kristina for lunch on Monday and Tuesday. max joins kristina for dinner on Tuesday only."
}

response = requests.post(f"{base_url}/start_plan", headers=headers, json=payload)
```

**Response Example**:
```json
{
  "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
  "status": "paused",
  "hitl_step_required": "confirm_calendar",
  "hitl_data_for_ui": {
    "calendar": {
      "Monday": {
        "breakfast": ["kristina"],
        "lunch": ["kristina", "robin"],
        "dinner": ["kristina"]
      },
      "Tuesday": {
        "breakfast": ["kristina"],
        "lunch": ["kristina", "robin"], 
        "dinner": ["kristina", "max"]
      },
      "Wednesday": {
        "breakfast": ["kristina"],
        "lunch": ["kristina"],
        "dinner": ["kristina"]
      }
    }
  },
  "error_message": null
}
```

#### POST `/resume_plan` - Resume Paused Workflow

Continues a paused workflow with user input.

**Calendar Confirmation Example**:
```python
resume_payload = {
    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
    "user_input": {
        "confirmed_calendar": {
            "Monday": {
                "breakfast": ["kristina"],
                "lunch": ["kristina", "robin"],
                "dinner": ["kristina"]
            },
            "Tuesday": {
                "breakfast": ["kristina"],
                "lunch": ["kristina", "robin"],
                "dinner": ["kristina", "max"]
            },
            "Wednesday": {
                "breakfast": ["kristina"],
                "lunch": ["kristina"],
                "dinner": ["kristina"]
            }
        }
    }
}

response = requests.post(f"{base_url}/resume_plan", headers=headers, json=resume_payload)
```

**Plan Approval Example**:
```python
approve_payload = {
    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
    "user_input": {
        "confirmed_plan": [
            {
                "day": "Monday",
                "meal_type": "Breakfast",
                "actual_date": "2025-06-10",
                "attendees": ["kristina"],
                "recipe_id": "123",
                "recipe_name": "Oatmeal with Berries",
                "spoonacular_id": 556668
            }
            # ... more meal plan items
        ]
    }
}

response = requests.post(f"{base_url}/resume_plan", headers=headers, json=approve_payload)
```

#### POST `/workflow_status` - Check Workflow Status

Get current status of any workflow.

```python
status_payload = {
    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488"
}

response = requests.post(f"{base_url}/workflow_status", headers=headers, json=status_payload)
```

**Response Example**:
```json
{
  "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749048488",
  "status": "paused",
  "hitl_step_required": "confirm_calendar",
  "hitl_data_for_ui": { /* calendar or plan data */ },
  "error_message": null
}
```

## Complete Workflow Examples

### Example 1: Simple Single-User Meal Plan

```python
import requests
import json

# Configuration
base_url = "https://healthynest-planner-105939838979.europe-west1.run.app"
headers = {
    'Authorization': 'Bearer healthynest-secret-key-2025',
    'Content-Type': 'application/json'
}

def simple_meal_plan_workflow():
    """Complete workflow for a simple single-user meal plan"""
    
    # Step 1: Start the workflow
    print("Step 1: Starting meal plan workflow...")
    start_payload = {
        "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
        "start_date": "2025-06-15",
        "days_to_generate": 1,
        "plan_description": "Plan for kristina. She needs breakfast, lunch, and dinner for Friday."
    }
    
    response = requests.post(f"{base_url}/start_plan", headers=headers, json=start_payload)
    
    if response.status_code != 200:
        print(f"Error starting workflow: {response.status_code}")
        return False
    
    result = response.json()
    thread_id = result["thread_id"]
    print(f"Workflow started with thread ID: {thread_id}")
    
    # Step 2: Confirm calendar (First HITL pause)
    if result["status"] == "paused" and result["hitl_step_required"] == "confirm_calendar":
        print("Step 2: Confirming generated calendar...")
        
        calendar_data = result["hitl_data_for_ui"]["calendar"]
        print(f"Generated calendar: {json.dumps(calendar_data, indent=2)}")
        
        confirm_payload = {
            "thread_id": thread_id,
            "user_input": {"confirmed_calendar": calendar_data}
        }
        
        response = requests.post(f"{base_url}/resume_plan", headers=headers, json=confirm_payload)
        result = response.json()
    
    # Step 3: Approve meal plan (Second HITL pause)
    if result["status"] == "paused" and result["hitl_step_required"] == "review_full_plan":
        print("Step 3: Reviewing and approving meal plan...")
        
        plan_data = result["hitl_data_for_ui"]
        print(f"Generated plan has {len(plan_data)} meals")
        
        # Print meal plan summary
        for item in plan_data:
            print(f"  {item['day']} {item['meal_type']}: {item['recipe_name']}")
        
        approve_payload = {
            "thread_id": thread_id,
            "user_input": {"confirmed_plan": plan_data}
        }
        
        response = requests.post(f"{base_url}/resume_plan", headers=headers, json=approve_payload)
        result = response.json()
    
    # Step 4: Check final status
    final_status = result.get("status")
    print(f"Final workflow status: {final_status}")
    
    if final_status in ["completed", "running_modifications"]:
        print("✅ Meal plan workflow completed successfully!")
        print("✅ Data has been saved to the database")
        return True
    else:
        print(f"❌ Workflow ended with unexpected status: {final_status}")
        return False

# Run the example
if __name__ == "__main__":
    success = simple_meal_plan_workflow()
    print(f"Workflow result: {'Success' if success else 'Failed'}")
```

### Example 2: Multi-Attendee Complex Scenario

```python
def complex_multi_attendee_workflow():
    """Complete workflow with multiple attendees and complex scheduling"""
    
    print("Starting complex multi-attendee meal plan...")
    
    # Step 1: Start with complex description
    start_payload = {
        "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
        "start_date": "2025-06-20",
        "days_to_generate": 3,
        "plan_description": "Plan for kristina and robin. kristina eats breakfast and dinner daily. robin joins kristina for lunch on Monday and Tuesday. Both attend dinner on Monday. max joins for dinner on Tuesday only."
    }
    
    response = requests.post(f"{base_url}/start_plan", headers=headers, json=start_payload)
    result = response.json()
    thread_id = result["thread_id"]
    
    print(f"Complex workflow started: {thread_id}")
    
    # Step 2: Review and potentially modify calendar
    if result["hitl_step_required"] == "confirm_calendar":
        calendar = result["hitl_data_for_ui"]["calendar"]
        
        # Example: Modify the calendar before confirming
        # Add robin to Wednesday lunch
        if "Wednesday" in calendar:
            calendar["Wednesday"]["lunch"] = ["kristina", "robin"]
        
        print("Modified calendar to add robin to Wednesday lunch")
        
        confirm_payload = {
            "thread_id": thread_id,
            "user_input": {"confirmed_calendar": calendar}
        }
        
        response = requests.post(f"{base_url}/resume_plan", headers=headers, json=confirm_payload)
        result = response.json()
    
    # Step 3: Review plan and make recipe swaps
    if result["hitl_step_required"] == "review_full_plan":
        plan_items = result["hitl_data_for_ui"]
        
        # Example: Swap a recipe for Monday dinner
        monday_dinner = None
        for item in plan_items:
            if item["day"] == "Monday" and item["meal_type"] == "Dinner":
                monday_dinner = item
                break
        
        # Create modified plan with recipe swap
        modified_plan = plan_items.copy()
        if monday_dinner and len(monday_dinner.get("alternative_recipes", [])) > 0:
            # Swap to first alternative recipe
            alternative = monday_dinner["alternative_recipes"][0]
            monday_dinner["recipe_id"] = alternative["id"]
            monday_dinner["recipe_name"] = alternative["name"]
            print(f"Swapped Monday dinner to: {alternative['name']}")
        
        approve_payload = {
            "thread_id": thread_id,
            "user_input": {"confirmed_plan": modified_plan}
        }
        
        response = requests.post(f"{base_url}/resume_plan", headers=headers, json=approve_payload)
        result = response.json()
    
    print(f"Complex workflow completed with status: {result.get('status')}")
    return result.get("status") in ["completed", "running_modifications"]

# Run complex example
complex_success = complex_multi_attendee_workflow()
```

### Example 3: Error Handling and Status Monitoring

```python
def workflow_with_error_handling():
    """Demonstrates proper error handling and status monitoring"""
    
    def check_workflow_status(thread_id):
        """Helper to check and print workflow status"""
        status_payload = {"thread_id": thread_id}
        response = requests.post(f"{base_url}/workflow_status", headers=headers, json=status_payload)
        
        if response.status_code == 200:
            status = response.json()
            print(f"Status: {status['status']}, HITL Step: {status.get('hitl_step_required', 'None')}")
            return status
        else:
            print(f"Status check failed: {response.status_code}")
            return None
    
    try:
        # Start workflow with potential error scenarios
        start_payload = {
            "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
            "start_date": "2025-06-25",
            "days_to_generate": 2,
            "plan_description": "Plan for kristina with vegan preferences and alex with gluten-free needs."
        }
        
        response = requests.post(f"{base_url}/start_plan", headers=headers, json=start_payload)
        
        if response.status_code != 200:
            print(f"Start failed: {response.status_code}")
            print(f"Error details: {response.text}")
            return False
        
        result = response.json()
        thread_id = result["thread_id"]
        
        # Monitor status throughout workflow
        print("Initial status:")
        check_workflow_status(thread_id)
        
        # Handle first HITL pause with validation
        if result.get("error_message"):
            print(f"Error in workflow: {result['error_message']}")
            return False
        
        if result["hitl_step_required"] == "confirm_calendar":
            calendar_data = result["hitl_data_for_ui"]["calendar"]
            
            # Validate calendar before confirming
            if not calendar_data:
                print("Error: Empty calendar data received")
                return False
            
            confirm_payload = {
                "thread_id": thread_id,
                "user_input": {"confirmed_calendar": calendar_data}
            }
            
            response = requests.post(f"{base_url}/resume_plan", headers=headers, json=confirm_payload)
            
            if response.status_code != 200:
                print(f"Resume failed: {response.status_code}")
                return False
            
            result = response.json()
            
            print("After calendar confirmation:")
            check_workflow_status(thread_id)
        
        # Handle second HITL pause
        if result["hitl_step_required"] == "review_full_plan":
            plan_data = result["hitl_data_for_ui"]
            
            # Validate plan data
            if not isinstance(plan_data, list) or len(plan_data) == 0:
                print("Error: Invalid or empty plan data")
                return False
            
            # Check for placeholder recipes (indicates planning issues)
            placeholder_count = sum(1 for item in plan_data if item.get("recipe_id") == "placeholder_not_found")
            if placeholder_count > 0:
                print(f"Warning: {placeholder_count} meals could not be planned (placeholder recipes)")
            
            approve_payload = {
                "thread_id": thread_id,
                "user_input": {"confirmed_plan": plan_data}
            }
            
            response = requests.post(f"{base_url}/resume_plan", headers=headers, json=approve_payload)
            result = response.json()
            
            print("Final status:")
            final_status = check_workflow_status(thread_id)
            
            if final_status and final_status.get("status") in ["completed", "running_modifications"]:
                print("✅ Workflow completed successfully with error handling")
                return True
            else:
                print("❌ Workflow did not complete successfully")
                return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"Timeout error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

# Run error handling example
error_handling_success = workflow_with_error_handling()
```

## HITL (Human-in-the-Loop) Patterns

The HealthyNest API follows a two-stage HITL pattern:

### Stage 1: Calendar Confirmation

**Trigger**: After LLM generates attendee calendar from natural language
**Purpose**: Allow user to review and modify meal scheduling
**Data Format**: Nested dictionary with days and meal types

```python
# Calendar confirmation pattern
calendar_confirmation = {
    "confirmed_calendar": {
        "Monday": {
            "breakfast": ["kristina"],
            "lunch": ["kristina", "robin"],
            "dinner": ["kristina"]
        },
        "Tuesday": {
            "breakfast": ["kristina"],
            "lunch": ["kristina", "robin"],
            "dinner": ["kristina", "max"]
        }
    }
}
```

### Stage 2: Plan Review and Approval

**Trigger**: After recipe selection and meal plan generation
**Purpose**: Allow user to review recipes, swap alternatives, and approve final plan
**Data Format**: Array of meal plan items with recipe details

```python
# Plan approval pattern
plan_approval = {
    "confirmed_plan": [
        {
            "day": "Monday",
            "meal_type": "Breakfast",
            "actual_date": "2025-06-10",
            "attendees": ["kristina"],
            "recipe_id": "123",
            "recipe_name": "Oatmeal with Berries",
            "spoonacular_id": 556668,
            "alternative_recipes": [
                {"id": "124", "name": "Greek Yogurt Parfait"},
                {"id": "125", "name": "Avocado Toast"}
            ]
        }
    ]
}
```

### Recipe Swapping Example

```python
def swap_recipe_in_plan(plan_items, day, meal_type, new_recipe_choice):
    """Helper function to swap recipes in meal plan"""
    for item in plan_items:
        if item["day"] == day and item["meal_type"] == meal_type:
            if "alternative_recipes" in item:
                # Find the desired alternative
                for alt in item["alternative_recipes"]:
                    if alt["id"] == new_recipe_choice["id"]:
                        item["recipe_id"] = alt["id"]
                        item["recipe_name"] = alt["name"]
                        item["spoonacular_id"] = alt.get("spoonacular_id")
                        return True
    return False

# Usage example
plan_data = result["hitl_data_for_ui"]
swap_recipe_in_plan(plan_data, "Monday", "Dinner", {"id": "456", "name": "Pasta Primavera"})
```

## Error Handling

### Common HTTP Status Codes

- **200**: Success
- **401**: Unauthorized - Invalid or missing API key
- **500**: Internal server error - Check error_message in response

### Error Response Format

```json
{
  "detail": "Error description",
  "status_code": 500
}
```

## cURL Examples

For quick testing without Python:

### Start Workflow
```bash
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/start_plan \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -d '{
    "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
    "start_date": "2025-06-10",
    "days_to_generate": 1,
    "plan_description": "Plan for kristina breakfast and lunch"
  }'
```

### Resume Workflow (Calendar Confirmation)
```bash
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -d '{
    "thread_id": "THREAD_ID_FROM_START_RESPONSE",
    "user_input": {
      "confirmed_calendar": {
        "Friday": {
          "breakfast": ["kristina"],
          "lunch": ["kristina"],
          "dinner": ["kristina"]
        }
      }
    }
  }'
```

### Check Workflow Status
```bash
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/workflow_status \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -d '{
    "thread_id": "THREAD_ID_FROM_START_RESPONSE"
  }'
```

## Best Practices

1. **Always validate API responses** before proceeding to next steps
2. **Store thread_id safely** - it's required for all subsequent operations
3. **Handle HITL pauses gracefully** - don't assume immediate completion
4. **Implement proper error handling** for network and API errors
5. **Use status monitoring** for long-running workflows
6. **Validate data formats** before sending user input
7. **Implement retry logic** for transient failures

## Workflow State Management

```python
class MealPlanWorkflow:
    """Complete workflow management class"""
    
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self.thread_id = None
        self.current_status = None
    
    def start(self, user_id, start_date, days_to_generate, plan_description):
        """Start new meal plan workflow"""
        payload = {
            "user_id": user_id,
            "start_date": start_date,
            "days_to_generate": days_to_generate,
            "plan_description": plan_description
        }
        
        response = requests.post(f"{self.base_url}/start_plan", headers=self.headers, json=payload)
        result = response.json()
        
        self.thread_id = result.get("thread_id")
        self.current_status = result.get("status")
        
        return result
    
    def confirm_calendar(self, calendar_data):
        """Confirm calendar at first HITL pause"""
        if not self.thread_id:
            raise ValueError("No active workflow")
        
        payload = {
            "thread_id": self.thread_id,
            "user_input": {"confirmed_calendar": calendar_data}
        }
        
        response = requests.post(f"{self.base_url}/resume_plan", headers=self.headers, json=payload)
        result = response.json()
        
        self.current_status = result.get("status")
        return result
    
    def approve_plan(self, plan_data):
        """Approve plan at second HITL pause"""
        if not self.thread_id:
            raise ValueError("No active workflow")
        
        payload = {
            "thread_id": self.thread_id,
            "user_input": {"confirmed_plan": plan_data}
        }
        
        response = requests.post(f"{self.base_url}/resume_plan", headers=self.headers, json=payload)
        result = response.json()
        
        self.current_status = result.get("status")
        return result
    
    def check_status(self):
        """Check current workflow status"""
        if not self.thread_id:
            raise ValueError("No active workflow")
        
        payload = {"thread_id": self.thread_id}
        response = requests.post(f"{self.base_url}/workflow_status", headers=self.headers, json=payload)
        result = response.json()
        
        self.current_status = result.get("status")
        return result

# Usage example
workflow = MealPlanWorkflow(
    "https://healthynest-planner-105939838979.europe-west1.run.app",
    "healthynest-secret-key-2025"
)

# Complete workflow
start_result = workflow.start(
    "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
    "2025-06-15",
    1,
    "Plan for kristina for Friday"
)

if start_result["hitl_step_required"] == "confirm_calendar":
    calendar_result = workflow.confirm_calendar(start_result["hitl_data_for_ui"]["calendar"])
    
    if calendar_result["hitl_step_required"] == "review_full_plan":
        final_result = workflow.approve_plan(calendar_result["hitl_data_for_ui"])
        print(f"Workflow completed: {final_result['status']}")
```

This comprehensive guide provides everything needed to integrate with the HealthyNest Meal Planning API, including working code examples, error handling patterns, and best practices for production use.