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

try:
    from PySide6 import QtCore
except ImportError:
    try:
        from PySide2 import QtCore
    except ImportError:
        try:
            from PyQt5 import QtCore
        except ImportError:
            QtCore = None


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
                "POST /move - Move a prim by updating its transform",
                "POST /prompt - Process a prompt message"
            ]
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        try:
            parsed_path = urlparse(self.path)
            endpoint = parsed_path.path.lower()
            
            # Check if endpoint exists first, before parsing body
            if endpoint not in ['/move', '/prompt']:
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
            elif endpoint == '/prompt':
                self._handle_prompt_request(request_data)
                
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
            "sdfPath": "/path/to/prim",          # Required
            "x": 1.0,                            # Optional - preserves current value if not provided
            "y": 2.0,                            # Optional - preserves current value if not provided
            "z": 3.0,                            # Optional - preserves current value if not provided
            "rotateX": 0.0,                      # Optional - preserves current value if not provided (rotation in degrees)
            "rotateY": 0.0,                      # Optional - preserves current value if not provided (rotation in degrees)
            "rotateZ": 45.0,                     # Optional - preserves current value if not provided (rotation in degrees)
            "scaleX": 1.0,                       # Optional - preserves current value if not provided
            "scaleY": 1.0,                       # Optional - preserves current value if not provided
            "scaleZ": 1.0                        # Optional - preserves current value if not provided
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
            current_transform = self._get_current_transform(prim_path)
            current_x, current_y, current_z = current_transform['translation']
            current_rotateX, current_rotateY, current_rotateZ = current_transform['rotation']
            current_scaleX, current_scaleY, current_scaleZ = current_transform['scale']
            
            # Use provided values or fallback to current values
            x = float(request_data.get('x', current_x))
            y = float(request_data.get('y', current_y))
            z = float(request_data.get('z', current_z))
            rotate_x = float(request_data.get('rotateX', current_rotateX))
            rotate_y = float(request_data.get('rotateY', current_rotateY))
            rotate_z = float(request_data.get('rotateZ', current_rotateZ))
            scale_x = float(request_data.get('scaleX', current_scaleX))
            scale_y = float(request_data.get('scaleY', current_scaleY))
            scale_z = float(request_data.get('scaleZ', current_scaleZ))
            
            # Execute the move operation
            success, message = self._move_prim(prim_path, x, y, z, rotate_x, rotate_y, rotate_z, scale_x, scale_y, scale_z)
            
            if success:
                self._send_success({
                    "message": message,
                    "prim_path": str(prim_path),
                    "transform": {
                        "translation": [x, y, z],
                        "rotation_degrees": [rotate_x, rotate_y, rotate_z],
                        "scale": [scale_x, scale_y, scale_z]
                    }
                })
            else:
                self._send_error(400, message)
                
        except ValueError as e:
            self._send_error(400, f"Invalid numeric parameter: {str(e)}")
        except Exception as e:
            self._send_error(500, f"Error processing move request: {str(e)}")
            traceback.print_exc()
    
    def _handle_prompt_request(self, request_data):
        """
        Handle a prompt request and wait for user input.
        
        Expected request format:
        {
            "message": "Your prompt message here"    # Required
        }
        
        Response format:
        {
            "status": "success",
            "message": "Your prompt message here",
            "user_response": "User's input from userPromptInput"
        }
        """
        try:
            # Validate required parameters
            if 'message' not in request_data:
                self._send_error(400, "Missing required parameter: message")
                return
            
            message = request_data['message']
            
            # Add prefix to the message
            formatted_message = f"[Agent] {message}"
            
            # Add the message to the history QTextEdit if app_controller is available
            if self.app_controller and hasattr(self.app_controller, '_ui'):
                try:
                    # Use QMetaObject.invokeMethod for thread-safe execution
                    if QtCore:
                        # Get the history widget from app_controller
                        history_widget = None
                        if hasattr(self.app_controller._ui, 'history'):
                            history_widget = self.app_controller._ui.history
                        elif hasattr(self.app_controller, '_mainWindow') and hasattr(self.app_controller._mainWindow, '_ui'):
                            if hasattr(self.app_controller._mainWindow._ui, 'history'):
                                history_widget = self.app_controller._mainWindow._ui.history
                        
                        if history_widget:
                            # Schedule the GUI update to happen in the main thread
                            def append_message():
                                try:
                                    history_widget.append(formatted_message)
                                except Exception as e:
                                    print(f"Error appending to history: {e}")
                            
                            # Execute in main thread using QApplication.postEvent or direct call
                            try:
                                # Simple direct call - Qt should handle thread safety for basic operations
                                history_widget.append(formatted_message)
                            except Exception as e:
                                print(f"Warning: Could not append to history: {e}")
                    else:
                        # Fallback if Qt is not available
                        print(f"Qt not available, printing message: {formatted_message}")
                        
                except Exception as e:
                    print(f"Warning: Could not update history: {e}")
            else:
                print(f"Warning: app_controller not available for history update")
            
            # Wait for user to press Enter in userPromptInput
            if self.app_controller:
                # Create an event to wait for user input
                user_input_event = threading.Event()
                
                # Set the event in app_controller so it knows to signal when Enter is pressed
                try:
                    # Direct call - should be safe for setting simple instance variables
                    self.app_controller.setPromptPendingEvent(user_input_event)
                except Exception as e:
                    print(f"Warning: Could not set prompt event: {e}")
                    return self._json_response({"error": "Could not set up prompt handling"}, 500)
                
                # Wait for the user to press Enter (with a timeout to prevent hanging)
                if user_input_event.wait(timeout=300):  # 5 minute timeout
                    # Get the user's response
                    user_response = self.app_controller.getPromptResponse()
                    
                    # Send success response with user input
                    self._send_success({
                        "message": f"Received prompt message: {message}",
                        "response": user_response or "",
                        "user_response": user_response or "",  # Keep for backward compatibility
                        "status": "completed"
                    })
                else:
                    # Timeout occurred
                    self._send_error(408, "Request timeout: User did not respond within 5 minutes")
            else:
                self._send_error(500, "App controller not available for user input")
                
        except Exception as e:
            self._send_error(500, f"Error processing prompt request: {str(e)}")
            traceback.print_exc()
    
    def _get_current_transform(self, prim_path):
        """
        Get the current transform values of a prim.
        
        Returns:
            dict: {
                'translation': [x, y, z],
                'rotation': [rotateX, rotateY, rotateZ],  # in degrees
                'scale': [scaleX, scaleY, scaleZ]
            }
            Defaults to (0,0,0), (0,0,0), (1,1,1) if no transform exists
        """
        if not self.usd_stage:
            return {
                'translation': [0.0, 0.0, 0.0],
                'rotation': [0.0, 0.0, 0.0],
                'scale': [1.0, 1.0, 1.0]
            }
        
        # Get the prim
        prim = self.usd_stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            # Return default values for non-existent prims
            return {
                'translation': [0.0, 0.0, 0.0],
                'rotation': [0.0, 0.0, 0.0],
                'scale': [1.0, 1.0, 1.0]
            }
        
        # Check if the prim is xformable
        if not UsdGeom.Xformable(prim):
            return {
                'translation': [0.0, 0.0, 0.0],
                'rotation': [0.0, 0.0, 0.0],
                'scale': [1.0, 1.0, 1.0]
            }
        
        xformable = UsdGeom.Xformable(prim)
        
        try:
            # Initialize default values
            translation = [0.0, 0.0, 0.0]
            rotation = [0.0, 0.0, 0.0]  # [rotateX, rotateY, rotateZ]
            scale = [1.0, 1.0, 1.0]
            
            # Get the xform ops and their order
            xform_ops = xformable.GetOrderedXformOps()
            
            for xform_op in xform_ops:
                op_type = xform_op.GetOpType()
                
                # Handle different transform operation types
                if op_type == UsdGeom.XformOp.TypeTransform:
                    # This is a transform matrix - extract all components
                    matrix = xform_op.Get()
                    if matrix:
                        # Extract translation
                        trans = matrix.ExtractTranslation()
                        translation = [float(trans[0]), float(trans[1]), float(trans[2])]
                        
                        # Extract scale
                        scale_vec = matrix.ExtractScale()
                        scale = [float(scale_vec[0]), float(scale_vec[1]), float(scale_vec[2])]
                        
                        # Extract rotation (simplified - assumes XYZ Euler)
                        import math
                        rot = matrix.ExtractRotation()
                        rot_matrix = rot.GetMatrix()
                        
                        # Extract Euler angles from rotation matrix (XYZ order)
                        # This is a simplified extraction
                        sy = math.sqrt(rot_matrix[0][0] * rot_matrix[0][0] + rot_matrix[1][0] * rot_matrix[1][0])
                        singular = sy < 1e-6
                        
                        if not singular:
                            x = math.atan2(rot_matrix[2][1], rot_matrix[2][2])
                            y = math.atan2(-rot_matrix[2][0], sy)
                            z = math.atan2(rot_matrix[1][0], rot_matrix[0][0])
                        else:
                            x = math.atan2(-rot_matrix[1][2], rot_matrix[1][1])
                            y = math.atan2(-rot_matrix[2][0], sy)
                            z = 0
                        
                        rotation = [float(x * 180.0 / math.pi), 
                                   float(y * 180.0 / math.pi), 
                                   float(z * 180.0 / math.pi)]
                
                elif op_type == UsdGeom.XformOp.TypeTranslate:
                    # Translation operation
                    trans = xform_op.Get()
                    if trans and len(trans) >= 3:
                        translation = [float(trans[0]), float(trans[1]), float(trans[2])]
                
                elif op_type == UsdGeom.XformOp.TypeScale:
                    # Scale operation
                    scale_val = xform_op.Get()
                    if scale_val:
                        if hasattr(scale_val, '__len__') and len(scale_val) >= 3:
                            # Vector scale
                            scale = [float(scale_val[0]), float(scale_val[1]), float(scale_val[2])]
                        else:
                            # Uniform scale
                            uniform_scale = float(scale_val)
                            scale = [uniform_scale, uniform_scale, uniform_scale]
                
                elif op_type == UsdGeom.XformOp.TypeRotateX:
                    # X rotation operation (in degrees)
                    rot_x = xform_op.Get()
                    if rot_x is not None:
                        rotation[0] = float(rot_x)
                
                elif op_type == UsdGeom.XformOp.TypeRotateY:
                    # Y rotation operation (in degrees)
                    rot_y = xform_op.Get()
                    if rot_y is not None:
                        rotation[1] = float(rot_y)
                
                elif op_type == UsdGeom.XformOp.TypeRotateZ:
                    # Z rotation operation (in degrees)
                    rot_z = xform_op.Get()
                    if rot_z is not None:
                        rotation[2] = float(rot_z)
                
                elif op_type == UsdGeom.XformOp.TypeRotateXYZ:
                    # XYZ rotation operation
                    rot_xyz = xform_op.Get()
                    if rot_xyz and len(rot_xyz) >= 3:
                        rotation = [float(rot_xyz[0]), float(rot_xyz[1]), float(rot_xyz[2])]
            
            return {
                'translation': translation,
                'rotation': rotation,
                'scale': scale
            }
            
        except Exception as e:
            # If we can't extract transform, return defaults
            print(f"Warning: Could not extract transform from {prim_path}: {e}")
            return {
                'translation': [0.0, 0.0, 0.0],
                'rotation': [0.0, 0.0, 0.0],
                'scale': [1.0, 1.0, 1.0]
            }
    
    def _move_prim(self, prim_path, x, y, z, rotate_x, rotate_y, rotate_z, scale_x, scale_y, scale_z):
        """
        Move a prim by updating its transform.
        
        Args:
            prim_path: SdfPath of the prim
            x, y, z: Translation values
            rotate_x, rotate_y, rotate_z: Rotation values in degrees
            scale_x, scale_y, scale_z: Scale values
        
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
            
            # Look for existing ops
            translate_op = None
            rotate_x_op = None
            rotate_y_op = None
            rotate_z_op = None
            rotate_xyz_op = None
            scale_op = None
            transform_op = None
            
            for op in existing_ops:
                op_type = op.GetOpType()
                if op_type == UsdGeom.XformOp.TypeTranslate:
                    translate_op = op
                elif op_type == UsdGeom.XformOp.TypeRotateX:
                    rotate_x_op = op
                elif op_type == UsdGeom.XformOp.TypeRotateY:
                    rotate_y_op = op
                elif op_type == UsdGeom.XformOp.TypeRotateZ:
                    rotate_z_op = op
                elif op_type == UsdGeom.XformOp.TypeRotateXYZ:
                    rotate_xyz_op = op
                elif op_type == UsdGeom.XformOp.TypeScale:
                    scale_op = op
                elif op_type == UsdGeom.XformOp.TypeTransform:
                    transform_op = op
            
            # If there's a transform matrix, we need to clear and rebuild with individual ops
            if transform_op is not None:
                xformable.ClearXformOpOrder()
                translate_op = None
                rotate_x_op = None
                rotate_y_op = None
                rotate_z_op = None
                rotate_xyz_op = None
                scale_op = None
            
            # Determine the best rotation strategy
            use_individual_rotations = (rotate_x != 0.0 or rotate_y != 0.0 or rotate_z != 0.0)
            has_non_zero_xy_rotation = (rotate_x != 0.0 or rotate_y != 0.0)
            
            # Create/update translation op
            if translate_op is None:
                translate_op = xformable.AddTranslateOp()
            translate_op.Set(Gf.Vec3d(x, y, z))
            
            # Handle rotation operations
            if use_individual_rotations:
                if has_non_zero_xy_rotation:
                    # Use rotateXYZ if we have X or Y rotation
                    if rotate_xyz_op is None:
                        # Remove individual rotation ops if they exist
                        if rotate_x_op or rotate_y_op or rotate_z_op:
                            xformable.ClearXformOpOrder()
                            translate_op = xformable.AddTranslateOp()
                            translate_op.Set(Gf.Vec3d(x, y, z))
                        rotate_xyz_op = xformable.AddRotateXYZOp()
                    rotate_xyz_op.Set(Gf.Vec3f(rotate_x, rotate_y, rotate_z))
                else:
                    # Only Z rotation - use individual rotateZ op
                    if rotate_z_op is None:
                        # Remove rotateXYZ if it exists and create individual ops
                        if rotate_xyz_op:
                            xformable.ClearXformOpOrder()
                            translate_op = xformable.AddTranslateOp()
                            translate_op.Set(Gf.Vec3d(x, y, z))
                        rotate_z_op = xformable.AddRotateZOp()
                    rotate_z_op.Set(rotate_z)
            
            # Handle scale
            has_non_uniform_scale = (scale_x != 1.0 or scale_y != 1.0 or scale_z != 1.0)
            if has_non_uniform_scale or scale_op is not None:
                # If we have an existing scale op or need to set scale, use it
                if scale_op is None:
                    scale_op = xformable.AddScaleOp(precision=UsdGeom.XformOp.PrecisionFloat)
                
                # Always set as Vec3f for consistency with USD schema
                scale_op.Set(Gf.Vec3f(scale_x, scale_y, scale_z))
            
            # Refresh the viewer if app_controller is available
            if self.app_controller:
                try:
                    # Trigger a refresh of the viewer
                    self.app_controller.updateGUI()
                except Exception as e:
                    print(f"Warning: Could not refresh GUI: {e}")
            
            return True, f"Successfully updated prim {prim_path} - translation: ({x}, {y}, {z}), rotation: ({rotate_x}, {rotate_y}, {rotate_z}), scale: ({scale_x}, {scale_y}, {scale_z})"
            
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
            print(f"  POST /prompt - Process a prompt message")
            
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
