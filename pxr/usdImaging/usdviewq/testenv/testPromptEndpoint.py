#!/usr/bin/env python3
"""
USDViewer HTTP Server Prompt Endpoint Test Script

This script tests the new /prompt endpoint functionality of the USDViewer HTTP server.
It sends various prompt messages and displays the responses.
"""

import json
import requests
import time
import sys


class PromptEndpointTester:
    """Test class for the USDViewer HTTP Server prompt endpoint."""
    
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.prompt_url = f"{server_url}/prompt"
    
    def test_server_connection(self):
        """Test if the server is running and accessible."""
        print("🔍 Testing server connection...")
        try:
            response = requests.get(self.server_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server is running")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Available endpoints: {data.get('available_endpoints', [])}")
                return True
            else:
                print(f"❌ Server returned status code: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Could not connect to server at {self.server_url}")
            print("   Make sure USDViewer is running with HTTP server enabled")
            return False
        except Exception as e:
            print(f"❌ Error connecting to server: {e}")
            return False
    
    def send_prompt(self, message, description=""):
        """Send a prompt message to the server."""
        print(f"\n📤 Sending prompt: {description}")
        print(f"   Message: '{message}'")
        
        try:
            payload = {"message": message}
            response = requests.post(
                self.prompt_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            print(f"   Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success!")
                print(f"   Server Response: {data.get('response', 'No response')}")
                print(f"   Full Message: {data.get('message', 'No message')}")
                return True
            else:
                print(f"   ❌ Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error Message: {error_data.get('message', 'Unknown error')}")
                except:
                    print(f"   Error Body: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"   ❌ Request timed out")
            return False
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection error")
            return False
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            return False
    
    def test_invalid_requests(self):
        """Test invalid request scenarios."""
        print(f"\n🧪 Testing invalid request scenarios...")
        
        # Test 1: Missing message parameter
        print(f"\n📤 Test: Missing 'message' parameter")
        try:
            response = requests.post(
                self.prompt_url,
                json={},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"   Response Status: {response.status_code}")
            if response.status_code == 400:
                print(f"   ✅ Correctly rejected invalid request")
                error_data = response.json()
                print(f"   Error Message: {error_data.get('message', 'No error message')}")
            else:
                print(f"   ❌ Expected 400, got {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Invalid JSON
        print(f"\n📤 Test: Invalid JSON")
        try:
            response = requests.post(
                self.prompt_url,
                data="invalid json",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"   Response Status: {response.status_code}")
            if response.status_code == 400:
                print(f"   ✅ Correctly rejected invalid JSON")
            else:
                print(f"   ❌ Expected 400, got {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Empty message
        print(f"\n📤 Test: Empty message")
        try:
            response = requests.post(
                self.prompt_url,
                json={"message": ""},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"   Response Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ Empty message accepted (as expected)")
                data = response.json()
                print(f"   Response: {data.get('response', 'No response')}")
            else:
                print(f"   ❓ Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    def run_test_suite(self):
        """Run the complete test suite."""
        print("🚀 Starting USDViewer Prompt Endpoint Test Suite")
        print("=" * 60)
        
        # Test server connection
        if not self.test_server_connection():
            print("\n❌ Cannot continue tests - server is not accessible")
            return False
        
        # Test basic prompt messages
        test_messages = [
            ("Hello, USDViewer!", "Simple greeting"),
            ("What is the current time?", "Question about time"),
            ("Move the camera to position (0, 5, 10)", "Camera movement instruction"),
            ("Show me all the prims in the scene", "Scene query"),
            ("This is a longer message with multiple sentences. It contains various punctuation marks! Does the server handle this correctly?", "Long multi-sentence message"),
            ("日本語のメッセージをテストします", "Japanese text"),
            ("Mensaje en español con acentos: ñáéíóú", "Spanish text with accents"),
            ("🎬🎭🎨 Emoji test message 🚀✨🎯", "Message with emojis"),
            ("{'json': 'like', 'structure': true, 'number': 42}", "JSON-like string"),
            ("Line 1\nLine 2\nLine 3", "Multi-line message"),
        ]
        
        print(f"\n🧪 Testing {len(test_messages)} different prompt messages...")
        
        success_count = 0
        for message, description in test_messages:
            if self.send_prompt(message, description):
                success_count += 1
            time.sleep(0.5)  # Small delay between requests
        
        # Test invalid scenarios
        self.test_invalid_requests()
        
        # Summary
        print(f"\n📊 Test Results Summary")
        print("=" * 60)
        print(f"✅ Successful prompt tests: {success_count}/{len(test_messages)}")
        
        if success_count == len(test_messages):
            print(f"🎉 All prompt tests passed!")
            return True
        else:
            print(f"⚠️  Some tests failed")
            return False


def main():
    """Main function to run the test suite."""
    # Parse command line arguments
    server_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"Using server URL: {server_url}")
    
    # Create tester and run tests
    tester = PromptEndpointTester(server_url)
    success = tester.run_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
