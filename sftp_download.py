import paramiko
import os
from stat import S_ISDIR
import posixpath  # 使用 posixpath 确保路径分隔符是正斜杠
import io
import threading
import time



class SFTPDownloader:
    def __init__(self, hostname, port, username, password=None, key_content=None,key_password=None):
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
            self.ssh.connect(self.hostname,port=self.port, username=self.username, pkey=key, timeout=600)
        else:
            self.ssh.connect(self.hostname, self.port, self.username, password=self.password,timeout=600)
        
        # 创建SFTP客户端
        self.sftp = self.ssh.open_sftp()

    def get_tasks(self):
        return self.tasks

    def add_task(self, remote_path, local_path):
        # 计算任务总大小
        total_size = self._get_remote_size(remote_path)
        self.tasks.append({
            'remote_path': remote_path,
            'local_path': local_path,
            'progress': 0,
            'size': total_size,
            'downloaded': 0,  # 已下载的字节数
            'current_file_start': 0  # 当前文件的起始字节数
        })

    def _get_remote_size(self, remote_path):
        try:
            attr = self.sftp.stat(remote_path)
            if S_ISDIR(attr.st_mode):
                # 如果是目录，递归计算总大小
                total_size = 0
                for item in self.sftp.listdir_attr(remote_path):
                    item_path = posixpath.join(remote_path, item.filename)
                    total_size += self._get_remote_size(item_path)
                return total_size
            else:
                # 如果是文件，直接返回文件大小
                return attr.st_size
        except FileNotFoundError:
            print(f"Remote path {remote_path} does not exist.")
            return 0

    def _download_file(self, remote_path, local_path, task_index):
        def progress_callback(bytes_transferred, total_bytes):
            # 计算增量字节数
            incremental_bytes = bytes_transferred - self.tasks[task_index]['current_file_start']
            # 更新已下载的字节数
            self.tasks[task_index]['downloaded'] += incremental_bytes
            # 更新当前文件的起始字节数
            self.tasks[task_index]['current_file_start'] = bytes_transferred
            # 计算总体进度
            total_downloaded = self.tasks[task_index]['downloaded']
            total_size = self.tasks[task_index]['size']
            progress = (total_downloaded / total_size) * 100
            self.tasks[task_index]['progress'] = progress
            # print(self.tasks[0])

        try:
            # 重置当前文件的起始字节数
            self.tasks[task_index]['current_file_start'] = 0
            self.sftp.get(remote_path, local_path, callback=progress_callback)
        except Exception as e:
            print(f"Error downloading file {remote_path}: {e}")

    def _download_directory(self, remote_path, local_path, task_index):
        try:
            # 检查远程路径是否存在
            if not self._remote_path_exists(remote_path):
                print(f"Remote path {remote_path} does not exist. Skipping.")
                return

            print(os.path.basename(remote_path))
            new_local_path = os.path.join(local_path, os.path.basename(remote_path))
            os.makedirs(new_local_path, exist_ok=True)
            for item in self.sftp.listdir_attr(remote_path):
                # 使用 posixpath.join 确保路径分隔符是正斜杠
                remote_item_path = posixpath.join(remote_path, item.filename)
                local_item_path = os.path.join(new_local_path, item.filename)
                if S_ISDIR(item.st_mode):
                    self._download_directory(remote_item_path, local_item_path, task_index)
                else:
                    self._download_file(remote_item_path, local_item_path, task_index)
        except Exception as e:
            print(f"Error downloading directory {remote_path}: {e}")

    def _remote_path_exists(self, remote_path):
        try:
            self.sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def start_download(self):
        for i, task in enumerate(self.tasks):
            remote_path = task['remote_path']
            local_path = task['local_path']
            if self._remote_path_exists(remote_path):
                if S_ISDIR(self.sftp.stat(remote_path).st_mode):
                    self._download_directory(remote_path, local_path, i)
                else:
                    filename = os.path.basename(remote_path)
                    local_path = os.path.join(local_path, filename)
                    self._download_file(remote_path, local_path, i)
            else:
                print(f"Remote path {remote_path} does not exist. Skipping task.")

    def close(self):
        self.sftp.close()
        self.ssh.close()

def run(downloader,remote_path,local_path):
    downloader.add_task(remote_path, local_path)
    downloader.start_download()

# 示例用法
# if __name__ == "__main__":
#     tasks = []
#     # 使用密码连接
#     downloader = SFTPDownloader(hostname='xxx', port=22, username='root', password='xxx')
    
#     # 使用密钥连接
#     # private_key = paramiko.RSAKey.from_private_key_file('/path/to/private/key')
#     # downloader = SFTPDownloader(hostname='your_host', port=22, username='your_username', pkey=private_key)

#     threading.Thread(target=run, args=(downloader,'/root/bin/DnsServer', './dir/',)).start()
#     tasks.append({'id':len(tasks) + 1,'remote_path': '/root/bin/DnsServer', 'local_path': './dir/','obj': downloader,'status': 'ready'})

#     while True:
#         for task in tasks:
#             try:   
#                 print(task['obj'].tasks[0])
#                 time.sleep(1)
#             except Exception as e:
#                 print(e)
#                 time.sleep(1)