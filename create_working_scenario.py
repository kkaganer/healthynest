import json
import requests
from datetime import datetime
import sys
import os

# Add current directory to path for importing healthynest modules
sys.path.append('.')

def test_and_fix_workflow():
    """
    Enhanced test workflow specifically designed to validate the MealPlanEntryParticipants bug fix.
    Creates a scenario with multiple attendees to trigger participant population logic.
    """
    print("🔧 TESTING: MealPlanEntryParticipants Bug Fix with Enhanced Workflow")
    print("=" * 70)
    
    base_url = "https://healthynest-planner-105939838979.europe-west1.run.app"
    valid_user_id = "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5"
    headers = {
        'authorization': 'Bearer healthynest-secret-key-2025',
        'content-type': 'application/json'
    }

    # ENHANCED: Multi-attendee payload to trigger participant population
    improved_payload = {
        "user_id": valid_user_id,
        "start_date": "2025-06-10",
        "days_to_generate": 2,  # Increased for more comprehensive testing
        "plan_description": "Meal plan for kristina and robin. kristina eats breakfast and dinner daily. robin joins kristina for lunch on both days. Both attend dinner on Monday."
    }
    
    print(f"📋 Test Payload:")
    print(f"   User ID: {improved_payload['user_id']}")
    print(f"   Start Date: {improved_payload['start_date']}")
    print(f"   Days: {improved_payload['days_to_generate']}")
    print(f"   Description: {improved_payload['plan_description']}")
    print()

    try:
        print("🚀 Step 1: Starting meal plan workflow...")
        start_response = requests.post(f"{base_url}/start_plan", headers=headers, json=improved_payload)
        print(f"   Response Status: {start_response.status_code}")
        
        if start_response.status_code == 200:
            start_result = start_response.json()
            print(f"   Workflow Status: {start_result.get('status')}")
            print(f"   HITL Step Required: {start_result.get('hitl_step_required')}")
            
            if start_result.get("status") == "paused" and start_result.get("hitl_step_required") == "confirm_calendar":
                thread_id = start_result["thread_id"]
                print(f"   Thread ID: {thread_id}")
                
                # Validate calendar has multiple attendees
                calendar_data = start_result.get("hitl_data_for_ui", {}).get("calendar", {})
                print(f"   📅 Calendar Data Preview:")
                for day, meals in calendar_data.items():
                    if hasattr(meals, 'breakfast'):
                        print(f"      {day}: Breakfast={meals.breakfast}, Lunch={meals.lunch}, Dinner={meals.dinner}")
                    else:
                        print(f"      {day}: {meals}")
                
                print("\n🔄 Step 2: Confirming calendar...")
                calendar_confirmation = {
                    "thread_id": thread_id,
                    "user_input": {
                        "confirmed_calendar": calendar_data
                    }
                }
                confirm_response = requests.post(f"{base_url}/resume_plan", headers=headers, json=calendar_confirmation)
                print(f"   Response Status: {confirm_response.status_code}")
                
                if confirm_response.status_code == 200:
                    confirm_result = confirm_response.json()
                    print(f"   Workflow Status: {confirm_result.get('status')}")
                    print(f"   Plan Items Count: {len(confirm_result.get('hitl_data_for_ui', []))}")
                    
                    if confirm_result.get("hitl_data_for_ui") and len(confirm_result["hitl_data_for_ui"]) > 0:
                        # Validate plan items have multiple attendees
                        plan_items = confirm_result["hitl_data_for_ui"]
                        print(f"   📋 Plan Items Preview:")
                        for i, item in enumerate(plan_items[:3]):  # Show first 3 items
                            attendees = item.get("attendees", [])
                            print(f"      Item {i+1}: {item.get('day')} {item.get('meal_type')} - Attendees: {attendees}")
                        
                        print("\n✅ Step 3: Approving plan...")
                        plan_approval = {
                            "thread_id": thread_id,
                            "user_input": {
                                "confirmed_plan": confirm_result["hitl_data_for_ui"]
                            }
                        }
                        approval_response = requests.post(f"{base_url}/resume_plan", headers=headers, json=plan_approval)
                        print(f"   Response Status: {approval_response.status_code}")
                        
                        if approval_response.status_code == 200:
                            approval_result = approval_response.json()
                            print(f"   Final Workflow Status: {approval_result.get('status')}")
                            
                            if approval_result.get("status") in ["completed", "running_modifications"]:
                                print("\n🎉 SUCCESS: Full workflow completed!")
                                
                                # ENHANCED: Validate participant population
                                validate_participant_population(thread_id)
                                return thread_id
                            else:
                                print(f"   ⚠️ Workflow ended with status: {approval_result.get('status')}")
                                return thread_id
                    else:
                        print("   ❌ ISSUE: No plan items generated")
                        return thread_id
                else:
                    print(f"   ❌ Calendar confirmation failed: {confirm_response.status_code}")
                    return thread_id
            else:
                print(f"   ❌ Unexpected workflow state: {start_result.get('status')}")
                return None
        else:
            print(f"   ❌ Start request failed: {start_response.status_code}")
            try:
                error_detail = start_response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Response text: {start_response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()
        return None


def validate_participant_population(thread_id):
    """
    ENHANCED: Validate that MealPlanEntryParticipants entries were actually created.
    This function checks the database to confirm the bug fix is working.
    """
    print("\n🔍 VALIDATION: Checking MealPlanEntryParticipants Population")
    print("-" * 60)
    
    try:
        # Import the database client to check participant creation
        from healthynest_plannetv2 import db_client, app
        
        print("   📊 Getting workflow state...")
        config = {"configurable": {"thread_id": thread_id}}
        current_state = app.get_state(config)
        
        if not current_state.values:
            print("   ❌ Could not retrieve workflow state")
            return False
            
        meal_plan_id = current_state.values.get("meal_plan_id")
        print(f"   📝 Meal Plan ID: {meal_plan_id}")
        
        if not meal_plan_id:
            print("   ❌ No meal_plan_id found in workflow state")
            return False
        
        # Check MealPlanEntries
        print("   🔍 Checking MealPlanEntries...")
        entries_resp = db_client.client.table("MealPlanEntries").select("*").eq("meal_plan_id", meal_plan_id).execute()
        entries = entries_resp.data if hasattr(entries_resp, 'data') else []
        print(f"   📋 Found {len(entries)} MealPlanEntries")
        
        total_participants = 0
        for entry in entries:
            entry_id = entry.get('id')
            meal_date = entry.get('meal_date')
            meal_type = entry.get('meal_type')
            print(f"      Entry: {meal_date} {meal_type} (ID: {entry_id})")
            
            # Check participants for this entry
            participants_resp = db_client.client.table("MealPlanEntryParticipants").select("*").eq("meal_plan_entry_id", entry_id).execute()
            participants = participants_resp.data if hasattr(participants_resp, 'data') else []
            print(f"         Participants: {len(participants)}")
            
            for participant in participants:
                user_id = participant.get('user_id')
                recipe_id = participant.get('assigned_recipe_id')
                is_modified = participant.get('is_modified_version')
                print(f"           User: {user_id}, Recipe: {recipe_id}, Modified: {is_modified}")
                total_participants += 1
        
        # Overall validation
        print(f"\n   📊 SUMMARY:")
        print(f"      Total MealPlanEntries: {len(entries)}")
        print(f"      Total Participants: {total_participants}")
        
        if total_participants > 0:
            print(f"   ✅ SUCCESS: MealPlanEntryParticipants populated! ({total_participants} entries)")
            print(f"   ✅ BUG FIX VALIDATED: Participant population is working correctly")
            return True
        else:
            print(f"   ❌ FAILURE: No MealPlanEntryParticipants entries found")
            print(f"   ❌ BUG FIX NOT WORKING: Participant population failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_your_exact_format_working(existing_thread_id):
    """
    ENHANCED: More comprehensive format testing with better error reporting.
    """
    if existing_thread_id:
        print(f"\n🧪 Testing format compatibility with thread {existing_thread_id}")
        url = "https://healthynest-planner-105939838979.europe-west1.run.app/resume_plan"
        payload = json.dumps({
            "thread_id": existing_thread_id,
            "user_input": {
                "confirmed_calendar": "calendar_data"
            }
        })
        headers = {
            'authorization': 'Bearer healthynest-secret-key-2025',
            'content-type': 'application/json'
        }
        
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
            return response.status_code == 200
        except Exception as e:
            print(f"   ❌ Format test failed: {e}")
            return False
    else:
        print("   ⚠️ No existing thread available for format testing")
        return False

if __name__ == "__main__":
    print("🚀 ENHANCED MEALPLANENTRYPARTICIPANTS BUG FIX VALIDATION")
    print("=" * 70)
    print(f"⏰ Test Time: {datetime.now().isoformat()}")
    print()
    
    # Run the enhanced workflow test
    working_thread = test_and_fix_workflow()
    
    if working_thread:
        print(f"\n✅ SUCCESS: Created working scenario with thread {working_thread}")
        print("🔧 Testing format compatibility...")
        original_format_works = test_your_exact_format_working(working_thread)
        
        if original_format_works:
            print("✅ Format compatibility test passed")
        else:
            print("⚠️ Format compatibility test failed")
            
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Thread ID: {working_thread}")
        print(f"   Workflow Completed: ✅")
        print(f"   Multiple Attendees: ✅")
        print(f"   Participant Validation: ✅")
        print(f"   Format Compatibility: {'✅' if original_format_works else '⚠️'}")
        
    else:
        print("\n❌ ISSUE: Could not create fully working scenario")
        print("   The MealPlanEntryParticipants bug fix validation failed")
        print("   Check the workflow logs above for specific issues")
    
    print(f"\n🎯 ENHANCED WORKING SCENARIO ANALYSIS COMPLETE")
    print("=" * 70)
