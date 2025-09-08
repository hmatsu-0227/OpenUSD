#
# Copyright 2025 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""
HTTP Request Server for USDViewer

This module provides an HTTP server that allows external applications to
send requests to modify the USD stage that is currently loaded in USDViewer.

Supported requests:
- Move: Updates the transform of a prim with the specified SdfPath
"""

from __future__ import print_function

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import traceback

from pxr import Usd, UsdGeom, Sdf, Gf, Tf


class USDViewerHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for USDViewer operations."""
    
    def __init__(self, *args, usd_stage=None, app_controller=None, **kwargs):
        self.usd_stage = usd_stage
        self.app_controller = app_controller
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[USDViewer HTTP Server] {format % args}")
    
    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "status": "ok",
            "message": "USDViewer HTTP Request Server is running",
            "available_endpoints": [
                "POST /move - Move a prim by updating its transform"
            ]
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        try:
            parsed_path = urlparse(self.path)
            endpoint = parsed_path.path.lower()
            
            # Check if endpoint exists first, before parsing body
            if endpoint not in ['/move']:
                self._send_error(404, f"Unknown endpoint: {endpoint}")
                return
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse JSON data
            try:
                request_data = json.loads(post_data.decode('utf-8')) if content_length > 0 else {}
            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON in request body")
                return
            
            if endpoint == '/move':
                self._handle_move_request(request_data)
                
        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")
            traceback.print_exc()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _handle_move_request(self, request_data):
        """
        Handle a move request.
        
        Expected request format:
        {
            "sdfPath": "/path/to/prim",
            "x": 1.0,
            "y": 2.0,
            "z": 3.0,
            "rotateZ": 45.0  # rotation in degrees
        }
        """
        try:
            # Validate required parameters
            required_params = ['sdfPath', 'x', 'y', 'z', 'rotateZ']
            for param in required_params:
                if param not in request_data:
                    self._send_error(400, f"Missing required parameter: {param}")
                    return
            
            sdf_path = request_data['sdfPath']
            x = float(request_data['x'])
            y = float(request_data['y'])
            z = float(request_data['z'])
            rotate_z = float(request_data['rotateZ'])
            
            # Validate SdfPath
            try:
                prim_path = Sdf.Path(sdf_path)
                if not prim_path.IsPrimPath():
                    self._send_error(400, f"Invalid prim path: {sdf_path}")
                    return
            except Exception as e:
                self._send_error(400, f"Invalid prim path: {sdf_path} - {str(e)}")
                return
            
            # Execute the move operation
            success, message = self._move_prim(prim_path, x, y, z, rotate_z)
            
            if success:
                self._send_success({
                    "message": message,
                    "prim_path": str(prim_path),
                    "transform": {
                        "translation": [x, y, z],
                        "rotation_z_degrees": rotate_z
                    }
                })
            else:
                self._send_error(400, message)
                
        except ValueError as e:
            self._send_error(400, f"Invalid numeric parameter: {str(e)}")
        except Exception as e:
            self._send_error(500, f"Error processing move request: {str(e)}")
            traceback.print_exc()
    
    def _move_prim(self, prim_path, x, y, z, rotate_z_degrees):
        """
        Move a prim by updating its transform.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.usd_stage:
            return False, "No USD stage available"
        
        # Get the prim
        prim = self.usd_stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return False, f"Prim not found at path: {prim_path}"
        
        # Ensure the prim is an Xformable
        if not UsdGeom.Xformable(prim):
            # Try to make it xformable by adding Xform schema
            xformable = UsdGeom.Xformable.Define(self.usd_stage, prim_path)
            if not xformable:
                return False, f"Could not make prim xformable: {prim_path}"
        else:
            xformable = UsdGeom.Xformable(prim)
        
        # Create the transform matrix
        # Convert rotation from degrees to radians
        rotate_z_radians = rotate_z_degrees * (3.14159265359 / 180.0)
        
        # Create translation matrix
        translation = Gf.Vec3d(x, y, z)
        
        # Create rotation matrix (rotation around Z axis)
        rotation = Gf.Rotation(Gf.Vec3d(0, 0, 1), rotate_z_radians)
        
        # Create the transform matrix
        transform_matrix = Gf.Matrix4d(1.0)
        transform_matrix.SetTranslateOnly(translation)
        transform_matrix = transform_matrix * Gf.Matrix4d(rotation, Gf.Vec3d(0, 0, 0))
        
        # Clear existing transform ops and set new one
        xformable.ClearXformOpOrder()
        transform_op = xformable.AddTransformOp()
        transform_op.Set(transform_matrix)
        
        # Refresh the viewer if app_controller is available
        if self.app_controller:
            try:
                # Trigger a refresh of the viewer
                self.app_controller._refreshGUI()
            except Exception as e:
                print(f"Warning: Could not refresh GUI: {e}")
        
        return True, f"Successfully moved prim {prim_path} to position ({x}, {y}, {z}) with Z rotation {rotate_z_degrees} degrees"
    
    def _send_success(self, data):
        """Send a successful response."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "status": "success",
            **data
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def _send_error(self, code, message):
        """Send an error response."""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "status": "error",
            "code": code,
            "message": message
        }
        self.wfile.write(json.dumps(response, indent=2).encode())


class USDViewerHTTPServer:
    """HTTP Server for USDViewer that runs in a separate thread."""
    
    def __init__(self, port=8080, host='localhost'):
        self.port = port
        self.host = host
        self.server = None
        self.server_thread = None
        self.usd_stage = None
        self.app_controller = None
        self.running = False
    
    def set_usd_stage(self, stage):
        """Set the USD stage that the server will operate on."""
        self.usd_stage = stage
    
    def set_app_controller(self, app_controller):
        """Set the app controller for GUI refresh operations."""
        self.app_controller = app_controller
    
    def start(self):
        """Start the HTTP server in a separate thread."""
        if self.running:
            print("HTTP server is already running")
            return
        
        try:
            # Create request handler class with stage and app_controller
            def handler_factory(*args, **kwargs):
                return USDViewerHTTPRequestHandler(
                    *args, 
                    usd_stage=self.usd_stage,
                    app_controller=self.app_controller,
                    **kwargs
                )
            
            # Create and start the server
            self.server = HTTPServer((self.host, self.port), handler_factory)
            self.server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True
            )
            
            self.running = True
            self.server_thread.start()
            
            print(f"USDViewer HTTP Request Server started on http://{self.host}:{self.port}")
            print(f"Available endpoints:")
            print(f"  GET  / - Server status")
            print(f"  POST /move - Move a prim")
            
        except Exception as e:
            print(f"Failed to start HTTP server: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the HTTP server."""
        if not self.running:
            return
        
        try:
            if self.server:
                print("Stopping USDViewer HTTP Request Server...")
                self.server.shutdown()
                self.server.server_close()
                
            if self.server_thread:
                self.server_thread.join(timeout=5.0)
            
            self.running = False
            print("USDViewer HTTP Request Server stopped")
            
        except Exception as e:
            print(f"Error stopping HTTP server: {e}")
    
    def is_running(self):
        """Check if the server is running."""
        return self.running


# Global server instance
_global_http_server = None


def get_http_server():
    """Get the global HTTP server instance."""
    global _global_http_server
    if _global_http_server is None:
        _global_http_server = USDViewerHTTPServer()
    return _global_http_server


def start_http_server(port=8080, host='localhost', stage=None, app_controller=None):
    """
    Start the HTTP server for USDViewer.
    
    Args:
        port (int): Port number for the server
        host (str): Host address for the server
        stage (Usd.Stage): USD stage to operate on
        app_controller: USDViewer app controller for GUI refresh
    """
    server = get_http_server()
    server.port = port
    server.host = host
    
    if stage:
        server.set_usd_stage(stage)
    if app_controller:
        server.set_app_controller(app_controller)
    
    server.start()
    return server


def stop_http_server():
    """Stop the HTTP server."""
    server = get_http_server()
    server.stop()


def update_stage(stage):
    """Update the USD stage that the HTTP server operates on."""
    server = get_http_server()
    server.set_usd_stage(stage)


def update_app_controller(app_controller):
    """Update the app controller for GUI refresh operations."""
    server = get_http_server()
    server.set_app_controller(app_controller)
