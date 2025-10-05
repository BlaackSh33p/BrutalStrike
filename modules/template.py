"""
Module Template - Copy this to create new modules
"""

MODULE_INFO = {
    'name': 'Module Name',
    'description': 'Module description',
    'category': 'Category',  # Discovery, Execution, Persistence, etc.
    'platforms': ['windows', 'linux', 'macos'],  # Supported platforms
    'privileges': 'user',  # user or admin
}

def execute(arguments, agent_context):
    """
    Execute the module
    
    Args:
        arguments (dict): Module arguments
        agent_context (dict): Agent information and utilities
    
    Returns:
        str: Module output
    """
    try:
        # Your module logic here
        result = "Module executed successfully"
        return result
    except Exception as e:
        return f"Module error: {str(e)}"