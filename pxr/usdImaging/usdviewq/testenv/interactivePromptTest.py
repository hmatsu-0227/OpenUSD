#!/usr/bin/env python3
"""
Interactive Prompt Endpoint Test

This script provides an interactive interface to test the USDViewer prompt endpoint.
You can send custom messages and see the responses in real-time.
"""

import json
import requests
import sys


def test_server_connection(server_url):
    """Test if the server is accessible."""
    try:
        response = requests.get(server_url, timeout=5)
        return response.status_code == 200
    except:
        return False


def send_prompt_message(server_url, message):
    """Send a prompt message to the server and return the response synchronously."""
    prompt_url = f"{server_url}/prompt"
    
    try:
        payload = {"message": message}
        response = requests.post(
            prompt_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"Server Message: {data.get('message', 'No message')}")
            response_text = data.get('response', 'No response')
            print(f"Response: {response_text}")
            # Return the actual response content
            return response_text
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                error_message = error_data.get('message', 'Unknown error')
                print(f"Error: {error_message}")
                # Return error information
                return f"Error: {error_message}"
            except:
                error_text = response.text
                print(f"Error Body: {error_text}")
                return f"Error: {error_text}"
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return "Error: Request timed out"
    except requests.exceptions.ConnectionError:
        print("❌ Connection error")
        return "Error: Connection error"
    except Exception as e:
        error_message = f"Error: {e}"
        print(f"❌ {error_message}")
        return error_message


def main():
    """Main interactive loop."""
    server_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print("🔧 Interactive USDViewer Prompt Endpoint Test")
    print("=" * 50)
    print(f"Server URL: {server_url}")
    
    # Test connection
    if not test_server_connection(server_url):
        print("❌ Cannot connect to server. Make sure USDViewer is running with HTTP server enabled.")
        sys.exit(1)
    
    print("✅ Server is accessible")
    print("\nYou can now send prompt messages to the server.")
    print("Type 'quit' or 'exit' to stop, 'help' for commands.")
    print("-" * 50)
    
    while True:
        try:
            # Get user input
            message = input("\n📝 Enter prompt message: ").strip()
            
            # Handle special commands
            if message.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif message.lower() in ['help', 'h']:
                print("\nAvailable commands:")
                print("  help, h     - Show this help")
                print("  quit, exit, q - Exit the program")
                print("  Any other text - Send as prompt message")
                continue
            elif not message:
                print("⚠️  Please enter a message")
                continue
            
            # Send the message and get the response
            print(f"\n📤 Sending: '{message}'")
            print("-" * 30)
            response = send_prompt_message(server_url, message)
            
            # Display the returned response
            print(f"\n📥 Returned response: '{response}'")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
