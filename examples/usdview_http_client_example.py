#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
USDViewer HTTP Request Server - Usage Example

This script demonstrates how to send HTTP requests to the USDViewer HTTP server
to manipulate USD files remotely.

Before running this script:
1. Start usdview with a USD file that contains a prim you want to move
2. The HTTP server will automatically start on http://localhost:8080
3. Run this script to send a move request

You can also customize the server port and host by setting environment variables:
- USDVIEW_HTTP_PORT: Port number (default: 8080)
- USDVIEW_HTTP_HOST: Host address (default: localhost)
"""

import json
import requests


def check_server_status(host='localhost', port=8080):
    """Check if the USDViewer HTTP server is running."""
    try:
        url = f"http://{host}:{port}/"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✓ USDViewer HTTP Server is running")
            print(f"  Status: {data.get('status')}")
            print(f"  Message: {data.get('message')}")
            print("  Available endpoints:")
            for endpoint in data.get('available_endpoints', []):
                print(f"    - {endpoint}")
            return True
        else:
            print(f"✗ Server responded with status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not connect to server: {e}")
        return False


def send_move_request(sdf_path, x, y, z, rotate_z, host='localhost', port=8080):
    """
    Send a move request to the USDViewer HTTP server.
    
    Args:
        sdf_path (str): The SdfPath of the prim to move (e.g., "/World/Cube")
        x (float): X position
        y (float): Y position  
        z (float): Z position
        rotate_z (float): Z rotation in degrees
        host (str): Server host
        port (int): Server port
    """
    try:
        url = f"http://{host}:{port}/move"
        
        # Prepare request data
        request_data = {
            "sdfPath": sdf_path,
            "x": x,
            "y": y,
            "z": z,
            "rotateZ": rotate_z
        }
        
        print(f"Sending move request to {url}")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        # Send POST request
        response = requests.post(
            url,
            json=request_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        # Parse response
        response_data = response.json()
        
        if response.status_code == 200:
            print("✓ Move request successful!")
            print(f"  Status: {response_data.get('status')}")
            print(f"  Message: {response_data.get('message')}")
            if 'transform' in response_data:
                transform = response_data['transform']
                print(f"  New transform:")
                print(f"    Translation: {transform.get('translation')}")
                print(f"    Z Rotation: {transform.get('rotation_z_degrees')}°")
        else:
            print(f"✗ Move request failed!")
            print(f"  Status Code: {response.status_code}")
            print(f"  Status: {response_data.get('status')}")
            print(f"  Error: {response_data.get('message')}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Network error: {e}")
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON response: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def main():
    """Main function with example usage."""
    print("USDViewer HTTP Request Server - Usage Example")
    print("=" * 50)
    
    # Server configuration
    host = 'localhost'
    port = 8080
    
    # Check if server is running
    print("1. Checking server status...")
    if not check_server_status(host, port):
        print("\nPlease make sure usdview is running with a USD file loaded.")
        print("The HTTP server should start automatically when usdview starts.")
        return
    
    print("\n2. Sending example move requests...")
    
    # Example 1: Move a cube to position (5, 0, 0) with no rotation
    print("\nExample 1: Moving /World/Cube to (5, 0, 0)")
    send_move_request("/World/Cube", 5.0, 0.0, 0.0, 0.0, host, port)
    
    # Example 2: Move the same cube with rotation
    print("\nExample 2: Moving /World/Cube to (0, 5, 2) with 45° Z rotation")
    send_move_request("/World/Cube", 0.0, 5.0, 2.0, 45.0, host, port)
    
    # Example 3: Move a different prim (adjust path as needed)
    print("\nExample 3: Moving /World/Sphere to (-3, -3, 1) with 90° Z rotation")
    send_move_request("/World/Sphere", -3.0, -3.0, 1.0, 90.0, host, port)
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTip: Modify the prim paths in this script to match your USD file.")
    print("You can check the prim hierarchy in usdview to find valid paths.")


if __name__ == "__main__":
    main()
