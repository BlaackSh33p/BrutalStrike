"""
File Search Module
"""

MODULE_INFO = {
    'name': 'File Search',
    'description': 'Search for files matching patterns',
    'category': 'File Operations',
    'platforms': ['windows', 'linux', 'macos'],
    'privileges': 'user',
}

def execute(arguments, agent_context):
    try:
        import os
        import glob
        
        pattern = arguments.get('pattern', '*.txt')
        search_path = arguments.get('path', '.')
        
        if not os.path.exists(search_path):
            return f"Path not found: {search_path}"
        
        found_files = []
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if glob.fnmatch.fnmatch(file, pattern):
                    full_path = os.path.join(root, file)
                    found_files.append(full_path)
            
            # Limit results for performance
            if len(found_files) > 100:
                found_files.append("... (results truncated)")
                break
        
        if found_files:
            result = f"Found {len(found_files)} files matching '{pattern}':\n"
            result += "\n".join(found_files[:50])  # Show first 50
            if len(found_files) > 50:
                result += f"\n... and {len(found_files) - 50} more"
            return result
        else:
            return f"No files found matching '{pattern}' in {search_path}"
            
    except Exception as e:
        return f"File search failed: {str(e)}"