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
            "sdfPath": "/path/to/prim",      # Required
            "x": 1.0,                        # Optional - preserves current value if not provided
            "y": 2.0,                        # Optional - preserves current value if not provided
            "z": 3.0,                        # Optional - preserves current value if not provided
            "rotateZ": 45.0                  # Optional - preserves current value if not provided (rotation in degrees)
        }
        """
        try:
            # Validate required parameters (only sdfPath is required)
            if 'sdfPath' not in request_data:
                self._send_error(400, "Missing required parameter: sdfPath")
                return
            
            sdf_path = request_data['sdfPath']
            
            # Validate SdfPath
            try:
                prim_path = Sdf.Path(sdf_path)
                if not prim_path.IsPrimPath():
                    self._send_error(400, f"Invalid prim path: {sdf_path}")
                    return
            except Exception as e:
                self._send_error(400, f"Invalid prim path: {sdf_path} - {str(e)}")
                return
            
            # Get current transform values if prim exists
            current_x, current_y, current_z, current_rotate_z = self._get_current_transform(prim_path)
            
            # Use provided values or fallback to current values
            x = float(request_data.get('x', current_x))
            y = float(request_data.get('y', current_y))
            z = float(request_data.get('z', current_z))
            rotate_z = float(request_data.get('rotateZ', current_rotate_z))
            
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
    
    def _get_current_transform(self, prim_path):
        """
        Get the current transform values of a prim.
        
        Returns:
            tuple: (x, y, z, rotate_z_degrees) - defaults to (0,0,0,0) if no transform exists
        """
        if not self.usd_stage:
            return 0.0, 0.0, 0.0, 0.0
        
        # Get the prim
        prim = self.usd_stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            # Return default values for non-existent prims
            return 0.0, 0.0, 0.0, 0.0
        
        # Check if the prim is xformable
        if not UsdGeom.Xformable(prim):
            return 0.0, 0.0, 0.0, 0.0
        
        xformable = UsdGeom.Xformable(prim)
        
        try:
            # Initialize default values
            x, y, z = 0.0, 0.0, 0.0
            rotate_z_degrees = 0.0
            
            # Get the xform ops and their order
            xform_ops = xformable.GetOrderedXformOps()
            
            for xform_op in xform_ops:
                op_type = xform_op.GetOpType()
                
                # Handle different transform operation types
                if op_type == UsdGeom.XformOp.TypeTransform:
                    # This is a transform matrix
                    matrix = xform_op.Get()
                    if matrix:
                        # Extract translation
                        translation = matrix.ExtractTranslation()
                        x, y, z = float(translation[0]), float(translation[1]), float(translation[2])
                        
                        # Extract Z rotation from matrix
                        import math
                        # Extract the rotation component
                        rotation = matrix.ExtractRotation()
                        rotation_matrix = rotation.GetMatrix()
                        
                        # Calculate Z rotation assuming it's the primary rotation
                        rotate_z_radians = math.atan2(rotation_matrix[1][0], rotation_matrix[0][0])
                        rotate_z_degrees = float(rotate_z_radians * (180.0 / math.pi))
                
                elif op_type == UsdGeom.XformOp.TypeTranslate:
                    # Translation operation
                    translation = xform_op.Get()
                    if translation and len(translation) >= 3:
                        x, y, z = float(translation[0]), float(translation[1]), float(translation[2])
                
                elif op_type == UsdGeom.XformOp.TypeRotateZ:
                    # Z rotation operation (in degrees)
                    rotation = xform_op.Get()
                    if rotation is not None:
                        rotate_z_degrees = float(rotation)
                
                elif op_type == UsdGeom.XformOp.TypeRotateXYZ:
                    # XYZ rotation operation
                    rotation = xform_op.Get()
                    if rotation and len(rotation) >= 3:
                        # Take only the Z component
                        rotate_z_degrees = float(rotation[2])
            
            return x, y, z, rotate_z_degrees
            
        except Exception as e:
            # If we can't extract transform, return defaults
            print(f"Warning: Could not extract transform from {prim_path}: {e}")
            return 0.0, 0.0, 0.0, 0.0
    
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
        
        try:
            # Get existing xform ops or create new ones
            existing_ops = xformable.GetOrderedXformOps()
            
            # Look for existing translate and rotateZ ops
            translate_op = None
            rotate_z_op = None
            
            for op in existing_ops:
                if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                    translate_op = op
                elif op.GetOpType() == UsdGeom.XformOp.TypeRotateZ:
                    rotate_z_op = op
                elif op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                    # If there's a transform matrix, we need to clear and rebuild
                    xformable.ClearXformOpOrder()
                    translate_op = None
                    rotate_z_op = None
                    break
            
            # Create translate op if it doesn't exist
            if translate_op is None:
                translate_op = xformable.AddTranslateOp()
            
            # Create rotateZ op if it doesn't exist
            if rotate_z_op is None:
                rotate_z_op = xformable.AddRotateZOp()
            
            # Set the translation
            translate_op.Set(Gf.Vec3d(x, y, z))
            
            # Set the Z rotation (in degrees - USD rotateZ expects degrees)
            rotate_z_op.Set(rotate_z_degrees)
            
            # Refresh the viewer if app_controller is available
            if self.app_controller:
                try:
                    # Trigger a refresh of the viewer
                    self.app_controller._refreshGUI()
                except Exception as e:
                    print(f"Warning: Could not refresh GUI: {e}")
            
            return True, f"Successfully moved prim {prim_path} to position ({x}, {y}, {z}) with Z rotation {rotate_z_degrees} degrees"
            
        except Exception as e:
            return False, f"Error setting transform: {str(e)}"
    
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
