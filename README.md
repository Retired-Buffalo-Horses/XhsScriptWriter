# 小红书脚本生成器

输入写作的方向，一键生成小红书用的文章脚本。

## 安装与设置

1. 克隆仓库
2. 安装依赖: `pip install -r requirements.txt`
3. 通过复制 `.env.sample` 来创建 `.env` 文件
4. 将你的写作指示存为 `script_prompts/write_script_agent.prompt` ，系统每次写作时都会参考你提供的写作提示
5. 放一些例文到 `script_sample.txt` 文件，系统每次写作时都会参考你事先提供的例文
6. 运行应用: `python flask_app.py`

## 访问控制

系统需要输入正确的访问码才能访问功能页面。访问码在 `.env` 文件中通过 `ACCESS_CODE` 环境变量设置。