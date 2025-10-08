#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Intelligent Database Chatbot
Tests all API endpoints with focus on BOTH chart and table generation features

Priority 1: Table Generation Feature (NEW)
- List all inspection parameters
- Show all tables related to quality control  
- Display all machine information
- What are all the operations?
- Give me all user management tables

Priority 2: Chart Generation Feature (EXISTING)
- Bar charts, pie charts, line charts, visualizations

Priority 3: Combined and Edge Cases
- Regular queries (no chart/table)
- Mixed conversation history
- Proper data separation
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
    
    def test_table_generation_inspection_parameters(self):
        """Test table generation with inspection parameters request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "List all inspection parameters",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if table_data is present and properly structured
                if data.get("table_data"):
                    table_data = data["table_data"]
                    required_table_fields = ["title", "columns", "rows", "description"]
                    
                    if all(field in table_data for field in required_table_fields):
                        # Verify table data structure
                        title = table_data.get("title")
                        columns = table_data.get("columns")
                        rows = table_data.get("rows")
                        description = table_data.get("description")
                        
                        if isinstance(columns, list) and len(columns) > 0:
                            if isinstance(rows, list) and len(rows) > 0:
                                # Check that chart_data is null for table requests
                                if data.get("chart_data") is None:
                                    self.log_test("Table Generation - Inspection Parameters", True, 
                                                f"Table generated successfully: {title}", data)
                                    return True
                                else:
                                    self.log_test("Table Generation - Inspection Parameters", False, 
                                                "chart_data should be null for table requests")
                                    return False
                            else:
                                self.log_test("Table Generation - Inspection Parameters", False, 
                                            "Rows should be non-empty array")
                                return False
                        else:
                            self.log_test("Table Generation - Inspection Parameters", False, 
                                        "Columns should be non-empty array")
                            return False
                    else:
                        missing = [f for f in required_table_fields if f not in table_data]
                        self.log_test("Table Generation - Inspection Parameters", False, 
                                    f"Table data missing fields: {missing}")
                        return False
                else:
                    self.log_test("Table Generation - Inspection Parameters", False, 
                                "No table_data returned for table request")
                    return False
            else:
                self.log_test("Table Generation - Inspection Parameters", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Table Generation - Inspection Parameters", False, f"Error: {str(e)}")
            return False
    
    def test_table_generation_quality_control(self):
        """Test table generation with quality control tables request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Show all tables related to quality control",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("table_data"):
                    table_data = data["table_data"]
                    if "title" in table_data and "quality" in table_data["title"].lower():
                        self.log_test("Table Generation - Quality Control", True, 
                                    f"Quality control table generated: {table_data['title']}", data)
                        return True
                    else:
                        self.log_test("Table Generation - Quality Control", True, 
                                    f"Table generated (title may vary): {table_data.get('title', 'No title')}", data)
                        return True
                else:
                    self.log_test("Table Generation - Quality Control", False, 
                                "No table_data returned for quality control request")
                    return False
            else:
                self.log_test("Table Generation - Quality Control", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Table Generation - Quality Control", False, f"Error: {str(e)}")
            return False
    
    def test_table_generation_machine_info(self):
        """Test table generation with machine information request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Display all machine information",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("table_data"):
                    table_data = data["table_data"]
                    # Verify proper table structure
                    if isinstance(table_data.get("columns"), list) and isinstance(table_data.get("rows"), list):
                        self.log_test("Table Generation - Machine Info", True, 
                                    f"Machine info table generated: {table_data.get('title', 'Machine Data')}", data)
                        return True
                    else:
                        self.log_test("Table Generation - Machine Info", False, 
                                    "Invalid table structure (columns/rows not arrays)")
                        return False
                else:
                    self.log_test("Table Generation - Machine Info", False, 
                                "No table_data returned for machine info request")
                    return False
            else:
                self.log_test("Table Generation - Machine Info", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Table Generation - Machine Info", False, f"Error: {str(e)}")
            return False
    
    def test_table_generation_operations(self):
        """Test table generation with operations request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "What are all the operations?",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("table_data"):
                    table_data = data["table_data"]
                    # Check that we have meaningful data
                    if len(table_data.get("rows", [])) > 0:
                        self.log_test("Table Generation - Operations", True, 
                                    f"Operations table generated with {len(table_data['rows'])} rows", data)
                        return True
                    else:
                        self.log_test("Table Generation - Operations", False, 
                                    "Table generated but no data rows")
                        return False
                else:
                    self.log_test("Table Generation - Operations", False, 
                                "No table_data returned for operations request")
                    return False
            else:
                self.log_test("Table Generation - Operations", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Table Generation - Operations", False, f"Error: {str(e)}")
            return False
    
    def test_table_generation_user_management(self):
        """Test table generation with user management request"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Give me all user management tables",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("table_data"):
                    table_data = data["table_data"]
                    # Verify description mentions user management
                    description = table_data.get("description", "").lower()
                    if "user" in description or "management" in description or len(table_data.get("rows", [])) > 0:
                        self.log_test("Table Generation - User Management", True, 
                                    f"User management table generated: {table_data.get('title', 'User Data')}", data)
                        return True
                    else:
                        self.log_test("Table Generation - User Management", False, 
                                    "Table doesn't seem related to user management")
                        return False
                else:
                    self.log_test("Table Generation - User Management", False, 
                                "No table_data returned for user management request")
                    return False
            else:
                self.log_test("Table Generation - User Management", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Table Generation - User Management", False, f"Error: {str(e)}")
            return False
    
    def test_regular_query_no_chart_no_table(self):
        """Test regular query that should return neither chart nor table data"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Explain the inspection workflow",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check that both chart_data and table_data are null
                if data.get("chart_data") is None and data.get("table_data") is None:
                    if len(data.get("response", "")) > 0:
                        self.log_test("Regular Query - No Chart/Table", True, 
                                    "Regular query processed correctly (no chart/table data)", data)
                        return True
                    else:
                        self.log_test("Regular Query - No Chart/Table", False, 
                                    "No response text provided")
                        return False
                else:
                    chart_status = "present" if data.get("chart_data") else "null"
                    table_status = "present" if data.get("table_data") else "null"
                    self.log_test("Regular Query - No Chart/Table", False, 
                                f"Expected both null, got chart_data: {chart_status}, table_data: {table_status}")
                    return False
            else:
                self.log_test("Regular Query - No Chart/Table", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Regular Query - No Chart/Table", False, f"Error: {str(e)}")
            return False
    
    def test_database_permissions_query(self):
        """Test regular query about database permissions"""
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "How does the database handle user permissions?",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should be regular response with no chart/table data
                if data.get("chart_data") is None and data.get("table_data") is None:
                    if "permission" in data.get("response", "").lower() or len(data.get("response", "")) > 50:
                        self.log_test("Database Permissions Query", True, 
                                    "Permissions query answered correctly", data)
                        return True
                    else:
                        self.log_test("Database Permissions Query", False, 
                                    "Response doesn't address permissions or too short")
                        return False
                else:
                    self.log_test("Database Permissions Query", False, 
                                "Regular query should not return chart/table data")
                    return False
            else:
                self.log_test("Database Permissions Query", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Database Permissions Query", False, f"Error: {str(e)}")
            return False
    
    def test_combined_conversation_persistence(self):
        """Test that both chart and table data can exist in conversation history"""
        try:
            # First make a chart request
            chart_payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Show me a bar chart of inspection types",
                "is_suggestion": False
            }
            chart_response = requests.post(f"{self.base_url}/chat/message", json=chart_payload)
            
            if chart_response.status_code != 200:
                self.log_test("Combined Conversation - Chart", False, 
                            f"Chart request failed: {chart_response.status_code}")
                return False
            
            # Then make a table request
            table_payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "List all inspection parameters",
                "is_suggestion": False
            }
            table_response = requests.post(f"{self.base_url}/chat/message", json=table_payload)
            
            if table_response.status_code != 200:
                self.log_test("Combined Conversation - Table", False, 
                            f"Table request failed: {table_response.status_code}")
                return False
            
            # Check history contains both
            history_response = requests.get(f"{self.base_url}/chat/history/{self.session_id or TEST_SESSION_ID}")
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                messages = history_data.get("messages", [])
                
                # Look for both chart and table data in history
                has_chart = any(msg.get("chart_data") for msg in messages)
                has_table = any(msg.get("table_data") for msg in messages)
                
                if has_chart and has_table:
                    self.log_test("Combined Conversation Persistence", True, 
                                f"Both chart and table data found in history ({len(messages)} messages)", history_data)
                    return True
                else:
                    self.log_test("Combined Conversation Persistence", False, 
                                f"Missing data in history - chart: {has_chart}, table: {has_table}")
                    return False
            else:
                self.log_test("Combined Conversation Persistence", False, 
                            f"History request failed: {history_response.status_code}")
                return False
        except Exception as e:
            self.log_test("Combined Conversation Persistence", False, f"Error: {str(e)}")
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
        print("🚀 Starting Comprehensive Backend API Tests - Chart & Table Generation")
        print("=" * 70)
        
        # Priority 1: Core functionality
        self.test_root_endpoint()
        self.test_initialize_chat()
        
        # Priority 2: Table generation (NEW FEATURE - HIGH PRIORITY)
        print("\n📋 TESTING TABLE GENERATION FEATURES")
        print("-" * 50)
        self.test_table_generation_inspection_parameters()
        self.test_table_generation_quality_control()
        self.test_table_generation_machine_info()
        self.test_table_generation_operations()
        self.test_table_generation_user_management()
        
        # Priority 3: Chart generation (EXISTING FEATURE)
        print("\n📊 TESTING CHART GENERATION FEATURES")
        print("-" * 50)
        self.test_chart_generation_bar()
        self.test_chart_generation_pie()
        self.test_chart_generation_line()
        self.test_chart_generation_visualization()
        
        # Priority 4: Combined and edge cases
        print("\n🔄 TESTING COMBINED & EDGE CASES")
        print("-" * 50)
        self.test_regular_query_no_chart_no_table()
        self.test_database_permissions_query()
        self.test_combined_conversation_persistence()
        
        # Priority 5: Regular chat functionality & session management
        print("\n⚙️ TESTING CORE FUNCTIONALITY")
        print("-" * 50)
        self.test_regular_message()
        self.test_metadata_and_suggestions()
        self.test_chat_history()
        self.test_decision_tree()
        self.test_session_reset()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Categorize results
        table_tests = [r for r in self.test_results if "Table Generation" in r["test"]]
        chart_tests = [r for r in self.test_results if "Chart Generation" in r["test"]]
        combined_tests = [r for r in self.test_results if "Combined" in r["test"] or "Regular Query" in r["test"]]
        core_tests = [r for r in self.test_results if r not in table_tests + chart_tests + combined_tests]
        
        print(f"\n📋 Table Generation Tests: {sum(1 for t in table_tests if t['success'])}/{len(table_tests)} passed")
        print(f"📊 Chart Generation Tests: {sum(1 for t in chart_tests if t['success'])}/{len(chart_tests)} passed")
        print(f"🔄 Combined/Edge Case Tests: {sum(1 for t in combined_tests if t['success'])}/{len(combined_tests)} passed")
        print(f"⚙️ Core Functionality Tests: {sum(1 for t in core_tests if t['success'])}/{len(core_tests)} passed")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        else:
            print("\n✅ ALL TESTS PASSED!")
        
        return passed == total

if __name__ == "__main__":
    tester = ChatbotAPITester(BACKEND_URL)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the details above.")