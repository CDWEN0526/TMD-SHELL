const tab = `
<div style="text-align: center;box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1); margin: 20px; padding: 20px; ">
<h3>欢迎使用TMD-SHELL</h3>
<p>Autor: Davin Chen</p>
<p>Email: 949178863@qq.com</p>
<p>技术： Vue、python、flask、pywebview、websocket</p>
<p>创建新的终端，开始你的运维工作吧！</p>
</div>
`
let notificationQueue = [];
let isShowingNotification = false;

new Vue({
  el: '#app',
  delimiters: ['${', '}'],
  data: {
    editableTabsValue: '1',
    editableTabs: [
      {
        title: '简介',
        name: '1',
        id: '0',
        content: tab
      },
    ],
    tabIndex: 1,

    serverManagementDrawer: false,
    sftpDrawer: false,
    serverListData: [{ 'id': 1, 'label': 'null', 'children': [] }],
    defaultProps: {
      children: 'children',
      label: 'label'
    },

    nodeCount: 0,
    preNodeId: null,
    curNodeId: null,
    nodeTimer: null,

    dialogAddGroupFormVisible: false,
    addGroupForm: {
      id: '',
      name: '',
      status: ''
    },

    dialogAddServerFormVisible: false,
    addServerForm: {
      name: '',
      id: '',
      ip: '',
      port: '',
      username: '',
      password: '',
      key: '',
      key_content: '',
      passphrase: '',
      group_id: '',
      status: '',
    },

    serverRightSelect: {
      type: '',
      id: ''
    },

    rules: {
      name: [
        { required: true, message: '请输入必填项', trigger: 'blur' },
        { min: 1, max: 100, message: '长度过长', trigger: 'blur' }
      ],
      ip: [
        { required: true, message: '请输入必填项', trigger: 'blur' },
        { min: 1, max: 100, message: '长度过长', trigger: 'blur' }
      ],
      port: [
        { required: true, message: '请输入必填项', trigger: 'blur' },
        { min: 1, max: 5, message: '长度过长', trigger: 'blur' }
      ],
      username: [
        { required: true, message: '请输入必填项', trigger: 'blur' },
      ],
      group_id: [
        { required: true, message: '请输入必填项', trigger: 'blur' },
      ],
    },

    server_current_path: [{ id: 0, path: '/', tab: 1 }],
    current_path_data: [],
    now_server_id: '0',
    sftp_input_data: '',
    sftp_loading: true,
    transmit: false,
    sftp_task: [],
    sftp_task_timer: null,
    sftp_task_loading: false,
    table_height: 155,

    ip: "null",
    cpu: 0,
    memory: 0,
    health: "success",
    netCardTableData: [],
    devTableData: [],
    monitoring_timer: null,
    monitoring_timer_status: false,
    monitoring_loading: false,

  },

  watch: {
    serverManagementDrawer: {
      handler(newVal, oldVal) {
        this.UpdateServerList(newVal);
      },
      deep: true,
    },
    //获取服务器目录内容
    sftpDrawer: {
      handler(newVal, oldVal) {
        if (newVal) {
          this.getServerDir()
        }
      },
      deep: true,
    },
    now_server_id: {
      handler(newVal, oldVal) {
        this.monitoring_loading = true
        if (this.monitoring_timer != null) {
          clearInterval(this.monitoring_timer)
          this.monitoring_timer_status = false;
        }
        if (newVal == '0') {
          clearInterval(this.monitoring_timer)
          this.ip = "null"
          this.cpu = 0
          this.memory = 0
          this.health = "success"
          this.netCardTableData = []
          this.devTableData = []
          this.monitoring_timer = null
          this.monitoring_timer_status = false
          this.monitoring_loading = false
          return
        }

        this.monitoring_timer = setInterval(() => {
          if (this.monitoring_timer_status) {
            return
          }
          var data = { id: newVal }
          axios.post('/get_server_monitor_data', data).then(response => {
            this.monitoring_timer_status = true;
            if (response.data.status == 'success') {
              this.ip = response.data.data.ip;
              this.cpu = parseInt(response.data.data.cpu.replace('%', ''));
              this.memory = parseInt(response.data.data.memory.replace('%', ''));

              if (this.cpu > 80) {
                this.health = "warning";
              } else if (this.cpu > 90) {
                this.health = "danger";
              }

              if (this.memory > 80) {
                this.health = "warning";
              } else if (this.memory > 90) {
                this.health = "danger";
              }

              this.netCardTableData = response.data.data.net_card;
              this.devTableData = response.data.data.dev;
              for (var i = 0; i < this.devTableData.length; i++) {
                use = this.devTableData[i].use.replace('%', '')
                if (use >= 80 && use < 90) {
                  this.health = "warning";
                } else if (use >= 90) {
                  this.health = "danger"
                }
              }
              this.monitoring_loading = false;
            }
            this.monitoring_timer_status = false;
          }).catch(error => {
            console.error('Error fetching server data:', error);
            this.monitoring_timer_status = false;
          });
        }, 1000)
      },
      deep: true,
    },
  },

  methods: {
    //取消sftp的传输任务
    cancelSftpTasks(id) {
      data = { id: id }
      axios.post('/cancel_sftp_tasks', data).then(response => {
        if (response.data.status == 'success') {
          this.$notify({
            title: '成功',
            message: response.data.message,
            type: 'success',
            position: 'bottom-right'
          });
        } else {
          this.$notify({
            title: '失败',
            message: response.data.message,
            type: 'error',
            position: 'bottom-right'
          });
        }
      })
    },

    //sftp传输任务打开触发
    transmitOpen() {
      this.sftp_task_loading = true;
      this.sftp_task_timer = setInterval(() => {
        axios.get('/get_tasks_list').then(response => {
          this.sftp_task = response.data
          this.transmit = true
          console.log(this.sftp_task)
          this.sftp_task_loading = false
        })
      }, 1000)
    },

    //sftp传输任务关闭触发
    transmitClose() {
      this.sftp_task = []
      clearInterval(this.sftp_task_timer)
      this.transmit = false
    },

    //sftp定位到当前终端工作目录
    locateToDir() {
      data = { id: this.now_server_id }
      axios.post('/get_server_locate_dir', data)
        .then(response => {
          if (response.data.status == 'success') {
            dir = response.data.data
            console.log(dir)
            // this.current_path_data = response.data.data
            for (let i = 0; i < this.server_current_path.length; i++) {
              if (String(this.server_current_path[i].id) == String(this.now_server_id) && String(this.server_current_path[i].tab == String(this.editableTabsValue))) {
                this.server_current_path[i].path = dir
                this.getServerDir()
                break
              }
            }

          }
        })
    },

    //sftp返回上一步
    sftpBack() {
      function getParentPath(path) {
        path = path.replace(/\/+/g, '/').replace(/\/+$/, '');
        const parts = path.split('/');
        parts.pop();
        if (parts.length === 0 || (parts.length === 1 && parts[0] === '')) return '/';
        return parts.join('/');
      }

      if (this.now_server_id == '0') {
        return
      };
      for (let i = 0; i < this.server_current_path.length; i++) {
        if (String(this.server_current_path[i].id) == String(this.now_server_id) && String(this.server_current_path[i].tab == String(this.editableTabsValue))) {
          this.server_current_path[i].path = getParentPath(this.sftp_input_data)
          this.getServerDir()
          break
        }
      }
    },
    //sftp输入框改变路径
    changeServerDir() {
      if (this.now_server_id == '0') {
        return
      };
      for (let i = 0; i < this.server_current_path.length; i++) {
        if (String(this.server_current_path[i].id) == String(this.now_server_id) && String(this.server_current_path[i].tab == String(this.editableTabsValue))) {
          this.server_current_path[i].path = this.sftp_input_data
          break
        }
      }
      this.getServerDir()
    },
    //获取sftp目录内容
    getServerDir() {
      this.sftp_loading = true;
      if (this.now_server_id == '0') {
        return
      };
      var data = null
      for (let i = 0; i < this.server_current_path.length; i++) {
        if (String(this.server_current_path[i].id) == String(this.now_server_id) && String(this.server_current_path[i].tab == String(this.editableTabsValue))) {
          var data = { id: this.now_server_id, server_dir: this.server_current_path[i].path }
          break
        }
      }
      if (data == null) {
        var data = { id: this.now_server_id, server_dir: '/' }
        this.server_current_path.push({ id: this.now_server_id, path: '/', tab: this.editableTabsValue })
      }
      axios.post('/get_server_dir', data)
        .then(response => {
          if (response.data.status == 'success') {
            this.current_path_data = response.data.data
            this.sftp_input_data = response.data.dir
            this.sftp_loading = false;
          }
        })
    },

    //sftp表格图标
    getIconClass(type) {
      switch (type) {
        case 'f':
          return 'el-icon-tickets';
        case 'd':
          return 'el-icon-folder';
        case 'l':
          return 'el-icon-paperclip';
        default:
          return ''; // 或者返回一个默认的类名
      }
    },
    //sftp表格行双击事件
    sftpTableRowDbClick(row, column, event) {
      this.sftp_loading = true;
      if (row.type != 'f') {
        function joinPaths(...parts) {
          return parts
            .map(part => String(part).trim().replace(/\/+/g, '/')) // 确保每个部分都是字符串，并清理多余斜杠
            .filter(part => part.length > 0) // 过滤掉空字符串
            .join('/')
            .replace('//', '/'); // 使用单个斜杠连接各部分
        }
        var path = null
        for (let i = 0; i < this.server_current_path.length; i++) {
          if (String(this.server_current_path[i].id) == String(this.now_server_id) && String(this.server_current_path[i].tab == String(this.editableTabsValue))) {
            var path = this.server_current_path[i].path
            break
          }
        }
        if (path == null) {
          var path = '/'
        }
        axios.post('/get_server_dir', { id: this.now_server_id, server_dir: joinPaths(path, row.name) })
          .then(response => {
            if (response.data.status == 'success') {
              this.current_path_data = response.data.data
              this.sftp_input_data = response.data.dir
              for (let i = 0; i < this.server_current_path.length; i++) {
                if (String(this.server_current_path[i].id) == String(this.now_server_id) && String(this.server_current_path[i].tab == String(this.editableTabsValue))) {
                  this.server_current_path[i].path = response.data.dir
                  this.sftp_loading = false;
                  break
                }
              }
            }
          })
      }
    },
    //标签页选项点击后触发
    optionReplacement(tab, event) {
      selectedId = event.target.getAttribute('id');
      for (let i = 0; i < this.editableTabs.length; i++) {
        if ('tab-' + this.editableTabs[i].name == selectedId) {
          newTabData = this.editableTabs[i];
          this.now_server_id = newTabData.id;
          break
        };
      };
    },

    //移除服务器列表中指定的服务器id
    removeServerByIdAndType(array, id, type) {
      array.forEach(group => {
        if (group.children && group.children.length > 0) {
          group.children = group.children.filter(child => {
            if (child.id === id && child.type === type) {
              return false; // 移除符合条件的元素
            }
            return true;
          });
        }
      });
    },
    //对sftp表格右键菜单触发
    sftpTableRowContextmenu(row, column, event) {
      event.preventDefault();
      this.$contextmenu({
        items: [
          {
            label: "下载",
            onClick: () => {
              console.log(row)
              var data = { id: this.now_server_id, remote_path: (this.sftp_input_data + '/' + row.name).replace('//', '/') }
              axios.post("/sftp_download", data)
                .then(function (response) {
                  console.log(response.data);
                })
            }
          },
          {
            label: "上传",
            onClick: () => {
              console.log(row)
              var data = { id: this.now_server_id, remote_path: (this.sftp_input_data + '/' + row.name).replace('//', '/') }
              axios.post("/sftp_upload", data)
                .then(function (response) {
                  console.log(response.data);
                })
            }
          },
          {
            label: "删除",
            onClick: () => {
              console.log(row)
              var delete_path = (this.sftp_input_data + '/' + row.name).replace('//', '/')
              this.$confirm('此操作将永久删除' + delete_path + '是否继续?', '警告', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
              }).then(() => {
                var del_data = { id: this.now_server_id, remote_path: delete_path }
                axios.post("/sftp_delete", del_data)
                  .then(function (response) {
                    console.log(response.data);
                    davin.$message({
                      type: 'success',
                      message: '删除成功!'
                    });
                    davin.getServerDir()
                  })
              }).catch(() => {
                this.$message({
                  type: 'info',
                  message: '已取消删除'
                });
              });
            }
          }
        ],
        event,
        custonClass: "custom-class",
        zIndex: 20003,
        minWidth: 200
      })
    },
    //对服务器列表右键菜单触发
    handleNodeContextmenu(event, data) {
      this.$contextmenu({
        items: [
          {
            label: "编辑",
            onClick: () => {
              if (data.type == "server") {
                this.dialogAddServerFormVisible = true;
                this.addServerForm.name = data.label;
                this.addServerForm.id = data.id;
                this.addServerForm.ip = data.ip;
                this.addServerForm.port = data.port;
                this.addServerForm.username = data.username;
                this.addServerForm.status = "update"
              } else if (data.type == "group") {
                this.dialogAddGroupFormVisible = true;
                this.addGroupForm.status = "update";
                this.addGroupForm.name = data.label;
                this.addGroupForm.id = data.id;
              }
            }
          },
          {
            label: "删除",
            onClick: () => {
              if (data.type == "server") {
                axios.post('/del_server', data)
                  .then(response => {
                    if (response.data.status == 'success') {
                      this.$notify({
                        title: '成功',
                        message: response.data.message,
                        type: 'success'
                      });
                      console.log(this.serverListData)
                      this.removeServerByIdAndType(this.serverListData, data.id, data.type)
                    } else {
                      this.$notify.error({})
                    }
                  })
              } else if (data.type == "group") {
                axios.post('/del_group', data)
                  .then(response => {
                    if (response.data.status == 'success') {
                      this.$notify({
                        title: '成功',
                        message: response.data.message,
                        type: 'success'
                      });
                    } else {
                      this.$notify.error({})
                    }
                  })
                // 遍历数组，找到并移除指定id的字典
                for (let i = 0; i < this.serverListData.length; i++) {
                  if (this.serverListData[i].id === data.id && this.serverListData[i].type === 'group') {
                    this.serverListData.splice(i, 1);
                    break; // 找到后就退出循环
                  }

                }
              }
            }
          }
        ],
        event,
        custonClass: "custom-class",
        zIndex: 20003,
        minWidth: 200
      })
    },

    //更新服务器列表
    UpdateServerList(newVal) {
      if (newVal) {
        axios.get('/get_server_list')
          .then(response => {
            this.serverListData = response.data;
          })
          .catch(error => {
            console.error('请求失败:', error);
          });
      }
    },

    //获取添加服务器时候的key内容
    getKey(event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          this.addServerForm.key_content = e.target.result;
        };
        reader.readAsText(file);
      }
    },

    //取消添加服务器
    cancelAddServer() {
      this.dialogAddServerFormVisible = false;
      this.addServerForm = {
        name: '',
        ip: '',
        id: '',
        port: '',
        username: '',
        password: '',
        key: '',
        key_content: '',
        passphrase: '',
        group_id: '',
        status: '',
      };
    },

    //添加服务器
    addServer() {
      if (!this.addServerForm.key && !this.addServerForm.password) {
        this.$notify.error({
          title: '错误',
          message: '密码或密钥必须填写一个'
        });
        return;
      }
      if (!this.addServerForm.name || !this.addServerForm.ip || !this.addServerForm.port || !this.addServerForm.username || !this.addServerForm.group_id) {
        this.$notify.error({
          title: '错误',
          message: "缺少关键数据，请检查名称、ip、端口、用户名、分组名称！",
        });
        return;
      };
      axios.post('/add_server', this.addServerForm)
        .then(response => {
          if (response.data.status == 'success') {
            this.dialogAddServerFormVisible = false;
            this.$notify({
              title: '成功',
              message: response.data.message,
              type: 'success'
            });
            this.UpdateServerList(true);
          } else {
            this.dialogAddServerFormVisible = true;
            this.$notify.error({
              title: '失败',
              message: response.data.message
            })
          }
        });
      this.addServerForm = {
        name: '',
        ip: '',
        id: '',
        port: '',
        username: '',
        password: '',
        key: '',
        key_content: '',
        passphrase: '',
        group_id: '',
        status: '',
      };
    },

    //添加服务器分组
    addGroup() {
      if (!this.addGroupForm.name) {
        return;
      }
      axios.post('/add_group', this.addGroupForm)
        .then(response => {
          this.dialogAddGroupFormVisible = false;
          if (response.data.status == 'success') {
            this.$notify({
              title: '成功',
              message: response.data.message,
              type: 'success'
            });
            this.addGroupForm = {
              ip: "",
              name: "",
            };
            this.UpdateServerList(true);
          } else {
            this.$notify.error({
              title: '失败',
              message: response.data.message
            });
          }
        })
        .catch(error => {
          console.error('请求失败:', error);
        });
      this.addGroupForm = {
        ip: "",
        name: "",
        status: ""
      }
    },

    //连接服务器添加标签页
    connectedServer(data) {
      if (data.type == "server") {
        this.nodeCount++;
        if (this.preNodeId && this.nodeCount >= 2) {
          this.curNodeId = data.ip
          this.nodeCount = 0;
          if (this.curNodeId === this.preNodeId) {
            let newTabName = ++this.tabIndex + '';
            this.editableTabs.push({
              title: data.label,
              name: newTabName,
              id: data.id,
              content: '<iframe src="/ssh?id=' + data.id + '" title="a"></iframe>'
            })
            this.now_server_id = data.id;
            this.editableTabsValue = newTabName;
            this.curNodeId = null;
            this.preNodeId = null;
            //检查服务器监控状态
            axios.post('/get_server_monitor_data', { id: data.id }).then(response => {
              if (response.data.status == 'success') {
                console.log(response.data);
                var cpu = parseInt(response.data.data.cpu.replace('%', ''));
                var memory = parseInt(response.data.data.memory.replace('%', ''));
                var netCardTableData = response.data.data.net_card;
                var devTableData = response.data.data.dev;
                //判断CPU使用率
                if (cpu >= 80 && cpu < 90) {
                  this.addNotification('错误', '主机：' + data.label + '[' + data.ip + ']<br>CPU使用率超过80%', 'warning')
                } else if (cpu >= 90) {
                  this.addNotification('错误', '主机：' + data.label + '[' + data.ip + ']<br>CPU使用率超过90%', 'error')
                }
                //判断内存使用率
                if (memory >= 80 && memory < 90) {
                  this.addNotification('错误', '主机：' + data.label + '[' + data.ip + ']<br>内存使用率超过80%', 'warning')
                } else if (memory >= 90) {
                  this.addNotification('错误', '主机：' + data.label + '[' + data.ip + ']<br>内存使用率超过90%', 'error')
                }
                //判断磁盘使用率
                for (let i = 0; i < devTableData.length; i++) {
                  dev_data = devTableData[i]
                  var dev = dev_data.dev
                  var use = dev_data.use.replace('%', '');
                  if (use >= 80 && use < 90) {
                    this.addNotification('错误', '主机：' + data.label + '[' + data.ip + ']<br>磁盘:' + dev + '<br>使用率超过80%', 'warning')
                  } else if (use >= 90) {
                    this.addNotification('错误', '主机：' + data.label + '[' + data.ip + ']<br>磁盘:' + dev + '<br>使用率超过90%', 'error')
                  }
                }


              }
            }).catch(error => {
              console.error('Error fetching server data:', error);
            });
            return;
          }
        }
        this.preNodeId = data.ip;
        this.nodeTimer = setTimeout(() => {
          this.preNodeId = null;
          this.curNodeId = null;
        }, 300);
      }
    },

    //标签页删除和添加
    handleTabsEdit(targetName, action) {
      if (action === 'add') {
        this.serverManagementDrawer = true;
      }
      if (action === 'remove') {
        let tabs = this.editableTabs;
        let activeName = this.editableTabsValue;
        if (activeName === targetName) {
          tabs.forEach((tab, index) => {
            if (tab.name === targetName) {
              let nextTab = tabs[index + 1] || tabs[index - 1];
              if (nextTab) {
                activeName = nextTab.name;
              }
            }
          });
        }
        this.editableTabsValue = activeName;
        this.editableTabs = tabs.filter(tab => tab.name !== targetName);
      }
    },

    //初始化标签页拖拽
    initSortable() {
      const el = document.querySelector('#ServerConnetcTab .el-tabs__nav');
      Sortable.create(el);
    },
    //通知延迟显示（防样式重叠）
    showNextNotification() {
      if (notificationQueue.length > 0 && !isShowingNotification) {
        const { title, message, type } = notificationQueue.shift();
        isShowingNotification = true;

        this.$notify({
          title,
          message,
          type,
          dangerouslyUseHTMLString: true,
          duration: 0, // 持续时间设置为无限
          position: 'bottom-right'
        });

        // 使用 setTimeout 来延迟下一条通知的显示
        setTimeout(() => {
          isShowingNotification = false;
          this.showNextNotification(); // 尝试显示队列中的下一个通知
        }, 500);
      }
    },
    //添加通知
    addNotification(title, message, type) {
      notificationQueue.push({ title, message, type });
      this.showNextNotification(); // 尝试显示队列中的第一个通知
    },
    //ip复制按钮
    ipCopy() {
      navigator.clipboard.writeText(this.ip);
    }
  },
  mounted() {
    this.initSortable();
    this.UpdateServerList(true);
    davin = this;
    // 对上部标签的右键点击事件进行监听
    document.querySelector('#ServerConnetcTab').oncontextmenu = event => {
      this.$contextmenu({
        items: [{
          label: "克隆",
          onClick: () => {
            if (String(event.target.getAttribute('id')).includes('tab-')) {
              let newTabName = ++this.tabIndex + '';
              selectedId = event.target.getAttribute('id');
              for (let i = 0; i < this.editableTabs.length; i++) {
                if ('tab-' + this.editableTabs[i].name == selectedId) {
                  newTabData = this.editableTabs[i];
                  this.editableTabs.push({
                    title: newTabData.title,
                    name: newTabName,
                    id: newTabName,
                    content: newTabData.content
                  });
                };
              };
              this.editableTabsValue = newTabName;
            }
          }
        },
        {
          label: "关闭所有标签",
          onClick: () => {
            this.editableTabs = [
              {
                title: '简介',
                name: '1',
                id: '0',
                content: tab
              },
            ];
            this.editableTabsValue = '1';
          }
        }
        ],
        event,
        custonClass: "custom-class",
        zIndex: 3,
        minWidth: 200
      });
      return false;
    };

    //加入ftp按钮
    sftp_button = document.querySelector('#ServerConnetcTab .el-tabs__header')
    sftp_button.insertAdjacentHTML('afterbegin', `<span id="sftp_button" class="el-tabs__new-tab"><i class="el-icon-folder-opened"></i></sapn>`)
    //点击ftp按钮事件
    document.getElementById('sftp_button').onclick = function () {
      davin._data.sftpDrawer = true;
    };

    //加入下载任务按钮
    task_button = document.querySelector('#ServerConnetcTab .el-tabs__header')
    task_button.insertAdjacentHTML('afterbegin', `<span id="task_button" class="el-tabs__new-tab"><svg t="1737514224378" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="6311" width="16" height="16"><path d="M832 419.2c0-3.2 0-3.2 0 0 0-144-115.2-256-256-256-99.2 0-185.6 57.6-227.2 140.8-19.2-12.8-41.6-16-64-16-89.6 0-160 70.4-160 160 0 12.8 3.2 28.8 6.4 41.6-76.8 25.6-131.2 96-131.2 182.4 0 105.6 86.4 192 192 192h320l-256-256h128v-192h256v192h128l-256 256h320v-3.2c108.8-16 192-108.8 192-220.8 0-115.2-83.2-208-192-220.8z" fill="#cdcdcd" p-id="6312"></path></svg></sapn>`)
    //点击下载任务按钮事件
    document.getElementById('task_button').onclick = function () {
      davin._data.transmit = true;
    };
    // 定义一个处理函数来响应窗口尺寸变化
    function handleResize() {
      const Height = Math.floor(window.innerHeight / 4.75);
      console.log(Height);
      davin._data.table_height = Height;
    }

    window.addEventListener('resize', handleResize);
  },
})