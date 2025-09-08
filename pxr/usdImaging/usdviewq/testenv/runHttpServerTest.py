#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
USDViewer HTTP Server Test Runner

This script simplifies the process of testing the USDViewer HTTP server functionality.
It can automatically start USDViewer with the test file and run the HTTP tests.

Usage:
    python runHttpServerTest.py [options]

Options:
    --manual    Only run HTTP tests (assume USDViewer is already running)
    --host      Server host (default: localhost)
    --port      Server port (default: 8080)
    --help      Show this help message
"""

import sys
import os
import subprocess
import time
import argparse
from pathlib import Path


def find_usdview_executable():
    """Try to find usdview executable."""
    # Common locations for usdview
    possible_paths = [
        "usdview",  # If in PATH
        "./usdview",  # Local build
        "../../../bin/usdview/usdview.py",  # Relative to test location
    ]
    
    for path in possible_paths:
        try:
            # Test if executable exists and runs
            result = subprocess.run([sys.executable if path.endswith('.py') else path, '--help'], 
                                   capture_output=True, timeout=5)
            if result.returncode == 0 or 'usdview' in result.stderr.decode().lower():
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            continue
    
    return None


def wait_for_server(host, port, timeout=30):
    """Wait for HTTP server to become available."""
    import urllib.request
    import urllib.error
    
    url = f"http://{host}:{port}/"
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            time.sleep(0.5)
    
    return False


def run_manual_test(host, port):
    """Run HTTP tests assuming USDViewer is already running."""
    print("Running HTTP server tests...")
    print(f"Expecting server at: http://{host}:{port}")
    print()
    
    # Import and run the test
    current_dir = Path(__file__).parent
    test_script = current_dir / "testHttpServer.py"
    
    if not test_script.exists():
        print(f"Error: Test script not found at {test_script}")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(test_script), host, str(port)], 
                               cwd=current_dir)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def run_automatic_test(host, port):
    """Automatically start USDViewer and run tests."""
    current_dir = Path(__file__).parent
    test_usd_file = current_dir / "testHttpServer.usda"
    
    if not test_usd_file.exists():
        print(f"Error: Test USD file not found at {test_usd_file}")
        return False
    
    # Find usdview
    usdview_cmd = find_usdview_executable()
    if not usdview_cmd:
        print("Error: Could not find usdview executable")
        print("Please ensure usdview is in your PATH or provide the full path")
        return False
    
    print(f"Found usdview: {usdview_cmd}")
    print(f"Starting USDViewer with {test_usd_file}...")
    
    # Set environment variables for HTTP server
    env = os.environ.copy()
    env['USDVIEW_HTTP_HOST'] = host
    env['USDVIEW_HTTP_PORT'] = str(port)
    
    # Start USDViewer
    try:
        cmd = [sys.executable, usdview_cmd] if usdview_cmd.endswith('.py') else [usdview_cmd]
        cmd.append(str(test_usd_file))
        
        print(f"Running: {' '.join(cmd)}")
        usdview_process = subprocess.Popen(cmd, env=env)
        
        # Wait for HTTP server to start
        print(f"Waiting for HTTP server to start on http://{host}:{port}...")
        if wait_for_server(host, port, timeout=30):
            print("✓ HTTP server is ready!")
            
            # Run tests
            time.sleep(2)  # Give a bit more time for full initialization
            success = run_manual_test(host, port)
            
            # Stop USDViewer
            print("\nStopping USDViewer...")
            usdview_process.terminate()
            try:
                usdview_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                usdview_process.kill()
                usdview_process.wait()
            
            return success
        else:
            print("✗ HTTP server did not start within timeout")
            usdview_process.terminate()
            usdview_process.wait()
            return False
            
    except Exception as e:
        print(f"Error starting USDViewer: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="USDViewer HTTP Server Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python runHttpServerTest.py                    # Auto-start USDViewer and run tests
    python runHttpServerTest.py --manual           # Run tests only (USDViewer already running)
    python runHttpServerTest.py --port 9090        # Use custom port
        """
    )
    
    parser.add_argument('--manual', action='store_true',
                       help='Only run HTTP tests (assume USDViewer is already running)')
    parser.add_argument('--host', default='localhost',
                       help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=8080,
                       help='Server port (default: 8080)')
    
    args = parser.parse_args()
    
    print("USDViewer HTTP Server Test Runner")
    print("=" * 40)
    print(f"Python version: {sys.version}")
    print(f"Target server: http://{args.host}:{args.port}")
    print()
    
    if args.manual:
        print("Manual mode: Running tests only")
        print("Please ensure USDViewer is running with testHttpServer.usda")
        input("Press Enter when ready...")
        success = run_manual_test(args.host, args.port)
    else:
        print("Automatic mode: Starting USDViewer and running tests")
        success = run_automatic_test(args.host, args.port)
    
    if success:
        print("\n✓ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
