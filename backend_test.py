#!/usr/bin/env python3
"""
Backend Test Suite for TickleGram Instagram DM Integration
Tests all Instagram-related endpoints and functionality
"""

import requests
import json
import time
from typing import Dict, Any, Optional

class TickleGramBackendTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.api_url}{endpoint}"
        
        # Add auth header if token exists
        if self.auth_token and headers is None:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
        elif self.auth_token and headers:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, params=params, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {"error": f"Unsupported method: {method}", "status_code": 400}
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "headers": dict(response.headers)
            }
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": 0}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response", "status_code": response.status_code}
    
    def test_admin_login(self) -> bool:
        """Test admin login and store auth token"""
        print("\n=== Testing Admin Authentication ===")
        
        login_data = {
            "identifier": "admin@ticklegram.com",
            "password": "admin123"
        }
        
        response = self.make_request("POST", "/auth/login", data=login_data)
        
        if response.get("status_code") == 200 and "access_token" in response.get("data", {}):
            self.auth_token = response["data"]["access_token"]
            user_info = response["data"].get("user", {})
            self.log_test(
                "Admin Login", 
                True, 
                f"Successfully logged in as {user_info.get('email')} ({user_info.get('role')})",
                response["data"]
            )
            return True
        else:
            self.log_test(
                "Admin Login", 
                False, 
                f"Login failed with status {response.get('status_code')}",
                response
            )
            return False
    
    def test_instagram_account_management(self) -> Optional[str]:
        """Test Instagram account CRUD operations"""
        print("\n=== Testing Instagram Account Management ===")
        
        # Test data
        instagram_data = {
            "page_id": "test_ig_account_123",
            "username": "test_instagram",
            "access_token": "mock_token_12345"
        }
        
        # 1. Connect Instagram Account (POST)
        response = self.make_request("POST", "/instagram/accounts", data=instagram_data)
        
        if response.get("status_code") == 200:
            account_data = response.get("data", {})
            account_id = account_data.get("id")
            self.log_test(
                "Connect Instagram Account", 
                True, 
                f"Account connected with ID: {account_id}",
                account_data
            )
        else:
            self.log_test(
                "Connect Instagram Account", 
                False, 
                f"Failed with status {response.get('status_code')}",
                response
            )
            return None
        
        # 2. List Instagram Accounts (GET)
        response = self.make_request("GET", "/instagram/accounts")
        
        if response.get("status_code") == 200:
            accounts = response.get("data", [])
            self.log_test(
                "List Instagram Accounts", 
                True, 
                f"Retrieved {len(accounts)} accounts",
                accounts
            )
        else:
            self.log_test(
                "List Instagram Accounts", 
                False, 
                f"Failed with status {response.get('status_code')}",
                response
            )
        
        # 3. Get Specific Instagram Account (GET)
        if account_id:
            response = self.make_request("GET", f"/instagram/accounts/{account_id}")
            
            if response.get("status_code") == 200:
                account = response.get("data", {})
                self.log_test(
                    "Get Specific Instagram Account", 
                    True, 
                    f"Retrieved account: {account.get('username')} ({account.get('page_id')})",
                    account
                )
            else:
                self.log_test(
                    "Get Specific Instagram Account", 
                    False, 
                    f"Failed with status {response.get('status_code')}",
                    response
                )
        
        return account_id
    
    def test_instagram_webhook_verification(self) -> bool:
        """Test Instagram webhook verification endpoint"""
        print("\n=== Testing Instagram Webhook Verification ===")
        
        # Test webhook verification
        params = {
            "hub.mode": "subscribe",
            "hub.challenge": "12345",
            "hub.verify_token": "ticklegram_fb_verify_token_2025"
        }
        
        # Don't use auth token for webhook verification
        response = self.make_request("GET", "/webhooks/instagram", params=params, headers={})
        
        if response.get("status_code") == 200:
            challenge_response = response.get("data")
            expected_challenge = "12345"
            
            if str(challenge_response) == expected_challenge:
                self.log_test(
                    "Instagram Webhook Verification", 
                    True, 
                    f"Webhook verified successfully, returned challenge: {challenge_response}",
                    response["data"]
                )
                return True
            else:
                self.log_test(
                    "Instagram Webhook Verification", 
                    False, 
                    f"Challenge mismatch. Expected: {expected_challenge}, Got: {challenge_response}",
                    response
                )
                return False
        else:
            self.log_test(
                "Instagram Webhook Verification", 
                False, 
                f"Verification failed with status {response.get('status_code')}",
                response
            )
            return False
    
    def test_instagram_webhook_message(self) -> Optional[str]:
        """Test Instagram webhook message processing"""
        print("\n=== Testing Instagram Webhook Message Processing ===")
        
        # Mock Instagram webhook payload
        webhook_payload = {
            "object": "instagram",
            "entry": [{
                "id": "test_ig_account_123",
                "messaging": [{
                    "sender": {"id": "test_user_456"},
                    "recipient": {"id": "test_ig_account_123"},
                    "message": {
                        "mid": "msg_123",
                        "text": "Hello from Instagram!"
                    }
                }]
            }]
        }
        
        # Don't use auth token for webhook processing
        response = self.make_request("POST", "/webhooks/instagram", data=webhook_payload, headers={})
        
        if response.get("status_code") == 200:
            webhook_response = response.get("data", {})
            if webhook_response.get("status") == "received":
                self.log_test(
                    "Instagram Webhook Message Processing", 
                    True, 
                    "Webhook message processed successfully",
                    webhook_response
                )
                
                # Wait a moment for database operations to complete
                time.sleep(1)
                
                # Verify chat was created by checking chats endpoint
                chats_response = self.make_request("GET", "/chats", params={"platform": "instagram"})
                
                if chats_response.get("status_code") == 200:
                    chats = chats_response.get("data", [])
                    instagram_chats = [chat for chat in chats if chat.get("platform") == "INSTAGRAM"]
                    
                    if instagram_chats:
                        chat = instagram_chats[0]  # Get the first Instagram chat
                        chat_id = chat.get("id")
                        self.log_test(
                            "Verify Chat Creation from Webhook", 
                            True, 
                            f"Chat created with ID: {chat_id}, User: {chat.get('username')}",
                            chat
                        )
                        return chat_id
                    else:
                        self.log_test(
                            "Verify Chat Creation from Webhook", 
                            False, 
                            "No Instagram chats found after webhook processing",
                            chats
                        )
                        return None
                else:
                    self.log_test(
                        "Verify Chat Creation from Webhook", 
                        False, 
                        f"Failed to retrieve chats with status {chats_response.get('status_code')}",
                        chats_response
                    )
                    return None
            else:
                self.log_test(
                    "Instagram Webhook Message Processing", 
                    False, 
                    f"Unexpected webhook response status: {webhook_response.get('status')}",
                    webhook_response
                )
                return None
        else:
            self.log_test(
                "Instagram Webhook Message Processing", 
                False, 
                f"Webhook processing failed with status {response.get('status_code')}",
                response
            )
            return None
    
    def test_cross_platform_message_sending(self, chat_id: str) -> bool:
        """Test sending messages to Instagram chats"""
        print("\n=== Testing Cross-Platform Message Sending ===")
        
        if not chat_id:
            self.log_test(
                "Cross-Platform Message Sending", 
                False, 
                "No chat ID provided for testing",
                None
            )
            return False
        
        # Test message data
        message_data = {
            "content": "Reply from agent",
            "message_type": "text"
        }
        
        response = self.make_request("POST", f"/chats/{chat_id}/message", data=message_data)
        
        if response.get("status_code") == 200:
            message_response = response.get("data", {})
            self.log_test(
                "Cross-Platform Message Sending", 
                True, 
                f"Message sent successfully. ID: {message_response.get('id')}, Platform: {message_response.get('platform')}",
                message_response
            )
            return True
        else:
            self.log_test(
                "Cross-Platform Message Sending", 
                False, 
                f"Message sending failed with status {response.get('status_code')}",
                response
            )
            return False
    
    def test_platform_filtering(self) -> bool:
        """Test platform-specific chat filtering"""
        print("\n=== Testing Platform Filtering ===")
        
        # Test Instagram-only filtering
        response = self.make_request("GET", "/chats", params={"platform": "instagram"})
        
        if response.get("status_code") == 200:
            instagram_chats = response.get("data", [])
            all_instagram = all(chat.get("platform") == "INSTAGRAM" for chat in instagram_chats)
            
            if all_instagram:
                self.log_test(
                    "Instagram Platform Filtering", 
                    True, 
                    f"Retrieved {len(instagram_chats)} Instagram chats only",
                    {"count": len(instagram_chats), "platforms": [chat.get("platform") for chat in instagram_chats]}
                )
            else:
                platforms = [chat.get("platform") for chat in instagram_chats]
                self.log_test(
                    "Instagram Platform Filtering", 
                    False, 
                    f"Non-Instagram chats found in filtered results: {platforms}",
                    instagram_chats
                )
                return False
        else:
            self.log_test(
                "Instagram Platform Filtering", 
                False, 
                f"Platform filtering failed with status {response.get('status_code')}",
                response
            )
            return False
        
        # Test all chats (no filter)
        response = self.make_request("GET", "/chats")
        
        if response.get("status_code") == 200:
            all_chats = response.get("data", [])
            platforms = list(set(chat.get("platform") for chat in all_chats))
            
            self.log_test(
                "All Chats Retrieval", 
                True, 
                f"Retrieved {len(all_chats)} total chats across platforms: {platforms}",
                {"count": len(all_chats), "platforms": platforms}
            )
            return True
        else:
            self.log_test(
                "All Chats Retrieval", 
                False, 
                f"All chats retrieval failed with status {response.get('status_code')}",
                response
            )
            return False
    
    def test_instagram_account_deletion(self, account_id: str) -> bool:
        """Test Instagram account deletion"""
        print("\n=== Testing Instagram Account Deletion ===")
        
        if not account_id:
            self.log_test(
                "Instagram Account Deletion", 
                False, 
                "No account ID provided for deletion test",
                None
            )
            return False
        
        response = self.make_request("DELETE", f"/instagram/accounts/{account_id}")
        
        if response.get("status_code") == 200:
            delete_response = response.get("data", {})
            if delete_response.get("success"):
                self.log_test(
                    "Instagram Account Deletion", 
                    True, 
                    f"Account deleted successfully: {delete_response.get('message')}",
                    delete_response
                )
                return True
            else:
                self.log_test(
                    "Instagram Account Deletion", 
                    False, 
                    f"Deletion response indicates failure: {delete_response}",
                    delete_response
                )
                return False
        else:
            self.log_test(
                "Instagram Account Deletion", 
                False, 
                f"Account deletion failed with status {response.get('status_code')}",
                response
            )
            return False
    
    def run_all_tests(self):
        """Run all Instagram DM integration tests"""
        print("🚀 Starting TickleGram Instagram DM Integration Backend Tests")
        print("=" * 60)
        
        # 1. Admin Authentication
        if not self.test_admin_login():
            print("\n❌ Cannot proceed without admin authentication")
            return self.generate_summary()
        
        # 2. Instagram Account Management
        account_id = self.test_instagram_account_management()
        
        # 3. Instagram Webhook Verification
        self.test_instagram_webhook_verification()
        
        # 4. Instagram Webhook Message Processing
        chat_id = self.test_instagram_webhook_message()
        
        # 5. Cross-Platform Message Sending
        if chat_id:
            self.test_cross_platform_message_sending(chat_id)
        
        # 6. Platform Filtering
        self.test_platform_filtering()
        
        # 7. Instagram Account Deletion (cleanup)
        if account_id:
            self.test_instagram_account_deletion(account_id)
        
        return self.generate_summary()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests*100) if total_tests > 0 else 0,
            "detailed_results": self.test_results
        }

if __name__ == "__main__":
    # Initialize tester with backend URL
    tester = TickleGramBackendTester("http://localhost:8001")
    
    # Run all tests
    summary = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if summary["failed_tests"] == 0 else 1)
