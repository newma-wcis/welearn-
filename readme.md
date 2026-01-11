# WeLearn Pro - WeLearn 随行课堂辅助工具

WeLearn Pro 是一个基于 Python 的自动化辅助工具，旨在简化 [WeLearn 随行课堂](http://welearn.sflep.com/ "null") 的繁琐操作。它通过模拟 HTTP 请求，实现了课程信息的自动获取和学习进度的同步。

> ⚠️ **免责声明**：本项目仅供 Python 学习与技术交流使用。请勿用于商业用途或破坏平台公平性。使用本工具产生的任何后果由使用者自行承担。

## ✨ 功能特性

- **多模式登录**：支持 SSO 账号密码自动登录（自动处理加密与重定向）及 Cookie 手动登录。

- **智能探测**：
  
  - 自动解析课程 URL 提取 CID 和 ClassID。
  
  - 自动通过个人主页跳转逻辑获取 UserID。

- **全自动流程**：
  
  - 自动遍历单元与小节。
  
  - 自动激活未开始的章节。
  
  - 自动提交满分记录（支持盲打模式）。

- **高鲁棒性**：内置重试机制，自动处理网络波动和 SSL 错误。

## 🛠️ 安装与使用

1. **克隆仓库**
   
   ```
   git clone [https://github.com/你的用户名/WeLearn-Pro.git](https://github.com/你的用户名/WeLearn-Pro.git)
   cd WeLearn-Pro
   ```

2. **安装依赖**
   
   ```
   pip install -r requirements.txt
   ```

3. **运行程序**
   
   ```
   python welearn_pro.py
   ```

4. **操作指引**
   
   - 按提示选择登录方式（推荐使用账号密码）。
   
   - 粘贴你需要学习的课程主页链接（例如：`http://welearn.sflep.com/Student/StudyCourse.aspx?...`）。
   
   - 确认解析出的用户信息无误后，输入 `y` 开始运行。

## 📝 常见问题

- **Q: 登录失败怎么办？**
  
  - A: 可能是学校的 SSO 接口有特殊限制，请尝试选择“手动输入 Cookie”模式。

- **Q: 程序卡在“正在探测 User ID”？**
  
  - A: 请确保你的账号已加入该班级，且网络能正常访问 WeLearn 个人主页。

## 📄 开源协议

本项目遵循 [MIT License](https://www.google.com/search?q=LICENSE "null") 开源协议。
