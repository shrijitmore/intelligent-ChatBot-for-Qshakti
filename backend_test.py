#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Intelligent Database Chatbot
Tests all API endpoints with focus on chart generation feature
"""

import requests
import json
import uuid
import time
from typing import Dict, Any, List

# Configuration
BACKEND_URL = "https://repo-analyze.preview.emergentagent.com/api"
TEST_SESSION_ID = str(uuid.uuid4())

class ChatbotAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "running" in data["message"]:
                    self.log_test("Root Endpoint", True, "API is running correctly")
                    return True
                else:
                    self.log_test("Root Endpoint", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Connection error: {str(e)}")
            return False
    
    def test_initialize_chat(self):
        """Test chat initialization"""
        try:
            payload = {"session_id": TEST_SESSION_ID}
            response = requests.post(f"{self.base_url}/chat/initialize", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["session_id", "suggestions", "message"]
                
                if all(field in data for field in required_fields):
                    if len(data["suggestions"]) == 5:
                        self.session_id = data["session_id"]
                        self.log_test("Initialize Chat", True, 
                                    f"Session initialized with 5 suggestions", data)
                        return True
                    else:
                        self.log_test("Initialize Chat", False, 
                                    f"Expected 5 suggestions, got {len(data['suggestions'])}")
                        return False
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test("Initialize Chat", False, f"Missing fields: {missing}")
                    return False
            else:
                self.log_test("Initialize Chat", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Initialize Chat", False, f"Error: {str(e)}")
            return False
    
    def test_regular_message(self):
        """Test regular message without chart request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "What tables are related to inspection?",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["session_id", "response", "suggestions", "context_path"]
                
                if all(field in data for field in required_fields):
                    # Check that chart_data is null for non-chart requests
                    if data.get("chart_data") is None:
                        if len(data["suggestions"]) == 5:
                            self.log_test("Regular Message", True, 
                                        "Non-chart message processed correctly", data)
                            return True
                        else:
                            self.log_test("Regular Message", False, 
                                        f"Expected 5 suggestions, got {len(data['suggestions'])}")
                            return False
                    else:
                        self.log_test("Regular Message", False, 
                                    "chart_data should be null for non-chart requests")
                        return False
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test("Regular Message", False, f"Missing fields: {missing}")
                    return False
            else:
                self.log_test("Regular Message", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Regular Message", False, f"Error: {str(e)}")
            return False
    
    def test_chart_generation_bar(self):
        """Test chart generation with bar chart request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Show me a bar chart of inspection types",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if chart_data is present and properly structured
                if data.get("chart_data"):
                    chart_data = data["chart_data"]
                    required_chart_fields = ["type", "title", "data"]
                    
                    if all(field in chart_data for field in required_chart_fields):
                        # Verify chart data structure
                        chart_type = chart_data.get("type")
                        chart_title = chart_data.get("title")
                        chart_data_obj = chart_data.get("data", {})
                        
                        if "labels" in chart_data_obj and "datasets" in chart_data_obj:
                            if isinstance(chart_data_obj["datasets"], list) and len(chart_data_obj["datasets"]) > 0:
                                dataset = chart_data_obj["datasets"][0]
                                if "data" in dataset and "label" in dataset:
                                    self.log_test("Chart Generation - Bar", True, 
                                                f"Bar chart generated successfully: {chart_type}", data)
                                    return True
                                else:
                                    self.log_test("Chart Generation - Bar", False, 
                                                "Dataset missing required fields (data, label)")
                                    return False
                            else:
                                self.log_test("Chart Generation - Bar", False, 
                                            "Datasets should be non-empty array")
                                return False
                        else:
                            self.log_test("Chart Generation - Bar", False, 
                                        "Chart data missing labels or datasets")
                            return False
                    else:
                        missing = [f for f in required_chart_fields if f not in chart_data]
                        self.log_test("Chart Generation - Bar", False, 
                                    f"Chart data missing fields: {missing}")
                        return False
                else:
                    self.log_test("Chart Generation - Bar", False, 
                                "No chart_data returned for chart request")
                    return False
            else:
                self.log_test("Chart Generation - Bar", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Chart Generation - Bar", False, f"Error: {str(e)}")
            return False
    
    def test_chart_generation_pie(self):
        """Test chart generation with pie chart request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Create a pie chart comparing quality metrics",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("chart_data"):
                    chart_data = data["chart_data"]
                    chart_type = chart_data.get("type")
                    
                    if chart_type in ["pie", "doughnut"]:
                        self.log_test("Chart Generation - Pie", True, 
                                    f"Pie chart generated: {chart_type}", data)
                        return True
                    else:
                        self.log_test("Chart Generation - Pie", False, 
                                    f"Expected pie chart, got: {chart_type}")
                        return False
                else:
                    self.log_test("Chart Generation - Pie", False, 
                                "No chart_data returned for pie chart request")
                    return False
            else:
                self.log_test("Chart Generation - Pie", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Chart Generation - Pie", False, f"Error: {str(e)}")
            return False
    
    def test_chart_generation_line(self):
        """Test chart generation with line chart request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Generate a line graph showing trends over time",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("chart_data"):
                    chart_data = data["chart_data"]
                    chart_type = chart_data.get("type")
                    
                    if chart_type == "line":
                        self.log_test("Chart Generation - Line", True, 
                                    "Line chart generated successfully", data)
                        return True
                    else:
                        self.log_test("Chart Generation - Line", False, 
                                    f"Expected line chart, got: {chart_type}")
                        return False
                else:
                    self.log_test("Chart Generation - Line", False, 
                                "No chart_data returned for line chart request")
                    return False
            else:
                self.log_test("Chart Generation - Line", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Chart Generation - Line", False, f"Error: {str(e)}")
            return False
    
    def test_chart_generation_visualization(self):
        """Test chart generation with visualization request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Visualize the machine data distribution",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("chart_data"):
                    chart_data = data["chart_data"]
                    chart_type = chart_data.get("type")
                    
                    # Accept any valid chart type for visualization request
                    valid_types = ["bar", "line", "pie", "scatter", "histogram"]
                    if chart_type in valid_types:
                        self.log_test("Chart Generation - Visualization", True, 
                                    f"Visualization chart generated: {chart_type}", data)
                        return True
                    else:
                        self.log_test("Chart Generation - Visualization", False, 
                                    f"Invalid chart type: {chart_type}")
                        return False
                else:
                    self.log_test("Chart Generation - Visualization", False, 
                                "No chart_data returned for visualization request")
                    return False
            else:
                self.log_test("Chart Generation - Visualization", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Chart Generation - Visualization", False, f"Error: {str(e)}")
            return False
    
    def test_chat_history(self):
        """Test chat history retrieval"""
        try:
            session_id = self.session_id or TEST_SESSION_ID
            response = requests.get(f"{self.base_url}/chat/history/{session_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if "session_id" in data and "messages" in data:
                    if isinstance(data["messages"], list):
                        # Should have messages from previous tests
                        if len(data["messages"]) > 0:
                            self.log_test("Chat History", True, 
                                        f"Retrieved {len(data['messages'])} messages", data)
                            return True
                        else:
                            self.log_test("Chat History", True, 
                                        "No messages in history (expected for new session)")
                            return True
                    else:
                        self.log_test("Chat History", False, 
                                    "Messages should be an array")
                        return False
                else:
                    self.log_test("Chat History", False, 
                                "Missing session_id or messages in response")
                    return False
            else:
                self.log_test("Chat History", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Chat History", False, f"Error: {str(e)}")
            return False
    
    def test_decision_tree(self):
        """Test decision tree path retrieval"""
        try:
            session_id = self.session_id or TEST_SESSION_ID
            response = requests.get(f"{self.base_url}/chat/tree/{session_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if "session_id" in data and "tree_path" in data:
                    if isinstance(data["tree_path"], list):
                        self.log_test("Decision Tree", True, 
                                    f"Retrieved tree path with {len(data['tree_path'])} steps", data)
                        return True
                    else:
                        self.log_test("Decision Tree", False, 
                                    "tree_path should be an array")
                        return False
                else:
                    self.log_test("Decision Tree", False, 
                                "Missing session_id or tree_path in response")
                    return False
            else:
                self.log_test("Decision Tree", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Decision Tree", False, f"Error: {str(e)}")
            return False
    
    def test_session_reset(self):
        """Test session reset functionality"""
        try:
            session_id = self.session_id or TEST_SESSION_ID
            response = requests.delete(f"{self.base_url}/chat/reset/{session_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if "message" in data and "reset" in data["message"].lower():
                    self.log_test("Session Reset", True, 
                                "Session reset successfully", data)
                    return True
                else:
                    self.log_test("Session Reset", False, 
                                f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Session Reset", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Session Reset", False, f"Error: {str(e)}")
            return False
    
    def test_metadata_and_suggestions(self):
        """Test that responses include proper metadata and suggestions"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "How does production planning work?",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check metadata
                if "metadata" in data and data["metadata"]:
                    metadata = data["metadata"]
                    if "relevant_tables" in metadata:
                        # Check suggestions
                        if "suggestions" in data and len(data["suggestions"]) == 5:
                            # Check context_path
                            if "context_path" in data and isinstance(data["context_path"], list):
                                self.log_test("Metadata and Suggestions", True, 
                                            "All metadata and suggestions present", data)
                                return True
                            else:
                                self.log_test("Metadata and Suggestions", False, 
                                            "context_path missing or invalid")
                                return False
                        else:
                            self.log_test("Metadata and Suggestions", False, 
                                        f"Expected 5 suggestions, got {len(data.get('suggestions', []))}")
                            return False
                    else:
                        self.log_test("Metadata and Suggestions", False, 
                                    "relevant_tables missing from metadata")
                        return False
                else:
                    self.log_test("Metadata and Suggestions", False, 
                                "metadata missing from response")
                    return False
            else:
                self.log_test("Metadata and Suggestions", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Metadata and Suggestions", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Backend API Tests")
        print("=" * 60)
        
        # Priority 1: Core functionality
        self.test_root_endpoint()
        self.test_initialize_chat()
        
        # Priority 2: Chart generation (new feature)
        self.test_chart_generation_bar()
        self.test_chart_generation_pie()
        self.test_chart_generation_line()
        self.test_chart_generation_visualization()
        
        # Priority 3: Regular chat functionality
        self.test_regular_message()
        self.test_metadata_and_suggestions()
        
        # Priority 4: Session management
        self.test_chat_history()
        self.test_decision_tree()
        self.test_session_reset()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return passed == total

if __name__ == "__main__":
    tester = ChatbotAPITester(BACKEND_URL)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the details above.")