"""
File Operations Module with LangChain Tool Wrappers
Complete implementation with @tool decorators for LangGraph integration
"""

import os
import shutil
import platform
import json
from typing import Dict, Any, List
from langchain_core.tools import tool


# =============== HELPERS ===============

def get_desktop_path() -> str:
    """Get the desktop path for the current OS"""
    if platform.system() == "Windows":
        return os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    elif platform.system() == "Darwin":  # macOS
        return os.path.join(os.path.expanduser("~"), "Desktop")
    else:  # Linux
        return os.path.join(os.path.expanduser("~"), "Desktop")


def normalize_path(path: str) -> str:
    """Convert path to OS-specific format and expand special keywords"""
    path = path.strip()
    path_lower = path.lower()
    
    # Handle "desktop" keyword
    if path_lower == "desktop":
        return get_desktop_path()
    elif path_lower.startswith("desktop/") or path_lower.startswith("desktop\\"):
        subpath = path.split(os.sep, 1)[1] if os.sep in path else path.split("/", 1)[1]
        return os.path.join(get_desktop_path(), subpath)
    
    # Expand and normalize
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return os.path.normpath(path)


# =============== CORE FILE OPERATIONS ===============

def create_file(filename: str = "new_file.txt", path: str = ".", content: str = "") -> Dict[str, Any]:
    """Create a new file with optional content"""
    try:
        target_path = normalize_path(path)
        
        if not os.path.exists(target_path):
            os.makedirs(target_path, exist_ok=True)
        
        file_path = os.path.join(target_path, filename)
        
        if os.path.exists(file_path):
            return {"success": False, "error": f"File already exists: {file_path}"}
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": "File created successfully",
            "path": file_path,
            "filename": filename,
            "size": len(content)
        }
    except Exception as e:
        return {"success": False, "error": f"Error creating file: {str(e)}"}





def read_file(file_path: str) -> Dict[str, Any]:
    """Read content from a file"""
    try:
        target_path = normalize_path(file_path)
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"File not found: {target_path}"}
        
        if not os.path.isfile(target_path):
            return {"success": False, "error": f"Path is not a file: {target_path}"}
        
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "size": len(content),
            "path": target_path,
            "filename": os.path.basename(target_path)
        }
    except UnicodeDecodeError:
        return {"success": False, "error": "File contains binary data or unsupported encoding"}
    except Exception as e:
        return {"success": False, "error": f"Error reading file: {str(e)}"}


def write_file(file_path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    """Write or overwrite content to a file"""
    try:
        target_path = normalize_path(file_path)
        
        if os.path.exists(target_path) and not overwrite:
            return {"success": False, "error": f"File already exists. Use overwrite=True: {target_path}"}
        
        dir_path = os.path.dirname(target_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": "File written successfully",
            "path": target_path,
            "size": len(content)
        }
    except Exception as e:
        return {"success": False, "error": f"Error writing file: {str(e)}"}


def append_to_file(file_path: str, content: str) -> Dict[str, Any]:
    """Append content to the end of an existing file"""
    try:
        target_path = normalize_path(file_path)
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"File not found: {target_path}"}
        
        if not os.path.isfile(target_path):
            return {"success": False, "error": f"Path is not a file: {target_path}"}
        
        with open(target_path, 'a', encoding='utf-8') as f:
            f.write(content)
        
        new_size = os.path.getsize(target_path)
        
        return {
            "success": True,
            "message": "Content appended successfully",
            "path": target_path,
            "appended_size": len(content),
            "new_total_size": new_size
        }
    except Exception as e:
        return {"success": False, "error": f"Error appending to file: {str(e)}"}


def delete_file(file_path: str) -> Dict[str, Any]:
    """Delete a single file"""
    try:
        target_path = normalize_path(file_path)
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"File does not exist: {target_path}"}
        
        if not os.path.isfile(target_path):
            return {"success": False, "error": f"Not a file: {target_path}"}
        
        os.remove(target_path)
        
        return {
            "success": True,
            "message": "File deleted successfully",
            "deleted_path": target_path
        }
    except Exception as e:
        return {"success": False, "error": f"Error deleting file: {str(e)}"}


def create_folder(folder_name: str, path: str = ".") -> Dict[str, Any]:
    """Create a new folder"""
    try:
        target_path = normalize_path(path)
        folder_path = os.path.join(target_path, folder_name)
        
        if os.path.exists(folder_path):
            return {"success": False, "error": f"Folder already exists: {folder_path}"}
        
        os.makedirs(folder_path, exist_ok=True)
        
        return {
            "success": True,
            "message": "Folder created successfully",
            "path": folder_path,
            "folder_name": folder_name
        }
    except Exception as e:
        return {"success": False, "error": f"Error creating folder: {str(e)}"}


def delete_folder(folder_path: str, recursive: bool = False) -> Dict[str, Any]:
    """Delete a folder"""
    try:
        target_path = normalize_path(folder_path)
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"Folder does not exist: {target_path}"}
        
        if not os.path.isdir(target_path):
            return {"success": False, "error": f"Not a folder: {target_path}"}
        
        if recursive:
            shutil.rmtree(target_path)
        else:
            os.rmdir(target_path)
        
        return {
            "success": True,
            "message": "Folder deleted successfully",
            "deleted_path": target_path,
            "recursive": recursive
        }
    except OSError as e:
        if "not empty" in str(e).lower():
            return {"success": False, "error": f"Folder is not empty. Use recursive=True: {folder_path}"}
        return {"success": False, "error": f"Error deleting folder: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error deleting folder: {str(e)}"}


def list_directory(path: str = ".") -> Dict[str, Any]:
    """List all files and folders in a directory"""
    try:
        target_path = normalize_path(path)
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"Path does not exist: {target_path}"}
        
        if not os.path.isdir(target_path):
            return {"success": False, "error": f"Not a directory: {target_path}"}
        
        items = os.listdir(target_path)
        folders = []
        files = []
        
        for item in items:
            item_path = os.path.join(target_path, item)
            if os.path.isdir(item_path):
                folders.append({"name": item, "type": "folder", "path": item_path})
            else:
                files.append({
                    "name": item,
                    "type": "file",
                    "size": os.path.getsize(item_path),
                    "path": item_path
                })
        
        return {
            "success": True,
            "path": target_path,
            "total_items": len(items),
            "folder_count": len(folders),
            "file_count": len(files),
            "folders": sorted(folders, key=lambda x: x["name"]),
            "files": sorted(files, key=lambda x: x["name"])
        }
    except Exception as e:
        return {"success": False, "error": f"Error listing directory: {str(e)}"}


def move_file(source_path: str, destination_path: str) -> Dict[str, Any]:
    """Move or rename a file"""
    try:
        src = normalize_path(source_path)
        dest = normalize_path(destination_path)
        
        if not os.path.exists(src):
            return {"success": False, "error": f"Source file not found: {src}"}
        
        if not os.path.isfile(src):
            return {"success": False, "error": f"Source is not a file: {src}"}
        
        dest_dir = os.path.dirname(dest)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        shutil.move(str(src), str(dest))
        
        return {
            "success": True,
            "message": "File moved successfully",
            "source": src,
            "destination": dest
        }
    except Exception as e:
        return {"success": False, "error": f"Error moving file: {str(e)}"}


def move_folder(source_path: str, destination_path: str) -> Dict[str, Any]:
    """Move or rename a folder"""
    try:
        src = normalize_path(source_path)
        dest = normalize_path(destination_path)
        
        if not os.path.exists(src):
            return {"success": False, "error": f"Source folder not found: {src}"}
        
        if not os.path.isdir(src):
            return {"success": False, "error": f"Source is not a folder: {src}"}
        
        if os.path.exists(dest):
            return {"success": False, "error": f"Destination already exists: {dest}"}
        
        dest_parent = os.path.dirname(dest)
        if dest_parent and not os.path.exists(dest_parent):
            os.makedirs(dest_parent, exist_ok=True)
        
        shutil.move(str(src), str(dest))
        
        return {
            "success": True,
            "message": "Folder moved successfully",
            "source": src,
            "destination": dest
        }
    except Exception as e:
        return {"success": False, "error": f"Error moving folder: {str(e)}"}


def search_files(directory: str = ".", pattern: str = "*", recursive: bool = False) -> Dict[str, Any]:
    """Search for files matching a pattern"""
    try:
        from pathlib import Path
        
        dir_path = normalize_path(directory)
        
        if not os.path.exists(dir_path):
            return {"success": False, "error": f"Directory not found: {dir_path}"}
        
        path_obj = Path(dir_path)
        
        if recursive:
            matches = list(path_obj.rglob(pattern))
        else:
            matches = list(path_obj.glob(pattern))
        
        files = [m for m in matches if m.is_file()]
        
        results = []
        for file in files:
            results.append({
                "name": file.name,
                "path": str(file.absolute()),
                "size": file.stat().st_size,
                "extension": file.suffix
            })
        
        return {
            "success": True,
            "pattern": pattern,
            "directory": str(dir_path),
            "recursive": recursive,
            "count": len(results),
            "files": results
        }
    except Exception as e:
        return {"success": False, "error": f"Error searching files: {str(e)}"}


def copy_file(source_path: str, destination_path: str) -> Dict[str, Any]:
    """Copy a file to a new location"""
    try:
        src = normalize_path(source_path)
        dest = normalize_path(destination_path)
        
        if not os.path.exists(src):
            return {"success": False, "error": f"Source file not found: {src}"}
        
        if not os.path.isfile(src):
            return {"success": False, "error": f"Source is not a file: {src}"}
        
        dest_dir = os.path.dirname(dest)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        shutil.copy2(str(src), str(dest))
        
        return {
            "success": True,
            "message": "File copied successfully",
            "source": src,
            "destination": dest
        }
    except Exception as e:
        return {"success": False, "error": f"Error copying file: {str(e)}"}


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get detailed information about a file"""
    try:
        path = normalize_path(file_path)
        
        if not os.path.exists(path):
            return {"success": False, "error": f"File not found: {path}"}
        
        stat = os.stat(path)
        
        return {
            "success": True,
            "name": os.path.basename(path),
            "path": path,
            "type": "file" if os.path.isfile(path) else "directory",
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "extension": os.path.splitext(path)[1] if os.path.isfile(path) else None
        }
    except Exception as e:
        return {"success": False, "error": f"Error getting file info: {str(e)}"}


def get_file_size(file_path: str) -> Dict[str, Any]:
    """Get the size of a file"""
    try:
        target_path = normalize_path(file_path)
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"File not found: {target_path}"}
        
        if not os.path.isfile(target_path):
            return {"success": False, "error": f"Path is not a file: {target_path}"}
        
        size_bytes = os.path.getsize(target_path)
        
        return {
            "success": True,
            "path": target_path,
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 2),
            "size_mb": round(size_bytes / 1024 / 1024, 2)
        }
    except Exception as e:
        return {"success": False, "error": f"Error getting file size: {str(e)}"}


def get_folder_size(folder_path: str) -> Dict[str, Any]:
    """Calculate total size of all files in a folder"""
    try:
        target_path = normalize_path(folder_path)
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"Folder not found: {target_path}"}
        
        if not os.path.isdir(target_path):
            return {"success": False, "error": f"Path is not a folder: {target_path}"}
        
        total_size = 0
        file_count = 0
        folder_count = 0
        
        for dirpath, dirnames, filenames in os.walk(target_path):
            folder_count += len(dirnames)
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except:
                    pass
        
        return {
            "success": True,
            "path": target_path,
            "total_size_bytes": total_size,
            "total_size_kb": round(total_size / 1024, 2),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_size_gb": round(total_size / 1024 / 1024 / 1024, 2),
            "file_count": file_count,
            "folder_count": folder_count
        }
    except Exception as e:
        return {"success": False, "error": f"Error calculating folder size: {str(e)}"}


# ============================================================
# LANGCHAIN TOOL WRAPPERS FOR LANGGRAPH
# ============================================================

@tool
def create_file_tool(filename: str = "new_file.txt", path: str = ".", content: str = "") -> str:
    """Create a new file with optional content.
    
    Args:
        filename: Name of the file to create (default: "new_file.txt")
        path: Directory path where file should be created (default: current directory)
        content: Initial content to write to the file (default: empty string)
    """
    result = create_file(filename, path, content)
    return json.dumps(result)


@tool
def read_file_tool(file_path: str) -> str:
    """Read content from a file.
    
    Args:
        file_path: Full path to the file to read
    """
    result = read_file(file_path)
    return json.dumps(result)


@tool
def write_file_tool(file_path: str, content: str, overwrite: bool = False) -> str:
    """Write or overwrite content to a file.
    
    Args:
        file_path: Full path to the file
        content: Content to write to the file
        overwrite: Whether to overwrite if file exists (default: False)
    """
    result = write_file(file_path, content, overwrite)
    return json.dumps(result)


@tool
def append_to_file_tool(file_path: str, content: str) -> str:
    """Append content to the end of an existing file.
    
    Args:
        file_path: Full path to the file
        content: Content to append to the file
    """
    result = append_to_file(file_path, content)
    return json.dumps(result)


@tool
def delete_file_tool(file_path: str) -> str:
    """Delete a single file.
    
    Args:
        file_path: Full path to the file to delete
    """
    result = delete_file(file_path)
    return json.dumps(result)


@tool
def create_folder_tool(folder_name: str, path: str = ".") -> str:
    """Create a new folder.
    
    Args:
        folder_name: Name of the folder to create
        path: Directory path where folder should be created (default: current directory)
    """
    result = create_folder(folder_name, path)
    return json.dumps(result)


@tool
def delete_folder_tool(folder_path: str, recursive: bool = False) -> str:
    """Delete a folder.
    
    Args:
        folder_path: Full path to the folder to delete
        recursive: Whether to delete non-empty folders (default: False)
    """
    result = delete_folder(folder_path, recursive)
    return json.dumps(result)


@tool
def list_directory_tool(path: str = ".") -> str:
    """List all files and folders in a directory.
    
    Args:
        path: Directory path to list (default: current directory)
    """
    result = list_directory(path)
    return json.dumps(result)


@tool
def move_file_tool(source_path: str, destination_path: str) -> str:
    """Move or rename a file.
    
    Args:
        source_path: Current path of the file
        destination_path: New path for the file
    """
    result = move_file(source_path, destination_path)
    return json.dumps(result)


@tool
def move_folder_tool(source_path: str, destination_path: str) -> str:
    """Move or rename a folder.
    
    Args:
        source_path: Current path of the folder
        destination_path: New path for the folder
    """
    result = move_folder(source_path, destination_path)
    return json.dumps(result)


@tool
def search_files_tool(directory: str = ".", pattern: str = "*", recursive: bool = False) -> str:
    """Search for files matching a pattern.
    
    Args:
        directory: Directory to search in (default: current directory)
        pattern: File pattern to match (e.g., "*.txt", "data*") (default: "*")
        recursive: Whether to search subdirectories (default: False)
    """
    result = search_files(directory, pattern, recursive)
    return json.dumps(result)


@tool
def copy_file_tool(source_path: str, destination_path: str) -> str:
    """Copy a file to a new location.
    
    Args:
        source_path: Path of the file to copy
        destination_path: Destination path for the copied file
    """
    result = copy_file(source_path, destination_path)
    return json.dumps(result)


@tool
def get_file_info_tool(file_path: str) -> str:
    """Get detailed information about a file.
    
    Args:
        file_path: Full path to the file
    """
    result = get_file_info(file_path)
    return json.dumps(result)


@tool
def get_file_size_tool(file_path: str) -> str:
    """Get the size of a file.
    
    Args:
        file_path: Full path to the file
    """
    result = get_file_size(file_path)
    return json.dumps(result)


@tool
def get_folder_size_tool(folder_path: str) -> str:
    """Calculate total size of all files in a folder.
    
    Args:
        folder_path: Full path to the folder
    """
    result = get_folder_size(folder_path)
    return json.dumps(result)


# ============================================================
# EXPORT LANGCHAIN TOOLS FOR LANGGRAPH
# ============================================================

LANGCHAIN_TOOLS = [
    create_file_tool,
    read_file_tool,
    write_file_tool,
    append_to_file_tool,
    delete_file_tool,
    create_folder_tool,
    delete_folder_tool,
    list_directory_tool,
    move_file_tool,
    move_folder_tool,
    search_files_tool,
    copy_file_tool,
    get_file_info_tool,
    get_file_size_tool,
    get_folder_size_tool
]


# ============================================================
# USAGE EXAMPLE
# ============================================================

if __name__ == "__main__":
    print("✅ File operations module loaded successfully!")
    print(f"✅ {len(LANGCHAIN_TOOLS)} LangChain tools available")
    print("\nAvailable tools:")
    for i, tool in enumerate(LANGCHAIN_TOOLS, 1):
        print(f"  {i}. {tool.name}")