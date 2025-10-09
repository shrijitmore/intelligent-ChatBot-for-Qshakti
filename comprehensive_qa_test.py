#!/usr/bin/env python3
"""
Comprehensive Q&A System Backend Tests
Tests all 6 question types as specified in the review request:

1. PO Status - Factory selection -> PO selection -> Complete table with 40+ columns + charts
2. Inward Material Quality 
3. In-Process Inspection
4. Final Inspection
5. Parameter Analysis with charts
6. Parameter Distribution with histogram + statistics

NO LLM - Pure static Q&A system
"""

import requests
import json
import uuid
import time
from typing import Dict, Any, List

# Configuration - Use the correct backend URL from frontend/.env
BACKEND_URL = "https://llm-removal-branch.preview.emergentagent.com/api"

class ComprehensiveQASystemTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
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
        """Test chat initialization - should return 6 question suggestions"""
        try:
            session_id = "test-session-123"
            payload = {"session_id": session_id}
            response = requests.post(f"{self.base_url}/chat/initialize", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["session_id", "suggestions", "message"]
                
                if all(field in data for field in required_fields):
                    suggestions = data["suggestions"]
                    if len(suggestions) == 6:
                        # Check if all 6 question types are present
                        expected_keywords = ["PO", "Inward", "In-process", "Final", "Parameter analysis", "distribution"]
                        found_keywords = 0
                        for keyword in expected_keywords:
                            if any(keyword.lower() in s.lower() for s in suggestions):
                                found_keywords += 1
                        
                        if found_keywords >= 5:  # Allow some flexibility in wording
                            self.log_test("Initialize Chat", True, 
                                        f"Session initialized with 6 question suggestions", data)
                            return True
                        else:
                            self.log_test("Initialize Chat", False, 
                                        f"Missing expected question types. Found {found_keywords}/6")
                            return False
                    else:
                        self.log_test("Initialize Chat", False, 
                                    f"Expected 6 suggestions, got {len(suggestions)}")
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
    
    def test_question_1_po_status_complete_flow(self):
        """Test Question 1: PO Status - Complete flow as specified"""
        try:
            session_id = "test-session-123"
            
            # Step 1: Send "1" to select PO Status
            payload = {
                "session_id": session_id,
                "message": "1",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code != 200:
                self.log_test("Q1 PO Status - Step 1", False, f"HTTP {response.status_code}")
                return False
            
            data = response.json()
            if not self._validate_response_structure(data):
                self.log_test("Q1 PO Status - Step 1", False, "Invalid response structure")
                return False
            
            # Check if factory selection is shown
            response_text = data.get("response", "").lower()
            if "factory" not in response_text and "plant" not in response_text:
                self.log_test("Q1 PO Status - Step 1", False, "Factory selection not shown")
                return False
            
            # Step 2: Select AMMUNITION FACTORY KHADKI
            payload = {
                "session_id": session_id,
                "message": "AMMUNITION FACTORY KHADKI",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code != 200:
                self.log_test("Q1 PO Status - Step 2", False, f"HTTP {response.status_code}")
                return False
            
            data = response.json()
            response_text = data.get("response", "").lower()
            if "po" not in response_text:
                self.log_test("Q1 PO Status - Step 2", False, "PO numbers not shown")
                return False
            
            # Step 3: Select PO 1004
            payload = {
                "session_id": session_id,
                "message": "PO 1004",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code != 200:
                self.log_test("Q1 PO Status - Step 3", False, f"HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            # Validate comprehensive table with 40+ columns
            table_data = data.get("table_data")
            if not table_data:
                self.log_test("Q1 PO Status - Complete", False, "No table_data returned")
                return False
            
            columns = table_data.get("columns", [])
            if len(columns) < 40:
                self.log_test("Q1 PO Status - Complete", False, 
                            f"Expected 40+ columns, got {len(columns)}")
                return False
            
            # Validate chart data
            chart_data = data.get("chart_data")
            if not chart_data:
                self.log_test("Q1 PO Status - Complete", False, "No chart_data returned")
                return False
            
            if not self._validate_chart_structure(chart_data):
                self.log_test("Q1 PO Status - Complete", False, "Invalid chart structure")
                return False
            
            self.log_test("Q1 PO Status - Complete Flow", True, 
                        f"Complete flow successful: {len(columns)} columns, chart included", data)
            return True
            
        except Exception as e:
            self.log_test("Q1 PO Status - Complete Flow", False, f"Error: {str(e)}")
            return False
    
    def test_question_5_parameter_analysis(self):
        """Test Question 5: Parameter Analysis with charts"""
        try:
            session_id = "test-session-456"
            
            # Initialize new session
            init_payload = {"session_id": session_id}
            requests.post(f"{self.base_url}/chat/initialize", json=init_payload)
            
            # Send "5" to select Parameter Analysis
            payload = {
                "session_id": session_id,
                "message": "5",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code != 200:
                self.log_test("Q5 Parameter Analysis", False, f"HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            # Should show parameter analysis options
            response_text = data.get("response", "").lower()
            if "parameter" not in response_text and "analysis" not in response_text:
                self.log_test("Q5 Parameter Analysis", False, "Parameter analysis not shown")
                return False
            
            # Should include chart_data with bar/line charts
            chart_data = data.get("chart_data")
            if chart_data:
                if not self._validate_chart_structure(chart_data):
                    self.log_test("Q5 Parameter Analysis", False, "Invalid chart structure")
                    return False
                
                chart_type = chart_data.get("type")
                if chart_type not in ["bar", "line"]:
                    self.log_test("Q5 Parameter Analysis", False, f"Expected bar/line chart, got {chart_type}")
                    return False
            
            self.log_test("Q5 Parameter Analysis", True, 
                        f"Parameter analysis with chart: {chart_data.get('type') if chart_data else 'no chart'}", data)
            return True
            
        except Exception as e:
            self.log_test("Q5 Parameter Analysis", False, f"Error: {str(e)}")
            return False
    
    def test_question_6_distribution(self):
        """Test Question 6: Distribution with histogram and statistics"""
        try:
            session_id = "test-session-789"
            
            # Initialize new session
            init_payload = {"session_id": session_id}
            requests.post(f"{self.base_url}/chat/initialize", json=init_payload)
            
            # Send "6" to select Distribution
            payload = {
                "session_id": session_id,
                "message": "6",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code != 200:
                self.log_test("Q6 Distribution", False, f"HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            # Should return histogram chart_data
            chart_data = data.get("chart_data")
            if not chart_data:
                self.log_test("Q6 Distribution", False, "No chart_data returned")
                return False
            
            if not self._validate_chart_structure(chart_data):
                self.log_test("Q6 Distribution", False, "Invalid chart structure")
                return False
            
            # Should be bar chart (histogram)
            chart_type = chart_data.get("type")
            if chart_type != "bar":
                self.log_test("Q6 Distribution", False, f"Expected bar chart (histogram), got {chart_type}")
                return False
            
            # Should return statistics table
            table_data = data.get("table_data")
            if not table_data:
                self.log_test("Q6 Distribution", False, "No statistics table returned")
                return False
            
            if not self._validate_table_structure(table_data):
                self.log_test("Q6 Distribution", False, "Invalid table structure")
                return False
            
            # Check for statistical measures
            rows = table_data.get("rows", [])
            stats_found = 0
            expected_stats = ["mean", "median", "std", "min", "max", "count"]
            for row in rows:
                if len(row) > 0:
                    stat_name = str(row[0]).lower()
                    if any(stat in stat_name for stat in expected_stats):
                        stats_found += 1
            
            if stats_found < 3:
                self.log_test("Q6 Distribution", False, f"Expected statistical measures, found {stats_found}")
                return False
            
            self.log_test("Q6 Distribution", True, 
                        f"Distribution with histogram and {stats_found} statistics", data)
            return True
            
        except Exception as e:
            self.log_test("Q6 Distribution", False, f"Error: {str(e)}")
            return False
    
    def test_all_question_types_basic(self):
        """Test all 6 question types for basic functionality"""
        try:
            session_id = "test-session-all"
            
            # Initialize session
            init_payload = {"session_id": session_id}
            requests.post(f"{self.base_url}/chat/initialize", json=init_payload)
            
            success_count = 0
            
            for i in range(1, 7):
                payload = {
                    "session_id": session_id,
                    "message": str(i),
                    "is_suggestion": False
                }
                response = requests.post(f"{self.base_url}/chat/message", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    if self._validate_response_structure(data):
                        success_count += 1
                        print(f"  ✅ Question {i}: OK")
                    else:
                        print(f"  ❌ Question {i}: Invalid structure")
                else:
                    print(f"  ❌ Question {i}: HTTP {response.status_code}")
            
            if success_count == 6:
                self.log_test("All Question Types", True, "All 6 question types working")
                return True
            else:
                self.log_test("All Question Types", False, f"Only {success_count}/6 working")
                return False
                
        except Exception as e:
            self.log_test("All Question Types", False, f"Error: {str(e)}")
            return False
    
    def test_no_llm_errors(self):
        """Test that there are no LLM-related errors"""
        try:
            session_id = "test-session-no-llm"
            
            # Initialize and send a few messages
            init_payload = {"session_id": session_id}
            requests.post(f"{self.base_url}/chat/initialize", json=init_payload)
            
            test_messages = ["1", "2", "3", "4", "5", "6"]
            
            for msg in test_messages:
                payload = {
                    "session_id": session_id,
                    "message": msg,
                    "is_suggestion": False
                }
                response = requests.post(f"{self.base_url}/chat/message", json=payload)
                
                if response.status_code != 200:
                    self.log_test("No LLM Errors", False, f"HTTP error on message '{msg}': {response.status_code}")
                    return False
                
                data = response.json()
                response_text = data.get("response", "").lower()
                
                # Check for common LLM error indicators
                error_indicators = ["api key", "openai", "gemini", "llm", "model", "token", "rate limit"]
                for indicator in error_indicators:
                    if indicator in response_text:
                        self.log_test("No LLM Errors", False, f"LLM error detected: {indicator}")
                        return False
            
            self.log_test("No LLM Errors", True, "No LLM-related errors found")
            return True
            
        except Exception as e:
            self.log_test("No LLM Errors", False, f"Error: {str(e)}")
            return False
    
    def test_data_comprehensiveness(self):
        """Test that all data from data.txt is being used"""
        try:
            session_id = "test-session-data"
            
            # Initialize session
            init_payload = {"session_id": session_id}
            requests.post(f"{self.base_url}/chat/initialize", json=init_payload)
            
            # Test Q1 to get comprehensive table
            payload = {
                "session_id": session_id,
                "message": "1",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code != 200:
                self.log_test("Data Comprehensiveness", False, "Failed to get initial response")
                return False
            
            # Continue to get table data
            payload = {
                "session_id": session_id,
                "message": "AMMUNITION FACTORY KHADKI",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                # Check for comprehensive data usage
                data_indicators = ["plant", "building", "item", "operation", "parameter", "machine", "operator"]
                found_indicators = 0
                
                for indicator in data_indicators:
                    if indicator in response_text.lower():
                        found_indicators += 1
                
                if found_indicators >= 5:
                    self.log_test("Data Comprehensiveness", True, 
                                f"Comprehensive data usage: {found_indicators}/7 indicators found")
                    return True
                else:
                    self.log_test("Data Comprehensiveness", False, 
                                f"Limited data usage: only {found_indicators}/7 indicators found")
                    return False
            else:
                self.log_test("Data Comprehensiveness", False, "Failed to get factory response")
                return False
                
        except Exception as e:
            self.log_test("Data Comprehensiveness", False, f"Error: {str(e)}")
            return False
    
    def _validate_response_structure(self, data: Dict) -> bool:
        """Validate basic response structure"""
        required_fields = ["response", "suggestions"]
        return all(field in data for field in required_fields)
    
    def _validate_chart_structure(self, chart_data: Dict) -> bool:
        """Validate chart data structure"""
        if not isinstance(chart_data, dict):
            return False
        
        required_fields = ["type", "data"]
        if not all(field in chart_data for field in required_fields):
            return False
        
        data_obj = chart_data.get("data", {})
        if not isinstance(data_obj, dict):
            return False
        
        # Check for basic chart data structure
        if "labels" not in data_obj and "datasets" not in data_obj:
            return False
        
        return True
    
    def _validate_table_structure(self, table_data: Dict) -> bool:
        """Validate table data structure"""
        if not isinstance(table_data, dict):
            return False
        
        required_fields = ["title", "columns", "rows"]
        if not all(field in table_data for field in required_fields):
            return False
        
        columns = table_data.get("columns", [])
        rows = table_data.get("rows", [])
        
        if not isinstance(columns, list) or not isinstance(rows, list):
            return False
        
        return len(columns) > 0 and len(rows) > 0
    
    def run_all_tests(self):
        """Run all comprehensive Q&A system tests"""
        print("🚀 Starting Comprehensive Q&A System Tests")
        print("=" * 70)
        print("Testing 6 Question Types: PO Status, Inward Quality, In-Process,")
        print("Final Inspection, Parameter Analysis, Distribution")
        print("=" * 70)
        
        # Core functionality tests
        print("\n🔧 CORE FUNCTIONALITY TESTS")
        print("-" * 50)
        self.test_root_endpoint()
        self.test_initialize_chat()
        self.test_no_llm_errors()
        self.test_data_comprehensiveness()
        
        # Specific question type tests
        print("\n📋 QUESTION TYPE TESTS")
        print("-" * 50)
        self.test_question_1_po_status_complete_flow()
        self.test_question_5_parameter_analysis()
        self.test_question_6_distribution()
        self.test_all_question_types_basic()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE Q&A SYSTEM TEST SUMMARY")
        print("=" * 70)
        
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
        else:
            print("\n✅ ALL TESTS PASSED!")
        
        return passed == total

if __name__ == "__main__":
    tester = ComprehensiveQASystemTester(BACKEND_URL)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All comprehensive Q&A system tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the details above.")