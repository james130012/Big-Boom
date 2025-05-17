import webview
import json
import os
import logging
import requests
import re
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# 定义用于LLM提示词的基础模板
PROMPT_TEMPLATE_BASE = """你是一个专业的Web前端开发助手。你的任务是帮助用户修改HTML网页的指定部分（如动画、样式、文本等），实现用户指定的功能，确保不影响其他组件（其他动画、文本、布局）。网页用于论文解读，包含HTML5、CSS、JavaScript和MathJax公式。

**重要指令**：
1. 返回严格的JSON格式，遵循下方结构，所有字符串值用双引号。
2. 若输入HTML为空或无效，返回 {"status": "error", "message": "无效或空HTML", "modules": [], "modification_manual": "", "modified_code": {}}.
3. **任务详情**：
   - **输入**：用户提供HTML代码和修改指令（{specific_instruction}）。
   - **目标**：根据修改指令识别目标元素（如特定动画、样式、文本）并实现新功能。
   - **要求**：
     - 动态识别目标元素的HTML、CSS、JS及关联项（如按钮、父容器、依赖样式/脚本）。
     - 生成新代码（HTML、CSS、JS）实现用户指定的功能。
     - 提供分步修改说明书，明确替换位置（行号或上下文）、添加/删除代码。
     - 确保不影响其他组件（如其他动画、布局、全局样式）。
     - 若修改涉及MathJax公式（如动画4、8），确保渲染正常（如触发MathJax.typesetPromise）。
   - **输出内容**：
     - **模块**：目标元素的模块，包含：
       - id：唯一标识（如"animation_box_1"或"body_styles"）。
       - description：模块描述（中文，如“动画1模块”或“页面背景样式”）。
       - html：当前HTML（目标元素及其子元素）。
       - css：相关CSS类/选择器列表。
       - js：相关JS函数或脚本。
       - associated_elements：关联元素（如按钮、描述、父容器）。
       - dependencies：依赖项（如全局样式、脚本）。
     - **新代码**：实现新功能的代码，包含：
       - html：新HTML（替换目标元素）。
       - css：新CSS（添加/修改样式）。
       - js：新JS（替换/添加函数）。
       - associated_elements：更新的关联元素（如按钮、描述）。
     - **修改说明书**：分步指南，包含：
       - 替换HTML的位置（行号或上下文）。
       - 添加/删除CSS（具体样式）。
       - 替换/添加JS（具体函数）。
       - 更新关联元素（如按钮、描述）。
       - 确保其他组件不受影响的注意事项。
4. **模块识别**：
   - 根据{specific_instruction}定位目标元素（如`<div class="animation-box" id="anim1-box">`或`body`）。
   - 分析关联项：父容器（如`<div class="animation-container">`）、按钮（如`<button onclick="playAnim1()">`）、描述（如`<p>`）、依赖样式（如`.animation-box`）、脚本（如`playAnim1`）。
   - 不修改无关元素（如其他动画、`<h1>`、`<div class="container">`）。
5. **新代码生成**：
   - 根据{specific_instruction}生成新HTML、CSS、JS。
   - 保留必要接口（如动画的`id="anim1-box"`、JS函数名`playAnim1`）。
   - 使用特定选择器（如`#anim1-box .cube`）避免影响其他元素。
   - 确保新代码适配父容器和全局样式（如`.animation-box`的`min-height: 150px`）。
6. **修改说明书**：
   - 指明替换位置（如“替换第100-104行HTML”）。
   - 列出CSS添加/删除（如“删除`.brain-outline`，添加`.cube`”）。
   - 指明JS替换/添加（如“替换`playAnim1`”）。
   - 说明关联元素更新（如“替换按钮为`<button onclick="playAnim1()">改变颜色</button>`”）。
   - 强调隔离措施（如“使用`#anim1-cube`避免影响其他动画”）。
7. **约束**：
   - 确保新代码与现有结构兼容（如保留父容器结构）。
   - 避免修改全局样式（如`body`、`.container`）或无关脚本（如`playAnim2`），除非指令明确要求。
   - 若涉及MathJax，添加渲染代码（如`MathJax.typesetPromise(['#anim1-box'])`）。
8. **输出JSON结构**：
```json
{
  "status": "<success 或 error>",
  "message": "<简要状态消息>",
  "modules": [
    {
      "id": "<模块ID，如animation_box_1>",
      "description": "<模块中文描述>",
      "html": "<当前目标元素HTML>",
      "css": ["<相关CSS类/选择器>", "..."],
      "js": "<相关JS代码>",
      "associated_elements": {
        "button": "<按钮HTML，若无则空>",
        "description": "<描述<p> HTML，若无则空>",
        "parent_container": "<父容器HTML，若无则空>",
        "other": "<其他关联元素，若无则空>"
      },
      "dependencies": ["<依赖项，如.animation-box样式>"
    }
  ],
  "modification_manual": "<分步修改指南>",
  "modified_code": {
    "html": "<新HTML>",
    "css": "<新CSS>",
    "js": "<新JS>",
    "associated_elements": {
      "button": "<新按钮HTML，若无则空>",
      "description": "<新描述<p> HTML，若无则空>",
      "parent_container": "<新父容器HTML，若无则空>",
      "other": "<其他新关联元素，若无则空>"
    }
  }
}

示例输入和输出：
输入HTML（简化）：

html

<div class="animation-container">
    <h3>动画1</h3>
    <div class="animation-box" id="anim1-box">
        <div class="brain-outline"></div>
    </div>
    <button onclick="playAnim1()">播放</button>
    <p>声波进入大脑</p>
</div>
<style>
    .animation-box { width: 90%; min-height: 150px; }
    .brain-outline { width: 100px; height: 100px; }
</style>
<script>
    function playAnim1() { /* 原逻辑 */ }
</script>

输入指令：{specific_instruction} = "将动画1替换为旋转立方体，点击改变颜色（蓝→红→绿）。"
输出：
json

{
  "status": "success",
  "message": "动画1修改成功",
  "modules": [
    {
      "id": "animation_box_1",
      "description": "动画1模块，包含HTML、CSS、JS、按钮和描述",
      "html": "<div class=\"animation-box\" id=\"anim1-box\"><div class=\"brain-outline\"></div></div>",
      "css": [".brain-outline", ".animation-box"],
      "js": "function playAnim1() { /* 原逻辑 */ }",
      "associated_elements": {
        "button": "<button onclick=\"playAnim1()\">播放</button>",
        "description": "<p>声波进入大脑</p>",
        "parent_container": "<div class=\"animation-container\">...</div>",
        "other": ""
      },
      "dependencies": [".animation-box样式"]
    }
  ],
  "modification_manual": "1. 替换第3-5行HTML为：<div class=\"animation-box\" id=\"anim1-box\"><div class=\"cube\" id=\"anim1-cube\"></div></div>\n2. 在<style>中，删除.brain-outline，添加：#anim1-cube { width: 100px; height: 100px; background-color: #3498db; animation: rotate 2s infinite; perspective: 1000px; transform-style: preserve-3d; cursor: pointer; } @keyframes rotate { from { transform: rotateY(0deg); } to { transform: rotateY(360deg); } }\n3. 在<script>中，替换playAnim1为：function playAnim1() { const cube = document.getElementById('anim1-cube'); const colors = ['#3498db', '#e74c3c', '#2ecc71']; let current = 0; cube.onclick = () => { current = (current + 1) % colors.length; cube.style.backgroundColor = colors[current]; }; }\n4. 替换第6行按钮为：<button onclick=\"playAnim1()\">改变颜色</button>\n5. 替换第7行描述为：<p>旋转立方体改变颜色，展示语言处理阶段</p>\n6. 确保其他动画、文本和布局不变，使用#anim1-cube选择器。",
  "modified_code": {
    "html": "<div class=\"animation-box\" id=\"anim1-box\"><div class=\"cube\" id=\"anim1-cube\"></div></div>",
    "css": "#anim1-cube { width: 100px; height: 100px; background-color: #3498db; animation: rotate 2s infinite; perspective: 1000px; transform-style: preserve-3d; cursor: pointer; }\n@keyframes rotate { from { transform: rotateY(0deg); } to { transform: rotateY(360deg); } }",
    "js": "function playAnim1() { const cube = document.getElementById('anim1-cube'); const colors = ['#3498db', '#e74c3c', '#2ecc71']; let current = 0; cube.onclick = () => { current = (current + 1) % colors.length; cube.style.backgroundColor = colors[current]; }; }",
    "associated_elements": {
      "button": "<button onclick=\"playAnim1()\">改变颜色</button>",
      "description": "<p>旋转立方体改变颜色，展示语言处理阶段</p>",
      "parent_container": "",
      "other": ""
    }
  }
}

空输入处理：
返回：{"status": "error", "message": "无效或空HTML", "modules": [], "modification_manual": "", "modified_code": {}}

输入HTML：
html

{user_html_code}

修改指令：
{specific_instruction}
请严格按上述JSON结构返回结果。
"""


DEFAULT_API_CONFIG = {
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "default_model": "google/gemini-2.5-flash-preview",
    "base_headers": {"Content-Type": "application/json"},
    "request_timeout_seconds": 120,
    "llm_temperature": 0.1,
    "llm_max_tokens": 4096,
    "max_modules_to_process_frontend": 10
}

class Api:
    def __init__(self):
        self.original_html_content_py = ""
        self.api_config = self._load_api_config()
        self.site_url = os.getenv("YOUR_SITE_URL", "http://localhost:8003/default-app")
        self.site_name = os.getenv("YOUR_SITE_NAME", "DefaultModularizerAppV3")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.modified_modules = {}  # 存储修改后的模块
        self.module_definitions = []  # 存储模块定义

    def _load_api_config(self, config_path="api_config.json"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logging.info(f"成功加载API配置文件: {config_path}")
                return {**DEFAULT_API_CONFIG, **config}
        except FileNotFoundError:
            logging.warning(f"API配置文件 '{config_path}' 未找到，使用默认配置")
            return DEFAULT_API_CONFIG
        except json.JSONDecodeError:
            logging.warning(f"API配置文件 '{config_path}' 格式错误，使用默认配置")
            return DEFAULT_API_CONFIG
        except Exception as e:
            logging.warning(f"加载API配置文件出错: {e}，使用默认配置")
            return DEFAULT_API_CONFIG

    def _add_comments_to_html(self, original_html, definitions):
        if not definitions:
            return original_html

        valid_definitions = []
        for d in definitions:
            if not (d.get("start_comment") and d.get("end_comment")):
                logging.debug(f"跳过模块 {d.get('id', 'Unknown')}，缺少 start_comment 或 end_comment")
                continue
            if not (("start_line" in d and "end_line" in d) or ("start_char" in d and "end_char" in d)):
                logging.debug(f"跳过模块 {d.get('id', 'Unknown')}，缺少有效起止位置")
                continue
            valid_definitions.append(d)

        sorted_definitions = sorted(
            valid_definitions,
            key=lambda x: x.get("end_line", x.get("end_char", 0)),
            reverse=True
        )

        lines = original_html.splitlines(keepends=True)
        modified_html = original_html
        processed_ids = set()

        for defi in sorted_definitions:
            module_id = defi.get("id")
            start_comment_text = defi.get("start_comment", "").strip()
            end_comment_text = defi.get("end_comment", "").strip()
            start_line = defi.get("start_line")
            end_line = defi.get("end_line")
            start_char = defi.get("start_char")
            end_char = defi.get("end_char")

            if not all([module_id, start_comment_text, end_comment_text]):
                logging.debug(f"跳过模块 {module_id or 'Unknown'}，定义字段不完整")
                continue

            if module_id in processed_ids:
                logging.debug(f"模块 '{module_id}' 已处理，跳过")
                continue

            start_marker_tag = f"<!-- {start_comment_text} -->\n"
            end_marker_tag = f"\n<!-- {end_comment_text} -->"

            try:
                if start_line is not None and end_line is not None:
                    start_line_1based = start_line
                    end_line_1based = end_line
                    if not (1 <= start_line_1based <= len(lines) and 1 <= end_line_1based <= len(lines)):
                        logging.warning(f"模块 '{module_id}' 的行号无效 (start_line: {start_line}, end_line: {end_line})")
                        continue
                    start_char_pos = sum(len(line) for line in lines[:start_line_1based-1])
                    end_char_pos = sum(len(line) for line in lines[:end_line_1based])
                    modified_html = (
                        modified_html[:start_char_pos] +
                        start_marker_tag +
                        modified_html[start_char_pos:end_char_pos] +
                        end_marker_tag +
                        modified_html[end_char_pos:]
                    )
                elif start_char is not None and end_char is not None:
                    if not (0 <= start_char <= end_char <= len(modified_html)):
                        logging.warning(f"模块 '{module_id}' 的字符索引无效 (start_char: {start_char}, end_char: {end_char})")
                        continue
                    modified_html = (
                        modified_html[:start_char] +
                        start_marker_tag +
                        modified_html[start_char:end_char] +
                        end_marker_tag +
                        modified_html[end_char:]
                    )
                else:
                    logging.warning(f"模块 '{module_id}' 缺少有效起止位置")
                    continue
                logging.debug(f"已为模块 '{module_id}' 添加注释标记")
                processed_ids.add(module_id)
                lines = modified_html.splitlines(keepends=True)
            except Exception as e:
                logging.error(f"在为模块 '{module_id}' 添加注释时出错: {e}")

        return modified_html

    def _extract_module_content_from_string(self, html_string, module_def):
        module_id = module_def.get('id', 'N/A')
        start_marker_text = module_def.get('start_comment', '').strip()
        end_marker_text = module_def.get('end_comment', '').strip()

        if not start_marker_text or not end_marker_text:
            logging.debug(f"模块 '{module_id}' 缺少标记，跳过")
            return ""

        start_marker = f"<!-- {start_marker_text} -->"
        end_marker = f"<!-- {end_marker_text} -->"

        start_index = html_string.find(start_marker)
        if start_index == -1:
            logging.debug(f"未找到模块 '{module_id}' 的起始标记")
            return ""

        content_start_index = start_index + len(start_marker)
        end_index = html_string.find(end_marker, content_start_index)
        if end_index == -1:
            logging.debug(f"未找到模块 '{module_id}' 的结束标记")
            return ""

        extracted = html_string[content_start_index:end_index].strip()
        extracted = re.sub(r'<!-- LLM_MODULE_(START|END): [a-zA-Z0-9_]+ -->', '', extracted).strip()
        return extracted

    def _generate_skeleton_from_string(self, html_string, modules_to_skeletonize):
        skeleton = html_string
        for i, module_def in enumerate(modules_to_skeletonize):
            module_id = module_def.get('id', f'unknown_module_{i}').strip()
            start_marker_text = module_def.get('start_comment', '').strip()
            end_marker_text = module_def.get('end_comment', '').strip()

            if not start_marker_text or not end_marker_text:
                continue

            start_marker = f"<!-- {start_marker_text} -->"
            end_marker = f"<!-- {end_marker_text} -->"
            placeholder = f"<!-- MODULE_PLACEHOLDER: {module_id} -->"

            start_idx = skeleton.find(start_marker)
            if start_idx == -1:
                continue
            end_idx = skeleton.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                continue

            content_to_replace = skeleton[start_idx:end_idx + len(end_marker)]
            skeleton = skeleton.replace(content_to_replace, placeholder, 1)
        return skeleton

    def analyze_html(self, original_code, specific_instruction=""):
        logging.info("Python API: analyze_html 调用")
        raw_original_code = original_code.strip() if original_code else ""

        if not raw_original_code:
            logging.warning("收到空HTML，返回空响应")
            self.original_html_content_py = ""
            return {
                "status": "error",
                "message": "无效或空HTML",
                "active_module_definitions": [],
                "html_skeleton": "",
                "modified_code": {}
            }

        self.original_html_content_py = raw_original_code
        self.original_html = raw_original_code

        # 第一步：模块化分析
        module_prompt = """分析以下HTML代码，识别潜在的模块（如动画、页眉、页脚、文本块），返回模块定义列表，每个模块包含：
- id：唯一标识（如animation_box_1、header）
- description：模块描述（中文，如“动画1模块”）
- start_line/end_line：模块起止行号
- start_char/end_char：模块起止字符位置
- start_comment/end_comment：注释标记（如<!-- LLM_MODULE_START: id -->）
返回JSON格式：
{
  "module_count_suggestion": <建议处理的模块数>,
  "definitions": [
    {
      "id": "<模块ID>",
      "description": "<描述>",
      "start_line": <起始行>,
      "end_line": <结束行>,
      "start_char": <起始字符>,
      "end_char": <结束字符>,
      "start_comment": "<起始注释>",
      "end_comment": "<结束注释>"
    }
  ]
}
HTML代码：
{user_html_code}
"""
        module_prompt = module_prompt.replace("{user_html_code}", raw_original_code)
        llm_response_data = None

        if not self.openrouter_api_key:
            logging.warning("OPENROUTER_API_KEY 未设置，使用模拟数据")
            mock_defs = [
                {
                    "id": "animation_box_1",
                    "description": "动画1模块",
                    "start_comment": "LLM_MODULE_START: animation_box_1",
                    "end_comment": "LLM_MODULE_END: animation_box_1",
                    "start_line": 100,
                    "end_line": 104,
                    "start_char": 1000,
                    "end_char": 1200
                }
            ]
            llm_response_data = {"module_count_suggestion": len(mock_defs), "definitions": mock_defs}
            html_to_process = self._add_comments_to_html(raw_original_code, llm_response_data["definitions"])
        else:
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name
                }
                payload = {
                    "model": self.api_config.get("default_model"),
                    "messages": [{"role": "user", "content": module_prompt}],
                    "temperature": self.api_config.get("llm_temperature", 0.1),
                    "max_tokens": self.api_config.get("llm_max_tokens", 4096)
                }
                response = requests.post(self.api_config.get("api_url"), headers=headers, json=payload, timeout=self.api_config.get("request_timeout_seconds", 120))
                response.raise_for_status()
                llm_response_data = json.loads(response.json()["choices"][0]["message"]["content"].strip("```json\n").strip("```"))
                html_to_process = self._add_comments_to_html(raw_original_code, llm_response_data["definitions"])
            except Exception as e:
                logging.error(f"模块化分析出错: {e}")
                html_to_process = raw_original_code

        self.original_html_content_py = html_to_process
        self.module_definitions = llm_response_data.get("definitions", []) if llm_response_data else []
        processed_definitions = []
        for module_def in self.module_definitions:
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def)
            processed_definitions.append({**module_def, "original_content": content})

        skeleton = self._generate_skeleton_from_string(self.original_html_content_py, self.module_definitions)

        # 第二步：处理用户指定的修改（如果有）
        modified_code = {}
        modification_manual = ""
        if specific_instruction:
            full_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", raw_original_code).replace("{specific_instruction}", specific_instruction)
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name
                }
                payload = {
                    "model": self.api_config.get("default_model"),
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": self.api_config.get("llm_temperature", 0.1),
                    "max_tokens": self.api_config.get("llm_max_tokens", 4096)
                }
                response = requests.post(self.api_config.get("api_url"), headers=headers, json=payload, timeout=self.api_config.get("request_timeout_seconds", 120))
                response.raise_for_status()
                response_data = json.loads(response.json()["choices"][0]["message"]["content"].strip("```json\n").strip("```"))
                if response_data["status"] == "success" and response_data["modules"]:
                    module_id = response_data["modules"][0]["id"]
                    self.modified_modules[module_id] = {
                        "modified_code": response_data["modified_code"],
                        "modification_manual": response_data["modification_manual"]
                    }
                    modified_code = response_data["modified_code"]
                    modification_manual = response_data["modification_manual"]
            except Exception as e:
                logging.error(f"处理修改指令出错: {e}")
                modified_code = {}
                modification_manual = f"处理指令失败: {str(e)}"

        return {
            "status": "success",
            "message": f"分析完成，识别到 {len(self.module_definitions)} 个模块",
            "active_module_definitions": processed_definitions,
            "html_skeleton": skeleton,
            "modified_code": modified_code,
            "modification_manual": modification_manual
        }

    def integrate_modules(self):
        logging.info("整合模块")
        if not self.original_html_content_py or not self.modified_modules:
            logging.warning("无原始HTML或修改模块")
            return self.original_html_content_py

        final_html = self.original_html_content_py
        for module_id, module_data in self.modified_modules.items():
            modified_html = module_data["modified_code"]["html"]
            associated_elements = module_data["modified_code"]["associated_elements"]

            start_marker = f"<!-- LLM_MODULE_START: {module_id} -->"
            end_marker = f"<!-- LLM_MODULE_END: {module_id} -->"
            start_idx = final_html.find(start_marker)
            end_idx = final_html.find(end_marker, start_idx) + len(end_marker) if start_idx != -1 else -1

            if start_idx != -1 and end_idx != -1:
                final_html = (
                    final_html[:start_idx] +
                    modified_html +
                    final_html[end_idx:]
                )
                logging.debug(f"替换模块 {module_id}")
            else:
                logging.warning(f"未找到模块 {module_id} 的标记，尝试直接替换HTML")
                html_start = final_html.find(modified_html)
                if html_start != -1:
                    html_end = html_start + len(modified_html)
                    final_html = (
                        final_html[:html_start] +
                        modified_html +
                        final_html[html_end:]
                    )

            for key, value in associated_elements.items():
                if value and key in ["button", "description"]:
                    element_start = final_html.find(f'<{key == "description" and "p" or "button"}')
                    element_end = final_html.find('>', element_start) + 1
                    if element_start != -1:
                        final_html = (
                            final_html[:element_start] +
                            value +
                            final_html[element_end:]
                        )
                        logging.debug(f"更新关联元素 {key}")

        return final_html

    def get_modification_manual(self, module_id):
        return self.modified_modules.get(module_id, {}).get("modification_manual", "")

    def get_prompt_template_for_frontend(self):
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code}", "[用户提供的HTML代码将在此处由后端插入]").replace("{specific_instruction}", "[用户提供的修改指令将在此处由前端插入]")
        self.original_html_content_py = html_to_process

        if not llm_response_data or "definitions" not in llm_response_data:
            print("错误: LLM响应数据不完整或格式不正确 (在最终检查中)。")
            return {"status": "error", "message": "LLM响应数据不完整或格式不正确。", "active_module_definitions": [], "html_skeleton": self.original_html_content_py}

        all_defs = llm_response_data.get("definitions", [])
        suggested_count = llm_response_data.get("module_count_suggestion", 0)
        max_allowed_from_config = self.api_config.get("max_modules_to_process_frontend", 10)
        num_to_process = min(suggested_count if suggested_count > 0 else len(all_defs), max_allowed_from_config, len(all_defs))
        current_active_module_definitions = all_defs[:num_to_process]

        processed_active_definitions = []
        print("\n--- 开始处理模块定义 (基于带注释的HTML) ---")
        for module_def in current_active_module_definitions:
            module_id = module_def.get('id', 'N/A')
            llm_start_comment_text = module_def.get('start_comment', '').strip()
            llm_end_comment_text = module_def.get('end_comment', '').strip()

            if not llm_start_comment_text or not llm_end_comment_text:
                print(f"警告: 模块 '{module_id}' 缺少有效的 start_comment 或 end_comment，跳过。")
                continue

            actual_start_marker = f"<!-- {llm_start_comment_text} -->"
            actual_end_marker = f"<!-- {llm_end_comment_text} -->"

            content = self._extract_module_content_from_string(self.original_html_content_py, module_def)

            print(f"DEBUG: 模块ID '{module_id}':")
            print(f"  期望的起始标记: '{actual_start_marker}'")
            print(f"  期望的结束标记: '{actual_end_marker}'")
            print(f"  位置: start_line={module_def.get('start_line', 'N/A')}, end_line={module_def.get('end_line', 'N/A')}, "
                  f"start_char={module_def.get('start_char', 'N/A')}, end_char={module_def.get('end_char', 'N/A')}")
            if not content and (llm_start_comment_text and llm_end_comment_text):
                print(f"  警告: original_content 为空。检查 self.original_html_content_py (前250字符: '{self.original_html_content_py[:250]}...') 中是否存在标记并正确界定内容。")
            print(f"  提取到的 original_content (前100字符): '{content[:100]}...' (长度: {len(content)})")
            processed_active_definitions.append({**module_def, "original_content": content})
        print("--- 结束处理模块定义 ---\n")

        skeleton = self._generate_skeleton_from_string(self.original_html_content_py, current_active_module_definitions)

        print("\nDEBUG: 处理后的活动模块定义 (将发送到前端):")
        print(json.dumps(processed_active_definitions, indent=2, ensure_ascii=False))
        print("---------------------------------------------------\n")

        print("\nDEBUG: 生成的HTML骨架 (将发送到前端):")
        print(skeleton if skeleton else "骨架为空或生成失败。")
        print("---------------------------------------------------\n")

        return {
            "status": "success",
            "message": f"LLM分析完成：识别到 {len(all_defs)} 个潜在模块，将处理 {num_to_process} 个。",
            "active_module_definitions": processed_active_definitions,
            "html_skeleton": skeleton
        }

    def integrate_html(self, skeleton_html, modified_modules_json_string):
        print("Python API: integrate_html 调用。")
        try:
            modified_modules = json.loads(modified_modules_json_string)
        except json.JSONDecodeError as e:
            print(f"错误: 解析 modified_modules_json_string 时发生JSONDecodeError: {e}")
            return {"status": "error", "message": f"无效的JSON (modified_modules): {e}", "final_html": skeleton_html}

        final_html = skeleton_html
        if not isinstance(modified_modules, dict):
            print(f"错误: modified_modules 不是一个字典: {type(modified_modules)}")
            return {"status": "error", "message": "modified_modules 格式错误，应为字典。", "final_html": skeleton_html}

        for module_id, new_content in modified_modules.items():
            placeholder = f"<!-- MODULE_PLACEHOLDER: {module_id} -->"
            new_content_str = str(new_content) if new_content is not None else ""

            if placeholder in final_html:
                final_html = final_html.replace(placeholder, new_content_str)
            else:
                print(f"警告 (integrate_html): 未找到占位符 '{placeholder}'。模块 '{module_id}' 的内容可能未被正确集成。")

        return {"status": "success", "final_html": final_html}

if __name__ == '__main__':
    api = Api()
    logging.info("Starting PyWebview window...")
    window = webview.create_window(
        '代码智能装配流水线',
        'gui.html',
        js_api=api,
        width=1200,
        height=850,
        resizable=True
    )
    logging.info("PyWebview window created, starting...")
    webview.start(debug=True)
    logging.info("PyWebview started.")