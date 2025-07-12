#!/usr/bin/env python3
"""
Fix the import in router.py
"""

import os
from pathlib import Path
from colorama import Fore, init

init(autoreset=True)

def fix_router_import():
    """Fix the import in router.py"""
    
    router_path = Path("app/api/v1/endpoints/creators/router.py")
    
    if not router_path.exists():
        print(f"{Fore.RED}Router file not found at: {router_path}")
        return False
    
    print(f"{Fore.CYAN}Fixing import in router.py...")
    
    # Read the file
    with open(router_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The wrong import
    wrong_import = "from app.models.creator import CreatorAudienceDemographics"
    
    # The correct import (based on your output, it's already imported correctly!)
    correct_import = "from app.models.demographics import CreatorAudienceDemographics"
    
    if wrong_import in content:
        # Replace the import
        new_content = content.replace(wrong_import, correct_import)
        
        # Write back
        with open(router_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"{Fore.GREEN}✓ Fixed import!")
        print(f"{Fore.RED}  - Removed: {wrong_import}")
        print(f"{Fore.GREEN}  + Added: {correct_import}")
        return True
    elif correct_import in content:
        print(f"{Fore.GREEN}✓ Import is already correct!")
        print(f"  Found: {correct_import}")
        
        # Check if there's a duplicate wrong import
        lines = content.split('\n')
        import_lines = [i for i, line in enumerate(lines) if 'CreatorAudienceDemographics' in line and 'import' in line]
        
        if len(import_lines) > 1:
            print(f"\n{Fore.YELLOW}⚠ Found multiple imports of CreatorAudienceDemographics:")
            for idx in import_lines:
                print(f"  Line {idx + 1}: {lines[idx].strip()}")
            print(f"\n{Fore.YELLOW}Remove any duplicate imports!")
        
        # The import is correct, but let's check the debug endpoint
        print(f"\n{Fore.CYAN}The import looks correct. Let's check your debug endpoint...")
        
        # Find where the model is used
        if "from app.models.creator import CreatorAudienceDemographics" in content:
            print(f"{Fore.RED}✗ Found conflicting import from app.models.creator")
            print(f"{Fore.YELLOW}This is causing the error!")
            
            # Remove the wrong import
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if "from app.models.creator import CreatorAudienceDemographics" not in line:
                    new_lines.append(line)
                else:
                    print(f"{Fore.RED}  Removing line: {line.strip()}")
            
            new_content = '\n'.join(new_lines)
            
            with open(router_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            print(f"{Fore.GREEN}✓ Removed conflicting import!")
            return True
    else:
        print(f"{Fore.RED}✗ Could not find import statement")
        print(f"\n{Fore.YELLOW}Add this import to your router.py:")
        print(f"{Fore.WHITE}{correct_import}")
        return False
    
    return True

def check_debug_endpoint():
    """Check if the debug endpoint has the wrong import"""
    
    # The debug endpoint might be in the router itself
    router_path = Path("app/api/v1/endpoints/creators/router.py")
    
    if router_path.exists():
        with open(router_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the debug endpoint
        if "demographics/test" in content and "from app.models.creator import CreatorAudienceDemographics" in content:
            print(f"\n{Fore.YELLOW}Found the issue!")
            print(f"The debug endpoint is trying to import from app.models.creator")
            print(f"But the model is in app.models.demographics")

def verify_model_location():
    """Verify the model exists in the correct location"""
    
    print(f"\n{Fore.CYAN}=== Verifying Model Location ===")
    
    # Check app/models/demographics.py
    demographics_model = Path("app/models/demographics.py")
    
    if demographics_model.exists():
        print(f"{Fore.GREEN}✓ app/models/demographics.py exists")
        
        with open(demographics_model, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "class CreatorAudienceDemographics" in content:
            print(f"{Fore.GREEN}✓ CreatorAudienceDemographics class found in demographics.py")
        else:
            print(f"{Fore.RED}✗ CreatorAudienceDemographics class NOT found in demographics.py")
    else:
        print(f"{Fore.RED}✗ app/models/demographics.py does not exist")

if __name__ == "__main__":
    print(f"{Fore.MAGENTA}{'*' * 60}")
    print(f"{Fore.MAGENTA}Import Fixer")
    print(f"{Fore.MAGENTA}{'*' * 60}\n")
    
    # Fix the import
    fixed = fix_router_import()
    
    # Check debug endpoint
    check_debug_endpoint()
    
    # Verify model location
    verify_model_location()
    
    if fixed:
        print(f"\n{Fore.GREEN}✓ Import should be fixed!")
        print(f"{Fore.YELLOW}Now restart your FastAPI server:")
        print(f"{Fore.WHITE}uvicorn app.main:app --reload --host 0.0.0.0 --port 8006")
    else:
        print(f"\n{Fore.YELLOW}Manual fix needed:")
        print(f"1. Open app/api/v1/endpoints/creators/router.py")
        print(f"2. Find: from app.models.creator import CreatorAudienceDemographics")
        print(f"3. Replace with: from app.models.demographics import CreatorAudienceDemographics")
        print(f"4. Save and restart your server")