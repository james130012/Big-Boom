import webview
import webview
import json
import os
import requests
import re
from dotenv import load_dotenv

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
        self.openrouter_api_key = None

    def _load_api_config(self, config_path="api_config.json"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"成功加载API配置文件: {config_path}")
                return {**DEFAULT_API_CONFIG, **config}
        except FileNotFoundError:
            print(f"警告: API配置文件 '{config_path}' 未找到，将使用默认配置。")
            return DEFAULT_API_CONFIG
        except json.JSONDecodeError:
            print(f"警告: API配置文件 '{config_path}' 格式错误，将使用默认配置。")
            return DEFAULT_API_CONFIG
        except Exception as e:
            print(f"警告: 加载API配置文件时发生错误: {e}，将使用默认配置。")
            return DEFAULT_API_CONFIG

    def get_prompt_template_for_frontend(self):
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code}", "[用户提供的HTML代码将在此处由后端插入]")

    def _add_comments_to_html(self, original_html, definitions):
        if not definitions:
            return original_html

        # 验证和过滤有效定义
        valid_definitions = []
        for d in definitions:
            if not (d.get("start_comment") and d.get("end_comment")):
                print(f"DEBUG (_add_comments_to_html): 跳过模块 {d.get('id', 'Unknown')}，缺少 start_comment 或 end_comment。")
                continue
            if not (("start_line" in d and "end_line" in d) or ("start_char" in d and "end_char" in d)):
                print(f"DEBUG (_add_comments_to_html): 跳过模块 {d.get('id', 'Unknown')}，缺少有效的起止位置。")
                continue
            valid_definitions.append(d)

        # 按 end_line 或 end_char 降序排序，确保外层模块先处理
        sorted_definitions = sorted(
            valid_definitions,
            key=lambda x: x.get("end_line", x.get("end_char", 0)),
            reverse=True
        )

        lines = original_html.splitlines(keepends=True)
        modified_html = original_html
        processed_ids = set()

        # 检查位置重叠
        for i, defi in enumerate(sorted_definitions):
            for j, other in enumerate(sorted_definitions[i+1:]):
                if (defi.get("start_line") and other.get("start_line") and
                    defi["start_line"] <= other["end_line"] and other["start_line"] <= defi["end_line"]) or \
                   (defi.get("start_char") and other.get("start_char") and
                    defi["start_char"] <= other["end_char"] and other["start_char"] <= defi["end_char"]):
                    print(f"警告: 模块 '{defi['id']}' 和 '{other['id']}' 位置重叠，可能导致嵌套问题。")

        for defi in sorted_definitions:
            module_id = defi.get("id")
            start_comment_text = defi.get("start_comment", "").strip()
            end_comment_text = defi.get("end_comment", "").strip()
            start_line = defi.get("start_line")
            end_line = defi.get("end_line")
            start_char = defi.get("start_char")
            end_char = defi.get("end_char")

            if not all([module_id, start_comment_text, end_comment_text]):
                print(f"DEBUG (_add_comments_to_html): 跳过模块 {module_id or 'Unknown'}，定义字段不完整。")
                continue

            if module_id in processed_ids:
                print(f"DEBUG (_add_comments_to_html): 模块 '{module_id}' 已处理，跳过。")
                continue

            start_marker_tag = f"<!-- {start_comment_text} -->\n"
            end_marker_tag = f"\n<!-- {end_comment_text} -->"

            try:
                if start_line is not None and end_line is not None:
                    start_line_1based = start_line
                    end_line_1based = end_line

                    if not (1 <= start_line_1based <= len(lines) and 1 <= end_line_1based <= len(lines)):
                        print(f"警告 (_add_comments_to_html): 模块 '{module_id}' 的行号无效 (start_line: {start_line}, end_line: {end_line})。")
                        continue

                    start_char_pos = sum(len(line) for line in lines[:start_line_1based-1])
                    end_char_pos = sum(len(line) for line in lines[:end_line_1based])

                    if start_char_pos >= end_char_pos or end_char_pos > len(modified_html):
                        print(f"警告 (_add_comments_to_html): 模块 '{module_id}' 的字符位置无效 (start_char_pos: {start_char_pos}, end_char_pos: {end_char_pos})。")
                        continue

                    modified_html = (
                        modified_html[:start_char_pos] +
                        start_marker_tag +
                        modified_html[start_char_pos:end_char_pos] +
                        end_marker_tag +
                        modified_html[end_char_pos:]
                    )
                elif start_char is not None and end_char is not None:
                    if not (0 <= start_char <= end_char <= len(modified_html)):
                        print(f"警告 (_add_comments_to_html): 模块 '{module_id}' 的字符索引无效 (start_char: {start_char}, end_char: {end_char})。")
                        continue

                    modified_html = (
                        modified_html[:start_char] +
                        start_marker_tag +
                        modified_html[start_char:end_char] +
                        end_marker_tag +
                        modified_html[end_char:]
                    )
                else:
                    print(f"警告 (_add_comments_to_html): 模块 '{module_id}' 缺少有效的起止位置。")
                    continue

                print(f"DEBUG (_add_comments_to_html): 已为模块 '{module_id}' 添加注释标记 (start: {start_line or start_char}, end: {end_line or end_char})。")
                processed_ids.add(module_id)

                lines = modified_html.splitlines(keepends=True)
            except Exception as e:
                print(f"错误 (_add_comments_to_html): 在为模块 '{module_id}' 添加注释时发生异常: {e}")

        return modified_html

    def _extract_module_content_from_string(self, html_string, module_def):
        module_id = module_def.get('id', 'N/A')
        start_marker_text = module_def.get('start_comment', '').strip()
        end_marker_text = module_def.get('end_comment', '').strip()

        if not start_marker_text or not end_marker_text:
            print(f"DEBUG (_extract_module_content_from_string): 模块 '{module_id}' 缺少标记，跳过。")
            return ""

        start_marker = f"<!-- {start_marker_text} -->"
        end_marker = f"<!-- {end_marker_text} -->"

        start_index = html_string.find(start_marker)
        if start_index == -1:
            print(f"DEBUG (_extract_module_content_from_string): 未找到模块 '{module_id}' 的起始标记。")
            return ""

        content_start_index = start_index + len(start_marker)
        end_index = html_string.find(end_marker, content_start_index)

        if end_index == -1:
            print(f"DEBUG (_extract_module_content_from_string): 未找到模块 '{module_id}' 的结束标记。")
            return ""

        extracted = html_string[content_start_index:end_index].strip()
        # 移除嵌套模块的注释
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

            content_to_replace_with_markers = skeleton[start_idx:end_idx + len(end_marker)]
            skeleton = skeleton.replace(content_to_replace_with_markers, placeholder, 1)
        return skeleton

    def analyze_html(self, original_code):
        print("Python API: analyze_html 调用。")
        raw_original_code = original_code.strip() if original_code else ""

        if not raw_original_code:
            print("警告: 收到的HTML代码为空，将返回空模块定义。")
            self.original_html_content_py = ""
            return {
                "status": "success",
                "message": "输入HTML为空，未识别到模块。",
                "active_module_definitions": [],
                "html_skeleton": ""
            }

        if not ("<" in raw_original_code and ">" in raw_original_code):
            print("警告: 收到的HTML代码不包含有效标签，将返回空模块定义。")
            self.original_html_content_py = raw_original_code
            return {
                "status": "success",
                "message": "输入HTML无效，未识别到模块。",
                "active_module_definitions": [],
                "html_skeleton": raw_original_code
            }

        print(f"DEBUG: 输入HTML (前200字符): '{raw_original_code[:200]}...'")

        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        print(f"DEBUG: 在 analyze_html 中, API Key 是: {'SET' if self.openrouter_api_key else 'NOT SET'}")

        llm_response_data = None
        html_to_process = raw_original_code

        if not self.openrouter_api_key:
            print("警告: OPENROUTER_API_KEY 环境变量未设置。将使用模拟LLM数据。")
            mock_header_content = "<header><h1>模拟页眉内容</h1></header>"
            mock_footer_content = "<footer><p>模拟页脚内容</p></footer>"
            raw_mock_html_input = f"<body>\n{mock_header_content}\n<div>一些中间内容</div>\n{mock_footer_content}\n</body>"

            mock_defs = [
                {
                    "id": "header_mock",
                    "description": "模拟页眉",
                    "start_comment": "LLM_MODULE_START: header_mock",
                    "end_comment": "LLM_MODULE_END: header_mock",
                    "start_line": 2,
                    "end_line": 2,
                    "start_char": 7,
                    "end_char": 32
                },
                {
                    "id": "footer_mock",
                    "description": "模拟页脚",
                    "start_comment": "LLM_MODULE_START: footer_mock",
                    "end_comment": "LLM_MODULE_END: footer_mock",
                    "start_line": 4,
                    "end_line": 4,
                    "start_char": 62,
                    "end_char": 83
                }
            ]
            llm_response_data = {"module_count_suggestion": len(mock_defs), "definitions": mock_defs}
            print(f"DEBUG: 使用模拟数据。原始模拟HTML: '{raw_mock_html_input[:200]}...'")
            if llm_response_data and "definitions" in llm_response_data:
                html_to_process = self._add_comments_to_html(raw_mock_html_input, llm_response_data["definitions"])
            print(f"DEBUG: 模拟数据处理后，带注释的HTML: '{html_to_process[:250]}...'")
        else:
            current_llm_model = os.getenv("DEFAULT_LLM_MODEL", self.api_config.get("default_model"))
            print(f"OpenRouter API密钥已加载。准备调用LLM (模型: {current_llm_model})...")
            full_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", raw_original_code)
            request_headers = self.api_config.get("base_headers", {}).copy()
            request_headers["Authorization"] = f"Bearer {self.openrouter_api_key}"
            if self.site_url: request_headers["HTTP-Referer"] = self.site_url
            if self.site_name: request_headers["X-Title"] = self.site_name
            request_data = {
                "model": current_llm_model,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": self.api_config.get("llm_temperature", 0.1),
                "max_tokens": self.api_config.get("llm_max_tokens", 4096),
            }
            api_url = self.api_config.get("api_url")
            timeout = self.api_config.get("request_timeout_seconds", 120)

            if not api_url:
                print("错误: API URL 未在配置文件中定义。")
                self.original_html_content_py = raw_original_code
                return {"status": "error", "message": "API URL配置缺失。", "active_module_definitions": [], "html_skeleton": raw_original_code}

            try:
                print(f"发送到 OpenRouter. URL: {api_url}, 模型: {request_data['model']}")
                print(f"DEBUG: 发送的提示词 (前500字符): '{full_prompt[:500]}...'")
                response = requests.post(api_url, headers=request_headers, data=json.dumps(request_data), timeout=timeout)
                response.raise_for_status()
                response_json = response.json()

                if 'choices' not in response_json or not response_json['choices']:
                    raise KeyError("LLM响应缺少 'choices' 字段")

                message_content = response_json['choices'][0].get('message', {}).get('content', '')
                if not message_content:
                    raise KeyError("LLM响应缺少 'content' 字段")

                cleaned_json_str = message_content.strip()
                if cleaned_json_str.startswith("```json"):
                    cleaned_json_str = cleaned_json_str[len("```json"):].lstrip()
                elif cleaned_json_str.startswith("```"):
                    cleaned_json_str = cleaned_json_str[len("```"):].lstrip()
                if cleaned_json_str.endswith("```"):
                    cleaned_json_str = cleaned_json_str[:-len("```")].rstrip()

                try:
                    llm_response_data = json.loads(cleaned_json_str)
                except json.JSONDecodeError:
                    print(f"错误: LLM返回的内容不是有效JSON。原始内容: '{cleaned_json_str[:200]}...'")
                    print(f"DEBUG: 完整API响应: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                    raise

                # 处理非预期格式（数组）
                if isinstance(llm_response_data, list):
                    print("警告: LLM返回了一个数组而不是对象，正在尝试转换为预期格式...")
                    normalized_defs = []
                    for defi in llm_response_data:
                        # 规范化字段名
                        if 'start_char_index' in defi:
                            defi['start_char'] = defi.pop('start_char_index')
                        if 'end_char_index' in defi:
                            defi['end_char'] = defi.pop('end_char_index')
                        # 修复 null 的 start_comment 和 end_comment
                        if defi.get('start_comment') is None or defi.get('end_comment') is None:
                            module_id = defi.get('id', 'unknown')
                            defi['start_comment'] = f"LLM_MODULE_START: {module_id}"
                            defi['end_comment'] = f"LLM_MODULE_END: {module_id}"
                        normalized_defs.append(defi)
                    llm_response_data = {
                        "module_count_suggestion": len(normalized_defs),
                        "definitions": normalized_defs
                    }

                print("\nDEBUG: 解析后的LLM响应数据 (llm_response_data):")
                print(json.dumps(llm_response_data, indent=2, ensure_ascii=False))

                if llm_response_data and "definitions" in llm_response_data:
                    html_to_process = self._add_comments_to_html(raw_original_code, llm_response_data["definitions"])
                    print(f"DEBUG: LLM处理后，带注释的HTML (前250字符): '{html_to_process[:250]}...'")
                else:
                    print("警告: LLM响应中无定义，无法添加注释标记。将使用原始HTML。")

            except requests.exceptions.HTTPError as e_http:
                print(f"Python API: OpenRouter API请求失败 (HTTPError): {e_http}")
                print(f"响应内容: {e_http.response.text if e_http.response else 'N/A'}")
                self.original_html_content_py = raw_original_code
                return {"status": "error", "message": f"LLM API请求失败: {str(e_http)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except requests.exceptions.RequestException as e_req:
                print(f"Python API: OpenRouter API请求失败: {e_req}")
                self.original_html_content_py = raw_original_code
                return {"status": "error", "message": f"LLM API请求失败: {str(e_req)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except json.JSONDecodeError as e_json:
                print(f"Python API: 解析JSON时出错: {e_json}")
                print(f"导致JSON解析错误的原始文本: '{cleaned_json_str[:200] if 'cleaned_json_str' in locals() else 'N/A'}...'")
                self.original_html_content_py = raw_original_code
                return {"status": "error", "message": f"返回的JSON格式无效: {str(e_json)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except KeyError as e_key:
                response_json_for_error = response_json if 'response_json' in locals() else "N/A"
                print(f"Python API: LLM返回的JSON缺少关键字段: {e_key}")
                print(f"LLM返回的JSON对象 (导致KeyError的): {json.dumps(response_json_for_error, indent=2, ensure_ascii=False) if isinstance(response_json_for_error, dict) else response_json_for_error}")
                self.original_html_content_py = raw_original_code
                return {"status": "error", "message": f"LLM返回的JSON缺少字段: {str(e_key)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except Exception as e:
                print(f"Python API: LLM分析或注释添加过程中发生错误: {e}")
                self.original_html_content_py = raw_original_code
                return {"status": "error", "message": f"LLM处理错误: {str(e)}", "active_module_definitions": [], "html_skeleton": raw_original_code}

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
    webview.create_window(
        '代码智能装配流水线',
        'gui.html',
        js_api=api,
        width=1200,
        height=850,
        resizable=True
    )
    webview.start(debug=True)