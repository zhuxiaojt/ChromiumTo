import os
import appdirs

def getAppDataPath():
    """获取应用数据目录"""
    config_dir = appdirs.user_data_dir("ChromiumTo", "ZhuxiaoGroup")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def getRelativePath(filename):
    """获取同目录文件路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def getDiskPartitions():
    """获取所有磁盘分区"""
    partitions = []
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        path = f'{letter}:\\'
        if os.path.exists(path):
            partitions.append(path)
    return partitions

def isChromiumApp(path):
    """检查是否为Chromium应用"""
    # 常见的Chromium应用特征文件
    chromium_features = [
        'chrome.dll',
        'chrome.exe',
        'msedge.dll',
        'msedge.exe',
        'brave.exe',
        'brave.dll',
        'chrome_elf.dll',
        'widevinecdmadapter.dll'
    ]
    
    # 检查目录下是否存在Chromium特征文件
    for feature in chromium_features:
        if os.path.exists(os.path.join(path, feature)):
            return True
    
    return False

def getAppName(path):
    """从路径中提取应用名称"""
    return os.path.basename(path)

def getChromeVersion(dll_path):
    """获取Chrome DLL版本信息"""
    try:
        import win32api
        info = win32api.GetFileVersionInfo(dll_path, '\\')
        ms = info['FileVersionMS']
        ls = info['FileVersionLS']
        version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
        return version
    except ImportError:
        return "无法获取版本"
    except Exception:
        return "未知版本"

def calculateDirectorySize(path):
    """计算目录大小"""
    total_size = 0
    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception:
        pass
    return total_size

def calculateChromeFilesSize(path):
    """计算Chrome相关文件的大小"""
    # 常见的Chromium应用核心文件
    chrome_files = [
        'chrome.dll',
        'chrome.exe',
        'chrome_elf.dll',
        'widevinecdmadapter.dll',
        'msedge.dll',
        'msedge.exe',
        'brave.dll',
        'brave.exe',
        'chrome_child.dll',
        'msedge_child.dll',
        'brave_child.dll',
        'icudtl.dat',
        'libEGL.dll',
        'libGLESv2.dll',
        'natives_blob.bin',
        'snapshot_blob.bin',
        'v8_context_snapshot.bin'
    ]
    
    total_size = 0
    for file in chrome_files:
        file_path = os.path.join(path, file)
        if os.path.exists(file_path):
            total_size += os.path.getsize(file_path)
    return total_size

def getChromiumFiles(path):
    """获取Chromium相关文件列表"""
    chrome_files = [
        'chrome.dll',
        'chrome.exe',
        'chrome_elf.dll',
        'widevinecdmadapter.dll',
        'msedge.dll',
        'msedge.exe',
        'brave.dll',
        'brave.exe',
        'chrome_child.dll',
        'msedge_child.dll',
        'brave_child.dll',
        'icudtl.dat',
        'libEGL.dll',
        'libGLESv2.dll',
        'natives_blob.bin',
        'snapshot_blob.bin',
        'v8_context_snapshot.bin'
    ]
    
    found_files = []
    for file in chrome_files:
        file_path = os.path.join(path, file)
        if os.path.exists(file_path):
            found_files.append(file)
    
    return found_files

def formatFileSize(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"
