# -*- coding: utf-8 -*-
"""
Hardware Device Mocks - Simulated physical devices for Astroflora
Exposed via MCP Server for Tools with realistic behavior patterns
"""
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import json

from mcp.protocol import HardwareDevice, HardwareDeviceType, CorrelationContext

class DeviceStatus(str, Enum):
    """Device status enumeration"""
    AVAILABLE = "available"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    OFFLINE = "offline"

class MockHardwareDevice:
    """Base class for mock hardware devices"""
    
    def __init__(self, device_info: HardwareDevice):
        self.device_info = device_info
        self.status = DeviceStatus.AVAILABLE
        self.current_operation: Optional[str] = None
        self.operation_start_time: Optional[float] = None
        self.operation_data: Dict[str, Any] = {}
        
    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a device action with realistic timing"""
        if self.status == DeviceStatus.BUSY:
            raise Exception(f"Device {self.device_info.device_id} is busy")
        
        if action not in self.device_info.mock_responses:
            raise Exception(f"Unsupported action: {action}")
        
        # Set device to busy
        self.status = DeviceStatus.BUSY
        self.current_operation = action
        self.operation_start_time = time.time()
        
        try:
            # Simulate operation with device-specific behavior
            result = await self._simulate_operation(action, parameters)
            return result
        finally:
            # Reset device status
            self.status = DeviceStatus.AVAILABLE
            self.current_operation = None
            self.operation_start_time = None

    async def _simulate_operation(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate device-specific operation - to be overridden by subclasses"""
        # Default simulation
        await asyncio.sleep(1.0)  # Basic operation time
        
        # Generate response from template
        response_template = self.device_info.mock_responses[action].copy()
        timestamp = str(int(time.time()))
        
        # Replace placeholders
        for key, value in response_template.items():
            if isinstance(value, str):
                response_template[key] = value.replace("{timestamp}", timestamp)
                for param_key, param_value in parameters.items():
                    response_template[key] = response_template[key].replace(f"{{{param_key}}}", str(param_value))
        
        return {
            "action": action,
            "result": response_template,
            "execution_time": time.time() - self.operation_start_time,
            "device_status": self.status.value
        }

class MockMicroscope(MockHardwareDevice):
    """Mock fluorescence microscope with realistic imaging simulation"""
    
    async def _simulate_operation(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate microscope operations"""
        
        if action == "capture_image":
            # Simulate image capture time based on settings
            exposure_time = parameters.get("exposure_time", 100)  # ms
            binning = parameters.get("binning", 1)
            
            # Realistic capture time calculation
            capture_time = (exposure_time / 1000) + (2.0 / binning)  # Base + readout time
            await asyncio.sleep(capture_time)
            
            image_id = f"img_{int(time.time())}"
            return {
                "action": action,
                "result": {
                    "image_id": image_id,
                    "format": "tiff",
                    "size": "2048x2048",
                    "bit_depth": 16,
                    "exposure_time_ms": exposure_time,
                    "binning": binning,
                    "wavelength": parameters.get("wavelength", 488),
                    "filename": f"{image_id}.tiff"
                },
                "execution_time": capture_time,
                "device_status": self.status.value
            }
            
        elif action == "set_magnification":
            # Quick magnification change
            await asyncio.sleep(0.5)
            mag = parameters.get("magnification", 100)
            
            return {
                "action": action,
                "result": {
                    "current_magnification": mag,
                    "field_of_view_um": 500 / mag,  # Typical FOV calculation
                    "numerical_aperture": min(1.4, mag / 100),  # Simplified NA
                    "resolution_um": 0.61 * 0.5 / min(1.4, mag / 100)  # Rayleigh criterion
                },
                "execution_time": 0.5,
                "device_status": self.status.value
            }
            
        elif action == "acquire_stack":
            # Z-stack acquisition
            z_slices = parameters.get("z_slices", 10)
            z_step = parameters.get("z_step", 0.2)  # μm
            exposure_time = parameters.get("exposure_time", 100)  # ms
            
            # Time calculation: move + capture for each slice
            total_time = z_slices * ((exposure_time / 1000) + 0.1)  # 0.1s for Z movement
            await asyncio.sleep(min(total_time, 5.0))  # Cap simulation time
            
            stack_id = f"stack_{int(time.time())}"
            return {
                "action": action,
                "result": {
                    "stack_id": stack_id,
                    "num_slices": z_slices,
                    "z_range_um": z_slices * z_step,
                    "z_step_um": z_step,
                    "total_acquisition_time": total_time,
                    "files": [f"{stack_id}_slice_{i:03d}.tiff" for i in range(z_slices)]
                },
                "execution_time": min(total_time, 5.0),
                "device_status": self.status.value
            }
        
        return await super()._simulate_operation(action, parameters)

class MockThermalCycler(MockHardwareDevice):
    """Mock PCR thermal cycler with realistic cycling simulation"""
    
    async def _simulate_operation(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate thermal cycler operations"""
        
        if action == "run_pcr":
            # Simulate PCR program
            cycles = parameters.get("cycles", 35)
            denaturation_temp = parameters.get("denaturation_temp", 95)
            annealing_temp = parameters.get("annealing_temp", 55)
            extension_temp = parameters.get("extension_temp", 72)
            
            # Realistic time calculation
            cycle_time = 30 + 30 + 60  # Typical cycle times in seconds
            total_time = cycles * cycle_time + 300  # + initial denaturation
            
            # Simulate with shortened time for demo
            simulation_time = min(total_time / 60, 3.0)  # Max 3 seconds simulation
            await asyncio.sleep(simulation_time)
            
            run_id = f"pcr_{int(time.time())}"
            return {
                "action": action,
                "result": {
                    "run_id": run_id,
                    "status": "completed",
                    "cycles_completed": cycles,
                    "total_time_seconds": total_time,
                    "temperatures": {
                        "denaturation": denaturation_temp,
                        "annealing": annealing_temp,
                        "extension": extension_temp
                    },
                    "estimated_yield": f"{85 + (cycles * 0.1):.1f}%",  # Mock yield calculation
                    "log_file": f"{run_id}_thermal_log.csv"
                },
                "execution_time": simulation_time,
                "device_status": self.status.value
            }
            
        elif action == "get_temperature":
            # Quick temperature reading
            await asyncio.sleep(0.1)
            target_temp = parameters.get("target_temp", 25)
            
            return {
                "action": action,
                "result": {
                    "current_temp": target_temp + (time.time() % 1 - 0.5) * 0.2,  # Small variation
                    "target_temp": target_temp,
                    "block_temp": target_temp + (time.time() % 1 - 0.5) * 0.1,
                    "lid_temp": target_temp + 5,
                    "heating_rate": "5.0°C/s",
                    "cooling_rate": "3.0°C/s"
                },
                "execution_time": 0.1,
                "device_status": self.status.value
            }
            
        elif action == "set_program":
            # Program setup
            await asyncio.sleep(0.2)
            cycles = parameters.get("cycles", 35)
            
            program_id = f"prog_{int(time.time())}"
            return {
                "action": action,
                "result": {
                    "program_id": program_id,
                    "cycles": cycles,
                    "steps": parameters.get("steps", [
                        {"temp": 95, "time": 30, "name": "denaturation"},
                        {"temp": 55, "time": 30, "name": "annealing"},
                        {"temp": 72, "time": 60, "name": "extension"}
                    ]),
                    "estimated_duration_minutes": cycles * 2 + 5,  # Rough estimate
                    "program_saved": True
                },
                "execution_time": 0.2,
                "device_status": self.status.value
            }
        
        return await super()._simulate_operation(action, parameters)

class HardwareManager:
    """Manager for all hardware devices"""
    
    def __init__(self):
        self.devices: Dict[str, MockHardwareDevice] = {}
        self._initialize_devices()
    
    def _initialize_devices(self):
        """Initialize all mock devices"""
        
        # Microscope device
        microscope_info = HardwareDevice(
            device_id="microscope_01",
            device_type=HardwareDeviceType.MICROSCOPE,
            name="Fluorescence Microscope Alpha",
            status="available",
            capabilities=["fluorescence", "brightfield", "phase_contrast", "z_stack"],
            parameters={
                "magnification_range": [10, 1000],
                "resolution": "0.2μm",
                "wavelengths": [405, 488, 561, 640],
                "max_z_range": "200μm",
                "camera_resolution": "2048x2048"
            },
            mock_responses={
                "capture_image": {"image_id": "img_{timestamp}", "format": "tiff", "size": "2048x2048"},
                "set_magnification": {"current_magnification": "{magnification}"},
                "acquire_stack": {"stack_id": "stack_{timestamp}", "num_slices": "{z_slices}"}
            }
        )
        self.devices["microscope_01"] = MockMicroscope(microscope_info)
        
        # Thermal cycler device
        thermal_cycler_info = HardwareDevice(
            device_id="thermal_cycler_01",
            device_type=HardwareDeviceType.THERMAL_CYCLER,
            name="PCR Thermal Cycler Beta",
            status="available",
            capabilities=["pcr", "gradient_pcr", "real_time_monitoring", "temperature_control"],
            parameters={
                "temperature_range": [-10, 105],
                "accuracy": "±0.1°C",
                "ramp_rate": "5°C/s",
                "block_volume": "0.2ml",
                "max_cycles": 99
            },
            mock_responses={
                "run_pcr": {"run_id": "pcr_{timestamp}", "status": "running"},
                "get_temperature": {"current_temp": "{target_temp}", "block_temp": "{target_temp}"},
                "set_program": {"program_id": "prog_{timestamp}", "cycles": "{cycles}"}
            }
        )
        self.devices["thermal_cycler_01"] = MockThermalCycler(thermal_cycler_info)
        
        # Additional devices can be added here...
    
    def get_device(self, device_id: str) -> Optional[MockHardwareDevice]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def list_devices(self) -> List[HardwareDevice]:
        """List all available devices"""
        return [device.device_info for device in self.devices.values()]
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status"""
        device = self.devices.get(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        return {
            "device_id": device_id,
            "status": device.status.value,
            "current_operation": device.current_operation,
            "operation_time": time.time() - device.operation_start_time if device.operation_start_time else None
        }
    
    async def execute_device_action(
        self, 
        device_id: str, 
        action: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute action on a device"""
        device = self.devices.get(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        return await device.execute_action(action, parameters)

# Global hardware manager instance
hardware_manager = HardwareManager()