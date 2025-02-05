import subprocess
import os
from typing import List, Optional
import time
import threading
import psutil
from flask import Flask, render_template, request, jsonify
import webview
import json
import sqlite3
import paramiko
from stat import S_ISDIR,S_ISLNK
from datetime import datetime
import math  # 确保导入math模块用于log和pow函数
import io
import tkinter as tk
from tkinter import filedialog
from sftp_download import run as sftp_download_run
from sftp_download import SFTPDownloader
from sftp_upload import run as sftp_upload_run
from sftp_upload import SFTPUploader
from file_system_selector import select_file_or_directory
from get_monitoring import get_remote_server_info

# 创建一个Flask应用实例
app = Flask(__name__)

# 进程管理器
class ProcessManager:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def start_process(self, command: List[str]) -> None:
        """Start a new process with the given command."""
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

    def terminate_process(self, timeout: int = 1) -> None:
        """Terminate the process gracefully, then kill it if it does not exit within the timeout."""
        try:
            proc = psutil.Process(self.process.pid)
            for child in proc.children(recursive=True):
                child.kill()
                proc.kill()
                proc.wait()  # 确保主进程已经结束
                print(f"成功终止了进程及其所有子进程，进程ID: {self.process.pid}")
        except psutil.NoSuchProcess:
            print("进程已不存在")
        except Exception as e:
            print(f"终止失败: {e}")
        finally:
            self.process = None

# 定义Flask应用的根路由，返回index.html页面
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ssh')
def ssh():
    id = request.args.get('id')
    cursor = db.cursor()
    get_server_config_sql = '''
        SELECT ip,username,port,password,key,passphrase FROM server_host sh WHERE id = ?;
    '''
    host = cursor.execute(get_server_config_sql, (id,)).fetchone()
    if host[4]:
        key = host[4].replace('\n', '\\n')
    else:
        key = ""
    ssh_info = {
        "host": host[0],
        "username": host[1],
        "port": host[2],
        "password": host[3],
        "key": key,
        "key_passphrase": host[5],
    }
    return render_template('ssh.html',ssh_info=ssh_info)
@app.route('/del_group',methods=['POST'])
def del_group():
    if request.method == 'POST':
        cursor = db.cursor()
        data = json.loads(request.data)
        cursor.execute("DELETE FROM server_group WHERE id = ?",(data['id'],))
        cursor.execute("DELETE FROM server_host WHERE group_id = ?",(data['id'],))
        db.commit()
    return jsonify({'status':"success",'message':'删除成功'})

@app.route('/add_group',methods=['POST'])
def add_group():
    if request.method == 'POST':
        data = request.get_json()
        cursor = db.cursor()
        if data['status'] == 'update':
            cursor.execute("UPDATE server_group SET name = ? WHERE id = ?",(data['name'],data['id']))
            return jsonify({'status':"success",'message':'修改成功'})
        else:
            group_data = cursor.execute("SELECT name from server_group where name = ?",(data['name'],)).fetchall()
            if group_data:
                return jsonify({"status": "error", "message": "组名称已存在"})
            else:
                cursor.execute("INSERT INTO server_group (name) VALUES (?)", (data['name'],))
                db.commit()
                return jsonify({"status": "success","message": "添加成功"})
        

@app.route('/del_server',methods=['POST'])
def del_server():
    if request.method == 'POST':
        cursor = db.cursor()
        data = json.loads(request.data)
        id = data['id']
        cursor.execute("DELETE FROM server_host WHERE id = ?", (id,))
        db.commit()
        return jsonify({"status": "success","message": "删除成功"})
    else:
        return jsonify({"status": "error","message": "请求错误"})
@app.route('/add_server',methods=['POST'])
def add_server():
    if request.method == 'POST':
        data = request.get_json()
        name = data['name']
        ip  = data['ip']
        port = data['port']
        username = data['username']
        password = data['password']
        if data['key']:
            key = data['key_content'].replace('\n', '\\n')
        else:
            key = ""
        passphrase = data['passphrase']
        group_id = data['group_id']
        status = data['status']
        cursor = db.cursor()
        if status == "update":
            print('更新服务器')
            cursor.execute("UPDATE server_host SET name = ?,ip = ?,port = ?,username = ?,password = ?,key = ?,passphrase = ?,group_id = ? WHERE id = ?", (name,ip,port,username,password,key,passphrase,group_id,data['id']))
        else:
            print('添加服务器')
            cursor.execute("INSERT INTO server_host (name,ip,port,username,password,key,passphrase,group_id) VALUES (?,?,?,?,?,?,?,?)", (name,ip,port,username,password,key,passphrase,group_id))
        db.commit()
    if status == 'update':
        return jsonify({"status": "success","message": "更新成功"})
    else:
        return jsonify({"status": "success","message": "添加成功"})
    
#获取服务器的目录定位
@app.route('/get_server_locate_dir',methods=['POST'])
def get_server_locate_dir():
    if request.method == 'POST':
        data = request.get_json()
        id = data['id']
        
        if id:
            cursor = db.cursor()
            get_server_config_sql = '''
                SELECT ip,username,port,password,key,passphrase FROM server_host sh WHERE id = ?;
            '''
            host = cursor.execute(get_server_config_sql, (id,)).fetchone()
            ip = host[0]
            username = host[1]
            port = host[2]
            password = host[3]
            key = host[4]
            passphrase = host[5]
            res = executeSshCommand(hostname=ip,port=port, username=username, password=password, key_content=key, key_password=passphrase,command='cat ~/.tmd-ssh/current_dir.txt')[0].replace('\n', '')
        return jsonify({"status": "success","message": "获取成功","data": res})
#获取服务器目录内容
@app.route('/get_server_dir',methods=['POST'])
def get_server_dir():
    if request.method == 'POST':
        data = request.get_json()
        id = data['id']
        server_dir = data['server_dir']

        if id:
            cursor = db.cursor()
            get_server_config_sql = '''
                SELECT ip,username,port,password,key,passphrase FROM server_host sh WHERE id = ?;
            '''
            host = cursor.execute(get_server_config_sql, (id,)).fetchone()
            ip = host[0]
            username = host[1]
            port = host[2]
            password = host[3]
            key = host[4]
            passphrase = host[5]
            if not server_dir:
                server_dir = '/'
            data_list = get_sftp_directory_contents(hostname=ip, port=port, username=username,password=password, key_content=key, key_password=passphrase, remote_path=server_dir)
    return jsonify({"status": "success","message": "获取成功","data":data_list,"dir":server_dir})
#获取服务器列表
@app.route('/get_server_list')
def get_server_list():
    cursor = db.cursor()
    data = []
    get_server_group_sql = '''
        SELECT id,name from server_group;
    '''
    group = cursor.execute(get_server_group_sql).fetchall()

    for group_index,group_name in group:
        group_data = {
            "id": group_index,
            "label": group_name,
            "type": "group",
            "children": []
        }
        get_server_host_sql = '''
            SELECT id,name,ip,port,username,group_id,remarks FROM server_host sh WHERE group_id = ?;
        '''
        host = cursor.execute(get_server_host_sql, (group_index,)).fetchall()
        for host_index,host_name,ip,port,username,group_id,remarks in host:
            group_data["children"].append({
                "id": host_index,
                "label": host_name,
                "ip": ip,
                "port": port,
                "username": username,
                "group_id": group_id,
                "remarks": remarks,
                "type": "server"
            })
        data.append(group_data)
    return jsonify(data)

#下载服务器文件
@app.route('/sftp_download',methods=['POST'])
def sftp_download():
    global tasks_list
    if request.method == 'POST':
        data = request.get_json()
        id = data['id']
        remote_path = data['remote_path']
        cursor = db.cursor()
        get_server_config_sql = '''
        SELECT ip,username,port,password,key,passphrase,name FROM server_host sh WHERE id = ?;
        '''
        host = cursor.execute(get_server_config_sql, (id,)).fetchone()
        history_save_path_sql = '''
            SELECT path FROM save_path;
        '''
        save_path = cursor.execute(history_save_path_sql).fetchone()
        print(save_path)
        ip = host[0]
        username = host[1]
        port = host[2]
        password = host[3]
        key = host[4]
        passphrase = host[5]
        name = host[6]
        if save_path:
            save_dir = select_save_dir(save_path)
        else:
            save_dir = select_save_dir()
            history_save_path_update_sql = '''
                INSERT INTO save_path (id, path)
                VALUES (1, ?)
                ON CONFLICT (id) DO UPDATE
                SET path = EXCLUDED.path;
            '''
            cursor.execute(history_save_path_update_sql, (save_dir,))
        db.commit()
        downloader = SFTPDownloader(hostname=ip, port=port, username=username, password=password, key_content=key, key_password=passphrase)
        threading.Thread(target=sftp_download_run, args=(downloader,remote_path, save_dir,)).start()
        tasks_list.append({'id':len(tasks_list) + 1,'remote_path': remote_path, 'local_path': save_dir,'obj': downloader,'status': 'ready','ip':ip,'progress': 0,"type": "下载","name":name})
    return jsonify({"status": "success","message": "获取成功"})

@app.route('/sftp_upload',methods=['POST'])
def sftp_upload():
    global tasks_list
    if request.method == 'POST':
        data = request.get_json()
        id = data['id']
        remote_path = data['remote_path']
        cursor = db.cursor()
        get_server_config_sql = '''
        SELECT ip,username,port,password,key,passphrase,name FROM server_host sh WHERE id = ?;
        '''
        host = cursor.execute(get_server_config_sql, (id,)).fetchone()
        ip = host[0]
        username = host[1]
        port = host[2]
        password = host[3]
        key = host[4]
        passphrase = host[5]
        name = host[6]
        selected_path = select_file_or_directory()
        if selected_path:
            uploader = SFTPUploader(hostname=ip, port=port, username=username, password=password, key_content=key, key_password=passphrase)
            threading.Thread(target=sftp_upload_run, args=(uploader,selected_path,remote_path,)).start()
            tasks_list.append({'id':len(tasks_list) + 1,'remote_path': remote_path, 'local_path': selected_path,'obj': uploader,'status': 'ready','ip':ip,'progress': 0,"type": "上传","name":name})
        return jsonify({"status": "success","message": "获取成功"})

@app.route('/sftp_delete',methods=['POST'])
def sftp_delete():
    global tasks_list
    if request.method == 'POST':
        data = request.get_json()
        id = data['id']
        del_path = data['remote_path']
        cursor = db.cursor()
        get_server_config_sql = '''
        SELECT ip,username,port,password,key,passphrase FROM server_host sh WHERE id = ?;
        '''
        host = cursor.execute(get_server_config_sql, (id,)).fetchone()
        ip = host[0]
        username = host[1]
        port = host[2]
        password = host[3]
        key = host[4]
        passphrase = host[5]
        executeSshCommand(hostname=ip, port=port, username=username, password=password, key_content=key, key_password=passphrase,command=f"rm -rf {del_path}")
        return jsonify({"status": "success","message": "删除成功"})

@app.route('/get_tasks_list')
def get_tasks_list():
    global tasks_list
    data = []
    for task in tasks_list:
        try:   
            print(task['obj'].get_tasks)
            progress = task['obj'].tasks[0]['progress']
            size = convert_size(task['obj'].tasks[0]['size'])
            if progress == 100:
                status = "success"
            else:
                status = "running"
            data.append({'id': task['id'],'remote_path': task['remote_path'], 'local_path': task['local_path'],'ip':task['ip'],'status': status,'progress': round(progress),'size':size,"type":task['type'],"name":task['name']})
        except Exception as e:
            print(e)
            data.append({'id': task['id'],'remote_path': task['remote_path'], 'local_path': task['local_path'],'ip':task['ip'],'status': 'ready','progress': 0,'size':'0',"type":task['type'],"name":task['name']})
    return jsonify(data)

@app.route('/cancel_sftp_tasks',methods=['POST'])
def cancel_sftp_tasks():
    global tasks_list
    if request.method == 'POST':
        data = request.get_json()
        id = data['id']
        for task in tasks_list:
            if task['id'] == id:
                task['obj'].close()
                tasks_list.remove(task)
                return jsonify({"status": "success","message": "取消任务成功"})
    return jsonify({"status": "error","message": "取消任务失败"})

#重启ws进程
@app.route('/ws_restart')
def ws_restart():
    # global manager
    # 终止进程
    manager.terminate_process()
    # 启动进程
    manager.start_process([ws])
    return jsonify({"status": "success","message": "重启ws成功"})

    
#获取服务器监控数据
@app.route('/get_server_monitor_data',methods=['POST'])
def get_server_monitor_data():
    global monitoring_id, monitoring_ssh,monitoring_status,monitoring_ip
    if request.method == 'POST':
        data = request.get_json()
        id = data['id']
        if id != monitoring_id:
            if monitoring_ssh:
                monitoring_ssh.close()
                monitoring_ssh = None
            cursor = db.cursor()
            get_server_config_sql = '''
            SELECT ip,username,port,password,key,passphrase,name FROM server_host sh WHERE id = ?;
            '''
            host = cursor.execute(get_server_config_sql, (id,)).fetchone()
            ip = host[0]
            username = host[1]
            port = host[2]
            password = host[3]
            key = host[4]
            passphrase = host[5]
            monitoring_ssh = create_ssh_connect(hostname=ip, port=port, username=username, password=password, key_content=key, key_password=passphrase)
            monitoring_id = id
            monitoring_ip = ip
            monitoring_status = True
        if monitoring_status:
            monitoring_status = False
            try:
                data = get_remote_server_info(monitoring_ssh)
            except Exception as e:
                print(e)
            monitoring_status = True
            data['ip'] = monitoring_ip
        else:
            return jsonify({"status": "error","message": "获取失败"})
        return jsonify({"status": "success","message": "获取成功","data":data})

def conn_sql():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    conn = sqlite3.connect(f'{script_dir}\\tmd-ssh.db',check_same_thread=False)
    cursor = conn.cursor()
    #服务器表
    """
    auth_mode: 有三种模式1、密码认证 2、密钥认证 3、密钥+密码认证
    """
    server_list_sql = '''
        CREATE TABLE IF NOT EXISTS server_host (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ip TEXT NOT NULL,
            port TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT,
            key TEXT,
            passphrase TEXT,
            group_id TEXT,
            remarks TEXT
        )
    '''
    #服务器组表
    server_group_sql = '''
        CREATE TABLE IF NOT EXISTS server_group (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    '''
    save_path_sql = '''
        CREATE TABLE IF NOT EXISTS save_path (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE
        )
    '''
    cursor.execute(server_list_sql)
    cursor.execute(server_group_sql)
    cursor.execute(save_path_sql)
    conn.commit()
    return conn

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

#创建监控使用的ssh连接
def create_ssh_connect(hostname, port, username, password=None, key_content=None, key_password=None,):
    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print('创建ssh连接')
    if key_content:
        # 使用SSH密钥认证
        print('使用密钥认证')
        new_key_content = key_content.replace('\\n', '\n')
        key = paramiko.RSAKey.from_private_key(io.StringIO(new_key_content), password=key_password)
        ssh.connect(hostname,port=port, username=username, pkey=key, timeout=600)
    else:
        # 使用密码认证
        print('使用密码认证')
        ssh.connect(hostname, port=port, username=username, password=password,timeout=600)
    return ssh
    
def executeSshCommand(hostname, port, username, password=None, key_content=None, key_password=None, command=None):
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if key_content:
            # 使用SSH密钥认证
            new_key_content = key_content.replace('\\n', '\n')
            print(new_key_content)
            key = paramiko.RSAKey.from_private_key(io.StringIO(new_key_content), password=key_password)
            ssh.connect(hostname,port=port, username=username, pkey=key, timeout=600)
        else:
            # 使用密码认证
            ssh.connect(hostname, port=port, username=username, password=password,timeout=600)
        
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.readlines()
        error = stderr.readlines()
        if error:
            print(f"Error: {error}")
            return
        else:
            return output
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def get_sftp_directory_contents(hostname, port, username, password=None, key_content=None, key_password=None, remote_path='/'):
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if key_content:
            # 使用SSH密钥认证
            new_key_content = key_content.replace('\\n', '\n')
            key = paramiko.RSAKey.from_private_key(io.StringIO(new_key_content), password=key_password)
            ssh.connect(hostname,port=port, username=username, pkey=key, timeout=600)
        else:
            # 使用密码认证
            ssh.connect(hostname, port=port, username=username, password=password,timeout=600)

        # 打开SFTP会话
        sftp = ssh.open_sftp()

        # 获取目录内容
        items = []
        for item in sftp.listdir_attr(remote_path):
            if S_ISDIR(item.st_mode):
                item_type = 'd'
            elif S_ISLNK(item.st_mode):
                item_type = 'l'
            else:
                item_type = 'f'

            item_info = {
                'type': item_type,
                'time': datetime.fromtimestamp(item.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'name': item.filename,
                'size': convert_size(item.st_size)
            }
            if item_type == 'd':
                items.insert(0, item_info)
            else:
                items.append(item_info)

        # 关闭SFTP会话和SSH连接
        sftp.close()
        ssh.close()

        return items

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# sftp下载文件保存路径
def select_save_dir(init_dir=None):
    # 创建 Tkinter 的主窗口但不显示
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    if init_dir:
        dir_path = filedialog.askdirectory(
        initialdir=init_dir,  # 初始目录
        title="保存路径",  # 对话框标题
    )
    else:
        # 弹出文件保存对话框
        dir_path = filedialog.askdirectory(
            initialdir="/",  # 初始目录
            title="保存路径",  # 对话框标题
        )
    root.update()
    root.destroy()
    if dir_path:
        return dir_path
    else:
        return None
# 关闭窗口时执行
def on_closed():
    for task in tasks_list:
        task['obj'].close()

# 使用示例
if __name__ == "__main__":
    monitoring_ssh = None
    monitoring_id = None
    monitoring_status = True
    monitoring_ip = None
    tasks_list = []
    db = conn_sql()
    #创建进程管理器
    manager = ProcessManager()
    #websocket服务执行路径
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    ws = script_dir + '\ws\ws.exe'
    # 启动进程
    manager.start_process([ws])

    window = webview.create_window('TMD-SHELL', app ,width=1360,height=820,min_size=(1360,820))
    window.events.closed += on_closed
    # 启动webview应用
    webview.start(debug=True)

    # 终止进程
    manager.terminate_process()