#!/usr/bin/env python3
"""
Debug script to diagnose the MealPlanEntryParticipants bug.
This script runs the workflow and captures diagnostic output to identify why participants aren't being populated.
"""

import sys
import os
sys.path.append('.')

from healthynest_plannetv2 import start_new_meal_plan, resume_meal_plan_workflow, get_workflow_status

def debug_participants_workflow():
    """
    Run a meal planning workflow with diagnostic logging to identify the participants bug.
    """
    print("🔍 DEBUGGING: MealPlanEntryParticipants Population Bug")
    print("=" * 60)
    
    # Step 1: Start workflow
    print("\n--- Step 1: Starting Meal Plan Workflow ---")
    result1 = start_new_meal_plan(
        user_id="1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
        start_date="2025-05-26", 
        days_to_generate=2,  # Reduced for faster debugging
        plan_description="Plan for kristina and robin. kristina eats breakfast and dinner daily. robin joins kristina for lunch on Monday only."
    )
    
    print(f"Initial Result Status: {result1.get('status')}")
    print(f"HITL Step Required: {result1.get('hitl_step_required')}")
    
    if result1.get('status') != 'paused':
        print("❌ Workflow didn't pause as expected. Exiting.")
        return False
    
    thread_id = result1["thread_id"]
    
    # Step 2: Resume with calendar confirmation
    print("\n--- Step 2: Confirming Calendar ---")
    calendar_confirmation = {"confirmed_calendar": result1["hitl_data_for_ui"]["calendar"]}
    result2 = resume_meal_plan_workflow(thread_id, calendar_confirmation)
    
    print(f"After Calendar Confirmation Status: {result2.get('status')}")
    print(f"HITL Step Required: {result2.get('hitl_step_required')}")
    
    if result2.get('status') != 'paused':
        print("❌ Workflow didn't pause for plan review. Exiting.")
        return False
    
    # Step 3: Resume with plan approval
    print("\n--- Step 3: Approving Plan ---")
    plan_approval = {"confirmed_plan": result2["hitl_data_for_ui"]}
    result3 = resume_meal_plan_workflow(thread_id, plan_approval)
    
    print(f"After Plan Approval Status: {result3.get('status')}")
    print(f"Final Status: {result3.get('final_plan_saved_status')}")
    
    # Step 4: Check final status and look for participant data
    print("\n--- Step 4: Checking Final Workflow Status ---")
    final_status = get_workflow_status(thread_id)
    print(f"Workflow Final Status: {final_status.get('status')}")
    
    return thread_id

def check_database_for_participants(meal_plan_id):
    """
    Manually check if any participants were created in the database.
    """
    print(f"\n--- Database Check for Participants ---")
    try:
        from healthynest_plannetv2 import db_client
        
        # Check MealPlanEntries
        entries_resp = db_client.client.table("MealPlanEntries").select("*").eq("meal_plan_id", meal_plan_id).execute()
        entries = entries_resp.data if hasattr(entries_resp, 'data') else []
        print(f"Found {len(entries)} MealPlanEntries for meal_plan_id {meal_plan_id}")
        
        for entry in entries:
            print(f"  Entry: {entry.get('meal_date')} {entry.get('meal_type')} - ID: {entry.get('id')}")
            
            # Check participants for this entry
            participants_resp = db_client.client.table("MealPlanEntryParticipants").select("*").eq("meal_plan_entry_id", entry.get('id')).execute()
            participants = participants_resp.data if hasattr(participants_resp, 'data') else []
            print(f"    Participants: {len(participants)}")
            
            for participant in participants:
                print(f"      User: {participant.get('user_id')}, Recipe: {participant.get('assigned_recipe_id')}")
        
        # Total participants count
        total_participants_resp = db_client.client.table("MealPlanEntryParticipants").select("*").execute()
        total_participants = total_participants_resp.data if hasattr(total_participants_resp, 'data') else []
        print(f"\nTotal MealPlanEntryParticipants in database: {len(total_participants)}")
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    print("Starting MealPlanEntryParticipants Bug Debug Session")
    
    try:
        thread_id = debug_participants_workflow()
        
        if thread_id:
            print(f"\n✅ Workflow completed. Thread ID: {thread_id}")
            
            # Try to extract meal_plan_id from workflow state for database check
            try:
                from healthynest_plannetv2 import app
                config = {"configurable": {"thread_id": thread_id}}
                current_state = app.get_state(config)
                meal_plan_id = current_state.values.get("meal_plan_id") if current_state.values else None
                
                if meal_plan_id:
                    check_database_for_participants(meal_plan_id)
                else:
                    print("❌ Could not extract meal_plan_id from workflow state")
                    
            except Exception as e:
                print(f"❌ Error checking workflow state: {e}")
        else:
            print("❌ Workflow failed to complete")
            
    except Exception as e:
        print(f"❌ Error during debug session: {e}")
        import traceback
        traceback.print_exc()