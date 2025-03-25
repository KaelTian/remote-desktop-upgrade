"""
远程桌面控制系统 - 配置模块
用于存储和管理系统配置
"""
import os
import json
import getpass
from pathlib import Path

# 默认配置
DEFAULT_CONFIG = {
    # 服务端配置
    "server": {
        "port": 5555,
        "screen_quality": 70,
        "allow_clipboard": True,
        "allow_file_transfer": False,
        "encryption_enabled": True,
        "password_protected": False,
        "password": "",
        "allowed_ip_list": [],
        "enable_logging": True,
    },
    
    # 客户端配置
    "client": {
        "recent_connections": [],
        "auto_reconnect": True,
        "default_quality": 70,
        "enable_fullscreen": True,
        "show_status_bar": True,
        "encryption_enabled": True,
        "save_passwords": False,
        "saved_passwords": {}
    }
}

def get_config_dir():
    """获取配置文件目录"""
    if os.name == 'nt':  # Windows
        config_dir = os.path.join(os.environ['APPDATA'], 'RemoteDesktopControl')
    else:  # Linux/Mac
        config_dir = os.path.join(str(Path.home()), '.remote-desktop-control')
        
    # 确保目录存在
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        
    return config_dir

def get_config_file(mode='server'):
    """获取配置文件路径"""
    config_dir = get_config_dir()
    if mode == 'server':
        return os.path.join(config_dir, 'server_config.json')
    else:
        return os.path.join(config_dir, 'client_config.json')

def load_config(mode='server'):
    """加载配置"""
    config_file = get_config_file(mode)
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_file):
        save_config(DEFAULT_CONFIG[mode], mode)
        return DEFAULT_CONFIG[mode].copy()
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 确保所有默认配置项都存在
        default = DEFAULT_CONFIG[mode].copy()
        for key, value in default.items():
            if key not in config:
                config[key] = value
                
        return config
    except Exception as e:
        print(f"加载配置文件出错: {e}")
        return DEFAULT_CONFIG[mode].copy()

def save_config(config, mode='server'):
    """保存配置"""
    config_file = get_config_file(mode)
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存配置文件出错: {e}")
        return False

def update_config(updates, mode='server'):
    """更新配置的部分内容"""
    config = load_config(mode)
    
    # 更新配置
    for key, value in updates.items():
        config[key] = value
    
    # 保存更新后的配置
    return save_config(config, mode)

def add_recent_connection(host, port):
    """添加最近连接到客户端配置"""
    config = load_config('client')
    
    # 连接信息
    connection = {
        "host": host,
        "port": port,
        "last_connected": import_time().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 检查是否已经存在
    recent = config.get('recent_connections', [])
    for i, conn in enumerate(recent):
        if conn.get('host') == host and conn.get('port') == port:
            # 移除旧记录
            recent.pop(i)
            break
    
    # 添加到最前面
    recent.insert(0, connection)
    
    # 保留最近10个连接
    config['recent_connections'] = recent[:10]
    
    # 保存配置
    save_config(config, 'client')

def import_time():
    """导入时间模块"""
    import datetime
    return datetime 