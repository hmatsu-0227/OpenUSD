#!/usr/bin/env python3
"""
USDViewer HTTP Client

This module provides a simple HTTP client for sending prompt messages to USDViewer.
The send_prompt_message() function can be used to interact with USDViewer's HTTP prompt endpoint.
"""

import json
import requests

# =============================================================================
# Configuration - Edit this section to change the server URL
# =============================================================================
SERVER_URL = "http://localhost:8080"  # Change this if USDViewer is running on a different host/port
# =============================================================================


def send_prompt_message(message):
    """Send a prompt message to the server and return the response synchronously.
    
    Args:
        message (str): The prompt message to send to USDViewer
        
    Returns:
        str: The user's response from USDViewer, or an error message if the request failed
        
    Example:
        response = send_prompt_message("Hello from client!")
        print(f"User responded: {response}")
    """
    prompt_url = f"{SERVER_URL}/prompt"
    
    try:
        payload = {"message": message}
        response = requests.post(
            prompt_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=None  # Wait indefinitely for user response
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


def test_server_connection(server_url=None):
    """Test if the server is accessible.
    
    Args:
        server_url (str, optional): The base URL of the USDViewer HTTP server.
                                   If None, uses the default SERVER_URL constant.
        
    Returns:
        bool: True if the server is accessible, False otherwise
    """
    if server_url is None:
        server_url = SERVER_URL
    try:
        response = requests.get(server_url, timeout=5)
        return response.status_code == 200
    except:
        return False


# Example usage
if __name__ == "__main__":
    # Example of how to use the client
    print("🔧 USDViewer HTTP Client Example")
    print("=" * 40)
    print(f"Using server URL: {SERVER_URL}")
    
    # Test connection
    if not test_server_connection():
        print("❌ Cannot connect to server. Make sure USDViewer is running with HTTP server enabled.")
        exit(1)
    
    print("✅ Server is accessible")
    
    # Send a test message
    test_message = "Hello from usdviewHttpClient.py!"
    print(f"\n📤 Sending test message: '{test_message}'")
    print("⏳ Go to USDViewer and enter your response in userPromptInput, then press Enter")
    
    response = send_prompt_message(test_message)
    print(f"\n📥 Final response: '{response}'")