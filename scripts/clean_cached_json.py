"""Clean up markdown fences from cached JSON files and fix audit enum issues."""
import json
import os

outputs_dir = "data/02_ai_outputs/A001"

def clean_fences(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    dirty = False
    if content.startswith("```json"):
        content = content[7:].strip()
        dirty = True
    elif content.startswith("```"):
        content = content[3:].strip()
        dirty = True
        
    if content.endswith("```"):
        content = content[:-3].strip()
        dirty = True
        
    if dirty:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Cleaned markdown fences from: {filepath}")
    else:
        print(f"No fences found in: {filepath}")

# Clean mapping.json and scenario_extraction.json
clean_fences(os.path.join(outputs_dir, "mapping.json"))
clean_fences(os.path.join(outputs_dir, "scenario_extraction.json"))

# Fix inconsistent_scenario_id in audit.json
audit_path = os.path.join(outputs_dir, "audit.json")
if os.path.exists(audit_path):
    with open(audit_path, "r", encoding="utf-8") as f:
        audit_data = json.load(f)
    
    fixed = False
    for issue in audit_data.get("issues", []):
        if issue.get("issue_type") == "inconsistent_scenario_id":
            issue["issue_type"] = "missing_scenario_linkage"
            fixed = True
            print("Fixed 'inconsistent_scenario_id' to 'missing_scenario_linkage' in audit.json")
            
    if fixed:
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2, ensure_ascii=False)
