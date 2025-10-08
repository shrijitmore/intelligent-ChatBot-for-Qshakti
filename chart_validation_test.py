#!/usr/bin/env python3
"""
Detailed Chart Data Validation Test
"""

import requests
import json
import uuid

BACKEND_URL = "https://repo-explorer-94.preview.emergentagent.com/api"
TEST_SESSION_ID = str(uuid.uuid4())

def test_chart_data_structure():
    """Test detailed chart data structure validation"""
    
    # Initialize session
    init_payload = {"session_id": TEST_SESSION_ID}
    requests.post(f"{BACKEND_URL}/chat/initialize", json=init_payload)
    
    # Test chart request
    payload = {
        "session_id": TEST_SESSION_ID,
        "message": "Show me a bar chart of inspection types",
        "is_suggestion": False
    }
    
    response = requests.post(f"{BACKEND_URL}/chat/message", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        chart_data = data.get("chart_data")
        
        if chart_data:
            print("✅ Chart Data Structure Validation:")
            print(f"  - Type: {chart_data.get('type')}")
            print(f"  - Title: {chart_data.get('title')}")
            
            chart_data_obj = chart_data.get('data', {})
            print(f"  - Labels: {chart_data_obj.get('labels', [])}")
            
            datasets = chart_data_obj.get('datasets', [])
            if datasets:
                dataset = datasets[0]
                print(f"  - Dataset Label: {dataset.get('label')}")
                print(f"  - Dataset Data: {dataset.get('data', [])}")
                print(f"  - Background Colors: {dataset.get('backgroundColor', [])}")
            
            options = chart_data.get('options', {})
            print(f"  - Responsive: {options.get('responsive')}")
            
            plugins = options.get('plugins', {})
            if plugins:
                print(f"  - Legend Position: {plugins.get('legend', {}).get('position')}")
                title_config = plugins.get('title', {})
                print(f"  - Title Display: {title_config.get('display')}")
                print(f"  - Title Text: {title_config.get('text')}")
            
            print("\n📊 Full Chart Data:")
            print(json.dumps(chart_data, indent=2))
            
            return True
        else:
            print("❌ No chart data returned")
            return False
    else:
        print(f"❌ API Error: {response.status_code}")
        return False

if __name__ == "__main__":
    test_chart_data_structure()