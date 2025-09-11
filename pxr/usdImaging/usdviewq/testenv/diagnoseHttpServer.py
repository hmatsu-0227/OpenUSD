#!/usr/bin/env python3
"""
USDViewer HTTP Server Diagnostic Script

This script helps diagnose why the HTTP server might not be starting
on some systems.
"""

import sys
import os
import socket
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

def check_python_version():
    """Check Python version compatibility."""
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 6):
        print("WARNING: Python 3.6+ is recommended for HTTP server functionality")
    else:
        print("✓ Python version is compatible")

def check_required_modules():
    """Check if required modules are available."""
    print("\nChecking required modules...")
    
    required_modules = [
        'http.server',
        'threading',
        'json',
        'socket',
        'urllib.request',
        'urllib.parse'
    ]
    
    for module_name in required_modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name} - Available")
        except ImportError as e:
            print(f"✗ {module_name} - NOT AVAILABLE: {e}")

def check_usd_modules():
    """Check if USD modules are available."""
    print("\nChecking USD modules...")
    
    usd_modules = [
        'pxr',
        'pxr.Usd',
        'pxr.UsdGeom',
        'pxr.Gf'
    ]
    
    for module_name in usd_modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name} - Available")
        except ImportError as e:
            print(f"✗ {module_name} - NOT AVAILABLE: {e}")

def check_port_availability(host='localhost', port=8080):
    """Check if the specified port is available."""
    print(f"\nChecking port availability on {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✗ Port {port} is already in use")
            return False
        else:
            print(f"✓ Port {port} is available")
            return True
    except Exception as e:
        print(f"✗ Error checking port {port}: {e}")
        return False

def test_socket_creation(host='localhost', port=8080):
    """Test if we can create and bind a socket."""
    print(f"\nTesting socket creation on {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(1)
        print(f"✓ Successfully created and bound socket on {host}:{port}")
        sock.close()
        return True
    except Exception as e:
        print(f"✗ Failed to create socket on {host}:{port}: {e}")
        return False

class TestHandler(BaseHTTPRequestHandler):
    """Simple test HTTP request handler."""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "success", "message": "Test server is working"}
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def test_http_server(host='localhost', port=8081):
    """Test if we can start a simple HTTP server."""
    print(f"\nTesting HTTP server creation on {host}:{port}...")
    
    try:
        # Use a different port to avoid conflicts
        server = HTTPServer((host, port), TestHandler)
        
        # Start server in a thread
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        print(f"✓ Test HTTP server started successfully on {host}:{port}")
        
        # Test if we can connect to our own server
        import urllib.request
        try:
            response = urllib.request.urlopen(f"http://{host}:{port}", timeout=5)
            data = response.read()
            print(f"✓ Successfully connected to test server: {data.decode()}")
        except Exception as e:
            print(f"✗ Could not connect to test server: {e}")
        
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
        print(f"✓ Test HTTP server stopped successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed to start test HTTP server: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_environment_variables():
    """Check relevant environment variables."""
    print("\nChecking environment variables...")
    
    env_vars = [
        'USDVIEW_HTTP_PORT',
        'USDVIEW_HTTP_HOST',
        'PYTHONPATH',
        'PATH'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var} = {value}")
        else:
            print(f"  {var} = <not set>")

def check_firewall_and_security():
    """Check for potential firewall/security issues."""
    print("\nFirewall and Security Check...")
    print("Note: This script cannot automatically detect all firewall/security issues.")
    print("If the HTTP server still fails to start after all other checks pass,")
    print("consider the following:")
    print("  1. Check Windows Firewall settings")
    print("  2. Check antivirus software that might block Python network access")
    print("  3. Check corporate security policies")
    print("  4. Try running as administrator")
    print("  5. Try using a different port (set USDVIEW_HTTP_PORT environment variable)")

def main():
    """Run all diagnostic tests."""
    print("USDViewer HTTP Server Diagnostic Tool")
    print("=" * 50)
    
    # Get configuration
    host = os.getenv('USDVIEW_HTTP_HOST', 'localhost')
    port = int(os.getenv('USDVIEW_HTTP_PORT', '8080'))
    
    print(f"Target configuration: {host}:{port}")
    
    # Run tests
    check_python_version()
    check_required_modules()
    check_usd_modules()
    check_environment_variables()
    
    port_available = check_port_availability(host, port)
    if port_available:
        socket_ok = test_socket_creation(host, port)
        if socket_ok:
            # Test with a different port to avoid conflicts
            test_port = port + 1 if port < 65535 else port - 1
            test_http_server(host, test_port)
    
    check_firewall_and_security()
    
    print("\n" + "=" * 50)
    print("Diagnostic complete!")
    print("\nIf all tests pass but USDViewer HTTP server still doesn't start,")
    print("the issue might be specific to the USDViewer integration.")
    print("Try running USDViewer with verbose output to see more details.")

if __name__ == "__main__":
    main()
