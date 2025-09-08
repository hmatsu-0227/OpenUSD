#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
USDViewer HTTP Request Server Test Script

This script tests the HTTP request functionality of USDViewer.
It sends various HTTP requests to verify that the server responds correctly
and that move operations work as expected.

Requirements:
- Python 3.12+
- USDViewer running with testHttpServer.usda
- HTTP server should be running on http://localhost:8080

Usage:
1. Start USDViewer with the test file:
   usdview testHttpServer.usda
   
2. Run this test script:
   python testHttpServer.py
"""

import sys
import time
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode


class USDViewerHTTPTester:
    """Simple HTTP tester for USDViewer HTTP server."""
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.test_results = []
    
    def log_test(self, test_name, success, message):
        """Log test result."""
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
    
    def make_request(self, method, endpoint, data=None, timeout=5):
        """Make HTTP request using urllib."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                with urlopen(url, timeout=timeout) as response:
                    return response.getcode(), response.read().decode('utf-8')
            
            elif method == 'POST':
                json_data = json.dumps(data).encode('utf-8') if data else b''
                request = Request(url, data=json_data)
                request.add_header('Content-Type', 'application/json')
                request.get_method = lambda: 'POST'
                
                with urlopen(request, timeout=timeout) as response:
                    return response.getcode(), response.read().decode('utf-8')
                    
        except HTTPError as e:
            return e.code, e.read().decode('utf-8')
        except URLError as e:
            raise ConnectionError(f"Could not connect to server: {e}")
        except Exception as e:
            raise Exception(f"Request failed: {e}")
    
    def test_server_status(self):
        """Test server status endpoint."""
        try:
            status_code, response = self.make_request('GET', '/')
            
            if status_code == 200:
                data = json.loads(response)
                if data.get('status') == 'ok':
                    self.log_test("Server Status", True, f"Server is running: {data.get('message')}")
                    return True
                else:
                    self.log_test("Server Status", False, f"Unexpected status: {data.get('status')}")
                    return False
            else:
                self.log_test("Server Status", False, f"HTTP {status_code}")
                return False
                
        except Exception as e:
            self.log_test("Server Status", False, str(e))
            return False
    
    def test_move_request_valid(self):
        """Test valid move request."""
        test_data = {
            "sdfPath": "/World/TestCube",
            "x": 2.0,
            "y": 1.0,
            "z": 0.5,
            "rotateZ": 30.0
        }
        
        try:
            status_code, response = self.make_request('POST', '/move', test_data)
            
            if status_code == 200:
                data = json.loads(response)
                if data.get('status') == 'success':
                    self.log_test("Valid Move Request", True, 
                                 f"Moved {test_data['sdfPath']} to ({test_data['x']}, {test_data['y']}, {test_data['z']})")
                    return True
                else:
                    self.log_test("Valid Move Request", False, f"Unexpected status: {data.get('status')}")
                    return False
            else:
                data = json.loads(response)
                self.log_test("Valid Move Request", False, 
                             f"HTTP {status_code}: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.log_test("Valid Move Request", False, str(e))
            return False
    
    def test_move_request_invalid_path(self):
        """Test move request with invalid prim path."""
        test_data = {
            "sdfPath": "/World/NonExistentPrim",
            "x": 1.0,
            "y": 1.0,
            "z": 1.0,
            "rotateZ": 0.0
        }
        
        try:
            status_code, response = self.make_request('POST', '/move', test_data)
            
            if status_code == 400:
                data = json.loads(response)
                if data.get('status') == 'error':
                    self.log_test("Invalid Path Move Request", True, 
                                 f"Correctly rejected invalid path: {data.get('message')}")
                    return True
                else:
                    self.log_test("Invalid Path Move Request", False, 
                                 f"Wrong error status: {data.get('status')}")
                    return False
            else:
                self.log_test("Invalid Path Move Request", False, 
                             f"Expected HTTP 400, got {status_code}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Path Move Request", False, str(e))
            return False
    
    def test_move_request_partial_params(self):
        """Test move request with partial parameters (should preserve current values)."""
        # First, set a known initial position
        initial_data = {
            "sdfPath": "/World/TestCube",
            "x": 10.0,
            "y": 5.0,
            "z": 2.0,
            "rotateZ": 90.0
        }
        
        try:
            # Set initial position
            status_code, response = self.make_request('POST', '/move', initial_data)
            if status_code != 200:
                self.log_test("Partial Parameters Move Request", False, 
                             f"Failed to set initial position: HTTP {status_code}")
                return False
            
            # Add a small delay to ensure the operation is complete
            import time
            time.sleep(0.1)
            
            # Now test partial update (only change x)
            partial_data = {
                "sdfPath": "/World/TestCube",
                "x": 15.0
                # y, z, rotateZ should be preserved
            }
            
            status_code, response = self.make_request('POST', '/move', partial_data)
            
            if status_code == 200:
                data = json.loads(response)
                if data.get('status') == 'success':
                    transform = data.get('transform', {})
                    translation = transform.get('translation', [])
                    rotation = transform.get('rotation_z_degrees', 0)
                    
                    # Check if partial update worked correctly
                    if (len(translation) == 3 and 
                        abs(translation[0] - 15.0) < 0.001 and  # x changed
                        abs(translation[1] - 5.0) < 0.001 and   # y preserved
                        abs(translation[2] - 2.0) < 0.001 and   # z preserved
                        abs(rotation - 90.0) < 0.001):          # rotateZ preserved
                        
                        self.log_test("Partial Parameters Move Request", True, 
                                     f"Correctly preserved existing values: x=15.0, y=5.0, z=2.0, rotateZ=90.0")
                        return True
                    else:
                        self.log_test("Partial Parameters Move Request", False, 
                                     f"Transform values incorrect: expected (15.0, 5.0, 2.0, 90.0), got ({translation[0] if len(translation) > 0 else 'N/A'}, {translation[1] if len(translation) > 1 else 'N/A'}, {translation[2] if len(translation) > 2 else 'N/A'}, {rotation})")
                        return False
                else:
                    self.log_test("Partial Parameters Move Request", False, 
                                 f"Unexpected status: {data.get('status')}")
                    return False
            else:
                data = json.loads(response)
                self.log_test("Partial Parameters Move Request", False, 
                             f"HTTP {status_code}: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.log_test("Partial Parameters Move Request", False, str(e))
            return False
    
    def test_move_request_missing_sdf_path(self):
        """Test move request with missing required sdfPath parameter."""
        test_data = {
            "x": 1.0,
            "y": 2.0,
            "z": 3.0,
            "rotateZ": 45.0
            # Missing sdfPath
        }
        
        try:
            status_code, response = self.make_request('POST', '/move', test_data)
            
            if status_code == 400:
                data = json.loads(response)
                if data.get('status') == 'error' and 'Missing required parameter: sdfPath' in data.get('message', ''):
                    self.log_test("Missing SdfPath Move Request", True, 
                                 f"Correctly rejected missing sdfPath: {data.get('message')}")
                    return True
                else:
                    self.log_test("Missing SdfPath Move Request", False, 
                                 f"Wrong error message: {data.get('message')}")
                    return False
            else:
                self.log_test("Missing SdfPath Move Request", False, 
                             f"Expected HTTP 400, got {status_code}")
                return False
                
        except Exception as e:
            self.log_test("Missing SdfPath Move Request", False, str(e))
            return False
    
    def test_move_request_only_sdf_path(self):
        """Test move request with only sdfPath (should preserve all current values)."""
        # Use TestSphere which has initial position (3, 0, 0) from USD file
        # First, set a known position
        initial_data = {
            "sdfPath": "/World/TestSphere",
            "x": 7.0,
            "y": 3.0,
            "z": 1.5,
            "rotateZ": 45.0
        }
        
        try:
            # Set initial position
            status_code, response = self.make_request('POST', '/move', initial_data)
            if status_code != 200:
                self.log_test("SdfPath Only Move Request", False, 
                             f"Failed to set initial position: HTTP {status_code}")
                return False
            
            # Add a small delay to ensure the operation is complete
            import time
            time.sleep(0.1)
            
            # Now test with only sdfPath
            sdf_path_only_data = {
                "sdfPath": "/World/TestSphere"
                # No other parameters - should preserve all values
            }
            
            status_code, response = self.make_request('POST', '/move', sdf_path_only_data)
            
            if status_code == 200:
                data = json.loads(response)
                if data.get('status') == 'success':
                    transform = data.get('transform', {})
                    translation = transform.get('translation', [])
                    rotation = transform.get('rotation_z_degrees', 0)
                    
                    # Check if all values were preserved
                    if (len(translation) == 3 and 
                        abs(translation[0] - 7.0) < 0.001 and   # x preserved
                        abs(translation[1] - 3.0) < 0.001 and   # y preserved
                        abs(translation[2] - 1.5) < 0.001 and   # z preserved
                        abs(rotation - 45.0) < 0.001):          # rotateZ preserved
                        
                        self.log_test("SdfPath Only Move Request", True, 
                                     f"Correctly preserved all values: x=7.0, y=3.0, z=1.5, rotateZ=45.0")
                        return True
                    else:
                        self.log_test("SdfPath Only Move Request", False, 
                                     f"Transform values not preserved: expected (7.0, 3.0, 1.5, 45.0), got ({translation[0] if len(translation) > 0 else 'N/A'}, {translation[1] if len(translation) > 1 else 'N/A'}, {translation[2] if len(translation) > 2 else 'N/A'}, {rotation})")
                        return False
                else:
                    self.log_test("SdfPath Only Move Request", False, 
                                 f"Unexpected status: {data.get('status')}")
                    return False
            else:
                data = json.loads(response)
                self.log_test("SdfPath Only Move Request", False, 
                             f"HTTP {status_code}: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.log_test("SdfPath Only Move Request", False, str(e))
            return False
    
    def test_invalid_endpoint(self):
        """Test request to non-existent endpoint."""
        try:
            # Send empty JSON object to avoid JSON parsing errors
            status_code, response = self.make_request('POST', '/invalid_endpoint', {})
            
            if status_code == 404:
                data = json.loads(response)
                if data.get('status') == 'error':
                    self.log_test("Invalid Endpoint", True, 
                                 f"Correctly returned 404: {data.get('message')}")
                    return True
                else:
                    self.log_test("Invalid Endpoint", False, 
                                 f"Wrong error status: {data.get('status')}")
                    return False
            else:
                self.log_test("Invalid Endpoint", False, 
                             f"Expected HTTP 404, got {status_code}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Endpoint", False, str(e))
            return False
    
    def test_multiple_moves(self):
        """Test multiple move operations in sequence."""
        test_prims = [
            {"path": "/World/TestCube", "pos": (1, 0, 0), "rot": 45},
            {"path": "/World/TestSphere", "pos": (0, 2, 1), "rot": 90},
            {"path": "/World/TestCylinder", "pos": (-2, 0, 0.5), "rot": 180}
        ]
        
        success_count = 0
        for i, prim_data in enumerate(test_prims):
            test_data = {
                "sdfPath": prim_data["path"],
                "x": prim_data["pos"][0],
                "y": prim_data["pos"][1], 
                "z": prim_data["pos"][2],
                "rotateZ": prim_data["rot"]
            }
            
            try:
                status_code, response = self.make_request('POST', '/move', test_data)
                if status_code == 200:
                    data = json.loads(response)
                    if data.get('status') == 'success':
                        success_count += 1
                        print(f"    Move {i+1}/3: {prim_data['path']} ✓")
                    else:
                        print(f"    Move {i+1}/3: {prim_data['path']} ✗ (status: {data.get('status')})")
                else:
                    print(f"    Move {i+1}/3: {prim_data['path']} ✗ (HTTP {status_code})")
                    
                # Small delay between requests
                time.sleep(0.1)
                
            except Exception as e:
                print(f"    Move {i+1}/3: {prim_data['path']} ✗ ({e})")
        
        if success_count == len(test_prims):
            self.log_test("Multiple Move Operations", True, 
                         f"Successfully moved {success_count}/{len(test_prims)} prims")
            return True
        else:
            self.log_test("Multiple Move Operations", False, 
                         f"Only {success_count}/{len(test_prims)} moves succeeded")
            return False
    
    def run_all_tests(self):
        """Run all tests."""
        print("USDViewer HTTP Request Server Test")
        print("=" * 50)
        
        # Check if server is reachable first
        if not self.test_server_status():
            print("\nERROR: Could not connect to USDViewer HTTP server!")
            print("Please ensure:")
            print("1. USDViewer is running")
            print("2. testHttpServer.usda is loaded")
            print(f"3. HTTP server is accessible at {self.base_url}")
            return False
        
        print("\nRunning tests...")
        print("-" * 30)
        
        # Run individual tests
        self.test_move_request_valid()
        self.test_move_request_invalid_path()
        self.test_move_request_partial_params()
        self.test_move_request_missing_sdf_path()
        self.test_move_request_only_sdf_path()
        self.test_invalid_endpoint()
        self.test_multiple_moves()
        
        # Summary
        print("\n" + "=" * 50)
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✓ All tests PASSED!")
            return True
        else:
            print("✗ Some tests FAILED!")
            print("\nFailed tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
            return False


def main():
    """Main function."""
    print("Starting USDViewer HTTP Server tests...")
    print("Python version:", sys.version)
    
    # Check if server parameters are provided
    host = 'localhost'
    port = 8080
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("\nUsage: python testHttpServer.py [host] [port]")
            print("Default: localhost 8080")
            print("\nBefore running this script:")
            print("1. Start USDViewer: usdview testHttpServer.usda")
            print("2. Verify HTTP server is running")
            return
        
        host = sys.argv[1] if len(sys.argv) > 1 else host
        port = int(sys.argv[2]) if len(sys.argv) > 2 else port
    
    print(f"Testing server at: http://{host}:{port}")
    print()
    
    # Run tests
    tester = USDViewerHTTPTester(host, port)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
