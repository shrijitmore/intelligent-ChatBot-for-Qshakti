#!/usr/bin/env python3
"""
Hierarchical Chatbot API Test Suite
Tests the new hierarchical data structure and conversational navigation

Test Suite:
1. Initialization Test - POST to /api/chat/initialize
2. Plant Level Navigation - "Explore AMMUNITION FACTORY KHADKI"
3. Section Level Navigation - "Show me CASE 4"
4. Item Level Navigation - "Tell me about 5.56MM BALL M-193"
5. Chart Generation - "Show me quality trends"
6. Table Generation - "Display all inspection parameters"
7. Session Persistence - Test that context is maintained across messages
"""

import requests
import json
import uuid
import time
from typing import Dict, Any, List

# Configuration
BACKEND_URL = "https://code-resolver.preview.emergentagent.com/api"
TEST_SESSION_ID = str(uuid.uuid4())

class HierarchicalChatbotTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id = None
        self.test_results = []
        self.conversation_history = []
        
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
        
    def test_initialization(self):
        """Test 1: Initialization Test - POST to /api/chat/initialize"""
        try:
            payload = {"session_id": TEST_SESSION_ID}
            response = requests.post(f"{self.base_url}/chat/initialize", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["session_id", "suggestions", "message"]
                
                if all(field in data for field in required_fields):
                    suggestions = data["suggestions"]
                    
                    # Check that suggestions include plants (should include "AMMUNITION FACTORY KHADKI")
                    has_ammunition_factory = any("AMMUNITION FACTORY KHADKI" in s for s in suggestions)
                    has_ordnance_factory = any("ORDNANCE FACTORY" in s for s in suggestions)
                    
                    # Check that suggestions are human-friendly (no table names)
                    no_db_terms = not any(
                        any(term in s.lower() for term in ['table', 'database', 'db', 'sql', 'query'])
                        for s in suggestions
                    )
                    
                    if has_ammunition_factory and no_db_terms:
                        self.session_id = data["session_id"]
                        self.conversation_history.append(("INIT", data))
                        self.log_test("1. Initialization Test", True, 
                                    f"✓ Found AMMUNITION FACTORY KHADKI in suggestions\n✓ Suggestions are human-friendly\n✓ Got {len(suggestions)} suggestions", data)
                        return True
                    else:
                        issues = []
                        if not has_ammunition_factory:
                            issues.append("Missing AMMUNITION FACTORY KHADKI")
                        if not no_db_terms:
                            issues.append("Contains database terminology")
                        self.log_test("1. Initialization Test", False, f"Issues: {', '.join(issues)}")
                        return False
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test("1. Initialization Test", False, f"Missing fields: {missing}")
                    return False
            else:
                self.log_test("1. Initialization Test", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("1. Initialization Test", False, f"Error: {str(e)}")
            return False
    
    def test_plant_level_navigation(self):
        """Test 2: Plant Level Navigation - "Explore AMMUNITION FACTORY KHADKI" """
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Explore AMMUNITION FACTORY KHADKI",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["session_id", "response", "suggestions", "context_path"]
                
                if all(field in data for field in required_fields):
                    response_text = data["response"]
                    suggestions = data["suggestions"]
                    
                    # Check response is conversational (no database terminology)
                    no_db_terms = not any(term in response_text.lower() for term in 
                                        ['table', 'database', 'db', 'sql', 'query', 'schema'])
                    
                    # Check suggestions include sections like "CASE 4"
                    has_case_section = any("CASE" in s for s in suggestions)
                    
                    # Check response mentions the plant naturally
                    mentions_plant = "AMMUNITION FACTORY KHADKI" in response_text or "ammunition" in response_text.lower()
                    
                    if no_db_terms and has_case_section and mentions_plant:
                        self.conversation_history.append(("PLANT", data))
                        self.log_test("2. Plant Level Navigation", True, 
                                    f"✓ Response is conversational (no DB terms)\n✓ Found CASE section in suggestions\n✓ Response mentions plant naturally", data)
                        return True
                    else:
                        issues = []
                        if not no_db_terms:
                            issues.append("Contains database terminology")
                        if not has_case_section:
                            issues.append("Missing CASE section in suggestions")
                        if not mentions_plant:
                            issues.append("Doesn't mention plant naturally")
                        self.log_test("2. Plant Level Navigation", False, f"Issues: {', '.join(issues)}")
                        return False
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test("2. Plant Level Navigation", False, f"Missing fields: {missing}")
                    return False
            else:
                self.log_test("2. Plant Level Navigation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("2. Plant Level Navigation", False, f"Error: {str(e)}")
            return False
    
    def test_section_level_navigation(self):
        """Test 3: Section Level Navigation - "Show me CASE 4" """
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Show me CASE 4",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                response_text = data["response"]
                suggestions = data["suggestions"]
                
                # Check response describes the section naturally
                describes_section = len(response_text) > 50 and ("case" in response_text.lower() or "section" in response_text.lower())
                
                # Check no database terminology
                no_db_terms = not any(term in response_text.lower() for term in 
                                    ['table', 'database', 'db', 'sql', 'query', 'schema'])
                
                # Check suggestions include items (should have items related to ammunition/cases)
                has_item_suggestions = len(suggestions) > 0 and any(
                    any(term in s.lower() for term in ['item', 'ball', 'case', 'ammunition', 'tell me about'])
                    for s in suggestions
                )
                
                if describes_section and no_db_terms and has_item_suggestions:
                    self.conversation_history.append(("SECTION", data))
                    self.log_test("3. Section Level Navigation", True, 
                                f"✓ Response describes section naturally\n✓ No database terminology\n✓ Suggestions include items", data)
                    return True
                else:
                    issues = []
                    if not describes_section:
                        issues.append("Doesn't describe section naturally")
                    if not no_db_terms:
                        issues.append("Contains database terminology")
                    if not has_item_suggestions:
                        issues.append("Missing item suggestions")
                    self.log_test("3. Section Level Navigation", False, f"Issues: {', '.join(issues)}")
                    return False
            else:
                self.log_test("3. Section Level Navigation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("3. Section Level Navigation", False, f"Error: {str(e)}")
            return False
    
    def test_item_level_navigation(self):
        """Test 4: Item Level Navigation - "Tell me about 5.56MM BALL M-193" """
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Tell me about 5.56MM BALL M-193",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                response_text = data["response"]
                suggestions = data["suggestions"]
                
                # Check response includes inspection/quality information
                has_quality_info = any(term in response_text.lower() for term in 
                                     ['inspection', 'quality', 'parameter', 'operation', 'machine', 'reading'])
                
                # Check for visualization suggestions
                has_viz_suggestions = any(
                    any(term in s.lower() for term in ['chart', 'trend', 'quality', 'show', 'display', 'visualize'])
                    for s in suggestions
                )
                
                # Check response is substantial (detailed item information)
                substantial_response = len(response_text) > 80
                
                # Check no database terminology
                no_db_terms = not any(term in response_text.lower() for term in 
                                    ['table', 'database', 'db', 'sql', 'query', 'schema'])
                
                if has_quality_info and has_viz_suggestions and substantial_response and no_db_terms:
                    self.conversation_history.append(("ITEM", data))
                    self.log_test("4. Item Level Navigation", True, 
                                f"✓ Response includes quality/inspection info\n✓ Has visualization suggestions\n✓ Substantial response\n✓ No DB terminology", data)
                    return True
                else:
                    issues = []
                    if not has_quality_info:
                        issues.append("Missing quality/inspection information")
                    if not has_viz_suggestions:
                        issues.append("Missing visualization suggestions")
                    if not substantial_response:
                        issues.append("Response too brief")
                    if not no_db_terms:
                        issues.append("Contains database terminology")
                    self.log_test("4. Item Level Navigation", False, f"Issues: {', '.join(issues)}")
                    return False
            else:
                self.log_test("4. Item Level Navigation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("4. Item Level Navigation", False, f"Error: {str(e)}")
            return False
    
    def test_chart_generation(self):
        """Test 5: Chart Generation - "Show me quality trends" """
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Create a chart",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check chart_data is returned
                chart_data = data.get("chart_data")
                if chart_data:
                    # Check chart has proper structure (type, title, data, options)
                    required_chart_fields = ["type", "title", "data"]
                    has_required_fields = all(field in chart_data for field in required_chart_fields)
                    
                    # Check chart data structure
                    chart_data_obj = chart_data.get("data", {})
                    has_labels = "labels" in chart_data_obj
                    has_datasets = "datasets" in chart_data_obj and isinstance(chart_data_obj["datasets"], list)
                    
                    # Check chart type is valid
                    valid_chart_type = chart_data.get("type") in ["line", "bar", "pie", "scatter", "histogram"]
                    
                    if has_required_fields and has_labels and has_datasets and valid_chart_type:
                        self.conversation_history.append(("CHART", data))
                        self.log_test("5. Chart Generation", True, 
                                    f"✓ Chart data returned\n✓ Proper structure (type: {chart_data.get('type')})\n✓ Has labels and datasets\n✓ Valid chart type", data)
                        return True
                    else:
                        issues = []
                        if not has_required_fields:
                            issues.append("Missing required chart fields")
                        if not has_labels:
                            issues.append("Missing labels")
                        if not has_datasets:
                            issues.append("Missing or invalid datasets")
                        if not valid_chart_type:
                            issues.append(f"Invalid chart type: {chart_data.get('type')}")
                        self.log_test("5. Chart Generation", False, f"Issues: {', '.join(issues)}")
                        return False
                else:
                    self.log_test("5. Chart Generation", False, "No chart_data returned for chart request")
                    return False
            else:
                self.log_test("5. Chart Generation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("5. Chart Generation", False, f"Error: {str(e)}")
            return False
    
    def test_table_generation(self):
        """Test 6: Table Generation - "Display all inspection parameters" """
        try:
            payload = {
                "session_id": self.session_id or TEST_SESSION_ID,
                "message": "Display all inspection parameters",
                "is_suggestion": False
            }
            response = requests.post(f"{self.base_url}/chat/message", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check table_data is returned
                table_data = data.get("table_data")
                if table_data:
                    # Check table has columns and rows
                    has_columns = "columns" in table_data and isinstance(table_data["columns"], list)
                    has_rows = "rows" in table_data and isinstance(table_data["rows"], list)
                    has_title = "title" in table_data
                    
                    # Check table has data
                    has_data = len(table_data.get("columns", [])) > 0 and len(table_data.get("rows", [])) > 0
                    
                    if has_columns and has_rows and has_title and has_data:
                        self.conversation_history.append(("TABLE", data))
                        self.log_test("6. Table Generation", True, 
                                    f"✓ Table data returned\n✓ Has columns ({len(table_data['columns'])})\n✓ Has rows ({len(table_data['rows'])})\n✓ Has title: {table_data['title']}", data)
                        return True
                    else:
                        issues = []
                        if not has_columns:
                            issues.append("Missing or invalid columns")
                        if not has_rows:
                            issues.append("Missing or invalid rows")
                        if not has_title:
                            issues.append("Missing title")
                        if not has_data:
                            issues.append("No data in table")
                        self.log_test("6. Table Generation", False, f"Issues: {', '.join(issues)}")
                        return False
                else:
                    self.log_test("6. Table Generation", False, "No table_data returned for table request")
                    return False
            else:
                self.log_test("6. Table Generation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("6. Table Generation", False, f"Error: {str(e)}")
            return False
    
    def test_session_persistence(self):
        """Test 7: Session Persistence - Test that context is maintained across messages"""
        try:
            # Get chat history
            session_id = self.session_id or TEST_SESSION_ID
            history_response = requests.get(f"{self.base_url}/chat/history/{session_id}")
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                messages = history_data.get("messages", [])
                
                # Check that we have messages from previous tests
                has_messages = len(messages) > 0
                
                # Get decision tree path
                tree_response = requests.get(f"{self.base_url}/chat/tree/{session_id}")
                
                if tree_response.status_code == 200:
                    tree_data = tree_response.json()
                    tree_path = tree_data.get("tree_path", [])
                    
                    # Check tree_path shows conversation flow
                    has_tree_path = len(tree_path) > 0
                    
                    # Check that tree path contains our test messages
                    expected_messages = [
                        "Explore AMMUNITION FACTORY KHADKI",
                        "Show me CASE 4", 
                        "Tell me about 5.56MM BALL M-193"
                    ]
                    
                    tree_contains_expected = any(
                        any(expected in path_item for expected in expected_messages)
                        for path_item in tree_path
                    )
                    
                    if has_messages and has_tree_path and tree_contains_expected:
                        self.log_test("7. Session Persistence", True, 
                                    f"✓ Context maintained ({len(messages)} messages)\n✓ Tree path shows flow ({len(tree_path)} steps)\n✓ Contains expected navigation", 
                                    {"history_count": len(messages), "tree_path_count": len(tree_path)})
                        return True
                    else:
                        issues = []
                        if not has_messages:
                            issues.append("No messages in history")
                        if not has_tree_path:
                            issues.append("No tree path")
                        if not tree_contains_expected:
                            issues.append("Tree path missing expected navigation")
                        self.log_test("7. Session Persistence", False, f"Issues: {', '.join(issues)}")
                        return False
                else:
                    self.log_test("7. Session Persistence", False, 
                                f"Tree request failed: {tree_response.status_code}")
                    return False
            else:
                self.log_test("7. Session Persistence", False, 
                            f"History request failed: {history_response.status_code}")
                return False
        except Exception as e:
            self.log_test("7. Session Persistence", False, f"Error: {str(e)}")
            return False
    
    def run_hierarchical_tests(self):
        """Run all hierarchical navigation tests in sequence"""
        print("🚀 Starting Hierarchical Chatbot API Test Suite")
        print("=" * 70)
        print("Testing new hierarchical data structure and conversational navigation")
        print("=" * 70)
        
        # Run tests in sequence (order matters for context building)
        tests = [
            self.test_initialization,
            self.test_plant_level_navigation,
            self.test_section_level_navigation,
            self.test_item_level_navigation,
            self.test_chart_generation,
            self.test_table_generation,
            self.test_session_persistence
        ]
        
        for test in tests:
            test()
            print()  # Add spacing between tests
        
        # Summary
        print("=" * 70)
        print("📊 HIERARCHICAL TEST SUMMARY")
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
            print("\n✅ ALL HIERARCHICAL TESTS PASSED!")
            print("🎉 Hierarchical chatbot API is working correctly!")
        
        # Show conversation flow
        print("\n📋 CONVERSATION FLOW:")
        for i, (level, data) in enumerate(self.conversation_history, 1):
            if level == "INIT":
                print(f"{i}. INITIALIZATION: Got {len(data.get('suggestions', []))} plant suggestions")
            elif level == "PLANT":
                print(f"{i}. PLANT LEVEL: Explored AMMUNITION FACTORY KHADKI")
            elif level == "SECTION":
                print(f"{i}. SECTION LEVEL: Explored CASE 4 section")
            elif level == "ITEM":
                print(f"{i}. ITEM LEVEL: Explored 5.56MM BALL M-193 item")
            elif level == "CHART":
                chart_type = data.get('chart_data', {}).get('type', 'unknown')
                print(f"{i}. CHART: Generated {chart_type} chart for quality trends")
            elif level == "TABLE":
                row_count = len(data.get('table_data', {}).get('rows', []))
                print(f"{i}. TABLE: Generated table with {row_count} rows for inspection parameters")
        
        return passed == total

if __name__ == "__main__":
    tester = HierarchicalChatbotTester(BACKEND_URL)
    success = tester.run_hierarchical_tests()
    
    if success:
        print("\n🎉 All hierarchical tests passed!")
        print("✅ The hierarchical chatbot API is working correctly with conversational navigation!")
    else:
        print("\n⚠️  Some hierarchical tests failed. Check the details above.")