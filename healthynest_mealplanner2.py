# ==============================================================================
# 1. Imports
# ==============================================================================
import operator
import os
from typing import TypedDict, List, Dict, Optional, Annotated, Sequence, Union, Any
import uuid # For generating mock UUIDs
import traceback # For detailed error printing
import json # For serializing Pydantic models if needed for DB

# LangChain & LangGraph Imports
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field 
from langgraph.graph import StateGraph, END, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser 
from langchain_core.output_parsers import StrOutputParser 
from datetime import datetime, timedelta

# Configuration
from dotenv import load_dotenv

# ==============================================================================
# 2. Configuration & Client Setup
# ==============================================================================
load_dotenv() 

ENABLE_TERMINAL_INTERACTIVE_SWAP = False 

# --- Pydantic Models for LLM Structured Output ---
class ModifiedIngredient(BaseModel):
    original_text: str = Field(description="The full ingredient line, e.g., '1 cup all-purpose flour, sifted'")

class LLMModifiedRecipeOutput(BaseModel):
    modified_recipe_name: str = Field(description="A descriptive name for the modified recipe, e.g., 'Vegan Asparagus Frittata' or 'Asparagus Frittata (Egg-Free for Max)'.")
    modified_ingredients: List[ModifiedIngredient] = Field(description="The complete list of ingredients for the modified recipe.")
    modified_instructions: List[str] = Field(description="Step-by-step instructions for preparing the modified recipe.")
    suitability_notes: str = Field(description="Notes on suitability. Should explicitly state if the recipe is now suitable for all attendees, or if any attendee's needs (especially allergies or hard restrictions) could not be met and why. If no modifications were needed because the original was suitable for all, state that.")
    modifications_were_made: bool = Field(description="True if significant modifications were made to ingredients or instructions, False if the original recipe was deemed suitable for all and no changes were needed.")

class LLMRecipeSelectionChoice(BaseModel):
    chosen_recipe_id: str = Field(description="The ID of the single recipe chosen by the LLM from the candidate list.")
    chosen_recipe_name: str = Field(description="The name of the chosen recipe (for confirmation and logging).")
    reasoning: str = Field(description="A brief explanation of why this recipe was chosen, considering hard/soft requirements, variety, and potential ingredient reuse.")
    no_suitable_candidate_found: Optional[bool] = Field(False, description="Set to true if, after evaluation, no candidate recipe is deemed suitable for the given criteria.")


# --- Mock Clients ---
class MockLLMClient:
    def parse_attendees(self, plan_request: str) -> Dict:
        print(f"MOCK LLM: Parsing attendees...")
        # Mock to return day names as keys
        return {
            "calendar": {
                "Monday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina"]},
                "Tuesday": {"breakfast": ["kristina"], "lunch": ["kristina", "robin"], "dinner": ["kristina", "max"]},
                "Wednesday": {"breakfast": ["kristina"], "lunch": ["kristina"], "dinner": ["kristina"]}
            }
        }

    def suggest_modifications_structured(self, recipe_name: str, original_ingredients: List[str], original_instructions: str) -> LLMModifiedRecipeOutput:
        print(f"MOCK LLM: Suggesting structured modifications for {recipe_name}...")
        if "fail_llm_mod" in recipe_name.lower(): # For testing failure
             raise Exception("Mock LLM modification failure")
        
        # Simulate if modifications are made or not
        if "no_mod_needed" in recipe_name.lower():
            return LLMModifiedRecipeOutput(
                modified_recipe_name=recipe_name,
                modified_ingredients=[ModifiedIngredient(original_text=ing) for ing in original_ingredients],
                modified_instructions=original_instructions.split('\n') if original_instructions else ["Original instructions were fine."],
                suitability_notes="Mock suitability: Original recipe is suitable for all mock attendees.",
                modifications_were_made=False
            )
        return LLMModifiedRecipeOutput(
            modified_recipe_name=f"{recipe_name} (Mock Modified)",
            modified_ingredients=[ModifiedIngredient(original_text="1 mock modified ingredient"), ModifiedIngredient(original_text="Another mock item")],
            modified_instructions=["Mock modified step 1.", "Mock modified step 2."],
            suitability_notes="Mock suitability: Suitable for all mock attendees after modifications.",
            modifications_were_made=True
        )
    
    def select_recipe_from_candidates(self, candidates: List[Dict], needs: Dict, plan_history: List[str]) -> LLMRecipeSelectionChoice:
        print(f"MOCK LLM: Selecting recipe from {len(candidates)} candidates...")
        if candidates:
            chosen = candidates[0] # Mock picks the first
            return LLMRecipeSelectionChoice(
                chosen_recipe_id=chosen.get("id", "mock_id_not_found"),
                chosen_recipe_name=chosen.get("name", "Mock Chosen Recipe"),
                reasoning="Mock LLM picked the first available candidate based on mock logic.",
                no_suitable_candidate_found=False
            )
        return LLMRecipeSelectionChoice(
            chosen_recipe_id="placeholder_not_found",
            chosen_recipe_name="No suitable recipe found (Mock)",
            reasoning="No candidates provided to mock LLM.",
            no_suitable_candidate_found=True
        )


class MockSupabaseClient:
    def get_user_profiles_by_names(self, names: List[str]) -> List[Dict]:
         print(f"MOCK DB: Fetching profiles for {names}...")
         all_users = [
             {"id": "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5", "user_name": "kristina", "lifestyle": "omnivore", "diet_type": "keto", "allergies": []},
             {"id": "a1fe4fe7-b9cd-43af-a5a3-a87313a86db0", "user_name": "robin", "lifestyle": "vegan", "diet_type": "vegetarian", "allergies": []},
             {"id": "ead69674-d3a1-4925-893e-d46c3dd7e58b", "user_name": "max", "lifestyle": "omnivore", "diet_type": "age appropriate nutrition", "allergies": ["egg"]},
         ]
         lowercase_names = [name.lower() for name in names]
         return [u for u in all_users if u['user_name'].lower() in lowercase_names]
    
    def update_meal_plan_entry_notes(self, meal_plan_id: str, meal_date: str, meal_type: str, new_notes: str) -> bool:
        print(f"MOCK DB: Updating notes for MPE - PlanID {meal_plan_id}, Date {meal_date}, Meal {meal_type} to: {new_notes[:70]}...")
        return True

    def get_candidate_recipes(self, aggregated_needs: Dict, current_meal_type_name: str) -> List[Dict]:
        print(f"MOCK DB: Fetching candidates for {current_meal_type_name} based on {aggregated_needs}...")
        if "vegan" in aggregated_needs.get("diets", []): return [{"id": "mock_recipe_vegan", "name": "Mock Vegan Delight", "spoonacular_id": 90001}]
        if "egg" in aggregated_needs.get("allergies", []): return [{"id": "mock_recipe_egg_free", "name": "Mock Egg-Free Wonder", "spoonacular_id": 90002}]
        return [{"id": "mock_recipe_1", "name": "Mock General Recipe", "spoonacular_id": 12345}, {"id": "mock_recipe_2", "name": "Another Mock Option", "spoonacular_id": 12346}]


    def get_recipe_details_by_ids(self, recipe_ids: List[str]) -> List[Dict]:
        # (Implementation from previous version)
        print(f"MOCK DB: Fetching details for recipe IDs: {recipe_ids}")
        mock_details = []
        for i, r_id in enumerate(recipe_ids):
            name = f"Mock Recipe Details {i}"
            if r_id == "mock_recipe_1": name = "Mock General Recipe"
            elif r_id == "mock_recipe_vegan": name = "Mock Vegan Delight"
            elif r_id == "mock_recipe_egg_free": name = "Mock Egg-Free Wonder"
            mock_details.append({
                "id": r_id, "name": name, "image_url": "https://via.placeholder.com/150",
                "spoonacular_id": 78900 + i,
                "fat_grams_portion": 10.0, "carb_grams_portion": 20.0,
                "protein_grams_portion": 15.0, "calories_kcal": 250.0,
                 # Mocking ingredients and instructions for snapshotting
                "extendedIngredients": [{"original": f"1 mock unit of base ingredient for {name}"}],
                "instructions": f"Mock base instructions for {name}"
            })
        return mock_details


    def create_meal_plan(self, user_id: str, plan_name: str, start_date_str: str, days_to_generate: int, description: Optional[str] = None) -> Optional[str]:
        print(f"MOCK DB: Creating meal plan shell for user {user_id} with name '{plan_name}'...")
        mock_id = str(uuid.uuid4())
        print(f"   MOCK DB: Generated meal_plan_id: {mock_id}")
        return mock_id

    def save_meal_plan_entries(self, meal_plan_id: str, plan_items: List[Dict]) -> bool:
        print(f"MOCK DB: Saving {len(plan_items)} entries for meal_plan_id {meal_plan_id}...")
        return True
        
    def save_meal_plan_recipe(self, plan_recipe_data: Dict) -> Optional[str]: # Renamed
       print(f"MOCK DB: Saving to MealPlanRecipes '{plan_recipe_data.get('name')}' (is_llm_modified: {plan_recipe_data.get('is_llm_modified')})...")
       mock_plan_recipe_id = "mpr_" + str(uuid.uuid4())
       print(f"   MOCK DB: Generated MealPlanRecipes.id: {mock_plan_recipe_id}")
       return mock_plan_recipe_id

    def save_meal_plan_entry_participants(self, participant_entries: List[Dict]) -> bool:
       print(f"MOCK DB: Saving {len(participant_entries)} entries to MealPlanEntryParticipants...")
       return True

# --- Instantiate Mock Clients (for fallback) ---
mock_llm_client = MockLLMClient()
mock_db_client = MockSupabaseClient()

# --- Real Supabase Client Definition ---
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = object 

class RealSupabaseClient:
    def __init__(self, url: str, key: str):
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase client library not found. Please install supabase-py.")
        print("Attempting to connect to Supabase...")
        self.client: Client = create_client(url, key)
        print("Supabase client initialized.")

    def get_user_profiles_by_names(self, names: List[str]) -> List[Dict]:
        # (Implementation from previous version - assumed correct)
        print(f"REAL DB: Fetching profiles for {names}...")
        lowercase_names = [name.lower() for name in names]
        final_users_data = []
        try:
            users_response = self.client.table("Users").select("id, user_name, lifestyle, diet_type").in_("user_name", lowercase_names).execute()
            users_data = users_response.data if hasattr(users_response, 'data') else []
            for user_profile in users_data:
                user_id = user_profile.get("id")
                allergies_for_user = []
                if user_id:
                    user_allergies_response = self.client.table("UserAllergies").select("attribute_id").eq("user_id", user_id).execute()
                    allergy_attribute_ids = [item['attribute_id'] for item in (user_allergies_response.data if hasattr(user_allergies_response, 'data') else [])]
                    if allergy_attribute_ids:
                        attributes_response = self.client.table("Attributes").select("name").in_("id", allergy_attribute_ids).eq("type", "allergen").execute()
                        allergies_for_user = [item['name'] for item in (attributes_response.data if hasattr(attributes_response, 'data') else [])]
                user_profile_with_allergies = {**user_profile, "allergies": allergies_for_user}
                final_users_data.append(user_profile_with_allergies)
            print(f"   Fetched profiles: {final_users_data}")
            return final_users_data
        except Exception as e:
            print(f"   ERROR: Supabase query failed during profile/allergy fetch: {e}"); traceback.print_exc(); return []


    def _get_recipes_with_all_attributes(self, attribute_ids: List[str]) -> set[str]:
        # (Implementation from previous version - assumed correct)
        if not attribute_ids: return set()
        sets_for_each_attribute_id = []
        for attr_id in attribute_ids:
            response = self.client.table("RecipeAttributes").select("recipe_id").eq("attribute_id", attr_id).execute()
            current_recipe_ids = {item['recipe_id'] for item in (response.data if hasattr(response, 'data') else [])}
            if not current_recipe_ids: return set() 
            sets_for_each_attribute_id.append(current_recipe_ids)
        return set.intersection(*sets_for_each_attribute_id) if sets_for_each_attribute_id else set()


    def get_candidate_recipes(self, aggregated_needs: Dict, current_meal_type_name: str) -> List[Dict]:
        # (Implementation from previous version - assumed correct, with logging)
        print(f"REAL DB: Fetching candidate recipes for MEAL TYPE '{current_meal_type_name}' based on {aggregated_needs}...")
        diet_names = [name.lower() for name in aggregated_needs.get('diets', [])]
        allergen_names = [name.lower() for name in aggregated_needs.get('allergies', [])]
        meal_type_name_lower = current_meal_type_name.lower()
        all_unique_attribute_names = list(set(diet_names + allergen_names + [meal_type_name_lower]))

        if not all_unique_attribute_names:
            print("   No attribute criteria. Fetching general recipes."); recipes_response = self.client.table("Recipes").select("id, name, spoonacular_id").limit(3).execute(); return recipes_response.data or []
        try:
            attributes_response = self.client.table("Attributes").select("id, name, type, is_hard_trait").in_("name", all_unique_attribute_names).execute()
            attributes_data = attributes_response.data or []
            if not attributes_data: print(f"   No attributes found for names: {all_unique_attribute_names}"); return []
            attributes_map = {attr['name']: attr for attr in attributes_data}
            hard_diet_ids = [attributes_map[name]['id'] for name in diet_names if name in attributes_map and attributes_map[name]['type'] in ['diet', 'lifestyle', 'diet_type'] and attributes_map[name]['is_hard_trait']]
            soft_diet_ids = [attributes_map[name]['id'] for name in diet_names if name in attributes_map and attributes_map[name]['type'] in ['diet', 'lifestyle', 'diet_type'] and not attributes_map[name]['is_hard_trait']]
            hard_allergen_suitability_ids = [attributes_map[name]['id'] for name in allergen_names if name in attributes_map and attributes_map[name]['type'] == 'allergen']
            current_meal_type_attribute_id = None
            if meal_type_name_lower in attributes_map and attributes_map[meal_type_name_lower]['type'] == 'meal_type':
                if not attributes_map[meal_type_name_lower]['is_hard_trait']: soft_diet_ids.append(attributes_map[meal_type_name_lower]['id']); soft_diet_ids = list(set(soft_diet_ids))
                else: hard_diet_ids.append(attributes_map[meal_type_name_lower]['id']); hard_diet_ids = list(set(hard_diet_ids))
            else: print(f"   WARN: Meal type '{meal_type_name_lower}' not found or not 'meal_type'.")
            print(f"   Hard Diet IDs: {hard_diet_ids}, Soft Diet IDs: {soft_diet_ids}, Allergen Suitability IDs: {hard_allergen_suitability_ids}")
            candidate_recipe_ids = set()
            ideal_required_attribute_ids = list(set(hard_diet_ids + hard_allergen_suitability_ids + soft_diet_ids))
            if ideal_required_attribute_ids: candidate_recipe_ids = self._get_recipes_with_all_attributes(ideal_required_attribute_ids)
            if not candidate_recipe_ids and soft_diet_ids and (hard_diet_ids or hard_allergen_suitability_ids):
                print("   Tier 1 empty, trying Tier 2 (hard only).")
                hard_only_required_attribute_ids = list(set(hard_diet_ids + hard_allergen_suitability_ids))
                if hard_only_required_attribute_ids: candidate_recipe_ids = self._get_recipes_with_all_attributes(hard_only_required_attribute_ids)
            if not candidate_recipe_ids:
                if not any([hard_diet_ids, hard_allergen_suitability_ids, soft_diet_ids]): print("   No criteria, fetching general."); fetch_query = self.client.table("Recipes").select("id, name, spoonacular_id").limit(3) # Return up to 3 general if no criteria
                else: print("   No recipes match criteria."); return []
            else: fetch_query = self.client.table("Recipes").select("id, name, spoonacular_id").in_("id", list(candidate_recipe_ids)).limit(3) # Return up to 3 from filtered
            final_recipes_response = fetch_query.execute()
            final_candidates = final_recipes_response.data or []
            print(f"   Final Candidate Recipes: {len(final_candidates)} found.")
            return final_candidates
        except Exception as e: print(f"   ERROR: Recipe fetch failed: {e}"); traceback.print_exc(); return []


    def get_recipe_details_by_ids(self, recipe_ids: List[str]) -> List[Dict]:
        # (Implementation from previous version - assumed correct)
        if not recipe_ids: return []
        print(f"REAL DB: Fetching details for recipe IDs: {recipe_ids}")
        try:
            # Also fetch ingredients and instructions for snapshotting later
            response = self.client.table("Recipes").select(
                "id, name, image_url, spoonacular_id, fat_grams_portion, carb_grams_portion, "
                "protein_grams_portion, calories_kcal, ingredients, instructions" # Assuming these columns exist for originals
            ).in_("id", recipe_ids).execute()
            return response.data if hasattr(response, 'data') else []
        except Exception as e: print(f"   ERROR: Recipe details fetch failed: {e}"); traceback.print_exc(); return []


    def update_meal_plan_entry_notes(self, meal_plan_id: str, meal_date: str, meal_type: str, new_notes: str) -> bool:
        # (Implementation from previous version, uses meal_date)
        print(f"REAL DB: Updating notes for MPE - PlanID {meal_plan_id}, Date {meal_date}, Meal {meal_type}...")
        try:
            response = self.client.table("MealPlanEntries").update({"notes": new_notes}).eq("meal_plan_id", meal_plan_id).eq("meal_date", meal_date).eq("meal_type", meal_type).execute()
            if hasattr(response, 'data') and isinstance(response.data, list) and len(response.data) > 0: return True
            if hasattr(response, 'count') and response.count is not None and response.count > 0: return True
            print("   WARN: Update notes response did not indicate success or no rows matched."); return False
        except Exception as e: print(f"   ERROR: MPE notes update failed: {e}"); traceback.print_exc(); return False

    
    def create_meal_plan(self, user_id: str, plan_name: str, start_date_str: str, days_to_generate: int, description: Optional[str] = None) -> Optional[str]:
        # (Implementation from previous version - assumed correct)
        print(f"REAL DB: Creating meal plan shell for user {user_id} with name '{plan_name}'...")
        try:
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d"); end_date_obj = start_date_obj + timedelta(days=days_to_generate - 1)
            plan_data = {"user_id": user_id, "name": plan_name, "description": description, "start_date": start_date_str, "end_date": end_date_obj.strftime("%Y-%m-%d")}
            response = self.client.table("MealPlans").insert(plan_data).execute()
            if hasattr(response, 'data') and response.data and len(response.data) > 0 and response.data[0].get('id'): return str(response.data[0]['id'])
            print(f"   ERROR: Failed to retrieve ID from MealPlans insert. Response: {response}"); return None
        except Exception as e: print(f"   ERROR: MealPlans insert failed: {e}"); traceback.print_exc(); return None

        
    def save_meal_plan_entries(self, meal_plan_id: str, plan_items: List[Dict]) -> bool:
        # (Implementation from previous version - assumed correct)
        print(f"REAL DB: Saving {len(plan_items)} entries for meal_plan_id {meal_plan_id}...")
        entries_to_insert = []
        for item in plan_items:
            db_entry = {
                "meal_plan_id": meal_plan_id, "meal_date": item.get("meal_date"), "meal_type": item.get("meal_type"),
                "primary_recipe_id": item.get("primary_recipe_id"), "servings": item.get("servings"),
                "notes": item.get("notes"), "modification_context": item.get("modification_context")
            }
            # A more robust check for required fields
            required_fields = ["meal_plan_id", "meal_date", "meal_type", "primary_recipe_id", "servings"]
            if not all(db_entry.get(field) is not None for field in required_fields):
                 print(f"   ERROR: Missing required data for entry: {db_entry}"); continue
            entries_to_insert.append(db_entry)

        if not entries_to_insert: print("   No valid entries to insert."); return False
        try:
            response = self.client.table("MealPlanEntries").insert(entries_to_insert).execute()
            if hasattr(response, 'data') and isinstance(response.data, list) and len(response.data) == len(entries_to_insert): print(f"   Successfully saved {len(response.data)} MPEs."); return True
            print(f"   WARN: MPE insert response indicates issues. Saved {len(response.data or [])} of {len(entries_to_insert)}."); return False
        except Exception as e: print(f"   ERROR: MPEs insert failed: {e}"); traceback.print_exc(); return False

    def save_meal_plan_recipe(self, plan_recipe_data: Dict) -> Optional[str]: # Renamed
       print(f"REAL DB: Saving to MealPlanRecipes '{plan_recipe_data.get('name')}'...")
       try:
           # Supabase JSONB columns can typically handle Python dicts/lists directly
           response = self.client.table("MealPlanRecipes").insert(plan_recipe_data).execute()
           if hasattr(response, 'data') and response.data and len(response.data) > 0:
               new_id = response.data[0].get('id')
               if new_id:
                   print(f"   Successfully saved to MealPlanRecipes with ID: {new_id}")
                   return str(new_id)
           print(f"   ERROR: Failed to retrieve ID from MealPlanRecipes insert. Response: {response}"); return None
       except Exception as e:
           print(f"   ERROR: Supabase insert failed for MealPlanRecipes: {e}"); traceback.print_exc(); return None

    def save_meal_plan_entry_participants(self, participant_entries: List[Dict]) -> bool:
       print(f"REAL DB: Saving {len(participant_entries)} entries to MealPlanEntryParticipants...")
       if not participant_entries: return True 
       try:
           response = self.client.table("MealPlanEntryParticipants").insert(participant_entries).execute()
           if hasattr(response, 'data') and isinstance(response.data, list) and len(response.data) == len(participant_entries):
               print(f"   Successfully saved {len(response.data)} MPE participant entries."); return True
           print(f"   WARN: MPE Participants insert response issues. Saved {len(response.data or [])} of {len(participant_entries)}."); return False
       except Exception as e:
           print(f"   ERROR: MPE Participants insert failed: {e}"); traceback.print_exc(); return False

# --- RealSpoonacularClient Definition (Moved Earlier) ---
class RealSpoonacularClient:
    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
        self.base_url = "https://api.spoonacular.com"
        if self.api_key:
            print("RealSpoonacularClient initialized with API key.")
        else:
            print("RealSpoonacularClient initialized WITHOUT API key (will use mock behavior).")

    def get_recipe_information(self, recipe_id: int, include_nutrition: bool = False) -> Optional[Dict]:
        if not self.api_key:
            print(f"MOCK SPOONACULAR (from RealSpoonacularClient): Fetching recipe {recipe_id} (no API key)...")
            return {
                "id": recipe_id, 
                "title": f"Mock Spoonacular Recipe {recipe_id}",
                "extendedIngredients": [{"original": "1 cup mock ingredient"}, {"original": "2 tbsp mock spice"}],
                "instructions": "Mock step 1. Mock step 2.",
                "servings": 2, 
                "image": "https://via.placeholder.com/400",
                # Mock nutrition
                "nutrition": {
                    "nutrients": [
                        {"name": "Calories", "amount": 250.0, "unit": "kcal"},
                        {"name": "Fat", "amount": 10.0, "unit": "g"},
                        {"name": "Carbohydrates", "amount": 20.0, "unit": "g"},
                        {"name": "Protein", "amount": 15.0, "unit": "g"}
                    ]
                }
            }
        
        print(f"REAL SPOONACULAR: Fetching recipe {recipe_id} information...")
        endpoint = f"{self.base_url}/recipes/{recipe_id}/information"
        params = { "apiKey": self.api_key, "includeNutrition": include_nutrition }
        try:
            import requests 
            response = requests.get(endpoint, params=params)
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
            recipe_data = response.json()
            print(f"   Successfully fetched data for recipe: {recipe_data.get('title')}")
            return recipe_data
        except requests.exceptions.RequestException as e:
            print(f"   ERROR: Spoonacular API request failed: {e}")
            traceback.print_exc()
            return None
        except Exception as e: # Catch any other unexpected errors
            print(f"   ERROR: An unexpected error occurred with Spoonacular API: {e}")
            traceback.print_exc()
            return None

# --- Instantiate Clients ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

db_client: Union[RealSupabaseClient, MockSupabaseClient]
if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
    print("Using Real Supabase Client."); db_client = RealSupabaseClient(SUPABASE_URL, SUPABASE_KEY)
else:
    print("Using Mock Supabase Client."); db_client = mock_db_client

llm: Union[ChatGoogleGenerativeAI, MockLLMClient]
if GOOGLE_API_KEY:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", api_key=GOOGLE_API_KEY, temperature=0.2) 
        print("Using real Google Gemini Flash client.")
    except Exception as e: print(f"ERROR: Failed to init Gemini: {e}. Using Mock LLM."); llm = mock_llm_client
else:
    print("WARNING: GOOGLE_API_KEY not found. Using Mock LLM."); llm = mock_llm_client

spoonacular_client = RealSpoonacularClient(SPOONACULAR_API_KEY)


# ==============================================================================
# 3. LangGraph State Definition & Pydantic Models (Attendee models from before)
# ==============================================================================
class MealAttendees(BaseModel):
    breakfast: List[str] = Field(default_factory=list); lunch: List[str] = Field(default_factory=list); dinner: List[str] = Field(default_factory=list)
class AttendeeCalendar(BaseModel):
    calendar: Dict[str, MealAttendees] = Field(description="A dictionary where keys are day names (e.g., 'Monday') and values specify attendees for each meal.") 

class MealSlot(TypedDict): day: str; meal_type: str; attendees: List[str]; actual_date: str
class CandidateRecipeInfo(TypedDict): id: Optional[str]; name: Optional[str]; spoonacular_id: Optional[int]; image_url: Optional[str] 
class DraftMealPlanSlotItem(TypedDict): day: str; meal_type: str; actual_date: str; attendees: List[str]; default_selected_recipe: CandidateRecipeInfo; all_candidate_recipes: List[CandidateRecipeInfo]; aggregated_needs: Optional[Dict]; attendee_profiles: List[Dict]
class MealPlanItemForUI(TypedDict): day: str; meal_type: str; actual_date: str; attendees: List[str]; recipe_id: Optional[str]; recipe_name: Optional[str]; spoonacular_id: Optional[int]; image_url: Optional[str]; fat_grams_portion: Optional[float]; carb_grams_portion: Optional[float]; protein_grams_portion: Optional[float]; calories_kcal: Optional[float]; alternative_recipes: List[CandidateRecipeInfo]; aggregated_needs: Optional[Dict]; attendee_profiles: List[Dict]

class HealthyNestState(TypedDict):
    user_id: Optional[str]; start_date: Optional[str]; days_to_generate: Optional[int]; plan_description: Optional[str]
    attendee_calendar_raw_llm_output: Optional[AttendeeCalendar]
    confirmed_attendee_calendar: Optional[Dict]
    meal_plan_id: Optional[str]
    meal_slots_to_plan: List[MealSlot]
    current_slot_index: int
    current_meal_slot: Optional[MealSlot]
    aggregated_needs_for_slot: Optional[Dict]
    candidate_recipes_for_slot: Optional[List[Dict]] 
    default_choice_for_slot: Optional[Dict] 
    current_slot_attendee_profiles: Optional[List[Dict]]
    draft_plan_items: List[DraftMealPlanSlotItem]
    current_recipe_for_detailed_view: Optional[Dict] # Used by modification flow
    live_recipe_details_for_modification: Optional[Dict] # Full Spoonacular details for current recipe
    current_meal_plan_entry_for_modification: Optional[Dict] 
    llm_modification_suggestions: Optional[Any] # Can be LLMModifiedRecipeOutput or error string
    # current_custom_recipe_id: Optional[str] # Replaced by contextual_recipe_id
    # custom_recipe_suitability_notes: Optional[str] # Replaced by contextual_recipe_suitability_notes
    contextual_recipe_id: Optional[str] # ID of the entry in MealPlanRecipes table
    contextual_recipe_suitability_notes: Optional[str] # Notes from LLM about this MealPlanRecipe
    hitl_step_required: Optional[str]
    hitl_data_for_ui: Optional[List[MealPlanItemForUI]]
    final_plan_saved_status: Optional[str]
    meal_plan_entry_participants_status: Optional[str] 
    error_message: Optional[str] 
    messages: Annotated[Sequence[BaseMessage], operator.add]

# ==============================================================================
# 4. Python Functions for LangGraph Nodes
# ==============================================================================
def get_plan_request_details_node(state: HealthyNestState) -> Dict:
    print("--- Node: Get Plan Request ---")
    mock_start_date = "2025-05-26"; mock_days = 3
    mock_description = ("Plan for kristina. robin joins kristina for lunch on Monday and Tuesday. "
                        "max joins kristina for dinner on Tuesday only. Meals for 3 days starting Monday.")
    mock_user_id = "1bbdee4d-b0fb-47b9-aa8e-ce22f70fb7c5"
    return {"user_id": mock_user_id, "start_date": mock_start_date, "days_to_generate": mock_days, "plan_description": mock_description}

def create_meal_plan_shell_node(state: HealthyNestState) -> Dict:
    print("--- Node: Create Meal Plan Shell ---")
    user_id, start_date, days, desc = state.get("user_id"), state.get("start_date"), state.get("days_to_generate"), state.get("plan_description")
    if not all([user_id, start_date, days is not None]): return {"meal_plan_id": None, "error_message": "Missing details for shell."}
    plan_name = f"Plan {start_date} for {days} days"
    meal_plan_id = db_client.create_meal_plan(user_id, plan_name, start_date, days, desc)
    return {"meal_plan_id": meal_plan_id} if meal_plan_id else {"meal_plan_id": None, "error_message": "Failed to create shell."}

def generate_attendee_calendar_llm_node(state: HealthyNestState) -> Dict:
    print("--- Node: Generate Attendee Calendar (PydanticParser) ---")
    plan_description, start_date_str, days_to_generate = state.get("plan_description"), state.get("start_date"), state.get("days_to_generate")
    if not all([plan_description, start_date_str, days_to_generate is not None]): 
        print("   ERROR: Missing plan details for LLM calendar generation.")
        return {"attendee_calendar_raw_llm_output": None}
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    date_list_for_context = [(start_date + timedelta(days=i)).strftime("%A (%Y-%m-%d)") for i in range(days_to_generate)]
    date_context = "The meal plan covers the following days: " + ", ".join(date_list_for_context) + \
                   ". Please use the full day names (e.g., 'Monday', 'Tuesday') as keys in your calendar output."

    current_llm_instance = llm
    if not isinstance(current_llm_instance, ChatGoogleGenerativeAI):
        print("   Using Mock LLM for calendar generation.")
        raw_calendar_dict = mock_llm_client.parse_attendees(plan_description) 
        try: 
            pydantic_mock = AttendeeCalendar.model_validate(raw_calendar_dict)
            print(f"   Mock Output (Pydantic): {pydantic_mock.calendar}")
            return {"attendee_calendar_raw_llm_output": pydantic_mock}
        except Exception as e: 
            print(f"   ERROR: Mock output couldn't be converted to Pydantic: {e}"); traceback.print_exc()
            return {"attendee_calendar_raw_llm_output": None}

    parser = PydanticOutputParser(pydantic_object=AttendeeCalendar)
    format_instructions = parser.get_format_instructions()
    
    prompt_template_str = (
        "You are an expert meal planning assistant. Your task is to analyze the user's "
        "request and extract a detailed attendee calendar for the specified days. "
        "The keys in the 'calendar' dictionary MUST be the full day names (e.g., 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'). "
        "Identify every person mentioned and determine which meals (Breakfast, Lunch, Dinner) "
        "they will be present for on each day of the week covered by the plan. Use lowercase for all attendee names in the output. "
        "The primary user (usually the first one mentioned in the request) is assumed to attend *all* "
        "meals on all specified days unless explicitly stated otherwise. "
        "Only include days that are part of the meal plan duration, using their day names as keys. "
        "Your output MUST be JSON that strictly follows the provided format instructions."
        "\n\n{format_instructions}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_template_str),
        ("human", "User Request: {plan_request}\n\nContext for days: {date_context}"),
    ])
    chain = prompt | current_llm_instance | parser
    try:
        raw_calendar_pydantic = chain.invoke({
            "plan_request": plan_description, 
            "date_context": date_context,
            "format_instructions": format_instructions
        })
        if raw_calendar_pydantic and raw_calendar_pydantic.calendar:
            for day_meals in raw_calendar_pydantic.calendar.values(): 
                day_meals.breakfast = [n.lower() for n in day_meals.breakfast]
                day_meals.lunch = [n.lower() for n in day_meals.lunch]
                day_meals.dinner = [n.lower() for n in day_meals.dinner]
        print(f"   LLM Output (Pydantic, keys should be day names): {raw_calendar_pydantic.calendar if raw_calendar_pydantic else 'None'}")
        return {"attendee_calendar_raw_llm_output": raw_calendar_pydantic}
    except Exception as e: 
        print(f"   ERROR: LLM calendar generation or parsing failed: {e}"); traceback.print_exc()
        return {"attendee_calendar_raw_llm_output": None}


def present_attendee_calendar_for_confirmation_node(state: HealthyNestState) -> Dict:
    print("--- Node: Present Attendee Calendar for Confirmation ---")
    raw_output = state.get("attendee_calendar_raw_llm_output")
    if not raw_output or not raw_output.calendar: return {"hitl_step_required": "error_calendar", "hitl_data_for_ui": {"error": "Calendar gen failed."}}
    return {"hitl_step_required": "confirm_calendar", "hitl_data_for_ui": raw_output.model_dump()}

def process_confirmed_attendee_calendar_node(state: HealthyNestState) -> Dict:
    print("--- Node: Process Confirmed Attendee Calendar ---")
    raw_pydantic_output = state.get("attendee_calendar_raw_llm_output")
    start_date_str = state.get("start_date")
    meal_plan_id = state.get("meal_plan_id") 
    days_to_generate = state.get("days_to_generate")

    if not raw_pydantic_output or not raw_pydantic_output.calendar: 
        raise ValueError("Calendar not generated or empty for processing!")
    if not all([start_date_str, meal_plan_id, days_to_generate is not None]): 
        raise ValueError("Missing state for calendar processing!")

    start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
    confirmed_calendar_dict = raw_pydantic_output.calendar 
    slots: List[MealSlot] = []
    
    first_key = next(iter(confirmed_calendar_dict)) if confirmed_calendar_dict else None
    keys_are_dates = False
    if first_key:
        try:
            datetime.strptime(first_key, "%Y-%m-%d") 
            keys_are_dates = True
            print("   Calendar keys appear to be date strings (e.g., YYYY-MM-DD).")
        except ValueError:
            print("   Calendar keys appear to be day names (e.g., Monday).")

    for day_offset in range(days_to_generate):
        current_date_obj = start_date_obj + timedelta(days=day_offset)
        current_date_str = current_date_obj.strftime("%Y-%m-%d")
        day_name_from_date = current_date_obj.strftime("%A") 
        
        key_to_use = current_date_str if keys_are_dates else day_name_from_date
        
        if key_to_use in confirmed_calendar_dict: 
            meals_pydantic_obj = confirmed_calendar_dict[key_to_use]
            meal_dict = meals_pydantic_obj.model_dump() 
            for meal_type_key, attendees in meal_dict.items(): 
                if attendees: 
                    slots.append({
                        "day": day_name_from_date, 
                        "meal_type": meal_type_key.capitalize(), 
                        "attendees": attendees, 
                        "actual_date": current_date_str
                    })
        else: 
            print(f"   Note: Key '{key_to_use}' (Date: {current_date_str}, Day: {day_name_from_date}) was expected but not found in LLM calendar output. No slots generated for this day/date.")
    print(f"   Generated {len(slots)} meal slots.")
    return {
        "confirmed_attendee_calendar": confirmed_calendar_dict, 
        "meal_slots_to_plan": slots,
        "current_slot_index": 0, 
        "draft_plan_items": [], 
        "hitl_step_required": None, 
        "hitl_data_for_ui": None,
    }

def determine_next_meal_slot_node(state: HealthyNestState) -> Dict:
    print("--- Node: Determine Next Meal Slot ---")
    index, slots = state.get("current_slot_index", 0), state.get("meal_slots_to_plan", [])
    if index < len(slots): current_slot = slots[index]; print(f"   Planning Slot {index+1}/{len(slots)}: {current_slot['day']} {current_slot['meal_type']} on {current_slot['actual_date']}"); return {"current_meal_slot": current_slot}
    print("   All meal slots processed."); return {"current_meal_slot": None}

def get_candidate_recipes_node(state: HealthyNestState) -> Dict:
    print("--- Node: Get Candidate Recipes ---")
    slot = state.get("current_meal_slot")
    if not slot: return {"candidate_recipes_for_slot": [], "aggregated_needs_for_slot": None, "current_slot_attendee_profiles": []}
    attendees, current_slot_meal_type = slot["attendees"], slot.get("meal_type")
    if not current_slot_meal_type: return {"candidate_recipes_for_slot": [], "aggregated_needs_for_slot": None, "current_slot_attendee_profiles": []}
    profiles = db_client.get_user_profiles_by_names(attendees)
    aggregated_needs = {"allergies": list(set(a for p in profiles for a in p.get("allergies", []))), "diets": list(set(d.lower() for p in profiles for d in [p.get("lifestyle", ""), p.get("diet_type", "")] if d))} 
    print(f"   Aggregated Needs: {aggregated_needs}")
    candidates = db_client.get_candidate_recipes(aggregated_needs, current_slot_meal_type)
    return {"candidate_recipes_for_slot": candidates, "aggregated_needs_for_slot": aggregated_needs, "current_slot_attendee_profiles": profiles}

def llm_intelligent_recipe_selection_node(state: HealthyNestState) -> Dict:
    print("--- Node: LLM Intelligent Recipe Selection ---")
    candidate_recipes = state.get("candidate_recipes_for_slot", []) 
    aggregated_needs = state.get("aggregated_needs_for_slot") 
    draft_plan = state.get("draft_plan_items", []) 
    current_meal_slot_info = state.get("current_meal_slot")

    if not candidate_recipes:
        print("   No candidate recipes to select from. Using placeholder.")
        return {"default_choice_for_slot": {"id": "placeholder_not_found", "name": "No suitable recipe found by DB", "spoonacular_id": None}}

    candidate_list_str = "\n".join([f"- ID: {c.get('id')}, Name: {c.get('name')}" for c in candidate_recipes])
    previously_selected_recipe_names = [item["default_selected_recipe"]["name"] for item in draft_plan if item.get("default_selected_recipe") and item["default_selected_recipe"].get("name")]
    history_str = "Already selected recipes in this plan: " + (", ".join(previously_selected_recipe_names) if previously_selected_recipe_names else "None yet.")
    
    allergies_str = ", ".join(aggregated_needs.get("allergies", ["None"])) if aggregated_needs else "None"
    diets_str = ", ".join(aggregated_needs.get("diets", ["None"])) if aggregated_needs else "None"
    meal_type_str = current_meal_slot_info.get('meal_type','N/A') if current_meal_slot_info else "N/A"

    hard_req_str = f"Hard Requirements (must be met by selection or be easily adaptable): Allergies: {allergies_str}"
    soft_req_str = f"Soft Preferences (try to accommodate): Diets: {diets_str}, Meal Type: {meal_type_str}"

    parser = PydanticOutputParser(pydantic_object=LLMRecipeSelectionChoice)
    format_instructions = parser.get_format_instructions()

    prompt_template_str = (
        "You are an intelligent recipe selection assistant for a meal planner.\n"
        "You will be given a list of candidate recipes that have already been pre-filtered to meet critical dietary restrictions.\n"
        "Your task is to select the ONE best recipe from this list for the current meal slot, considering the following:\n"
        "1. Slot Requirements: Prioritize recipes that best match the soft preferences (diets, meal type) for the current meal slot. Assume hard requirements (like major allergies) have been mostly handled by pre-filtering, but double-check if the recipe name or type obviously conflicts.\n"
        "2. Variety: Consider recipes already selected for this meal plan to encourage variety. Try not to repeat recipes or very similar recipe types if good alternatives exist.\n"
        "3. Suitability for Modification (General): Prefer recipes that seem inherently more adaptable to the soft preferences if not a perfect match. (Detailed modification is a separate step, but make a high-level judgment).\n"
        "4. Ingredient Reuse (Inference): If possible, infer and favor recipes that might allow for ingredient reuse with other meals in the plan, but variety and meeting slot requirements are more important.\n\n"
        "Candidate Recipes (ID, Name):\n{candidate_list}\n\n"
        "Current Meal Slot Requirements:\n{hard_requirements}\n{soft_preferences}\n\n"
        "Recipes Already in This Meal Plan (for variety context):\n{plan_history}\n\n"
        "Based on all the above, choose the single best recipe ID from the candidate list. Provide your reasoning.\n"
        "If, after careful consideration, you believe NONE of the candidates are a good fit (e.g., all conflict with soft preferences badly and offer no variety), you must set 'no_suitable_candidate_found' to true, set 'chosen_recipe_id' to 'placeholder_not_found', 'chosen_recipe_name' to 'No suitable recipe found by LLM', and explain why in 'reasoning'.\n"
        "Output Format Instructions:\n{format_instructions}"
    )
    
    prompt = ChatPromptTemplate.from_template(prompt_template_str)
    
    current_llm_instance = llm
    if not isinstance(current_llm_instance, ChatGoogleGenerativeAI):
        print("   Using Mock LLM for recipe selection.")
        mock_choice = mock_llm_client.select_recipe_from_candidates(candidate_recipes, aggregated_needs, previously_selected_recipe_names)
        chosen_recipe_details = next((c for c in candidate_recipes if c.get("id") == mock_choice.chosen_recipe_id), 
                                     {"id": "placeholder_not_found", "name": "No suitable recipe found (Mock)", "spoonacular_id": None})
        if mock_choice.no_suitable_candidate_found:
            chosen_recipe_details = {"id": "placeholder_not_found", "name": mock_choice.chosen_recipe_name, "spoonacular_id": None}

        print(f"   Mock LLM Chose: {chosen_recipe_details.get('name')}. Reasoning: {mock_choice.reasoning}")
        return {"default_choice_for_slot": chosen_recipe_details}

    chain = prompt | current_llm_instance | parser
    
    try:
        llm_selection = chain.invoke({
            "candidate_list": candidate_list_str,
            "hard_requirements": hard_req_str,
            "soft_preferences": soft_req_str,
            "plan_history": history_str,
            "format_instructions": format_instructions
        })

        if llm_selection.no_suitable_candidate_found or llm_selection.chosen_recipe_id == "placeholder_not_found":
            print(f"   LLM indicated no suitable candidate found or chose placeholder. Reasoning: {llm_selection.reasoning}")
            return {"default_choice_for_slot": {"id": "placeholder_not_found", "name": llm_selection.chosen_recipe_name or "No recipe selected by LLM", "spoonacular_id": None}}

        chosen_recipe_details = next((c for c in candidate_recipes if c.get("id") == llm_selection.chosen_recipe_id), None)

        if chosen_recipe_details:
            print(f"   LLM Chose: {chosen_recipe_details.get('name')} (ID: {llm_selection.chosen_recipe_id}). Reasoning: {llm_selection.reasoning}")
            return {"default_choice_for_slot": chosen_recipe_details}
        else:
            print(f"   ERROR: LLM chose recipe ID '{llm_selection.chosen_recipe_id}' but it was not found in candidates. Using placeholder.")
            return {"default_choice_for_slot": {"id": "placeholder_not_found", "name": "LLM choice error", "spoonacular_id": None}}

    except Exception as e:
        print(f"   ERROR: LLM recipe selection or parsing failed: {e}"); traceback.print_exc()
        return {"default_choice_for_slot": candidate_recipes[0]}


def store_draft_plan_item_node(state: HealthyNestState) -> Dict:
    # (Implementation from previous version - assumed correct)
    print("--- Node: Store Draft Plan Item ---")
    current_index, default_choice, all_candidates, current_slot, agg_needs, attendee_profiles, draft_plan = state.get("current_slot_index",0), state.get("default_choice_for_slot"), state.get("candidate_recipes_for_slot",[]), state.get("current_meal_slot"), state.get("aggregated_needs_for_slot"), state.get("current_slot_attendee_profiles",[]), state.get("draft_plan_items",[]).copy()
    if current_slot and default_choice: 
        default_info: CandidateRecipeInfo = {
            "id": default_choice.get("id"), "name": default_choice.get("name"),
            "spoonacular_id": default_choice.get("spoonacular_id"), "image_url": default_choice.get("image_url") 
        }
        candidates_info = [{"id":c.get("id"), "name":c.get("name"), "spoonacular_id":c.get("spoonacular_id"), "image_url":c.get("image_url")} for c in all_candidates]
        
        draft_item: DraftMealPlanSlotItem = {"day":current_slot["day"], "meal_type":current_slot["meal_type"], "actual_date":current_slot["actual_date"], "attendees":current_slot["attendees"], "default_selected_recipe":default_info, "all_candidate_recipes":candidates_info, "aggregated_needs":agg_needs, "attendee_profiles":attendee_profiles}
        draft_plan.append(draft_item); print(f"   Added to draft: {default_info.get('name')}")
    else: print(f"   ERROR: No current_slot/default_choice to store. Index: {current_index}")
    return {"current_slot_index": current_index + 1, "draft_plan_items": draft_plan, "default_choice_for_slot": None, "candidate_recipes_for_slot": [], "aggregated_needs_for_slot": None, "current_slot_attendee_profiles": None}

def present_full_plan_for_review_node(state: HealthyNestState) -> Dict:
    # (Implementation from previous version - assumed correct)
    print("--- Node: Present Full Plan for Review ---")
    draft_items = state.get("draft_plan_items", [])
    if not draft_items: return {"hitl_step_required": "review_full_plan", "hitl_data_for_ui": []}
    all_recipe_ids = set(item["default_selected_recipe"]["id"] for item in draft_items if item["default_selected_recipe"] and item["default_selected_recipe"]["id"] != "placeholder_not_found")
    all_recipe_ids.update(cand["id"] for item in draft_items for cand in item.get("all_candidate_recipes", []) if cand and cand.get("id") != "placeholder_not_found")
    details_map = {d['id']: d for d in db_client.get_recipe_details_by_ids(list(all_recipe_ids))} if all_recipe_ids else {}
    print(f"   Fetched details for {len(details_map)} unique recipes.")
    ui_plan: List[MealPlanItemForUI] = []
    for s_item in draft_items:
        def_recipe_sum = s_item["default_selected_recipe"]; def_details = details_map.get(def_recipe_sum["id"]) if def_recipe_sum and def_recipe_sum.get("id") else None
        alts_ui = [{"id":a.get("id"), "name":a.get("name"), "spoonacular_id":a.get("spoonacular_id"), "image_url": details_map.get(a["id"], {}).get("image_url") if a and a.get("id") else "https://via.placeholder.com/150"} for a in s_item.get("all_candidate_recipes", [])]
        ui_item: MealPlanItemForUI = {"day":s_item["day"], "meal_type":s_item["meal_type"], "actual_date":s_item["actual_date"], "attendees":s_item["attendees"], "recipe_id":def_recipe_sum.get("id"), "recipe_name":def_recipe_sum.get("name"), "spoonacular_id":def_recipe_sum.get("spoonacular_id"), "image_url":def_details.get("image_url") if def_details else "https://via.placeholder.com/150", "fat_grams_portion":def_details.get("fat_grams_portion") if def_details else None, "carb_grams_portion":def_details.get("carb_grams_portion") if def_details else None, "protein_grams_portion":def_details.get("protein_grams_portion") if def_details else None, "calories_kcal":def_details.get("calories_kcal") if def_details else None, "alternative_recipes":alts_ui, "aggregated_needs":s_item.get("aggregated_needs"), "attendee_profiles":s_item.get("attendee_profiles", [])}
        ui_plan.append(ui_item)
    print(f"   Prepared {len(ui_plan)} items for HITL 2.")
    return {"hitl_step_required": "review_full_plan", "hitl_data_for_ui": ui_plan}

def process_user_feedback_and_save_node(state: HealthyNestState) -> Dict:
    # (Implementation from previous version - now preserves hitl_data_for_ui)
    print("--- Node: Process User Feedback and Save ---")
    plan_to_save, meal_plan_id = state.get("hitl_data_for_ui", []), state.get("meal_plan_id")
    if not plan_to_save: return {"final_plan_saved_status": "No items to process"}
    if not meal_plan_id: return {"final_plan_saved_status": "Missing meal_plan_id"}
    items_to_save_db = []
    for idx, ui_item in enumerate(plan_to_save):
        chosen_recipe_id, chosen_recipe_name = ui_item.get("recipe_id"), ui_item.get("recipe_name")
        if idx == 0 and ui_item.get("alternative_recipes"): # Simulated swap for first item
            alt_choice = next((alt for alt in ui_item["alternative_recipes"] if alt.get("id") and alt.get("id") != chosen_recipe_id), None)
            if alt_choice: chosen_recipe_id, chosen_recipe_name = alt_choice["id"], alt_choice["name"]; print(f"   (Simulated swap) Slot 1 to: {chosen_recipe_name}")
        if not chosen_recipe_id or chosen_recipe_id == "placeholder_not_found": print(f"   Skipping slot {ui_item.get('day')} {ui_item.get('meal_type')}."); continue
        mod_context = {"base_recipe_id":chosen_recipe_id, "base_recipe_name":chosen_recipe_name, "attendees_with_profiles":ui_item.get("attendee_profiles",[]), "slot_aggregated_needs":ui_item.get("aggregated_needs")}
        notes = f"Confirmed: {chosen_recipe_name}." # Initial notes
        if ui_item.get("aggregated_needs"): notes += f" Slot Diets: {', '.join(ui_item['aggregated_needs'].get('diets',[]))}. Slot Allergies: {', '.join(ui_item['aggregated_needs'].get('allergies',[]))}."
        db_payload = {"meal_plan_id":meal_plan_id, "meal_date":ui_item.get("actual_date"), "meal_type":ui_item.get("meal_type"), "primary_recipe_id":chosen_recipe_id, "servings":len(ui_item.get("attendees",[])), "notes":notes, "modification_context":mod_context}
        items_to_save_db.append(db_payload)
    if not items_to_save_db: return {"final_plan_saved_status": "No valid items"}
    save_ok = db_client.save_meal_plan_entries(meal_plan_id, items_to_save_db)
    return {"final_plan_saved_status": "success" if save_ok else "failure", "hitl_step_required": None} # Keep hitl_data_for_ui

# --- LLM Modification Flow Nodes ---
def get_live_spoonacular_recipe_node(state: HealthyNestState) -> Dict:
    # (Implementation from previous version)
    print("--- Node: Get Live Spoonacular Recipe Details ---")
    recipe_to_fetch = state.get("current_recipe_for_detailed_view")
    if not recipe_to_fetch or not recipe_to_fetch.get("spoonacular_id"): return {"live_recipe_details_for_modification": None, "error_message": "Missing Spoonacular ID."}
    spoon_id, name = recipe_to_fetch.get("spoonacular_id"), recipe_to_fetch.get("name", f"ID {recipe_to_fetch.get('spoonacular_id')}")
    print(f"   Fetching live details for '{name}' (Spoonacular ID: {spoon_id})")
    live_details = spoonacular_client.get_recipe_information(recipe_id=spoon_id, include_nutrition=True)
    if live_details:
        # Store original ingredients/instructions from Spoonacular if not already structured
        # This helps the ensure_and_save_plan_recipe_version_node
        if 'extendedIngredients' in live_details and not isinstance(live_details.get('ingredients_structured'), list):
            live_details['ingredients_structured'] = [{'original_text': ing.get('original')} for ing in live_details['extendedIngredients']]
        if 'instructions' in live_details and not isinstance(live_details.get('instructions_structured'), list):
            live_details['instructions_structured'] = [step.strip() for step in live_details['instructions'].split('\n') if step.strip()]

    return {"live_recipe_details_for_modification": live_details} if live_details else {"live_recipe_details_for_modification": None, "error_message": f"Failed to fetch for {spoon_id}."}

def apply_critical_modifications_llm_node(state: HealthyNestState) -> Dict:
    # (Updated implementation from previous response for structured output)
    print("--- Node: Apply Critical Modifications LLM (Structured Output) ---")
    live_recipe_details = state.get("live_recipe_details_for_modification")
    mpe_context_holder = state.get("current_meal_plan_entry_for_modification")
    if not live_recipe_details: return {"llm_modification_suggestions": None, "error_message": "Recipe details missing for LLM."}
    if not mpe_context_holder or not mpe_context_holder.get("modification_context"): return {"llm_modification_suggestions": None, "error_message": "Modification context missing for LLM."}
    
    mod_ctx = mpe_context_holder["modification_context"]
    base_name = mod_ctx.get("base_recipe_name", "recipe")
    attendees_profiles = mod_ctx.get("attendees_with_profiles", [])
    
    orig_ingr_texts = [ing.get("original") for ing in live_recipe_details.get("extendedIngredients", []) if ing.get("original")]
    orig_instr_text = live_recipe_details.get("instructions", "No instructions provided.")
    if not orig_instr_text and live_recipe_details.get("analyzedInstructions"): 
        if live_recipe_details["analyzedInstructions"] and isinstance(live_recipe_details["analyzedInstructions"], list) and len(live_recipe_details["analyzedInstructions"]) > 0:
            steps = [s.get("step") for s in live_recipe_details["analyzedInstructions"][0].get("steps", []) if s.get("step")]
            if steps: orig_instr_text = "\n".join(steps)

    needs_summary = "\n".join([f"- {p.get('user_name','User')}: LS: {p.get('lifestyle','N/A')}, Diet: {p.get('diet_type','N/A')}, Allergies: {', '.join(p.get('allergies',[])) or 'None'}" for p in attendees_profiles]) or "No specific needs."

    parser = PydanticOutputParser(pydantic_object=LLMModifiedRecipeOutput)
    format_instr = parser.get_format_instructions()
    prompt = (f"Base Recipe Name: {base_name}\n\nBase Recipe Ingredients:\n{chr(10).join(orig_ingr_texts)}\n\nBase Recipe Instructions:\n{orig_instr_text}\n\nAttendee Needs for this meal:\n{needs_summary}\n\nYour Task:\n1. Analyze base recipe against ALL attendee needs. Focus on allergies and hard dietary restrictions.\n2. If modifications ARE NECESSARY, provide a complete, new version (name, full ingredient list, step-by-step instructions). Set 'modifications_were_made' to true.\n3. If original recipe IS ALREADY SUITABLE for all, set 'modifications_were_made' to false. 'modified_recipe_name' is original name; 'modified_ingredients' and 'modified_instructions' reflect original.\n4. In 'suitability_notes', state your assessment. If modified, confirm suitability. If needs CANNOT be met, state this explicitly (e.g., 'Not suitable for User X due to Y allergy to Z.'). If no mods needed, state original is suitable.\n5. For ingredients, use 'ModifiedIngredient' structure with 'original_text' for each line.\nOutput strictly in JSON format:\n{format_instr}\nEnsure all fields are populated.")
    
    print(f"   Prompting LLM for structured modifications for '{base_name}'.")
    current_llm_instance = llm
    if not isinstance(current_llm_instance, ChatGoogleGenerativeAI):
        return {"llm_modification_suggestions": mock_llm_client.suggest_modifications_structured(base_name, orig_ingr_texts, orig_instr_text), "error_message": None}
    
    llm_response_content = ""
    try:
        llm_response_content = current_llm_instance.invoke(prompt).content
        parsed_suggestions = parser.parse(llm_response_content)
        print(f"   LLM Structured Suggestions Parsed: {parsed_suggestions.modified_recipe_name}")
        return {"llm_modification_suggestions": parsed_suggestions, "error_message": None}
    except Exception as e:
        print(f"   ERROR: LLM structured modifications parse failed: {e}\nRaw LLM Output:\n{llm_response_content[:500]}...") 
        return {"llm_modification_suggestions": None, "error_message": f"LLM/Parse error: {str(e)}"}

def ensure_and_save_plan_recipe_version_node(state: HealthyNestState) -> Dict: # New Node
    print("--- Node: Ensure and Save Plan Recipe Version ---")
    llm_output: Optional[LLMModifiedRecipeOutput] = state.get("llm_modification_suggestions")
    original_recipe_details = state.get("live_recipe_details_for_modification") 
    mpe_context_holder = state.get("current_meal_plan_entry_for_modification")
    error_message_from_llm_step = state.get("error_message")

    if not original_recipe_details:
        print("   ERROR: Original recipe details not available.")
        return {"contextual_recipe_id": None, "contextual_recipe_suitability_notes": "Error: Original recipe details missing.", "error_message": "Original recipe details missing."}

    source_recipe_db_id = None
    if mpe_context_holder and mpe_context_holder.get("modification_context"):
        source_recipe_db_id = mpe_context_holder["modification_context"].get("base_recipe_id")
    
    if not source_recipe_db_id:
         print("   WARN: source_recipe_db_id (from main Recipes table) not found in context. Cannot link MealPlanRecipe to a canonical source.")
         # This is an issue if we expect all recipes to originate from the Recipes table.

    plan_recipe_data = {}
    
    # Default to snapshotting original if LLM fails or output is invalid
    snapshot_original = True
    suitability_notes_for_db = "Error during modification attempt; using original recipe."

    if isinstance(llm_output, LLMModifiedRecipeOutput) and not error_message_from_llm_step:
        suitability_notes_for_db = llm_output.suitability_notes
        if llm_output.modifications_were_made:
            print(f"   LLM made modifications. Preparing new version: '{llm_output.modified_recipe_name}'.")
            plan_recipe_data = {
                "name": llm_output.modified_recipe_name,
                "source_recipe_db_id": source_recipe_db_id, 
                "spoonacular_id": None, # It's a modified version
                "ingredients": [ing.model_dump() for ing in llm_output.modified_ingredients],
                "instructions": llm_output.modified_instructions,
                "image_url": original_recipe_details.get("image"), 
                "nutrition_info": original_recipe_details.get("nutrition", {}).get("nutrients"), 
                "is_llm_modified": True,
                "llm_suitability_notes": llm_output.suitability_notes + (" (Nutrition info is for base recipe and may vary)." if original_recipe_details.get("nutrition") else "")
            }
            snapshot_original = False
        else: # No modifications needed by LLM
            print(f"   LLM indicated no modifications needed for '{llm_output.modified_recipe_name}'. Snapshotting original.")
            # Data for snapshot will be prepared below if snapshot_original is True
    elif error_message_from_llm_step:
        print(f"   LLM modification step resulted in error: {error_message_from_llm_step}. Snapshotting original recipe.")
        suitability_notes_for_db = f"Original recipe used due to LLM modification error: {error_message_from_llm_step}"
    else: # llm_output is None or not the expected type
        print(f"   LLM modification output invalid or missing. Snapshotting original recipe.")
        suitability_notes_for_db = "Original recipe used due to invalid/missing LLM modification output."


    if snapshot_original:
        # Prepare ingredients for snapshot to match ModifiedIngredient structure for consistency in DB
        original_ingredients_structured = []
        if original_recipe_details.get("extendedIngredients"):
            original_ingredients_structured = [{'original_text': ing.get('originalString') or ing.get('original')} 
                                               for ing in original_recipe_details.get("extendedIngredients", [])]
        
        original_instructions_list = []
        if original_recipe_details.get("instructions"):
            original_instructions_list = [step.strip() for step in original_recipe_details.get("instructions", "").split('\n') if step.strip()]
        elif original_recipe_details.get("analyzedInstructions"): # Fallback
             if original_recipe_details["analyzedInstructions"] and isinstance(original_recipe_details["analyzedInstructions"], list) and len(original_recipe_details["analyzedInstructions"]) > 0:
                original_instructions_list = [s.get("step") for s in original_recipe_details["analyzedInstructions"][0].get("steps", []) if s.get("step")]


        plan_recipe_data = {
            "name": original_recipe_details.get("title", "Original Recipe (Name N/A)"),
            "source_recipe_db_id": source_recipe_db_id,
            "spoonacular_id": original_recipe_details.get("id"), # Store original Spoonacular ID
            "ingredients": original_ingredients_structured,
            "instructions": original_instructions_list,
            "image_url": original_recipe_details.get("image"),
            "nutrition_info": original_recipe_details.get("nutrition", {}).get("nutrients"),
            "is_llm_modified": False,
            "llm_suitability_notes": suitability_notes_for_db
        }

    contextual_recipe_id = db_client.save_meal_plan_recipe(plan_recipe_data)
    
    return {
        "contextual_recipe_id": contextual_recipe_id, 
        "contextual_recipe_suitability_notes": plan_recipe_data["llm_suitability_notes"], 
        "error_message": None if contextual_recipe_id else "Failed to save recipe to MealPlanRecipes."
    }


def update_meal_plan_entry_with_modifications_node(state: HealthyNestState) -> Dict: 
    print("--- Node: Update Meal Plan Entry with Overall Modification Status ---")
    suitability_notes = state.get("contextual_recipe_suitability_notes", "Suitability assessment not available.")
    current_mpe_context_holder = state.get("current_meal_plan_entry_for_modification")
    meal_plan_id = state.get("meal_plan_id")

    if not current_mpe_context_holder or not meal_plan_id:
        return {"meal_plan_entry_update_status": "failure_missing_context"}
    
    meal_date = current_mpe_context_holder.get("actual_date")
    meal_type = current_mpe_context_holder.get("meal_type")
    base_recipe_name = current_mpe_context_holder.get("modification_context", {}).get("base_recipe_name", "N/A")

    if not meal_date or not meal_type:
        return {"meal_plan_entry_update_status": "failure_missing_keys"}

    final_mpe_notes = f"Base Recipe: {base_recipe_name}. Overall Assessment: {suitability_notes}"
        
    success = db_client.update_meal_plan_entry_notes(meal_plan_id, meal_date, meal_type, final_mpe_notes)
    return {"meal_plan_entry_update_status": "success" if success else "failure", "error_message": None}


def populate_meal_plan_entry_participants_node(state: HealthyNestState) -> Dict:
    print("--- Node: Populate Meal Plan Entry Participants ---")
    meal_plan_id = state.get("meal_plan_id")
    mpe_ctx_holder = state.get("current_meal_plan_entry_for_modification")
    
    final_recipe_id_for_slot = state.get("contextual_recipe_id") 
    suitability_notes_for_slot = state.get("contextual_recipe_suitability_notes", "Notes unavailable.")
    
    # Determine is_llm_modified based on the LLM output that led to the contextual_recipe_id
    llm_suggestions_data = state.get("llm_modification_suggestions")
    is_llm_modified_flag = False # Default to False
    if isinstance(llm_suggestions_data, LLMModifiedRecipeOutput):
        is_llm_modified_flag = llm_suggestions_data.modifications_were_made
    elif not final_recipe_id_for_slot : # If contextual_recipe_id failed to be created, assume original is used
        is_llm_modified_flag = False


    if not mpe_ctx_holder or not meal_plan_id: return {"meal_plan_entry_participants_status": "failure_missing_context"}
    
    if not final_recipe_id_for_slot:
        print("   ERROR: No contextual_recipe_id available to assign to participants. Attempting fallback to original recipe ID from modification_context.")
        mod_ctx_check = mpe_ctx_holder.get("modification_context")
        if mod_ctx_check:
            final_recipe_id_for_slot = mod_ctx_check.get("base_recipe_id") 
            is_llm_modified_flag = False 
            suitability_notes_for_slot = "Original recipe used due to error in processing/saving contextual/modified version."
            print(f"   Falling back to original recipe ID (from Recipes table): {final_recipe_id_for_slot} for participants.")
            if not final_recipe_id_for_slot:
                 print("   CRITICAL ERROR: No recipe ID (original from context or contextual) to assign to participants.")
                 return {"meal_plan_entry_participants_status": "failure_no_recipe_id_at_all"}
        else:
            print("   CRITICAL ERROR: No modification context to find fallback recipe ID.")
            return {"meal_plan_entry_participants_status": "failure_no_mod_context_for_fallback"}


    meal_date, meal_type, mod_ctx = mpe_ctx_holder.get("actual_date"), mpe_ctx_holder.get("meal_type"), mpe_ctx_holder.get("modification_context")
    if not all([meal_date, meal_type, mod_ctx]): return {"meal_plan_entry_participants_status": "failure_missing_mpe_data"}

    attendees_profiles = mod_ctx.get("attendees_with_profiles", [])
    if not attendees_profiles : return {"meal_plan_entry_participants_status": "failure_no_attendees"}

    mpe_db_id = None
    try: 
        entry_resp = db_client.client.table("MealPlanEntries").select("id").eq("meal_plan_id", meal_plan_id).eq("meal_date", meal_date).eq("meal_type", meal_type).limit(1).single().execute()
        if hasattr(entry_resp, 'data') and entry_resp.data: mpe_db_id = entry_resp.data.get("id")
        if not mpe_db_id: print(f"   ERROR: MPE ID not found for {meal_plan_id}, {meal_date}, {meal_type}"); return {"meal_plan_entry_participants_status": "failure_mpe_not_found"}
        print(f"   Found MPE ID: {mpe_db_id}")
    except Exception as e: print(f"   ERROR querying MPE ID: {e}"); return {"meal_plan_entry_participants_status": "failure_query_mpe_id"}

    participant_entries = []
    for profile in attendees_profiles:
        user_id = profile.get("id")
        if not user_id: continue
        
        participant_entries.append({
            "meal_plan_entry_id": mpe_db_id, "user_id": user_id,
            "assigned_recipe_id": final_recipe_id_for_slot, # This is MealPlanRecipes.id
            "is_modified_version": is_llm_modified_flag, 
            "participant_specific_notes": suitability_notes_for_slot 
        })
    
    if not participant_entries: return {"meal_plan_entry_participants_status": "no_participants_to_save"}
    save_ok = db_client.save_meal_plan_entry_participants(participant_entries)
    
    # Clear state for next iteration in the loop
    return {
        "meal_plan_entry_participants_status": "success" if save_ok else "failure_db_save",
        "contextual_recipe_id": None, "contextual_recipe_suitability_notes": None, 
        "llm_modification_suggestions": None, "live_recipe_details_for_modification": None,
        "error_message": None
    }

# ==============================================================================
# 5. Conditional Logic Functions
# ==============================================================================
def should_continue_planning(state: HealthyNestState) -> str:
    return "get_candidate_recipes_node" if state.get("current_meal_slot") else "present_full_plan_for_review_node"

# ==============================================================================
# 6. Graph Construction
# ==============================================================================
workflow = StateGraph(HealthyNestState)
workflow.add_node("get_plan_request_details_node", get_plan_request_details_node)
workflow.add_node("create_meal_plan_shell_node", create_meal_plan_shell_node)
workflow.add_node("generate_attendee_calendar_llm_node", generate_attendee_calendar_llm_node)
workflow.add_node("present_attendee_calendar_for_confirmation_node", present_attendee_calendar_for_confirmation_node)
workflow.add_node("process_confirmed_attendee_calendar_node", process_confirmed_attendee_calendar_node)
workflow.add_node("determine_next_meal_slot_node", determine_next_meal_slot_node)
workflow.add_node("get_candidate_recipes_node", get_candidate_recipes_node)
workflow.add_node("llm_intelligent_recipe_selection_node", llm_intelligent_recipe_selection_node) 
workflow.add_node("store_draft_plan_item_node", store_draft_plan_item_node)
workflow.add_node("present_full_plan_for_review_node", present_full_plan_for_review_node)
workflow.add_node("process_user_feedback_and_save_node", process_user_feedback_and_save_node)

workflow.add_edge(START, "get_plan_request_details_node")
workflow.add_edge("get_plan_request_details_node", "create_meal_plan_shell_node")
workflow.add_edge("create_meal_plan_shell_node", "generate_attendee_calendar_llm_node")
workflow.add_edge("generate_attendee_calendar_llm_node", "present_attendee_calendar_for_confirmation_node")
workflow.add_edge("present_attendee_calendar_for_confirmation_node", "process_confirmed_attendee_calendar_node")
workflow.add_edge("process_confirmed_attendee_calendar_node", "determine_next_meal_slot_node")
workflow.add_conditional_edges("determine_next_meal_slot_node", should_continue_planning, {"get_candidate_recipes_node": "get_candidate_recipes_node", "present_full_plan_for_review_node": "present_full_plan_for_review_node"})
workflow.add_edge("get_candidate_recipes_node", "llm_intelligent_recipe_selection_node") 
workflow.add_edge("llm_intelligent_recipe_selection_node", "store_draft_plan_item_node") 
workflow.add_edge("store_draft_plan_item_node", "determine_next_meal_slot_node")
workflow.add_edge("present_full_plan_for_review_node", "process_user_feedback_and_save_node")
workflow.add_edge("process_user_feedback_and_save_node", END)

print("Compiling the graph...")
app = workflow.compile()

# ==============================================================================
# 7. Execution / Running the Graph
# ==============================================================================
if __name__ == "__main__":
    print("Starting HealthyNest Planner Graph Execution...")
    initial_state = HealthyNestState(
        user_id=None, start_date=None, days_to_generate=None, plan_description=None,
        attendee_calendar_raw_llm_output=None, confirmed_attendee_calendar=None,
        meal_plan_id=None, meal_slots_to_plan=[], current_slot_index=0,
        current_meal_slot=None, aggregated_needs_for_slot=None,
        candidate_recipes_for_slot=None, default_choice_for_slot=None,
        current_slot_attendee_profiles=None, draft_plan_items=[], 
        current_recipe_for_detailed_view=None, live_recipe_details_for_modification=None,
        current_meal_plan_entry_for_modification=None, 
        llm_modification_suggestions=None, 
        contextual_recipe_id=None, contextual_recipe_suitability_notes=None, 
        hitl_step_required=None, hitl_data_for_ui=None, 
        final_plan_saved_status=None, meal_plan_entry_participants_status=None, 
        error_message=None, 
        messages=[]
    )
    config = {"recursion_limit": 150}
    final_state = app.invoke(initial_state, config=config)
    
    print("\n--- Graph Execution Finished ---")
    print("\n--- Final State (Main Graph) ---")
    def pydantic_model_serializer(obj):
        if isinstance(obj, BaseModel): return obj.model_dump()
        if isinstance(obj, (datetime, timedelta)): return obj.isoformat()
        if isinstance(obj, uuid.UUID): return str(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
    try: print(json.dumps(final_state, indent=2, default=pydantic_model_serializer))
    except TypeError as e: print(f"JSON serialize error: {e}"); [print(f"  {k}: {v}") for k, v in final_state.items()]


    # --- Test Modification Sub-Flow for ALL Meal Plan Entries ---
    print("\n\n--- Testing Recipe Modification and Participant Population Sub-Flow for ALL Entries ---")
    if final_state and final_state.get("final_plan_saved_status") == "success":
        ui_plan_items = final_state.get("hitl_data_for_ui", []) 

        if ui_plan_items:
            print(f"   Found {len(ui_plan_items)} items to process for modification and participant assignment.")
            
            for index, item_to_modify in enumerate(ui_plan_items):
                print(f"\n--- Processing Item {index + 1}/{len(ui_plan_items)} for Mod/Participant: {item_to_modify.get('day')} {item_to_modify.get('meal_type')} ---")
                
                recipe_for_slot_details = {
                    "id": item_to_modify.get("recipe_id"), 
                    "name": item_to_modify.get("recipe_name"),
                    "spoonacular_id": item_to_modify.get("spoonacular_id")
                }
                
                modification_context_for_item = {
                     "base_recipe_id": recipe_for_slot_details["id"], 
                     "base_recipe_name": recipe_for_slot_details["name"],
                     "attendees_with_profiles": item_to_modify.get("attendee_profiles", []),
                     "slot_aggregated_needs": item_to_modify.get("aggregated_needs")
                }
                
                current_item_state = HealthyNestState(
                    meal_plan_id=final_state.get("meal_plan_id"),
                    current_recipe_for_detailed_view=recipe_for_slot_details, 
                    current_meal_plan_entry_for_modification={ 
                        "actual_date": item_to_modify.get("actual_date"), 
                        "meal_type": item_to_modify.get("meal_type"),   
                        "modification_context": modification_context_for_item 
                    },
                    live_recipe_details_for_modification=None, llm_modification_suggestions=None, 
                    contextual_recipe_id=None, contextual_recipe_suitability_notes=None,
                    error_message=None, meal_plan_entry_participants_status=None,
                    messages=[], user_id=final_state.get("user_id"), start_date=final_state.get("start_date"), 
                    days_to_generate=final_state.get("days_to_generate"), plan_description=final_state.get("plan_description"),
                    attendee_calendar_raw_llm_output=None, confirmed_attendee_calendar=None,
                    meal_slots_to_plan=[], current_slot_index=0, current_meal_slot=None,
                    aggregated_needs_for_slot=None, candidate_recipes_for_slot=None,
                    default_choice_for_slot=None, current_slot_attendee_profiles=None,
                    draft_plan_items=[], hitl_step_required=None, hitl_data_for_ui=None, 
                    final_plan_saved_status=None
                )
                
                print(f"   Recipe for slot: {recipe_for_slot_details.get('name')} (Spoonacular ID: {recipe_for_slot_details.get('spoonacular_id')})")

                if recipe_for_slot_details.get("spoonacular_id"):
                    step1_result = get_live_spoonacular_recipe_node(current_item_state)
                    current_item_state.update(step1_result)

                    if current_item_state.get("live_recipe_details_for_modification"):
                        step2_result = apply_critical_modifications_llm_node(current_item_state)
                        current_item_state.update(step2_result) 

                        step3_result = ensure_and_save_plan_recipe_version_node(current_item_state)
                        current_item_state.update(step3_result) 
                        
                        if current_item_state.get("contextual_recipe_id"):
                            print(f"     Saved/Snapshotted to MealPlanRecipes.ID: {current_item_state.get('contextual_recipe_id')}")
                            
                            step4_mpe_notes_result = update_meal_plan_entry_with_modifications_node(current_item_state)
                            print(f"     MealPlanEntry Original Notes Update Status: {step4_mpe_notes_result.get('meal_plan_entry_update_status')}")

                            step5_participants_result = populate_meal_plan_entry_participants_node(current_item_state)
                            print(f"     MealPlanEntryParticipants Population Status: {step5_participants_result.get('meal_plan_entry_participants_status')}")
                        else:
                            print(f"     ERROR: Failed to ensure recipe in MealPlanRecipes or LLM error prevented it.")
                            print(f"     Suitability notes/Error: {current_item_state.get('contextual_recipe_suitability_notes') or current_item_state.get('error_message')}")
                            step4_mpe_notes_result = update_meal_plan_entry_with_modifications_node(current_item_state) 
                            print(f"     MealPlanEntry Original Notes Update Status (with error/suitability): {step4_mpe_notes_result.get('meal_plan_entry_update_status')}")
                    else:
                        print(f"     Failed to get live Spoonacular details for {recipe_for_slot_details.get('name')}: {current_item_state.get('error_message')}")
                        current_item_state["contextual_recipe_suitability_notes"] = f"Failed to fetch Spoonacular details: {current_item_state.get('error_message')}"
                        step4_mpe_notes_result = update_meal_plan_entry_with_modifications_node(current_item_state)
                        print(f"     MealPlanEntry Original Notes Update Status (with fetch error): {step4_mpe_notes_result.get('meal_plan_entry_update_status')}")
                else:
                    print(f"     Skipping modification for {recipe_for_slot_details.get('name')} (no Spoonacular ID).")
                    current_item_state["contextual_recipe_suitability_notes"] = "Skipped modification process as no Spoonacular ID was available for the chosen recipe."
                    step4_mpe_notes_result = update_meal_plan_entry_with_modifications_node(current_item_state)
                    print(f"     MealPlanEntry Original Notes Update Status (skipped): {step4_mpe_notes_result.get('meal_plan_entry_update_status')}")
        else:
            print("   No items in hitl_data_for_ui to test modification flow. (Ensure process_user_feedback_and_save_node preserves this state).")
    else:
        print("   Skipping modification sub-flow test as main plan did not save successfully or final_state not available.")

    if SPOONACULAR_API_KEY and isinstance(spoonacular_client, RealSpoonacularClient):
        print("\n\n--- Testing Spoonacular API Fetch (Independent Test) ---")
        a_spoonacular_id_to_test = None
        if final_state and final_state.get("hitl_data_for_ui"): 
            ui_items = final_state.get("hitl_data_for_ui", [])
            if ui_items:
                first_ui_item = ui_items[0]
                if first_ui_item.get("spoonacular_id"):
                    a_spoonacular_id_to_test = first_ui_item.get("spoonacular_id")
        
        if a_spoonacular_id_to_test:
            print(f"Attempting to fetch details for Spoonacular ID: {a_spoonacular_id_to_test}")
            details = spoonacular_client.get_recipe_information(a_spoonacular_id_to_test, include_nutrition=True)
            if details:
                print(f"Successfully fetched details for: {details.get('title')}")
                # print(f"  Servings: {details.get('servings')}")
                # print(f"  Ready in minutes: {details.get('readyInMinutes')}")
                # if details.get("extendedIngredients"):
                #     print(f"  First ingredient: {details['extendedIngredients'][0]['original']}")
            else:
                print(f"Failed to fetch details for Spoonacular ID: {a_spoonacular_id_to_test}")
        else:
            test_fallback_id = 632925 
            print(f"No Spoonacular ID found in plan, attempting fallback test with ID: {test_fallback_id}")
            details = spoonacular_client.get_recipe_information(test_fallback_id, include_nutrition=True)
            if details: 
                 print(f"Successfully fetched details for fallback ID: {details.get('title')}")
            else:
                print(f"Failed to fetch details for fallback Spoonacular ID: {test_fallback_id}")
    elif not SPOONACULAR_API_KEY:
        print("\nSpoonacular API key not found. Skipping live API test. Mock client will be used if node is called in main flow.")
