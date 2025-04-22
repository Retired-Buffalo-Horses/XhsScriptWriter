import os
from glob import glob

from flask import Blueprint, jsonify, render_template

boss_bp = Blueprint('boss', __name__)


@boss_bp.route('/boss', methods=['GET'])
def boss_commands():
    """老板指令页面"""
    return render_template('boss.html', title='老板指令')


@boss_bp.route('/api/prompts', methods=['GET'])
def get_prompts():
    """获取所有prompt文件列表"""
    try:
        # 获取script_prompts目录下的所有.prompt文件
        prompt_files = glob('script_prompts/*.prompt')
        # 将文件路径转换为相对路径并排序
        prompt_files = sorted([os.path.relpath(f) for f in prompt_files])
        return jsonify({'success': True, 'prompts': prompt_files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
