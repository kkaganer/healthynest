# Corrected HealthyNest API Usage Guide

## Valid User IDs

Based on the database, these are the valid user IDs:
- `1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5`
- `ead69674-d3a1-4925-893e-d46c3dd7e58b`
- `a1fe4fe7-b9cd-43af-a5a3-a87313a86db0`

## Corrected API Examples

### 1. Start New Meal Plan (Working Example)

```bash
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/start_plan \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
    "start_date": "2025-06-10",
    "days_to_generate": 1,
    "plan_description": "test meal plan for testing"
  }'
```

**Expected Response:**
```json
{
  "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749053421",
  "status": "paused",
  "hitl_step_required": "confirm_calendar",
  "hitl_data_for_ui": {
    "calendar": {
      "Tuesday": {
        "breakfast": ["test"],
        "lunch": ["test"],
        "dinner": ["test"]
      }
    }
  },
  "error_message": null
}
```

### 2. Resume Plan - Calendar Confirmation

```bash
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -H 'Content-Type: application/json' \
  -d '{
    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749053421",
    "user_input": {
      "confirmed_calendar": {
        "Tuesday": {
          "breakfast": ["test"],
          "lunch": ["test"],
          "dinner": ["test"]
        }
      }
    }
  }'
```

**Expected Response:**
```json
{
  "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749053421",
  "status": "paused",
  "hitl_step_required": "review_full_plan",
  "hitl_data_for_ui": [
    {
      "day": "Tuesday",
      "meal_type": "Breakfast",
      "actual_date": "2025-06-10",
      "attendees": ["test"],
      "recipe_id": "26c4bd40-6dd8-4311-9664-0a1d3cce51ac",
      "recipe_name": "Asparagus and Asiago Frittata",
      "spoonacular_id": 632925,
      "image_url": "https://img.spoonacular.com/recipes/632925-312x231.jpg",
      "alternative_recipes": [...]
    }
  ]
}
```

### 3. Resume Plan - Final Approval

```bash
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -H 'Content-Type: application/json' \
  -d '{
    "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749053421",
    "user_input": {
      "confirmed_plan": []
    }
  }'
```

**Expected Response:**
```json
{
  "thread_id": "meal_plan_1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5_1749053421",
  "status": "completed",
  "hitl_step_required": null,
  "error_message": null,
  "final_plan_saved_status": "success"
}
```

## Database Requirements Met

The corrected usage respects all database constraints:
- Uses valid user_id that exists in Users table
- Foreign key relationships maintained
- Proper data types and formats


## Testing Commands Summary

```bash
# Test 1: Start workflow (use valid user_id)
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/start_plan \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5","start_date":"2025-06-10","days_to_generate":1,"plan_description":"test meal plan for testing"}'

# Test 2: Confirm calendar (use thread_id from step 1 response)
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -H 'Content-Type: application/json' \
  -d '{"thread_id":"<THREAD_ID_FROM_STEP_1>","user_input":{"confirmed_calendar":{"Tuesday":{"breakfast":["test"],"lunch":["test"],"dinner":["test"]}}}}'

# Test 3: Approve plan (use same thread_id)
curl -X POST https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan \
  -H 'Authorization: Bearer healthynest-secret-key-2025' \
  -H 'Content-Type: application/json' \
  -d '{"thread_id":"<THREAD_ID_FROM_STEP_1>","user_input":{"confirmed_plan":[]}}'
```