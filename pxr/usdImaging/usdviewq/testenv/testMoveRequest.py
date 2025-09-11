#!/usr/bin/env python3
"""
Simple test script for USDViewer HTTP Move Request.

Edit the parameters below and run this script to test move operations.
Comment out any parameter (except sdfPath) to exclude it from the request.
"""

import json
import urllib.request
import urllib.parse
import sys

# ========================================================================
# TEST PARAMETERS - Edit these values as needed
# ========================================================================

# Mandatory parameter
SDF_PATH = "/World/TestCube"  # Required - do not comment out

# Translation parameters
X = 5.0
Y = 3.0
Z = 2.0

# Rotation parameters (degrees)
ROTATE_X = 45.0
ROTATE_Y = 30.0
ROTATE_Z = 90.0

# Scale parameters
SCALE_X = 1.5
SCALE_Y = 2.0
SCALE_Z = 0.8

# Server configuration
SERVER_HOST = "localhost"
SERVER_PORT = 8080

# ========================================================================
# SCRIPT LOGIC - Do not edit below this line
# ========================================================================

def build_request_data():
    """Build the request data from the configured parameters."""
    data = {"sdfPath": SDF_PATH}  # sdfPath is always required
    
    # Check which parameters are defined (not commented out)
    if 'X' in globals():
        data['x'] = X
    if 'Y' in globals():
        data['y'] = Y
    if 'Z' in globals():
        data['z'] = Z
    if 'ROTATE_X' in globals():
        data['rotateX'] = ROTATE_X
    if 'ROTATE_Y' in globals():
        data['rotateY'] = ROTATE_Y
    if 'ROTATE_Z' in globals():
        data['rotateZ'] = ROTATE_Z
    if 'SCALE_X' in globals():
        data['scaleX'] = SCALE_X
    if 'SCALE_Y' in globals():
        data['scaleY'] = SCALE_Y
    if 'SCALE_Z' in globals():
        data['scaleZ'] = SCALE_Z
    
    return data

def send_move_request(host, port, data):
    """Send the move request to the USDViewer HTTP server."""
    url = f"http://{host}:{port}/move"
    
    try:
        # Prepare the request
        json_data = json.dumps(data, indent=2)
        json_bytes = json_data.encode('utf-8')
        
        req = urllib.request.Request(url, data=json_bytes)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Content-Length', str(len(json_bytes)))
        
        print(f"Sending Move Request to: {url}")
        print(f"Request Data:")
        print(json_data)
        print("-" * 50)
        
        # Send the request
        with urllib.request.urlopen(req) as response:
            status_code = response.status
            response_text = response.read().decode('utf-8')
            
            print(f"Response Status: {status_code}")
            print(f"Response:")
            
            try:
                # Pretty print JSON response
                response_data = json.loads(response_text)
                print(json.dumps(response_data, indent=2))
            except json.JSONDecodeError:
                print(response_text)
            
            return status_code == 200
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_response = e.read().decode('utf-8')
            error_data = json.loads(error_response)
            print("Error details:")
            print(json.dumps(error_data, indent=2))
        except:
            print(f"Error response: {error_response}")
        return False
        
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        print("Make sure USDViewer is running with the HTTP server enabled.")
        return False
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    """Main function."""
    print("USDViewer HTTP Move Request Test")
    print("=" * 50)
    
    # Build request data
    request_data = build_request_data()
    
    # Send the request
    success = send_move_request(SERVER_HOST, SERVER_PORT, request_data)
    
    print("-" * 50)
    if success:
        print("✓ Request completed successfully!")
    else:
        print("✗ Request failed!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
