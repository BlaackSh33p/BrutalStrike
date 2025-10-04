#!/usr/bin/env python3
import abc

class BaseModule(metaclass=abc.ABCMeta):
    def __init__(self):
        self.name = "base_module"
        self.description = "Base module description"
        self.author = "MyC2Framework"
        self.platforms = ["windows", "linux", "macos"]
        self.privileges = ["user", "admin"]
        self.options = {}
    
    @abc.abstractmethod
    def run(self, agent, arguments):
        """Execute module logic"""
        pass
    
    def setup(self, options):
        """Configure module options"""
        self.options.update(options)
    
    def cleanup(self):
        """Clean up after execution"""
        pass

class ShellModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "shell"
        self.description = "Execute shell commands"
        self.options = {
            "command": {
                "description": "Command to execute",
                "required": True,
                "value": ""
            }
        }
    
    def run(self, agent, arguments):
        command = arguments.get('command', '')
        return agent.execute_shell_command({'command': command})

class SystemInfoModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "sysinfo"
        self.description = "Get detailed system information"
        self.options = {}
    
    def run(self, agent, arguments):
        return agent.get_detailed_system_info()