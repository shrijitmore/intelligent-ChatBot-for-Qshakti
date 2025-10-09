#!/usr/bin/env python3
"""Debug chart generation issue"""

import requests
import json

def debug_chart_generation():
    session_id = 'debug-chart-session'
    base_url = "https://llm-removal-branch.preview.emergentagent.com/api"
    
    # Initialize session
    init_response = requests.post(f"{base_url}/chat/initialize", json={'session_id': session_id})
    print("1. Initialize:", init_response.status_code)
    
    # Navigate to plant
    plant_response = requests.post(f"{base_url}/chat/message", 
                                  json={'session_id': session_id, 'message': 'Explore AMMUNITION FACTORY KHADKI', 'is_suggestion': False})
    print("2. Plant navigation:", plant_response.status_code)
    
    # Navigate to section  
    section_response = requests.post(f"{base_url}/chat/message", 
                                    json={'session_id': session_id, 'message': 'Show me CASE 4', 'is_suggestion': False})
    print("3. Section navigation:", section_response.status_code)
    
    # Navigate to item
    item_response = requests.post(f"{base_url}/chat/message", 
                                 json={'session_id': session_id, 'message': 'Tell me about 5.56MM BALL M-193', 'is_suggestion': False})
    print("4. Item navigation:", item_response.status_code)
    item_data = item_response.json()
    print("   Item context:", item_data.get('metadata', {}).get('context'))
    
    # Try different chart requests
    chart_requests = [
        "Show me quality trends",
        "Create a chart",
        "Visualize the data", 
        "Show me a graph",
        "Display quality trends over time"
    ]
    
    for i, request in enumerate(chart_requests, 5):
        print(f"\n{i}. Testing chart request: '{request}'")
        chart_response = requests.post(f"{base_url}/chat/message", 
                                      json={'session_id': session_id, 'message': request, 'is_suggestion': False})
        print(f"   Status: {chart_response.status_code}")
        
        if chart_response.status_code == 200:
            chart_data = chart_response.json()
            has_chart = chart_data.get('chart_data') is not None
            print(f"   Has chart_data: {has_chart}")
            
            if has_chart:
                chart_info = chart_data['chart_data']
                print(f"   Chart type: {chart_info.get('type')}")
                print(f"   Chart title: {chart_info.get('title')}")
                break
            else:
                print(f"   Response: {chart_data.get('response', '')[:100]}...")
        else:
            print(f"   Error: {chart_response.text}")

if __name__ == "__main__":
    debug_chart_generation()