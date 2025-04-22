import os
from datetime import datetime
import json

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import pytz
from routes.boss import boss_bp

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 启用CORS支持

# 确保logs目录存在
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置
app.config.update(DEBUG=os.getenv("FLASK_DEBUG", "True").lower() == "true", SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev_secret_key"))


# 上下文处理器
@app.context_processor
def inject_now():
    """向所有模板注入当前时间"""
    return {'now': datetime.now()}


# 注册蓝图
app.register_blueprint(boss_bp)


# 路由
@app.route("/", methods=["GET"])
def index():
    """首页路由 - 菜单目录"""
    return render_template('index.html', title='为老板服务的心')


@app.route("/logs", methods=["GET"])
def logs():
    """日志查看页面 - 列出所有日志文件"""
    log_files = []
    # 设置GMT+8时区
    tz = pytz.timezone('Asia/Shanghai')

    for file in os.listdir(logs_dir):
        if os.path.isfile(os.path.join(logs_dir, file)):
            # 获取UTC时间并转换为GMT+8
            utc_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(logs_dir, file)))
            gmt8_time = utc_time.replace(tzinfo=pytz.utc).astimezone(tz)

            log_files.append({'name': file, 'size': os.path.getsize(os.path.join(logs_dir, file)), 'modified': gmt8_time})
    # 按修改时间逆序排序
    log_files.sort(key=lambda x: x['modified'], reverse=True)
    return render_template('logs.html', title='老板的日志', log_files=log_files)


@app.route("/logs/<filename>", methods=["GET"])
def view_log(filename):
    """查看特定日志文件内容"""
    file_path = os.path.join(logs_dir, filename)
    raw = request.args.get('raw', '0') == '1'

    if os.path.exists(file_path) and os.path.isfile(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 如果不是原始模式，处理ANSI转义序列，转换为HTML
        if not raw:
            content = convert_ansi_to_html(content)

        return render_template('log_view.html', title=f'老板正在查看 - {filename}', filename=filename, content=content, raw=raw)
    return render_template('error.html', error_code=404, error_message="日志文件未找到", error_description="请求的日志文件不存在或已被删除。"), 404


def convert_ansi_to_html(text):
    """根据日志内容特点添加颜色，使日志更易读"""
    import re

    # 替换HTML特殊字符
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # 将换行符转换为HTML换行
    text = text.replace('\n', '<br>')

    # 创建HTML结构
    html_parts = []

    # 按行处理
    lines = text.split('<br>')
    for line in lines:
        if not line.strip():
            html_parts.append('<br>')
            continue

        # 尝试匹配常见的日志格式: 日期时间 - 级别 - 消息
        log_pattern = r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+-\s+([A-Z]+)\s+-\s+(.*)$'
        match = re.match(log_pattern, line)

        if match:
            timestamp, level, message = match.groups()

            # 添加带颜色的时间戳
            html_line = f'<span style="color: #7ed321;">{timestamp}</span>'

            # 添加带颜色的日志级别
            level_color = {
                'DEBUG': '#8a8a8a',  # 灰色
                'INFO': '#4a90e2',  # 蓝色
                'WARNING': '#f5a623',  # 黄色
                'ERROR': '#d0021b',  # 红色
                'CRITICAL': '#b10dc9',  # 紫色
                'EXCEPTION': '#d0021b'  # 红色
            }.get(level, '#ffffff')

            html_line += f' - <span style="color: {level_color}; font-weight: bold;">{level}</span>'

            # 处理消息部分
            if message:
                # 处理HTTP请求方法
                message = re.sub(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', r'<span style="color: #f8e71c; font-weight: bold;">\1</span>', message)

                # 处理URL
                message = re.sub(r'(https?://[^\s<>"]+)', r'<span style="color: #4a90e2; text-decoration: underline;">\1</span>', message)

                # 处理HTTP状态码
                message = re.sub(
                    r'(HTTP/[\d\.]+\s)(\d{3})(\s\w+)',
                    lambda m: m.group(1) +
                    f'<span style="color: {"#7ed321" if m.group(2).startswith("2") else "#f5a623" if m.group(2).startswith("3") else "#d0021b"}; font-weight: bold;">{m.group(2)}</span>'  # pylint: disable=line-too-long
                    + m.group(3),
                    message)

                # 处理引号内的内容，但跳过已经包含样式的部分
                # 先检查是否包含样式标记
                if not re.search(r'"color: #[a-f0-9]+;', message):
                    # 如果不包含样式标记，才处理引号内的内容
                    message = re.sub(r'"([^"]*)"',
                                     r'<span style="color: #9013fe;">"</span><span style="color: #9013fe;">\1</span><span style="color: #9013fe;">"</span>',
                                     message)

                html_line += f' - {message}'

            html_parts.append(html_line)
        else:
            # 如果不匹配标准格式，简单地添加一些基本颜色
            # 处理日期时间
            colored_line = re.sub(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})', r'<span style="color: #7ed321;">\1</span>', line)

            # 处理HTTP请求方法
            colored_line = re.sub(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', r'<span style="color: #f8e71c; font-weight: bold;">\1</span>', colored_line)

            # 处理URL
            colored_line = re.sub(r'(https?://[^\s<>"]+)', r'<span style="color: #4a90e2; text-decoration: underline;">\1</span>', colored_line)

            # 处理日志级别关键字
            for level, color in {
                    'DEBUG': '#8a8a8a',
                    'INFO': '#4a90e2',
                    'WARNING': '#f5a623',
                    'ERROR': '#d0021b',
                    'CRITICAL': '#b10dc9',
                    'EXCEPTION': '#d0021b'
            }.items():
                colored_line = re.sub(f'\\b({level})\\b', f'<span style="color: {color}; font-weight: bold;">\\1</span>', colored_line)

            # 处理引号内的内容，但跳过已经包含样式的部分
            # 先检查是否包含样式标记
            if not re.search(r'"color: #[a-f0-9]+;', colored_line):
                # 如果不包含样式标记，才处理引号内的内容
                colored_line = re.sub(r'"([^"]*)"',
                                      r'<span style="color: #9013fe;">"</span><span style="color: #9013fe;">\1</span><span style="color: #9013fe;">"</span>',
                                      colored_line)

            html_parts.append(colored_line)

    return '<br>'.join(html_parts)


@app.route("/boss", methods=["GET"])
def boss_commands():
    """老板指令页面"""
    return render_template('boss.html', title='老板指令')


@app.route("/create_boss_order", methods=["POST"])
def create_boss_order():
    """创建老板指令并直接同步调用脚本生成服务"""
    try:
        # 获取请求数据
        data = request.get_json()
        content = data.get('content', '').strip()

        # 解析 JSON 内容
        order_data = json.loads(content)

        # 导入写稿服务
        from services.write_script_service import WriteScriptService

        # 验证写作方向是否存在
        writing_direction = order_data.get('writing_direction', '')
        if not writing_direction:
            return jsonify({'success': False, 'error': '写作方向不能为空！'})

        # 获取其他参数
        script_length = order_data.get('options', {}).get('script_length', 250)
        prompt_file = order_data.get('options', {}).get('promot_file', 'script_prompts/write_script_agent.prompt')

        # 初始化写稿服务并调用
        write_script_service = WriteScriptService()
        script_result = write_script_service.write_script(writing_direction=writing_direction, script_length=script_length, prompt_file=prompt_file)

        if not script_result:
            return jsonify({'success': False, 'error': '生成脚本失败，请查看日志了解详情'})

        # 返回成功结果及生成的内容
        return jsonify({'success': True, 'title': script_result.title, 'content': script_result.content})

    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': '请求内容格式不正确，请提供有效的JSON'})
    except Exception as e:
        app.logger.error(f"创建老板指令失败: {str(e)}")
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'})


# 错误处理
@app.errorhandler(404)
def not_found(error):
    """处理404错误"""
    app.logger.warning(f"404错误: {str(error)}, 路径: {request.path}")
    return render_template('error.html', error_code=404, error_message="页面未找到", error_description="您请求的页面不存在或已被移动。", error_detail=str(error)), 404


@app.errorhandler(500)
def server_error(error):
    """处理500错误"""
    app.logger.error(f"500错误: {str(error)}", exc_info=True)
    return render_template('error.html',
                           error_code=500,
                           error_message="服务器错误",
                           error_description="服务器遇到了一个错误。请稍后再试。",
                           error_detail=str(error) if app.debug else None), 500


# 添加通用错误处理
@app.errorhandler(Exception)
def handle_exception(error):
    """处理其他所有未捕获的异常"""
    app.logger.error(f"未捕获的异常: {str(error)}", exc_info=True)
    return render_template('error.html',
                           error_code=500,
                           error_message="服务器错误",
                           error_description="服务器遇到了一个意外错误。请稍后再试。",
                           error_detail=str(error) if app.debug else None), 500


# 主程序入口
if __name__ == "__main__":
    try:
        port = int(os.getenv("FLASK_PORT", "5001"))
    except ValueError:
        app.logger.error("无效的端口号配置，使用默认端口 5001")
        port = 5001
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    app.run(host=host, port=port)
