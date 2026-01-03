import tkinter as tk
import os
import ctypes
import threading
import requests
from tkinter import ttk, messagebox, filedialog, PhotoImage
from utils import getAppDataPath, calculateDirectorySize, calculateChromeFilesSize, formatFileSize
from config import loadConfig, writeLog
from scanner import scanSystem, quickScan
from redirector import (
    getSharedChromePath, setSharedChromePath,
    redirectAppToSharedChrome, restoreAppFromSharedChrome,
    redirectAllApps, restoreAllApps,
    initializeSharedChromeFromApp,
    getBackupDirs, deleteBackup, deleteAllBackups,
    autoDownloadSharedKernel
)
from plyer import notification
from PIL import Image
import pystray
import sys

# 当前版本
CURRENT_VERSION = [1, 1, 2]

# 版本检查URL
VERSION_CHECK_URL = 'https://zhuxiaojt.github.io/api/chromiumto/last_version.json'

# 版本检查结果
version_check_result = {
    'is_new_version': False,
    'message': '',
    'checked': False
}

# 检查是否以管理员权限运行
def isAdmin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# 检查版本
def checkVersion():
    """检查是否有新版本"""
    global version_check_result
    
    try:
        # 设置超时时间，跳过SSL证书验证（解决证书验证失败问题）
        response = requests.get(VERSION_CHECK_URL, timeout=5, verify=False)
        response.raise_for_status()
        
        # 解析JSON数据
        version_data = response.json()
        remote_version = version_data.get('VList', [0, 0, 0])
        
        # 比较版本号
        is_new = False
        for i in range(3):
            if remote_version[i] > CURRENT_VERSION[i]:
                is_new = True
                break
            elif remote_version[i] < CURRENT_VERSION[i]:
                break
        
        if is_new:
            version_check_result = {
                'is_new_version': True,
                'message': '当前软件不是最新版本，打开“关于”界面查看详情',
                'checked': True
            }
        else:
            version_check_result = {
                'is_new_version': False,
                'message': '',
                'checked': True
            }
        
    except requests.exceptions.Timeout:
        writeLog("版本检查超时", level="WARNING")
        version_check_result['checked'] = True
        version_check_result['message'] = '版本检查失败'
    except requests.exceptions.RequestException as e:
        writeLog(f"版本检查失败: {str(e)}", level="ERROR")
        version_check_result['checked'] = True
        version_check_result['message'] = '版本检查失败'
    except Exception as e:
        writeLog(f"版本检查异常: {str(e)}", level="ERROR")
        version_check_result['checked'] = True
        version_check_result['message'] = '版本检查失败'
    finally:
        # 更新UI
        updateVersionLabel()
        # 1分钟后重新检查版本
        root.after(60000,lambda: threading.Thread(target=checkVersion, daemon=True).start())

# 更新版本标签
def updateVersionLabel():
    """更新版本标签"""
    if 'version_label' in globals():
        if version_check_result['is_new_version']:
            version_label.config(
                text=version_check_result['message'],
                foreground='darkred',
                font=('Arial', 9, 'bold')
            )
        else:
            version_label.config(
                text=version_check_result['message'],
                foreground='black',
                font=('Arial', 9)
            )

# 请求管理员权限重启
def restartAsAdmin():
    """以管理员权限重启应用"""
    if messagebox.askyesno("需要管理员权限", "执行此操作需要管理员权限，是否重启应用？"):
        try:
            # 重启应用，请求管理员权限
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, ' '.join(sys.argv), None, 1
            )
            # 退出当前应用
            sys.exit()
        except Exception as e:
            writeLog(f"重启应用失败: {str(e)}", level="ERROR")
            messagebox.showerror("错误", f"无法重启应用: {str(e)}")

# 全局变量
root = None
app_tree = None
status_var = None
scan_thread = None
stop_scan_event = None
progress_var = None
progress_bar = None
progress_frame = None
shared_dir_label = None
disk_space_label = None
# 系统托盘相关变量
tray_icon = None
app_in_tray = False

# 颜色配置 - 完全统一的白色调
WHITE = '#FFFFFF'  # 纯白色
LIGHT_GRAY = '#F0F0F0'  # 浅灰色，仅用于需要区分的地方
TEXT_COLOR = '#333333'  # 文本颜色，保持统一

def initUI():
    """初始化UI"""
    global root, app_tree, status_var, progress_var, progress_bar, shared_dir_label, disk_space_label
    
    # 创建主窗口
    root = tk.Tk()
    root.title("ChromiumTo - 共享Chromium内核工具")
    root.geometry("1000x700")
    root.resizable(True, True)
    root.iconphoto(True,PhotoImage(file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')))
    root.minsize(1000, 700)  # 设置窗口最小大小
    
    # 使用vista主题，在Windows上更现代，背景色更接近白色
    style = ttk.Style()
    style.theme_use('vista')
    
    # 统一所有元素的背景色和边框色为纯白色
    # 确保在vista主题下，所有元素的背景色都是纯白色
    style.configure('TFrame', background=WHITE, borderwidth=0, relief='flat')
    style.configure('TLabelFrame', 
                    background=WHITE, 
                    foreground=TEXT_COLOR,
                    borderwidth=1,
                    relief='flat')
    style.configure('TLabel', background=WHITE, foreground=TEXT_COLOR)
    style.configure('TButton', 
                    background=WHITE, 
                    foreground=TEXT_COLOR,
                    borderwidth=1,
                    relief='flat')
    style.configure('Treeview', 
                    background=WHITE, 
                    fieldbackground=WHITE, 
                    foreground=TEXT_COLOR,
                    borderwidth=1,
                    relief='flat')
    style.configure('Treeview.Heading', 
                    background=WHITE, 
                    foreground=TEXT_COLOR,
                    borderwidth=0)
    style.configure('TScrollbar', background=WHITE, borderwidth=0)
    # 进度条：使用浅灰色作为进度部分，纯白色作为槽部分，形成微妙对比
    style.configure('TProgressbar', 
                    background=LIGHT_GRAY, 
                    troughcolor=WHITE,
                    borderwidth=1)
    
    # 针对vista主题，额外设置一些样式，确保背景色为纯白色
    style.configure('.', background=WHITE)  # 设置所有元素的默认背景色
    
    # 设置Treeview选中状态：使用浅灰色作为选中背景，保持文本颜色统一
    style.map('Treeview', 
              background=[('selected', LIGHT_GRAY)],
              foreground=[('selected', TEXT_COLOR)])
    
    # 设置按钮交互状态：保持纯白色调，仅在悬停时使用浅灰色
    style.map('TButton', 
              background=[('active', LIGHT_GRAY)],
              foreground=[('active', TEXT_COLOR)])
    
    # 设置滚动条滑块颜色，使用浅灰色
    style.configure('Vertical.TScrollbar', 
                    background=WHITE, 
                    troughcolor=WHITE,
                    arrowcolor=TEXT_COLOR)
    style.configure('Horizontal.TScrollbar', 
                    background=WHITE, 
                    troughcolor=WHITE,
                    arrowcolor=TEXT_COLOR)
    
    # 设置背景色为白色
    root.configure(background=WHITE)
    
    # 创建主框架
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # 顶部信息栏
    info_frame = ttk.LabelFrame(main_frame, text="系统信息")
    info_frame.pack(fill=tk.X, pady=(0, 15))
    
    # 共享目录显示
    shared_dir_label = ttk.Label(info_frame, text="")
    shared_dir_label.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
    
    # 磁盘空间显示
    disk_space_label = ttk.Label(info_frame, text="")
    disk_space_label.pack(side=tk.RIGHT, padx=10, pady=10)
    
    # 更新信息栏
    updateInfoBar()
    
    # 扫描控制区域
    scan_frame = ttk.LabelFrame(main_frame, text="扫描控制")
    scan_frame.pack(fill=tk.X, pady=(0, 15))
    
    # 扫描按钮组
    scan_buttons = ttk.Frame(scan_frame)
    scan_buttons.pack(side=tk.LEFT, padx=10, pady=10)
    
    ttk.Button(scan_buttons, text="快速扫描", command=startQuickScan).pack(side=tk.LEFT, padx=5)
    ttk.Button(scan_buttons, text="全盘扫描", command=startFullScan).pack(side=tk.LEFT, padx=5)
    ttk.Button(scan_buttons, text="停止扫描", command=stopScan).pack(side=tk.LEFT, padx=5)
    ttk.Button(scan_buttons, text="清空列表", command=clearList).pack(side=tk.LEFT, padx=5)
    
    # 进度条框架，初始隐藏
    global progress_frame, progress_var, progress_bar
    progress_frame = ttk.Frame(scan_frame)
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var)
    progress_bar.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=10)
    
    progress_label = ttk.Label(progress_frame, text="0%", width=5)
    progress_label.pack(side=tk.LEFT, padx=5)
    
    # 初始隐藏进度条
    hideProgressBar()
    
    # 应用列表区域
    tree_frame = ttk.LabelFrame(main_frame, text="已检测到的Chromium应用")
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    
    # 创建Treeview，支持多选 - 调整size列位置到path右边
    columns = ("name", "version", "path", "size", "status")
    app_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode='extended')
    
    # 设置列标题
    app_tree.heading("name", text="应用名称")
    app_tree.heading("version", text="内核版本")
    app_tree.heading("path", text="安装路径")
    app_tree.heading("size", text="占用空间")
    app_tree.heading("status", text="状态")
    
    # 设置列宽
    app_tree.column("name", width=150, anchor=tk.W)
    app_tree.column("version", width=120, anchor=tk.CENTER)
    app_tree.column("path", width=400, anchor=tk.W)
    app_tree.column("size", width=100, anchor=tk.E)  # 使用tk.E代替tk.RIGHT
    app_tree.column("status", width=100, anchor=tk.CENTER)
    
    # 添加滚动条 - 只显示垂直滚动条
    scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=app_tree.yview)
    app_tree.configure(yscroll=scrollbar_y.set)
    
    app_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 绑定双击事件
    app_tree.bind("<Double-1>", onDoubleClick)
    
    # 操作按钮区域
    action_frame = ttk.LabelFrame(main_frame, text="操作")
    action_frame.pack(fill=tk.X, pady=(0, 15))
    
    action_buttons = ttk.Frame(action_frame)
    action_buttons.pack(fill=tk.X, padx=10, pady=10)
    
    ttk.Button(action_buttons, text="重定向所选", command=redirectSelectedApps).pack(side=tk.LEFT, padx=5)
    ttk.Button(action_buttons, text="恢复所选", command=restoreSelectedApps).pack(side=tk.LEFT, padx=5)
    ttk.Button(action_buttons, text="重定向全部", command=redirectAll).pack(side=tk.LEFT, padx=5)
    ttk.Button(action_buttons, text="恢复全部", command=restoreAll).pack(side=tk.LEFT, padx=5)
    ttk.Button(action_buttons, text="从所选初始化共享内核", command=initSharedChromeFromSelected).pack(side=tk.LEFT, padx=5)
    ttk.Button(action_buttons, text="自动下载共享内核", command=downloadSharedKernel).pack(side=tk.RIGHT, padx=5)
    ttk.Button(action_buttons, text="选择共享内核路径", command=selectSharedChromePath).pack(side=tk.RIGHT, padx=5)
    ttk.Button(action_buttons, text="清除备份", command=clearBackups).pack(side=tk.RIGHT, padx=5)
    
    # 帮助按钮区域
    help_frame = ttk.LabelFrame(main_frame, text="帮助")
    help_frame.pack(fill=tk.X, pady=(0, 15))
    
    help_buttons = ttk.Frame(help_frame)
    help_buttons.pack(fill=tk.X, padx=10, pady=10)
    
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')
    logo_img = PhotoImage(file=logo_path)
    logo_label = ttk.Label(help_buttons, image=logo_img)
    logo_label.image = logo_img
    logo_label.pack(side=tk.LEFT, padx=5)
    ttk.Button(help_buttons, text="使用说明", command=lambda: openHelpPage("help.html")).pack(side=tk.RIGHT, padx=5)
    ttk.Button(help_buttons, text="关于", command=lambda: openHelpPage("about.html")).pack(side=tk.RIGHT, padx=5)
    ttk.Button(help_buttons, text="查看日志", command=showLogWindow).pack(side=tk.RIGHT, padx=5)
    
    # 版本信息标签
    global version_label
    version_label = ttk.Label(help_buttons, text="")
    version_label.pack(side=tk.RIGHT, padx=5)
    
    # 状态栏
    status_var = tk.StringVar()
    status_var.set("就绪")
    status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # 初始加载数据
    refreshAppList()
    
    # 启动版本检查线程
    threading.Thread(target=checkVersion, daemon=True).start()
    
    # 绑定窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", onClose)
    
    # 运行主循环
    root.mainloop()

def showLogWindow():
    """显示日志窗口"""
    from config import getLogContent, clearLog
    
    # 创建日志窗口
    log_window = tk.Toplevel(root)
    log_window.title("日志查看")
    log_window.geometry("800x600")
    log_window.resizable(True, True)
    log_window.transient(root)
    log_window.config(bg='white')
    
    # 创建文本框用于显示日志
    log_text = tk.Text(log_window, wrap=tk.WORD, font=('Consolas', 10))
    log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 添加滚动条
    scrollbar = ttk.Scrollbar(log_text, command=log_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.config(yscrollcommand=scrollbar.set)
    
    def refreshLog():
        """刷新日志内容"""
        log_content = getLogContent()
        log_text.delete(1.0, tk.END)
        log_text.insert(tk.END, log_content)
        log_text.see(tk.END)
    
    def clearLogContent():
        """清空日志"""
        if messagebox.askyesno("提示", "确定要清空日志吗？"):
            clearLog()
            refreshLog()
    
    # 按钮框架
    button_frame = ttk.Frame(log_window)
    button_frame.pack(fill=tk.X, padx=10, pady=10)
    
    # 刷新按钮
    refresh_button = ttk.Button(button_frame, text="刷新", command=refreshLog)
    refresh_button.pack(side=tk.LEFT, padx=5)
    
    # 清空按钮
    clear_button = ttk.Button(button_frame, text="清空", command=clearLogContent)
    clear_button.pack(side=tk.LEFT, padx=5)
    
    # 关闭按钮
    close_button = ttk.Button(button_frame, text="关闭", command=log_window.destroy)
    close_button.pack(side=tk.RIGHT, padx=5)
    
    # 初始加载日志
    refreshLog()


def updateInfoBar():
    """更新信息栏"""
    # 更新共享目录显示
    shared_path = getSharedChromePath()
    if shared_path:
        shared_dir_label.config(text=f"共享内核目录: {shared_path}")
    else:
        shared_dir_label.config(text="共享内核目录: 未设置")
    
    # 更新磁盘空间显示
    updateDiskSpaceInfo()

def updateTotalSpaceInfo():
    """更新总占用空间信息"""
    config = loadConfig()
    redirected_apps = config['redirected_apps']
    
    # 计算已重定向应用的总占用空间
    total_redirected_size = 0
    for app in redirected_apps:
        total_redirected_size += app.get('size', 0)
    
    # 更新信息栏
    shared_path = getSharedChromePath()
    updateDiskSpaceInfo(total_redirected_size)


def updateDiskSpaceInfo(total_redirected_size=0):
    """更新磁盘空间信息 - 只显示已重定向应用节省的空间"""
    config = loadConfig()
    detected_apps = config['detected_apps']
    redirected_apps = config['redirected_apps']
    shared_path = getSharedChromePath()
    
    # 计算未重定向应用的总占用空间
    total_unredirected_size = 0
    for app in detected_apps:
        if app['path'] not in [redirected_app['path'] for redirected_app in redirected_apps]:
            total_unredirected_size += app.get('size', 0)
    
    if not shared_path:
        # 如果没有设置共享内核路径，显示总占用空间
        total_space = total_unredirected_size + total_redirected_size
        disk_space_label.config(text=f"总占用空间: {formatFileSize(total_space)}")
        return
    
    # 计算共享内核大小
    shared_size = calculateDirectorySize(shared_path)
    
    # 计算已重定向应用节省的空间
    if total_redirected_size > 0:
        saved_space = total_redirected_size - shared_size
        if saved_space < 0:
            saved_space = 0
        # 总占用空间 = 未重定向应用空间 + 共享内核空间
        total_space = total_unredirected_size + shared_size
        disk_space_label.config(text=f"总占用空间: {formatFileSize(total_space)} | 已节省空间: {formatFileSize(saved_space)}")
    else:
        # 如果没有重定向应用，只显示未重定向应用空间
        disk_space_label.config(text=f"总占用空间: {formatFileSize(total_unredirected_size)}")

def updateStatus(message):
    """更新状态栏"""
    if status_var:
        status_var.set(message)
        root.update_idletasks()

def updateProgress(current, total):
    """更新进度条"""
    if current > 0 and total > 0:
        percent = (current / total) * 100
        progress_var.set(percent)
        progress_bar.update()
        # 更新进度百分比标签
        for child in progress_bar.master.winfo_children():
            if isinstance(child, ttk.Label) and child['width'] == 5:
                child.config(text=f"{int(percent)}%")
                break
    root.update_idletasks()

def addAppToTree(app_info):
    """添加应用到列表"""
    # 检查是否为共享内核
    shared_path = getSharedChromePath()
    if shared_path and app_info['path'] == shared_path:
        status = "作为共享内核使用"
        size_display = "-"
    else:
        # 检查是否已经重定向
        config = loadConfig()
        redirected_paths = [app['path'] for app in config['redirected_apps']]
        status = "已重定向" if app_info['path'] in redirected_paths else "未重定向"
        
        # 根据重定向状态显示占用空间
        if status == "已重定向":
            size_display = "-"
        else:
            size = app_info.get('size', 0)
            size_display = formatFileSize(size)
    
    app_tree.insert("", tk.END, values=(
        app_info['name'],
        app_info['version'],
        app_info['path'],
        size_display,
        status
    ))

def clearAppTree():
    """清空应用列表"""
    for item in app_tree.get_children():
        app_tree.delete(item)

def refreshAppList():
    """刷新应用列表"""
    clearAppTree()
    config = loadConfig()
    for app in config['detected_apps']:
        addAppToTree(app)
    updateStatus(f"已加载 {len(config['detected_apps'])} 个应用")
    updateInfoBar()

def onScanProgress(data):
    """扫描进度回调"""
    if isinstance(data, tuple) and len(data) >= 3 and data[2] == 'scan':
        # 扫描进度信息
        current, total, _, current_dir = data
        updateProgress(current, total)
        updateStatus(f"正在扫描: {current_dir}")
    else:
        # 发现应用信息
        app_info = data
        addAppToTree(app_info)
        updateStatus(f"发现应用: {app_info['name']}")
        # 更新总占用空间显示
        updateTotalSpaceInfo()

def hideProgressBar():
    """隐藏进度条"""
    progress_frame.pack_forget()

def showProgressBar():
    """显示进度条"""
    progress_frame.pack(fill=tk.X, padx=10, pady=10, expand=True)

def onScanComplete(apps):
    """扫描完成回调"""
    updateProgress(100, 100)
    updateStatus(f"扫描完成，共发现 {len(apps)} 个Chromium应用")
    updateTotalSpaceInfo()
    hideProgressBar()
    
    # 如果应用在系统托盘，发送通知
    if app_in_tray:
        notification.notify(
            title='任务完成！',
            message='扫描任务已完成，可以返回ChromiumTo查看',
            app_name='ChromiumTo'
        )

def startQuickScan():
    """开始快速扫描"""
    global scan_thread, stop_scan_event
    
    if scan_thread and scan_thread.is_alive():
        writeLog("扫描正在进行中", level="WARNING")
        updateStatus("扫描正在进行中")
        return
    
    clearAppTree()
    updateStatus("开始快速扫描...")
    showProgressBar()
    
    # 创建停止事件
    stop_scan_event = threading.Event()
    
    scan_thread = threading.Thread(
        target=quickScan,
        kwargs={
            'progress_callback': onScanProgress,
            'complete_callback': onScanComplete,
            'stop_event': stop_scan_event
        },
        daemon=True
    )
    scan_thread.start()

def startFullScan():
    """开始全盘扫描"""
    global scan_thread, stop_scan_event
    
    if scan_thread and scan_thread.is_alive():
        writeLog("扫描正在进行中", level="WARNING")
        updateStatus("扫描正在进行中")
        return
    
    if messagebox.askyesno("提示", "全盘扫描可能需要较长时间，确定要继续吗？"):
        clearAppTree()
        updateStatus("开始全盘扫描...")
        showProgressBar()
        
        # 创建停止事件
        stop_scan_event = threading.Event()
        
        scan_thread = threading.Thread(
            target=scanSystem,
            kwargs={
                'progress_callback': onScanProgress,
                'complete_callback': onScanComplete,
                'stop_event': stop_scan_event
            },
            daemon=True
        )
        scan_thread.start()

def stopScan():
    """停止扫描"""
    global stop_scan_event, scan_thread
    
    if scan_thread and scan_thread.is_alive() and stop_scan_event:
        stop_scan_event.set()
        updateStatus("正在停止扫描...")
    else:
        writeLog("没有正在进行的扫描", level="INFO")
        updateStatus("没有正在进行的扫描")


def showMainWindow(icon, item):
    """显示主界面"""
    global app_in_tray
    if app_in_tray:
        app_in_tray = False
        root.deiconify()
    else:
        root.lift()


def openHelpPage(page):
    """在浏览器中打开帮助页面"""
    try:
        # 构建HTML文件的完整路径
        help_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), page)
        # 使用浏览器打开HTML文件
        os.startfile(help_file_path)
        updateStatus(f"已打开{page}帮助页面")
    except Exception as e:
        messagebox.showerror("错误", f"无法打开帮助页面: {str(e)}")
        updateStatus(f"打开帮助页面失败: {str(e)}")


def exitApp(icon, item):
    """退出应用"""
    global app_in_tray
    app_in_tray = False
    if icon:
        icon.stop()
    if root:
        root.destroy()
    sys.exit()


def createTrayIcon():
    """创建系统托盘图标"""
    global tray_icon
    # 创建图标
    image = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico'))
    # 创建菜单
    menu = pystray.Menu(
        pystray.MenuItem("显示主界面", showMainWindow),
        pystray.MenuItem("停止扫描", stopScan),
        pystray.MenuItem("退出应用", exitApp)
    )
    # 创建图标
    tray_icon = pystray.Icon("ChromiumTo", image, "ChromiumTo", menu)
    # 启动托盘图标
    tray_icon.run()


def onClose():
    """窗口关闭事件处理"""
    global app_in_tray, tray_icon
    
    if scan_thread and scan_thread.is_alive():
        # 使用askyesnocancel询问用户
        result = messagebox.askyesnocancel("提示", "当前有扫描任务正在进行，是否为您将应用最小化到系统托盘？")
        if result is None:
            return  # 用户点击取消，不关闭窗口
        elif result:
            # 最小化到托盘
            app_in_tray = True
            root.withdraw()
            # 如果还没有创建托盘图标，创建一个
            if not tray_icon:
                threading.Thread(target=createTrayIcon, daemon=True).start()
        else:
            # 直接退出
            exitApp(None, None)
    else:
        # 没有正在进行的任务，直接退出
        exitApp(None, None)


def clearList():
    """清空列表"""
    if messagebox.askyesno("提示", "确定要清空当前列表吗？"):
        clearAppTree()
        updateStatus("列表已清空")


def onDoubleClick(event):
    """双击打开应用所在目录"""
    item = app_tree.selection()[0]
    path = app_tree.item(item, "values")[2]
    if os.path.exists(path):
        os.startfile(path)


def getSelectedApps():
    """获取选中的应用"""
    selected_items = app_tree.selection()
    selected_apps = []
    config = loadConfig()
    
    for item in selected_items:
        values = app_tree.item(item, "values")
        app_path = values[2]  # path列现在是索引2
        # 查找对应的应用信息
        for app in config['detected_apps']:
            if app['path'] == app_path:
                selected_apps.append(app)
                break
    
    return selected_apps

def redirectSelectedApps():
    """重定向所选应用"""
    
    selected_apps = getSelectedApps()
    if not selected_apps:
        writeLog("请选择要重定向的应用", level="WARNING")
        updateStatus("请选择要重定向的应用")
        return
    
    # 检查共享内核路径
    shared_path = getSharedChromePath()
    if not shared_path:
        writeLog("请先设置共享内核路径", level="WARNING")
        updateStatus("请先设置共享内核路径")
        return
    
    # 检查是否以管理员权限运行
    if not isAdmin():
        # 检查目标路径是否需要管理员权限
        for app in selected_apps:
            if app['path'].startswith('C:\\Program Files') or app['path'].startswith('C:\\Windows'):
                writeLog("需要管理员权限执行重定向操作", level="WARNING")
                restartAsAdmin()
                return
    
    success_count = 0
    fail_count = 0
    fail_messages = []
    
    # 记录日志
    writeLog(f"开始重定向所选应用，共 {len(selected_apps)} 个")
    
    for app in selected_apps:
        writeLog(f"正在重定向应用：{app['name']} ({app['path']})")
        success, message = redirectAppToSharedChrome(app)
        if success:
            success_count += 1
            writeLog(f"重定向成功：{app['name']}")
        else:
            fail_count += 1
            # 保存失败信息
            fail_messages.append(f"{app['name']}: {message}")
            writeLog(f"重定向失败：{app['name']} - {message}", level="ERROR")
    
    # 刷新列表
    refreshAppList()
    
    # 记录最终结果到日志
    result_message = f"重定向完成：成功 {success_count} 个，失败 {fail_count} 个"
    writeLog(result_message)
    if fail_messages:
        writeLog("失败详情：", level="ERROR")
        for msg in fail_messages:
            writeLog(f"- {msg}", level="ERROR")
    
    # 结果已记录到日志，不显示弹窗
    writeLog(f"用户已查看重定向结果：{result_message}")
    updateStatus(result_message)

def restoreSelectedApps():
    """恢复所选应用"""
    
    selected_apps = getSelectedApps()
    if not selected_apps:
        writeLog("请选择要恢复的应用", level="WARNING")
        updateStatus("请选择要恢复的应用")
        return
    
    # 检查是否以管理员权限运行
    if not isAdmin():
        # 检查目标路径是否需要管理员权限
        for app in selected_apps:
            if app['path'].startswith('C:\Program Files') or app['path'].startswith('C:\Windows'):
                writeLog("需要管理员权限执行恢复操作", level="WARNING")
                restartAsAdmin()
                return
    
    success_count = 0
    fail_count = 0
    
    # 记录日志
    writeLog(f"开始恢复所选应用，共 {len(selected_apps)} 个")
    
    for app in selected_apps:
        writeLog(f"正在恢复应用：{app['name']} ({app['path']})")
        success, message = restoreAppFromSharedChrome(app)
        if success:
            success_count += 1
            writeLog(f"恢复成功：{app['name']}")
        else:
            fail_count += 1
            writeLog(f"恢复失败：{app['name']} - {message}", level="ERROR")
    
    # 刷新列表
    refreshAppList()
    
    # 记录最终结果到日志
    result_message = f"恢复完成：成功 {success_count} 个，失败 {fail_count} 个"
    writeLog(result_message)
    
    # 结果已记录到日志，不显示弹窗
    writeLog(f"用户已查看恢复结果：{result_message}")
    updateStatus(result_message)

def redirectAll():
    """重定向所有应用"""
    
    # 检查共享内核路径
    shared_path = getSharedChromePath()
    if not shared_path:
        writeLog("请先设置共享内核路径", level="WARNING")
        updateStatus("请先设置共享内核路径")
        return
    
    # 检查是否需要管理员权限
    config = loadConfig()
    need_admin = False
    for app in config['detected_apps']:
        if app['path'].startswith('C:\Program Files') or app['path'].startswith('C:\Windows'):
            need_admin = True
            break
    
    if need_admin and not isAdmin():
        writeLog("需要管理员权限执行重定向操作", level="WARNING")
        restartAsAdmin()
        return
    
    if messagebox.askyesno("提示", "确定要重定向所有检测到的应用吗？"):
        writeLog("开始重定向所有检测到的应用")
        results = redirectAllApps()
        
        success_count = sum(1 for r in results if r['success'])
        fail_count = sum(1 for r in results if not r['success'])
        
        # 记录详细结果到日志
        writeLog(f"重定向全部完成：成功 {success_count} 个，失败 {fail_count} 个")
        if fail_count > 0:
            writeLog("失败详情：", level="ERROR")
            for result in results:
                if not result['success']:
                    app = result['app']
                    writeLog(f"- {app['name']}: {result['message']}", level="ERROR")
        
        # 刷新列表
        refreshAppList()
        
        # 结果已记录到日志，不显示弹窗
        writeLog(f"用户已查看全部重定向结果：成功 {success_count} 个，失败 {fail_count} 个")
        updateStatus(f"重定向全部完成：成功 {success_count} 个，失败 {fail_count} 个")

def restoreAll():
    """恢复所有应用"""
    
    # 检查是否需要管理员权限
    config = loadConfig()
    need_admin = False
    for app in config['redirected_apps']:
        if app['path'].startswith('C:\Program Files') or app['path'].startswith('C:\Windows'):
            need_admin = True
            break
    
    if need_admin and not isAdmin():
        writeLog("需要管理员权限执行恢复操作", level="WARNING")
        restartAsAdmin()
        return
    
    if messagebox.askyesno("提示", "确定要恢复所有已重定向的应用吗？"):
        writeLog("开始恢复所有已重定向的应用")
        results = restoreAllApps()
        
        success_count = sum(1 for r in results if r['success'])
        fail_count = sum(1 for r in results if not r['success'])
        
        # 记录详细结果到日志
        writeLog(f"恢复全部完成：成功 {success_count} 个，失败 {fail_count} 个")
        if fail_count > 0:
            writeLog("失败详情：", level="ERROR")
            for result in results:
                if not result['success']:
                    app = result['app']
                    writeLog(f"- {app['name']}: {result['message']}", level="ERROR")
        
        # 刷新列表
        refreshAppList()
        
        # 结果已记录到日志，不显示弹窗
        writeLog(f"用户已查看全部恢复结果：成功 {success_count} 个，失败 {fail_count} 个")
        updateStatus(f"恢复全部完成：成功 {success_count} 个，失败 {fail_count} 个")

def selectSharedChromePath():
    """选择共享内核路径"""
    path = filedialog.askdirectory(title="选择共享Chromium内核目录")
    if path:
        setSharedChromePath(path)
        updateStatus(f"共享内核路径已设置：{path}")
        updateInfoBar()

def downloadSharedKernel():
    """自动下载共享内核"""
    if messagebox.askyesno("提示", "确定要自动下载共享Chromium内核吗？这可能需要一些时间。"):
        # 显示进度条
        showProgressBar()
        updateProgress(0, 100)
        updateStatus("开始下载共享内核...")
        
        def downloadCallback(current, total, type='download'):
            """下载进度回调"""
            updateProgress(current, total)
            if type == 'download':
                updateStatus(f"下载中: {formatFileSize(current)} / {formatFileSize(total)}")
            else:
                updateStatus(f"解压中: {current} / {total} 文件")
        
        def downloadTask():
            """下载任务，在独立线程中执行"""
            # 执行下载
            success, message = autoDownloadSharedKernel(downloadCallback)
            
            # 隐藏进度条
            hideProgressBar()
            
            # 记录结果到日志
            if success:
                writeLog(f"共享内核下载成功：{message}")
                updateStatus("共享内核下载成功")
                updateInfoBar()
            else:
                writeLog(f"共享内核下载失败：{message}", level="ERROR")
                updateStatus("共享内核下载失败")
        
        # 创建并启动下载线程
        download_thread = threading.Thread(target=downloadTask, daemon=True)
        download_thread.start()

def initSharedChromeFromSelected():
    """从所选应用初始化共享内核"""
    selected_apps = getSelectedApps()
    if not selected_apps:
        writeLog("请选择一个应用来初始化共享内核", level="WARNING")
        updateStatus("请选择一个应用来初始化共享内核")
        return
    
    app = selected_apps[0]
    success, message = initializeSharedChromeFromApp(app)
    if success:
        writeLog(f"共享内核初始化成功：{message}")
        updateStatus(f"共享内核已从 {app['name']} 初始化")
        updateInfoBar()
    else:
        writeLog(f"共享内核初始化失败：{message}", level="ERROR")
        updateStatus(f"共享内核初始化失败")

def clearBackups():
    """清除备份"""
    backup_dirs = getBackupDirs()
    if not backup_dirs:
        writeLog("没有找到任何备份")
        updateStatus("没有找到任何备份")
        return
    
    # 显示备份列表，让用户选择要删除的备份
    backup_window = tk.Toplevel(root)
    backup_window.title("选择要清除的备份")
    backup_window.geometry("600x400")
    backup_window.transient(root)
    backup_window.config(bg="white")
    backup_window.grab_set()
    
    # 创建主框架，用于管理Treeview和滚动条
    tree_frame = ttk.Frame(backup_window)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 创建Treeview显示备份列表
    columns = ("app_name", "path", "size")
    backup_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode='extended')
    backup_tree.heading("app_name", text="应用名称")
    backup_tree.heading("path", text="备份路径")
    backup_tree.heading("size", text="大小")
    backup_tree.column("app_name", width=150)
    backup_tree.column("path", width=350)
    backup_tree.column("size", width=100, anchor=tk.CENTER)
    
    scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=backup_tree.yview)
    backup_tree.configure(yscroll=scrollbar.set)
    
    backup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 添加备份到Treeview
    for backup in backup_dirs:
        backup_tree.insert("", tk.END, values=(
            backup['app']['name'],
            backup['backup_path'],
            formatFileSize(backup['size'])
        ))
    
    def clearSelectedBackups():
        """清除选中的备份"""
        selected_items = backup_tree.selection()
        if not selected_items:
            writeLog("请选择要删除的备份", level="WARNING")
            return
        
        # 确认删除
        if not messagebox.askyesno("警告", "确定要删除选中的备份吗？此操作不可恢复！"):
            return
        
        if not messagebox.askyesno("再次确认", "您确定要删除这些备份吗？删除后将无法恢复！"):
            return
        
        success_count = 0
        fail_count = 0
        
        for item in selected_items:
            values = backup_tree.item(item, "values")
            # 从路径中提取应用路径
            backup_path = values[1]
            app_path = os.path.dirname(backup_path)
            
            success, message = deleteBackup(app_path)
            if success:
                success_count += 1
                backup_tree.delete(item)
            else:
                fail_count += 1
        
        # 生成结果消息
        result_message = f"备份删除完成：成功 {success_count} 个，失败 {fail_count} 个"
        writeLog(result_message)
        
        # 显示结果提示
        messagebox.showinfo("提示", result_message)
        
        # 更新状态栏
        updateStatus(result_message)
        
        # 如果没有更多备份，关闭窗口
        if not backup_tree.get_children():
            backup_window.destroy()
    
    def clearAllBackupsConfirm():
        """清除所有备份"""
        # 确认删除
        if not messagebox.askyesno("警告", "确定要删除所有备份吗？此操作不可恢复！"):
            return
        
        if not messagebox.askyesno("再次确认", "您确定要删除所有备份吗？删除后将无法恢复！"):
            return
        
        results = deleteAllBackups()
        success_count = sum(1 for r in results if r['success'])
        fail_count = sum(1 for r in results if not r['success'])
        
        # 生成结果消息
        result_message = f"所有备份删除完成：成功 {success_count} 个，失败 {fail_count} 个"
        writeLog(result_message)
        
        # 显示结果提示
        messagebox.showinfo("提示", result_message)
        
        # 更新状态栏
        updateStatus(result_message)
        
        # 关闭窗口
        backup_window.destroy()
    
    # 按钮区域 - 始终显示在窗口底部
    button_frame = ttk.Frame(backup_window)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
    
    ttk.Button(button_frame, text="清除选中", command=clearSelectedBackups).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="清除全部", command=clearAllBackupsConfirm).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="取消", command=backup_window.destroy).pack(side=tk.RIGHT, padx=5)

if __name__ == "__main__":
    threading.Thread(target=createTrayIcon, daemon=True).start()
    initUI()
