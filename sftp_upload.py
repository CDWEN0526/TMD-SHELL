import paramiko
import os
from stat import S_ISDIR, S_ISREG
import posixpath  # 使用 posixpath 确保路径分隔符是正斜杠
import io
import threading
import time

class SFTPUploader:
    def __init__(self, hostname, port, username, password=None, key_content=None, key_password=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key = key_content
        self.key_password = key_password
        self.tasks = []

        # 创建SSH客户端
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.key:
            # 使用SSH密钥认证
            new_key_content = self.key.replace('\\n', '\n')
            key = paramiko.RSAKey.from_private_key(io.StringIO(new_key_content), password=self.key_password)
            self.ssh.connect(self.hostname, port=self.port, username=self.username, pkey=key, timeout=600)
        else:
            self.ssh.connect(self.hostname, self.port, self.username, password=self.password, timeout=600)
        
        # 创建SFTP客户端
        self.sftp = self.ssh.open_sftp()

    def get_tasks(self):
        return self.tasks

    def add_task(self, local_path, remote_path):
        # 计算任务总大小
        total_size = self._get_local_size(local_path)
        self.tasks.append({
            'local_path': local_path,
            'remote_path': remote_path,
            'progress': 0,
            'size': total_size,
            'uploaded': 0,  # 已上传的字节数
            'current_file_start': 0  # 当前文件的起始字节数
        })

    def _get_local_size(self, local_path):
        if os.path.isfile(local_path):
            return os.path.getsize(local_path)
        elif os.path.isdir(local_path):
            total_size = 0
            for dirpath, _, filenames in os.walk(local_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            return total_size
        else:
            print(f"Local path {local_path} does not exist.")
            return 0

    def _upload_file(self, local_path, remote_path, task_index):
        def progress_callback(bytes_transferred, total_bytes):
            # 计算增量字节数
            incremental_bytes = bytes_transferred - self.tasks[task_index]['current_file_start']
            # 更新已上传的字节数
            self.tasks[task_index]['uploaded'] += incremental_bytes
            # 更新当前文件的起始字节数
            self.tasks[task_index]['current_file_start'] = bytes_transferred
            # 计算总体进度
            total_uploaded = self.tasks[task_index]['uploaded']
            total_size = self.tasks[task_index]['size']
            progress = (total_uploaded / total_size) * 100
            self.tasks[task_index]['progress'] = progress
            # print(self.tasks[0])

        try:
            print(remote_path,local_path)
            # 重置当前文件的起始字节数
            self.tasks[task_index]['current_file_start'] = 0
            self.sftp.put(local_path, remote_path, callback=progress_callback)
        except Exception as e:
            import traceback
            print(f"Error uploading file {local_path}: {e}")
            traceback.print_exc()


    def _upload_directory(self, local_path, remote_path, task_index):
        try:
            # 检查本地路径是否存在
            if not os.path.exists(local_path):
                print(f"Local path {local_path} does not exist. Skipping.")
                return
            
            # 创建远程目录
            # self.sftp.mkdir(remote_path)
            self._ensure_remote_directory_exists(remote_path)

            for item in os.listdir(local_path):
                local_item_path = os.path.join(local_path, item)
                remote_item_path = posixpath.join(remote_path, item)
                if os.path.isdir(local_item_path):
                    self._upload_directory(local_item_path, remote_item_path, task_index)
                else:
                    self._upload_file(local_item_path, remote_item_path, task_index)
        except Exception as e:
            import traceback
            print(f"Error uploading directory {local_path}: {e}")
            traceback.print_exc()

    def start_upload(self):
        for i, task in enumerate(self.tasks):
            local_path = task['local_path']
            remote_path = task['remote_path']
            #判断远程目录是不是文件，是文件的话值获取路径部分不要文件部分
            if S_ISREG(self.sftp.stat(remote_path).st_mode):
                remote_path = posixpath.dirname(remote_path)
            if os.path.exists(local_path):
                if os.path.isdir(local_path):
                    dirname = os.path.basename(local_path)
                    remote_path = posixpath.join(remote_path, dirname)
                    self._upload_directory(local_path, remote_path, i)
                else:
                    filename = os.path.basename(local_path)
                    remote_path = posixpath.join(remote_path, filename)
                    self._upload_file(local_path, remote_path, i)
            else:
                print(f"Local path {local_path} does not exist. Skipping task.")

    def close(self):
        self.sftp.close()
        self.ssh.close()

    def _ensure_remote_directory_exists(self, remote_path):
        """
        递归确保远程目录存在
        """
        try:
            self.sftp.stat(remote_path)  # 检查目录是否存在
        except FileNotFoundError:
            # 如果目录不存在，递归创建父目录
            parent_dir = posixpath.dirname(remote_path)
            if parent_dir != remote_path:  # 避免无限递归
                self._ensure_remote_directory_exists(parent_dir)
            self.sftp.mkdir(remote_path)  # 创建当前目录

def run(uploader, local_path, remote_path):
    uploader.add_task(local_path, remote_path)
    uploader.start_upload()

# 示例用法
# if __name__ == "__main__":
#     tasks = []
#     # 使用密码连接
#     uploader = SFTPUploader(hostname='xxxx', port=22, username='root', password='xxxxxx')
    
#     # 使用密钥连接
#     # private_key = paramiko.RSAKey.from_private_key_file('/path/to/private/key')
#     # uploader = SFTPUploader(hostname='your_host', port=22, username='your_username', pkey=private_key)

#     threading.Thread(target=run, args=(uploader, '.\dir\OneForAll', '/root/bin/ws/ws.py')).start()
#     tasks.append({'id': len(tasks) + 1, 'local_path': '.\dir\OneForAll', 'remote_path': '/root/bin/ws/ws.py', 'obj': uploader, 'status': 'ready'})

#     while True:
#         for task in tasks:
#             try:   
#                 print(task['obj'].tasks[0])
#                 time.sleep(1)
#             except Exception as e:
#                 print(e)
#                 time.sleep(1)