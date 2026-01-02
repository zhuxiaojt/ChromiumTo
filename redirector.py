import os
import shutil
import subprocess
from utils import getAppDataPath
from config import loadConfig, updateConfig, addRedirectedApp, removeRedirectedApp
from downloader import downloadChromiumKernel, getSharedKernelPath, cleanupDownloadFiles

def createSharedChromeDir():
    """创建共享Chrome目录"""
    shared_dir = os.path.join(getAppDataPath(), 'SharedChrome')
    os.makedirs(shared_dir, exist_ok=True)
    return shared_dir

def getSharedChromePath():
    """获取共享Chrome路径"""
    return loadConfig().get('shared_chrome_path', '')

def setSharedChromePath(path):
    """设置共享Chrome路径"""
    return updateConfig('shared_chrome_path', path)

def copyChromeFiles(source_path, target_path):
    """复制Chrome文件到共享目录，支持Electron和CEF框架"""
    try:
        # 确保目标目录存在
        os.makedirs(target_path, exist_ok=True)
        
        # 1. 定义需要复制的Chromium核心文件类型
        chromium_core_files = [
            # Chrome/Edge/Brave核心DLL
            'chrome.dll', 'chrome_elf.dll',
            'msedge.dll', 'msedge_elf.dll',
            'brave.dll', 'brave_elf.dll',
            'libcef.dll', 'cef_sandbox.dll',
            # 多媒体和安全相关
            'widevinecdmadapter.dll', 'widevinecdmadapter64.dll',
            'pdf.dll', 'ui.dll',
            # V8引擎和核心资源
            'v8_context_snapshot.bin',
            'natives_blob.bin', 'snapshot_blob.bin',
            'icudtl.dat',
            # 图形相关核心文件
            'libEGL.dll', 'libGLESv2.dll',
        ]
        
        # 2. 定义需要复制的.pak资源文件
        chromium_pak_files = [
            'chrome_100_percent.pak',
            'chrome_200_percent.pak',
            'resources.pak',
        ]
        
        # 3. 排除的文件模式
        excluded_patterns = [
            # 系统API集文件
            'api-ms-win-',
            'ext-ms-win-',
            # C++运行时库
            'msvcp',
            'vcruntime',
            'concrt140',
            'ucrtbase',
            # 第三方库
            '7-zip.dll',
            'ffmpeg.dll',
            'libzmq-',
            'sqlite3',
            # 图形驱动相关
            'd3dcompiler_',
            'vk_swiftshader.dll',
            'vulkan-1.dll',
            # Qt框架
            'Qt5',
            # 其他非Chromium核心文件
            'adj.dll',
            'aria2c.exe',
            'CrashHunter_PC3.dll',
            'FeverGames',
            'IPCPlugin.dll',
            'mpay.dll',
            'NtUniSdk',
            'OrbitSDK.dll',
            'QCefView.dll',
            'rlottie.dll',
            'TxBugReport.exe',
            'UniCrashReporter.exe',
            'WXWorkWeb.exe',
            'xyvodsdk.dll',
        ]
        
        # 4. 复制核心DLL文件
        for file in chromium_core_files:
            source_file = os.path.join(source_path, file)
            if os.path.exists(source_file):
                # 检查是否是排除的文件
                if any(pattern in file for pattern in excluded_patterns):
                    continue
                target_file = os.path.join(target_path, file)
                shutil.copy2(source_file, target_file)
        
        # 5. 复制匹配的.pak文件
        for file in os.listdir(source_path):
            if file.endswith('.pak'):
                # 检查是否是需要的pak文件
                if any(pak in file for pak in chromium_pak_files):
                    # 检查是否是排除的文件
                    if any(pattern in file for pattern in excluded_patterns):
                        continue
                    source_file = os.path.join(source_path, file)
                    target_file = os.path.join(target_path, file)
                    shutil.copy2(source_file, target_file)
        
        # 6. 复制通用的核心可执行文件
        common_exe = ['chrome.exe', 'electron.exe']
        for file in common_exe:
            source_file = os.path.join(source_path, file)
            if os.path.exists(source_file):
                target_file = os.path.join(target_path, file)
                shutil.copy2(source_file, target_file)
        
        return True
    except Exception as e:
        return False

def createSymlink(source, target):
    """创建符号链接"""
    try:
        # 1. 基本验证
        if not os.path.exists(source):
            return False, f"源文件不存在: {source}"
        
        if not os.path.exists(os.path.dirname(target)):
            return False, f"目标目录不存在: {os.path.dirname(target)}"
        
        # 2. 路径标准化和清理
        # 确保路径是绝对路径
        source = os.path.abspath(source)
        target = os.path.abspath(target)
        
        # 使用Windows格式路径
        source = source.replace('/', '\\')
        target = target.replace('/', '\\')
        
        # 3. 调试信息
        debug_msg = f"创建符号链接: 源={source}, 目标={target}"
        
        # 4. 尝试使用Python内置的os.symlink函数（需要Windows 10+和管理员权限）
        try:
            if os.path.isdir(source):
                os.symlink(source, target, target_is_directory=True)
            else:
                os.symlink(source, target)
            return True, debug_msg
        except OSError as e:
            # 如果内置函数失败，尝试使用mklink命令
            pass
        
        # 5. 准备mklink命令
        # 检查是否是目录
        is_dir = os.path.isdir(source)
        
        # 构建命令，避免引号问题
        if is_dir:
            cmd = ['cmd', '/c', 'mklink', '/D', target, source]
        else:
            cmd = ['cmd', '/c', 'mklink', target, source]
        
        # 6. 执行命令，不使用shell=True，避免引号问题
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        # 7. 检查结果
        if result.returncode == 0:
            return True, f"{debug_msg} - 成功"
        else:
            # 详细的错误信息
            error_msg = result.stderr.strip() if result.stderr.strip() else result.stdout.strip()
            return False, f"{debug_msg} - 失败: {error_msg}"
    except PermissionError as e:
        return False, f"权限不足，无法创建符号链接: {str(e)}"
    except Exception as e:
        return False, f"创建符号链接失败: {str(e)}"

def backupOriginalFiles(app_path):
    """备份原始文件"""
    backup_dir = os.path.join(app_path, 'backup_chrome')
    os.makedirs(backup_dir, exist_ok=True)
    
    try:
        # 只备份Chromium相关的核心文件，不备份系统DLL和非Chromium文件
        # 1. 主要的Chrome/Edge/Brave核心文件
        chromium_core_files = [
            # Chrome/Edge/Brave核心DLL
            'chrome.dll', 'chrome_elf.dll',
            'msedge.dll', 'msedge_elf.dll',
            'brave.dll', 'brave_elf.dll',
            'libcef.dll', 'cef_sandbox.dll',
            'electron.exe',
            # 多媒体和安全相关
            'widevinecdmadapter.dll', 'widevinecdmadapter64.dll',
            'pdf.dll', 'ui.dll',
            # V8引擎和核心资源
            'v8_context_snapshot.bin',
            'natives_blob.bin', 'snapshot_blob.bin',
            'icudtl.dat',
        ]
        
        # 2. 只备份特定的.pak资源文件
        chromium_pak_files = [
            'chrome_100_percent.pak',
            'chrome_200_percent.pak',
            'resources.pak',
            'locales',
        ]
        
        # 3. 合并所有需要备份的文件
        all_files = chromium_core_files.copy()
        
        # 添加匹配的.pak文件
        for file in os.listdir(app_path):
            if file.endswith('.pak') and any(pak in file for pak in chromium_pak_files):
                if file not in all_files:
                    all_files.append(file)
        
        # 4. 排除系统API集文件和其他非Chromium文件
        excluded_patterns = [
            'api-ms-win-',
            'ext-ms-win-',
            'msvcp',
            'vcruntime',
            'd3dcompiler_',
            '7-zip.dll',
            'ffmpeg.dll',
        ]
        
        # 过滤文件列表
        filtered_files = []
        for file in all_files:
            # 检查是否是排除的文件
            if any(pattern in file for pattern in excluded_patterns):
                continue
            filtered_files.append(file)
        
        backed_up_files = []
        for file in filtered_files:
            source_file = os.path.join(app_path, file)
            if os.path.exists(source_file):
                target_file = os.path.join(backup_dir, file)
                shutil.copy2(source_file, target_file)
                backed_up_files.append(file)
        
        return backed_up_files
    except Exception as e:
        return []

def restoreOriginalFiles(app_path):
    """恢复原始文件"""
    backup_dir = os.path.join(app_path, 'backup_chrome')
    
    if not os.path.exists(backup_dir):
        return False
    
    try:
        # 恢复所有备份的文件
        for file in os.listdir(backup_dir):
            backup_file = os.path.join(backup_dir, file)
            original_file = os.path.join(app_path, file)
            
            # 删除符号链接或现有文件
            if os.path.exists(original_file):
                if os.path.islink(original_file):
                    os.unlink(original_file)
                else:
                    os.remove(original_file)
            
            # 恢复原始文件
            shutil.copy2(backup_file, original_file)
        
        # 删除备份目录
        shutil.rmtree(backup_dir)
        return True
    except Exception:
        return False

def redirectAppToSharedChrome(app_info):
    """将应用重定向到共享Chrome内核"""
    try:
        shared_chrome_path = getSharedChromePath()
        if not shared_chrome_path or not os.path.exists(shared_chrome_path):
            return False, "共享Chrome路径未设置或不存在"
        
        app_path = app_info['path']
        
        # 检查应用路径是否存在
        if not os.path.exists(app_path):
            return False, f"应用路径不存在: {app_path}"
        
        # 检查是否已经重定向
        backup_dir = os.path.join(app_path, 'backup_chrome')
        if os.path.exists(backup_dir):
            return False, "应用已经被重定向"
        
        # 1. 备份原始文件
        backed_up_files = backupOriginalFiles(app_path)
        if not backed_up_files:
            return False, "无法备份原始文件，可能没有找到要备份的文件"
        
        # 2. 创建符号链接
        failed_files = []
        success_files = []
        for file in backed_up_files:
            source = os.path.join(shared_chrome_path, file)
            target = os.path.join(app_path, file)
            
            # 检查源文件是否存在
            if not os.path.exists(source):
                # 跳过不存在的源文件，但继续处理其他文件
                failed_files.append(f"{file} (源文件不存在)")
                continue
            
            try:
                # 检查目标文件是否存在
                if not os.path.exists(target):
                    failed_files.append(f"{file} (目标文件不存在，可能已被删除)")
                    continue
                
                # 删除原始文件
                os.remove(target)
                
                # 创建符号链接
                success, error_msg = createSymlink(source, target)
                if success:
                    success_files.append(file)
                else:
                    failed_files.append(f"{file} (创建符号链接失败: {error_msg})")
            except PermissionError as e:
                failed_files.append(f"{file} (权限不足: {str(e)})")
            except FileNotFoundError as e:
                failed_files.append(f"{file} (文件未找到: {str(e)})")
            except Exception as e:
                failed_files.append(f"{file} (未知错误: {str(e)})")
        
        # 如果所有文件都失败了，恢复备份
        if len(failed_files) == len(backed_up_files):
            restoreOriginalFiles(app_path)
            return False, f"所有文件都无法创建符号链接: {'; '.join(failed_files)}"
        
        # 3. 更新配置
        addRedirectedApp(app_info)
        
        if failed_files:
            return True, f"重定向部分成功 ({len(success_files)}/{len(backed_up_files)}): {'; '.join(failed_files)}"
        else:
            return True, f"重定向成功 ({len(success_files)}/{len(backed_up_files)})"
    except Exception as e:
        # 恢复备份
        app_path = app_info.get('path', '')
        if app_path and os.path.exists(os.path.join(app_path, 'backup_chrome')):
            restoreOriginalFiles(app_path)
        return False, f"重定向失败: {str(e)}"

def redirectAllApps():
    """重定向所有检测到的应用"""
    config = loadConfig()
    detected_apps = config['detected_apps']
    results = []
    
    for app in detected_apps:
        success, message = redirectAppToSharedChrome(app)
        results.append({
            'app': app,
            'success': success,
            'message': message
        })
    
    return results

def restoreAppFromSharedChrome(app_info):
    """取消应用的重定向"""
    app_path = app_info['path']
    
    try:
        # 恢复原始文件
        if restoreOriginalFiles(app_path):
            # 更新配置
            removeRedirectedApp(app_path)
            return True, "恢复成功"
        else:
            return False, "无法恢复原始文件"
    except Exception as e:
        return False, f"恢复失败: {str(e)}"

def restoreAllApps():
    """取消所有应用的重定向"""
    config = loadConfig()
    redirected_apps = config['redirected_apps']
    results = []
    
    for app in redirected_apps:
        success, message = restoreAppFromSharedChrome(app)
        results.append({
            'app': app,
            'success': success,
            'message': message
        })
    
    return results

def initializeSharedChromeFromApp(app_info):
    """从现有应用初始化共享Chrome"""
    app_path = app_info['path']
    shared_dir = createSharedChromeDir()
    
    # 复制Chrome文件到共享目录
    if copyChromeFiles(app_path, shared_dir):
        # 设置共享Chrome路径
        if setSharedChromePath(shared_dir):
            return True, "共享Chrome初始化成功"
        else:
            return False, "无法设置共享Chrome路径"
    else:
        return False, "无法复制Chrome文件到共享目录"

def getBackupDirs():
    """获取所有备份目录"""
    config = loadConfig()
    backup_dirs = []
    
    # 检查已重定向的应用
    for app in config['redirected_apps']:
        backup_dir = os.path.join(app['path'], 'backup_chrome')
        if os.path.exists(backup_dir):
            # 获取备份大小
            backup_size = 0
            for file in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, file)
                if os.path.isfile(file_path):
                    backup_size += os.path.getsize(file_path)
            
            backup_dirs.append({
                'app': app,
                'backup_path': backup_dir,
                'size': backup_size
            })
    
    return backup_dirs

def deleteBackup(app_path):
    """删除特定应用的备份"""
    backup_dir = os.path.join(app_path, 'backup_chrome')
    if os.path.exists(backup_dir):
        try:
            shutil.rmtree(backup_dir)
            return True, "备份删除成功"
        except Exception as e:
            return False, f"备份删除失败: {str(e)}"
    return False, "备份目录不存在"

def deleteAllBackups():
    """删除所有备份"""
    backup_dirs = getBackupDirs()
    results = []
    
    for backup in backup_dirs:
        success, message = deleteBackup(backup['app']['path'])
        results.append({
            'app': backup['app'],
            'success': success,
            'message': message
        })
    
    return results

def getBackupInfo(app_path):
    """获取备份详细信息"""
    backup_dir = os.path.join(app_path, 'backup_chrome')
    if not os.path.exists(backup_dir):
        return None
    
    files = []
    total_size = 0
    
    for file in os.listdir(backup_dir):
        file_path = os.path.join(backup_dir, file)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            total_size += size
            files.append({
                'name': file,
                'size': size
            })
    
    return {
        'backup_path': backup_dir,
        'files': files,
        'total_size': total_size
    }

def autoDownloadSharedKernel(progress_callback=None):
    """自动下载并设置共享内核"""
    # 下载Chromium内核
    success, result = downloadChromiumKernel(progress_callback)
    
    if success:
        # 设置共享内核路径
        setSharedChromePath(result)
        
        # 清理下载文件
        cleanupDownloadFiles()
        
        return True, "共享内核下载并设置成功"
    else:
        return False, f"共享内核下载失败: {result}"
