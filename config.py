import os
import json
import time
from utils import getAppDataPath

CONFIG_FILE_NAME = 'config.json'
LOG_FILE_NAME = 'chromiumto.log'

# 默认配置
default_config = {
    'shared_chrome_path': '',
    'detected_apps': [],
    'redirected_apps': [],
    'scan_exclusions': [
        'Windows',
        '$Recycle.Bin',
        'System Volume Information',
        'AppData\\Local\\Temp'
    ]
}

def getConfigPath():
    """获取配置文件路径"""
    return os.path.join(getAppDataPath(), CONFIG_FILE_NAME)

def loadConfig():
    """加载配置文件"""
    config_path = getConfigPath()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置和现有配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif key == 'scan_exclusions':
                        # 确保排除列表不包含Program Files目录
                        # 首先获取默认排除列表
                        default_exclusions = default_config['scan_exclusions']
                        # 创建新的排除列表，只包含默认排除列表中的项目
                        config['scan_exclusions'] = default_exclusions
                return config
        except Exception:
            return default_config.copy()
    else:
        return default_config.copy()

def saveConfig(config):
    """保存配置文件"""
    config_path = getConfigPath()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def updateConfig(key, value):
    """更新配置项"""
    config = loadConfig()
    config[key] = value
    return saveConfig(config)

def getConfig(key, default=None):
    """获取单个配置项"""
    config = loadConfig()
    return config.get(key, default)

def addDetectedApp(app_info):
    """添加已检测的应用"""
    config = loadConfig()
    # 检查是否已存在
    for app in config['detected_apps']:
        if app['path'] == app_info['path']:
            return False
    config['detected_apps'].append(app_info)
    return saveConfig(config)

def addRedirectedApp(app_info):
    """添加已重定向的应用"""
    config = loadConfig()
    # 检查是否已存在
    for app in config['redirected_apps']:
        if app['path'] == app_info['path']:
            return False
    config['redirected_apps'].append(app_info)
    return saveConfig(config)

def removeRedirectedApp(app_path):
    """移除已重定向的应用"""
    config = loadConfig()
    config['redirected_apps'] = [app for app in config['redirected_apps'] if app['path'] != app_path]
    return saveConfig(config)

def clearDetectedApps():
    """清空已检测的应用列表"""
    config = loadConfig()
    config['detected_apps'] = []
    return saveConfig(config)


def getLogPath():
    """获取日志文件路径"""
    return os.path.join(getAppDataPath(), LOG_FILE_NAME)


def writeLog(message, level="INFO"):
    """写入日志到文件"""
    log_path = getLogPath()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        return True
    except Exception:
        return False


def clearLog():
    """清空日志文件"""
    log_path = getLogPath()
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("")
        return True
    except Exception:
        return False


def getLogContent():
    """获取日志内容"""
    log_path = getLogPath()
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def getLogLines(max_lines=1000):
    """获取日志的最后N行"""
    log_path = getLogPath()
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return lines[-max_lines:]
    except Exception:
        return []
