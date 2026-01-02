import os
import time
import threading
from utils import getDiskPartitions, isChromiumApp, getAppName, getChromeVersion, calculateChromeFilesSize
from config import getConfig, clearDetectedApps, addDetectedApp

def shouldExclude(path, exclusions):
    """检查路径是否应该被排除"""
    for exclusion in exclusions:
        if exclusion in path:
            return True
    return False

def calculateTotalFiles(directories, exclusions):
    """计算所有目录的总文件数"""
    total_files = 0
    for directory in directories:
        if not os.path.exists(directory):
            continue
        try:
            for root, dirs, files in os.walk(directory):
                if shouldExclude(root, exclusions):
                    dirs.clear()
                    continue
                total_files += len(files)
        except Exception:
            pass
    return total_files

def scanDirectory(directory, exclusions, progress_callback=None, stop_event=None, cumulative_progress=None):
    """扫描单个目录"""
    chromium_apps = []
    
    try:
        for root, dirs, files in os.walk(directory):
            # 检查是否需要停止扫描
            if stop_event and stop_event.is_set():
                break
            
            # 检查是否排除该目录
            if shouldExclude(root, exclusions):
                # 跳过子目录
                dirs.clear()
                continue
            
            # 更新累积进度
            if cumulative_progress:
                cumulative_progress['scanned'] += len(files)
                current = cumulative_progress['scanned']
                total = cumulative_progress['total']
            
            # 检查是否为Chromium应用
            if isChromiumApp(root):
                # 查找Chrome DLL文件
                chrome_dll = None
                for file in files:
                    if file.lower() in ['chrome.dll', 'msedge.dll', 'brave.dll']:
                        chrome_dll = os.path.join(root, file)
                        break
                
                # 获取版本信息
                version = "未知版本"
                if chrome_dll:
                    version = getChromeVersion(chrome_dll)
                
                # 计算Chromium文件大小
                chromium_size = calculateChromeFilesSize(root)
                
                # 创建应用信息
                app_info = {
                    'name': getAppName(root),
                    'path': root,
                    'version': version,
                    'chrome_dll': chrome_dll,
                    'size': chromium_size,
                    'last_scan': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                chromium_apps.append(app_info)
                
                # 回调进度
                if progress_callback:
                    progress_callback(app_info)
                
                # 跳过子目录，因为Chromium应用通常在一个目录中
                dirs.clear()
            
            # 回调扫描进度，包含当前扫描目录和累积进度
            if progress_callback and cumulative_progress:
                # 发送进度信息，格式：(current, total, type, current_dir)
                progress_callback((cumulative_progress['scanned'], cumulative_progress['total'], 'scan', root))
    except PermissionError:
        # 忽略权限错误
        pass
    except Exception:
        # 忽略其他错误
        pass
    
    return chromium_apps

def scanSystem(progress_callback=None, complete_callback=None, stop_event=None):
    """全盘扫描系统"""
    # 清空已检测应用列表
    clearDetectedApps()
    
    # 获取扫描排除列表
    exclusions = getConfig('scan_exclusions', [])
    
    # 获取所有磁盘分区
    partitions = getDiskPartitions()
    
    # 计算总文件数
    total_files = calculateTotalFiles(partitions, exclusions)
    
    all_chromium_apps = []
    
    # 初始化累积进度
    cumulative_progress = {
        'total': total_files,
        'scanned': 0
    }
    
    for i, partition in enumerate(partitions):
        # 检查是否需要停止扫描
        if stop_event and stop_event.is_set():
            break
        
        # 扫描当前分区，传递累积进度
        apps = scanDirectory(partition, exclusions, progress_callback, stop_event, cumulative_progress)
        all_chromium_apps.extend(apps)
        
        # 添加到配置中
        for app in apps:
            addDetectedApp(app)
    
    # 调用完成回调
    if complete_callback:
        complete_callback(all_chromium_apps)
    
    return all_chromium_apps

def quickScan(progress_callback=None, complete_callback=None, stop_event=None):
    """快速扫描，只扫描常见应用目录"""
    # 清空已检测应用列表
    clearDetectedApps()
    
    # 常见应用安装目录
    common_dirs = [
        os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'), ''),
        os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), ''),
        os.path.join(os.environ.get('LOCALAPPDATA', r'C:\Users\Default\AppData\Local'), ''),
        os.path.join(os.environ.get('APPDATA', r'C:\Users\Default\AppData\Roaming'), '')
    ]
    
    # 计算总文件数
    total_files = calculateTotalFiles(common_dirs, [])
    
    all_chromium_apps = []
    
    # 初始化累积进度
    cumulative_progress = {
        'total': total_files,
        'scanned': 0
    }
    
    for dir_path in common_dirs:
        # 检查是否需要停止扫描
        if stop_event and stop_event.is_set():
            break
            
        if os.path.exists(dir_path):
            # 扫描当前目录，传递累积进度
            apps = scanDirectory(dir_path, [], progress_callback, stop_event, cumulative_progress)
            all_chromium_apps.extend(apps)
            
            # 添加到配置中
            for app in apps:
                addDetectedApp(app)
    
    # 调用完成回调
    if complete_callback:
        complete_callback(all_chromium_apps)
    
    return all_chromium_apps
