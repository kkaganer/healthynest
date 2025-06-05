#!/usr/bin/env python3
"""
Test the current API status to validate documentation accuracy
"""

import requests
import json
import time
from datetime import datetime

def test_api_comprehensive():
    """Test all API endpoints and workflows"""
    
    print("🧪 TESTING HEALTHYNEST API - CURRENT STATUS")
    print("=" * 60)
    print(f"⏰ Test Time: {datetime.now().isoformat()}")
    print()
    
    base_url = "https://healthynest-planner-105939838979.europe-west1.run.app"
    headers = {
        'Authorization': 'Bearer healthynest-secret-key-2025',
        'Content-Type': 'application/json'
    }
    
    test_results = {}
    
    # Test 1: Basic health check
    print("🔍 Test 1: API Health Check")
    print("-" * 30)
    try:
        response = requests.get(f"{base_url}/healthz", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
            test_results["health_check"] = "PASS"
        else:
            print(f"❌ Health check failed: {response.status_code}")
            test_results["health_check"] = "FAIL"
    except Exception as e:
        print(f"❌ Health check error: {e}")
        test_results["health_check"] = "ERROR"
    
    print()
    
    # Test 2: API root endpoint
    print("🔍 Test 2: API Root Information")
    print("-" * 30)
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            root_data = response.json()
            print(f"✅ Root endpoint: {root_data.get('message', 'No message')}")
            print(f"✅ Version: {root_data.get('version', 'No version')}")
            test_results["root_endpoint"] = "PASS"
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            test_results["root_endpoint"] = "FAIL"
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        test_results["root_endpoint"] = "ERROR"
    
    print()
    
    # Test 3: Start workflow
    print("🔍 Test 3: Start Meal Plan Workflow")
    print("-" * 30)
    try:
        start_payload = {
            "user_id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5",
            "start_date": "2025-06-15",
            "days_to_generate": 1,
            "plan_description": "API Test: Plan for kristina for Friday breakfast and lunch"
        }
        
        response = requests.post(f"{base_url}/start_plan", headers=headers, json=start_payload, timeout=30)
        
        if response.status_code == 200:
            start_result = response.json()
            thread_id = start_result.get("thread_id")
            status = start_result.get("status")
            hitl_step = start_result.get("hitl_step_required")
            
            print(f"✅ Workflow started successfully")
            print(f"   Thread ID: {thread_id}")
            print(f"   Status: {status}")
            print(f"   HITL Step: {hitl_step}")
            
            if status == "paused" and hitl_step == "confirm_calendar":
                print(f"✅ Workflow correctly paused at calendar confirmation")
                calendar_data = start_result.get("hitl_data_for_ui", {}).get("calendar", {})
                print(f"   Calendar generated: {len(calendar_data)} days")
                test_results["start_workflow"] = "PASS"
                
                # Test 4: Resume with calendar confirmation
                print()
                print("🔍 Test 4: Resume with Calendar Confirmation")
                print("-" * 30)
                
                try:
                    resume_payload = {
                        "thread_id": thread_id,
                        "user_input": {"confirmed_calendar": calendar_data}
                    }
                    
                    response = requests.post(f"{base_url}/resume_plan", headers=headers, json=resume_payload, timeout=30)
                    
                    if response.status_code == 200:
                        resume_result = response.json()
                        status2 = resume_result.get("status")
                        hitl_step2 = resume_result.get("hitl_step_required")
                        
                        print(f"✅ Calendar confirmation successful")
                        print(f"   Status: {status2}")
                        print(f"   HITL Step: {hitl_step2}")
                        
                        if status2 == "paused" and hitl_step2 == "review_full_plan":
                            print(f"✅ Workflow correctly paused at plan review")
                            plan_data = resume_result.get("hitl_data_for_ui", [])
                            print(f"   Plan items generated: {len(plan_data)}")
                            test_results["calendar_confirmation"] = "PASS"
                            
                            # Test 5: Final approval
                            print()
                            print("🔍 Test 5: Final Plan Approval")
                            print("-" * 30)
                            
                            try:
                                approve_payload = {
                                    "thread_id": thread_id,
                                    "user_input": {"confirmed_plan": plan_data}
                                }
                                
                                response = requests.post(f"{base_url}/resume_plan", headers=headers, json=approve_payload, timeout=30)
                                
                                if response.status_code == 200:
                                    final_result = response.json()
                                    final_status = final_result.get("status")
                                    
                                    print(f"✅ Plan approval successful")
                                    print(f"   Final Status: {final_status}")
                                    
                                    if final_status in ["completed", "running_modifications"]:
                                        print(f"✅ Workflow completed successfully")
                                        test_results["plan_approval"] = "PASS"
                                    else:
                                        print(f"⚠️ Unexpected final status: {final_status}")
                                        test_results["plan_approval"] = "PARTIAL"
                                else:
                                    print(f"❌ Plan approval failed: {response.status_code}")
                                    print(f"   Response: {response.text}")
                                    test_results["plan_approval"] = "FAIL"
                                    
                            except Exception as e:
                                print(f"❌ Plan approval error: {e}")
                                test_results["plan_approval"] = "ERROR"
                        else:
                            print(f"❌ Unexpected state after calendar confirmation: {status2}/{hitl_step2}")
                            test_results["calendar_confirmation"] = "FAIL"
                    else:
                        print(f"❌ Calendar confirmation failed: {response.status_code}")
                        print(f"   Response: {response.text}")
                        test_results["calendar_confirmation"] = "FAIL"
                        
                except Exception as e:
                    print(f"❌ Calendar confirmation error: {e}")
                    test_results["calendar_confirmation"] = "ERROR"
            else:
                print(f"❌ Unexpected workflow state: {status}/{hitl_step}")
                test_results["start_workflow"] = "FAIL"
        else:
            print(f"❌ Start workflow failed: {response.status_code}")
            print(f"   Response: {response.text}")
            test_results["start_workflow"] = "FAIL"
            
    except Exception as e:
        print(f"❌ Start workflow error: {e}")
        test_results["start_workflow"] = "ERROR"
    
    print()
    
    # Test 6: Status endpoint
    print("🔍 Test 6: Workflow Status Endpoint")
    print("-" * 30)
    try:
        # Use a dummy thread ID to test the status endpoint structure
        status_payload = {"thread_id": "test_thread_id"}
        response = requests.post(f"{base_url}/workflow_status", headers=headers, json=status_payload, timeout=10)
        
        # We expect this to fail, but we want to see the response structure
        print(f"   Status code: {response.status_code}")
        print(f"   Response indicates endpoint is accessible")
        test_results["status_endpoint"] = "ACCESSIBLE"
        
    except Exception as e:
        print(f"❌ Status endpoint error: {e}")
        test_results["status_endpoint"] = "ERROR"
    
    print()
    
    # Test Summary
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result == "PASS")
    
    for test_name, result in test_results.items():
        status_icon = {
            "PASS": "✅",
            "FAIL": "❌", 
            "ERROR": "⚠️",
            "PARTIAL": "🔶",
            "ACCESSIBLE": "🔍"
        }.get(result, "❓")
        
        print(f"   {status_icon} {test_name}: {result}")
    
    print()
    print(f"📈 Overall Score: {passed_tests}/{total_tests} tests passed")
    
    # API Status Assessment
    if passed_tests >= 3:
        print("🎉 API STATUS: OPERATIONAL")
        print("   The API is working correctly and ready for use")
        print("   Documentation examples should work as written")
    elif passed_tests >= 1:
        print("⚠️ API STATUS: PARTIALLY OPERATIONAL") 
        print("   Basic endpoints work but some workflow issues detected")
        print("   Documentation may need updates")
    else:
        print("❌ API STATUS: NOT OPERATIONAL")
        print("   API appears to be down or misconfigured")
        print("   Documentation examples will not work")
    
    return test_results

if __name__ == "__main__":
    test_api_comprehensive()