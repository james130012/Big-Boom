import webview
import json
import os
import logging
import requests
import re
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Define the base template for LLM prompts
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
    "api_url": "[https://openrouter.ai/api/v1/chat/completions](https://openrouter.ai/api/v1/chat/completions)",
    "default_model": "google/gemini-2.5-flash-preview",
    "base_headers": {"Content-Type": "application/json"},
    "request_timeout_seconds": 120,
    "llm_temperature": 0.1,
    "llm_max_tokens": 4096, # Increased from 2048 for potentially larger responses
    "max_modules_to_process_frontend": 10
}

class Api:
    def __init__(self):
        self.original_html_content_py = "" # Stores HTML after LLM adds its comments (LLM_MODULE_START/END)
        self.html_skeleton = ""            # Stores HTML skeleton with MODULE_PLACEHOLDER comments
        self.api_config = self._load_api_config()
        self.site_url = os.getenv("YOUR_SITE_URL", "http://localhost:8003/default-app") # Example URL
        self.site_name = os.getenv("YOUR_SITE_NAME", "DefaultModularizerAppV3") # Example App Name
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.modified_modules = {}  # Stores modification details if a specific_instruction is given
                                    # Key: module_id, Value: {"modified_code": {...}, "modification_manual": "..."}
        self.module_definitions = [] # Stores all module definitions identified by the LLM,
                                     # including their 'original_content'.
                                     # Structure: [{"id": "...", "description": "...", ..., "original_content": "..."}]

    def _load_api_config(self, config_path="api_config.json"):
        # Loads API configuration from a JSON file, falling back to defaults if issues occur.
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logging.info(f"Successfully loaded API config file: {config_path}")
                return {**DEFAULT_API_CONFIG, **config} # Merge with defaults, allowing overrides
        except FileNotFoundError:
            logging.warning(f"API config file '{config_path}' not found. Using default config.")
            return DEFAULT_API_CONFIG
        except json.JSONDecodeError:
            logging.warning(f"API config file '{config_path}' is malformed. Using default config.")
            return DEFAULT_API_CONFIG
        except Exception as e:
            logging.warning(f"Error loading API config file: {e}. Using default config.")
            return DEFAULT_API_CONFIG

    def _add_comments_to_html(self, original_html, definitions):
        # Adds LLM-specific start and end comments around identified modules in the HTML string.
        # These comments (e.g., ) are used internally by the LLM
        # and for extracting original module content.
        if not definitions:
            return original_html

        valid_definitions = []
        for d in definitions:
            # Ensure definitions have the necessary fields for comment insertion
            if not (d.get("start_comment") and d.get("end_comment")):
                logging.debug(f"Skipping module {d.get('id', 'Unknown')} due to missing start_comment or end_comment")
                continue
            # Ensure definitions have valid start/end positions (either line numbers or character offsets)
            if not (("start_line" in d and "end_line" in d) or ("start_char" in d and "end_char" in d)):
                logging.debug(f"Skipping module {d.get('id', 'Unknown')} due to missing valid start/end positions")
                continue
            valid_definitions.append(d)

        # Sort definitions by end position in reverse to avoid index shifts during insertion
        sorted_definitions = sorted(
            valid_definitions,
            key=lambda x: x.get("end_line", x.get("end_char", 0)), # Use end_line or end_char for sorting
            reverse=True
        )

        lines = original_html.splitlines(keepends=True)
        modified_html = original_html # Start with the original HTML
        processed_ids = set() # Keep track of processed module IDs to avoid duplicates

        for defi in sorted_definitions:
            module_id = defi.get("id")
            start_comment_text = defi.get("start_comment", "").strip()
            end_comment_text = defi.get("end_comment", "").strip()
            start_line = defi.get("start_line") # 1-based
            end_line = defi.get("end_line")     # 1-based
            start_char = defi.get("start_char") # 0-based
            end_char = defi.get("end_char")     # 0-based, exclusive

            if not all([module_id, start_comment_text, end_comment_text]):
                logging.debug(f"Skipping module {module_id or 'Unknown'} due to incomplete definition fields for comments.")
                continue

            if module_id in processed_ids:
                logging.debug(f"Module '{module_id}' already processed, skipping.")
                continue

            # Construct the comment tags
            start_marker_tag = f"\n"
            end_marker_tag = f"\n"

            try:
                if start_line is not None and end_line is not None:
                    # Line-based insertion
                    start_line_1based = start_line
                    end_line_1based = end_line
                    if not (1 <= start_line_1based <= len(lines) and 1 <= end_line_1based <= len(lines) and start_line_1based <= end_line_1based):
                        logging.warning(f"Module '{module_id}' has invalid line numbers (start_line: {start_line}, end_line: {end_line}). Skipping.")
                        continue
                    
                    # Calculate character positions from line numbers
                    # This is complex if not careful with how original_html is modified.
                    # Simpler to rebuild lines:
                    current_lines = modified_html.splitlines(keepends=True)
                    # Ensure start_line_1based-1 is a valid index for current_lines
                    if start_line_1based -1 < 0 or end_line_1based > len(current_lines):
                        logging.warning(f"Module '{module_id}' line numbers out of bounds for current HTML state. Skipping.")
                        continue

                    # Insert start marker before the start_line
                    # Insert end marker after the end_line (content of end_line is included in module)
                    # This logic requires careful handling of string concatenation and line endings.
                    # A safer way for line-based is to operate on the list of lines:
                    temp_lines = original_html.splitlines(keepends=True) # Use original HTML for consistent line numbers
                    if end_line_1based <= len(temp_lines): # Ensure end_line is within bounds
                        temp_lines.insert(end_line_1based, end_marker_tag) # Insert after the content of end_line
                    else: # If end_line is beyond the last line, append
                        temp_lines.append(end_marker_tag)

                    if start_line_1based -1 >= 0:
                         temp_lines.insert(start_line_1based -1, start_marker_tag) # Insert before start_line
                    else: # If start_line is 1, insert at the beginning
                        temp_lines.insert(0, start_marker_tag)
                    
                    # This line-based insertion is tricky because `modified_html` changes.
                    # The provided code uses char-based logic if lines are present, which is more robust.
                    # Let's stick to the original char-based logic if lines are provided.

                    # Convert line numbers to character positions for insertion
                    # This assumes lines in `original_html` for calculating positions
                    char_lines = original_html.splitlines(keepends=True)
                    start_char_pos = sum(len(line) for line in char_lines[:start_line_1based-1])
                    # end_char_pos is the position *after* the end_line content
                    end_char_pos = sum(len(line) for line in char_lines[:end_line_1based])


                    modified_html = (
                        modified_html[:start_char_pos] + # Part before module
                        start_marker_tag +              # Start comment
                        modified_html[start_char_pos:end_char_pos] + # Original module content
                        end_marker_tag +                # End comment
                        modified_html[end_char_pos:]    # Part after module
                    )

                elif start_char is not None and end_char is not None:
                    # Character-based insertion
                    if not (0 <= start_char <= end_char <= len(modified_html)): # Check bounds against current modified_html
                        logging.warning(f"Module '{module_id}' has invalid character indices (start_char: {start_char}, end_char: {end_char}) for current HTML. Skipping.")
                        continue
                    modified_html = (
                        modified_html[:start_char] +    # Part before module
                        start_marker_tag +              # Start comment
                        modified_html[start_char:end_char] + # Original module content
                        end_marker_tag +                # End comment
                        modified_html[end_char:]        # Part after module
                    )
                else:
                    logging.warning(f"Module '{module_id}' lacks valid start/end positions. Skipping.")
                    continue
                
                logging.debug(f"Added comment markers for module '{module_id}'.")
                processed_ids.add(module_id)
                # Important: Re-split lines if other modules are processed based on line numbers of `modified_html`
                # However, since we sort by end_char/end_line in reverse, modifications to earlier parts
                # of the string don't affect the indices of later parts.
            except Exception as e:
                logging.error(f"Error adding comments for module '{module_id}': {e}")

        return modified_html

    def _extract_module_content_from_string(self, html_string_with_llm_comments, module_def):
        # Extracts the content of a module from an HTML string that already has
        # LLM_MODULE_START/END comments. This is used to get the "original_content"
        # of a module after the LLM has identified it and comments have been added.
        module_id = module_def.get('id', 'N/A')
        # Use the start_comment and end_comment fields from the module definition
        start_marker_text = module_def.get('start_comment', '').strip() 
        end_marker_text = module_def.get('end_comment', '').strip()

        if not start_marker_text or not end_marker_text:
            logging.debug(f"Module '{module_id}' is missing start_comment or end_comment text in its definition. Cannot extract content.")
            return ""

        # Construct the full comment tags to search for
        start_marker = f""
        end_marker = f""

        start_index = html_string_with_llm_comments.find(start_marker)
        if start_index == -1:
            logging.debug(f"Start marker '{start_marker}' for module '{module_id}' not found in HTML. Cannot extract content.")
            return ""

        # Content starts after the start_marker
        content_start_index = start_index + len(start_marker)
        
        # Find the end_marker *after* the content_start_index
        end_index = html_string_with_llm_comments.find(end_marker, content_start_index)
        if end_index == -1:
            logging.debug(f"End marker '{end_marker}' for module '{module_id}' not found after start marker in HTML. Cannot extract content.")
            return ""

        # Extract the content between the markers
        extracted_content = html_string_with_llm_comments[content_start_index:end_index].strip()
        
        # Optionally, remove any nested LLM comments if they were somehow included, though ideally they shouldn't be.
        # extracted_content = re.sub(r'\n?', '', extracted_content).strip()
        return extracted_content

    def _generate_skeleton_from_string(self, html_string_with_llm_comments, modules_to_skeletonize):
        # Generates an HTML skeleton by replacing module content (between LLM_MODULE_START/END comments)
        # with placeholders ().
        skeleton = html_string_with_llm_comments
        
        # Sort modules to replace from longest content to shortest, or by occurrence,
        # to handle nested structures if they were to occur (though current LLM prompt aims for flat modules).
        # For simplicity, processing in the given order, assuming non-overlapping or careful LLM definitions.
        # A more robust way would be to sort by start_char in reverse.

        # Sort definitions by start_char in reverse to avoid index issues during replacement
        sorted_modules = sorted(
            modules_to_skeletonize,
            key=lambda x: x.get("start_char", 0), # Assuming start_char is reliable from LLM
            reverse=True
        )

        for module_def in sorted_modules:
            module_id = module_def.get('id', '').strip()
            start_marker_text = module_def.get('start_comment', '').strip()
            end_marker_text = module_def.get('end_comment', '').strip()

            if not module_id or not start_marker_text or not end_marker_text:
                logging.warning(f"Skipping skeletonization for module due to missing id or comment texts: {module_def.get('id')}")
                continue

            start_marker = f""
            end_marker = f""
            placeholder = f""

            # Find the module block including its LLM comments
            start_idx = skeleton.find(start_marker)
            if start_idx == -1:
                logging.warning(f"Could not find start marker '{start_marker}' for module '{module_id}' in skeleton generation.")
                continue
            
            # End index should be after the start_marker
            end_idx_of_end_marker = skeleton.find(end_marker, start_idx + len(start_marker))
            if end_idx_of_end_marker == -1:
                logging.warning(f"Could not find end marker '{end_marker}' for module '{module_id}' after start marker in skeleton generation.")
                continue
            
            # The content to replace is the entire block from start_marker to end_marker inclusive
            content_to_replace_start = start_idx
            content_to_replace_end = end_idx_of_end_marker + len(end_marker)
            
            # Replace the identified module block with the placeholder
            skeleton = skeleton[:content_to_replace_start] + placeholder + skeleton[content_to_replace_end:]
            logging.debug(f"Replaced module '{module_id}' with placeholder in skeleton.")
            
        return skeleton

    def analyze_html(self, original_code, specific_instruction=""):
        logging.info("Python API: analyze_html called.")
        logging.info(f"Received original_code (first 100 chars): {original_code[:100]}...")
        logging.info(f"Received specific_instruction: {specific_instruction}")
        
        raw_original_code = original_code.strip() if original_code else ""

        if not raw_original_code:
            logging.warning("Received empty HTML. Returning error response.")
            self.original_html_content_py = ""
            self.html_skeleton = ""
            self.module_definitions = []
            self.modified_modules = {}
            return {
                "status": "error",
                "message": "无效或空HTML (Invalid or empty HTML)",
                "active_module_definitions": [],
                "html_skeleton": "",
                "modified_code": {},
                "modification_manual": ""
            }

        # Store the raw original code before any modifications
        # self.original_html = raw_original_code # This was used before, but self.original_html_content_py will hold the commented version

        # --- Step 1: LLM Call for Module Definitions ---
        # This prompt asks the LLM to identify modules and suggest comment markers.
        module_definition_prompt = """分析以下HTML代码，识别潜在的模块（如动画、页眉、页脚、文本块），返回模块定义列表，每个模块包含：
- id：唯一标识（小写蛇形命名法，例如 animation_box_1, header_section）
- description：模块描述（中文，例如 “动画1模块”）
- start_line/end_line：模块在原始HTML中的起止行号（1-based, inclusive）。
- start_char/end_char：模块在原始HTML中的起止字符位置（0-based, start inclusive, end exclusive）。
- start_comment：建议的起始注释标记文本 (例如 "LLM_MODULE_START: animation_box_1")
- end_comment：建议的结束注释标记文本 (例如 "LLM_MODULE_END: animation_box_1")
确保 start_char 和 end_char 精确地包围模块的HTML内容，不包括模块外的空白或标签。
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
      "start_comment": "<起始注释文本>",
      "end_comment": "<结束注释文本>"
    }
  ]
}
HTML代码：
{user_html_code}
"""
        module_definition_prompt = module_definition_prompt.replace("{user_html_code}", raw_original_code)
        
        llm_module_definitions_response = None # To store raw response from LLM for definitions
        raw_definitions_from_llm = []

        if not self.openrouter_api_key:
            logging.warning("OPENROUTER_API_KEY is not set. Using mock data for module definitions.")
            # Example mock definitions - ensure these match the structure expected by _add_comments_to_html
            mock_defs = [
                {
                    "id": "header_module", "description": "网站Logo和标题",
                    "start_line": 7, "end_line": 7, # Example: <header><h1>网站Logo和标题</h1></header>
                    "start_char": 230, "end_char": 276, # Approximate, adjust to your sample HTML
                    "start_comment": "LLM_MODULE_START: header_module",
                    "end_comment": "LLM_MODULE_END: header_module"
                },
                {
                    "id": "anim1_box_module", "description": "动画1盒子",
                    "start_line": 13, "end_line": 15, # Example: <div class="animation-box" id="anim1-box">...</div>
                    "start_char": 430, "end_char": 530, # Approximate
                    "start_comment": "LLM_MODULE_START: anim1_box_module",
                    "end_comment": "LLM_MODULE_END: anim1_box_module"
                }
            ]
            llm_module_definitions_response = {"module_count_suggestion": len(mock_defs), "definitions": mock_defs}
            raw_definitions_from_llm = llm_module_definitions_response.get("definitions", [])
        else:
            try:
                logging.info("Calling LLM for module definitions...")
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.site_url, # Required by some OpenRouter models
                    "X-Title": self.site_name    # Required by some OpenRouter models
                }
                payload = {
                    "model": self.api_config.get("default_model"),
                    "messages": [{"role": "user", "content": module_definition_prompt}],
                    "temperature": self.api_config.get("llm_temperature", 0.1),
                    "max_tokens": self.api_config.get("llm_max_tokens", 4096),
                    "response_format": {"type": "json_object"} # Request JSON output if model supports
                }
                response = requests.post(
                    self.api_config.get("api_url"), 
                    headers=headers, 
                    json=payload, 
                    timeout=self.api_config.get("request_timeout_seconds", 120)
                )
                response.raise_for_status() # Raise an exception for HTTP errors
                
                # Attempt to parse JSON directly from response.json() if Content-Type is application/json
                # Or handle text if it's plain text that needs stripping of ```json
                raw_response_content = response.json()["choices"][0]["message"]["content"]
                try:
                    llm_module_definitions_response = json.loads(raw_response_content)
                except json.JSONDecodeError:
                    llm_module_definitions_response = json.loads(raw_response_content.strip("```json\n").strip("```"))
                
                raw_definitions_from_llm = llm_module_definitions_response.get("definitions", [])
                logging.info(f"LLM returned {len(raw_definitions_from_llm)} module definitions.")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error calling LLM for module definitions: {e}")
                # Fallback or error handling
                return {"status": "error", "message": f"LLM API Error (Definitions): {e}", "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Error parsing LLM response for module definitions: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
                return {"status": "error", "message": f"LLM Response Parse Error (Definitions): {e}", "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}

        # --- Step 2: Add LLM's internal comments to the HTML ---
        # This HTML (with LLM_MODULE_START/END) will be used to extract original content and generate the skeleton.
        self.original_html_content_py = self._add_comments_to_html(raw_original_code, raw_definitions_from_llm)
        logging.debug(f"HTML with LLM comments (first 200 chars): {self.original_html_content_py[:200]}...")

        # --- Step 3: Populate self.module_definitions with original_content ---
        # This is crucial for the new integration logic.
        temp_processed_definitions = []
        for module_def in raw_definitions_from_llm:
            # Extract content based on the *newly commented* HTML
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def)
            if content: # Only add if content was successfully extracted
                temp_processed_definitions.append({**module_def, "original_content": content})
            else:
                logging.warning(f"Could not extract original content for module ID: {module_def.get('id')}. It might be excluded.")
        
        self.module_definitions = temp_processed_definitions # Store these full definitions
        logging.info(f"Processed {len(self.module_definitions)} modules with their original content.")


        # --- Step 4: Generate HTML Skeleton ---
        # The skeleton uses self.html_skeleton = self._generate_skeleton_from_string(self.original_html_content_py, self.module_definitions)
        logging.debug(f"Generated HTML skeleton (first 200 chars): {self.html_skeleton[:200]}...")

        # --- Step 5: Handle Specific Modification Instruction (if provided) ---
        modified_code_for_response = {}
        modification_manual_for_response = ""
        self.modified_modules = {} # Reset modified modules for this call

        if specific_instruction:
            logging.info(f"Processing specific instruction: {specific_instruction}")
            # Use the main PROMPT_TEMPLATE_BASE for modification
            # Pass the raw_original_code to LLM for modification context, not the commented one.
            modification_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", raw_original_code).replace("{specific_instruction}", specific_instruction)
            
            if not self.openrouter_api_key:
                logging.warning("OPENROUTER_API_KEY not set. Skipping LLM call for modification, returning mock modification.")
                # Mock a modification if API key is missing
                if self.module_definitions: # If any modules were defined
                    mock_target_module_id = self.module_definitions[0]["id"]
                    modified_code_for_response = {
                        "html": f"<div id='{mock_target_module_id}-modified'>Mock modified HTML for {mock_target_module_id}</div>",
                        "css": f"#{mock_target_module_id}-modified {{ border: 2px solid red; }}",
                        "js": f"console.log('Mock JS for {mock_target_module_id}');"
                    }
                    modification_manual_for_response = f"Mock manual: Replace module {mock_target_module_id} with new content."
                    self.modified_modules[mock_target_module_id] = {
                        "modified_code": modified_code_for_response,
                        "modification_manual": modification_manual_for_response
                    }
                else:
                    modification_manual_for_response = "No modules defined to mock modification."

            else:
                try:
                    logging.info("Calling LLM for code modification...")
                    headers = {
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": self.site_url, 
                        "X-Title": self.site_name
                    }
                    payload = {
                        "model": self.api_config.get("default_model"),
                        "messages": [{"role": "user", "content": modification_prompt}],
                        "temperature": self.api_config.get("llm_temperature", 0.1),
                        "max_tokens": self.api_config.get("llm_max_tokens", 4096),
                        "response_format": {"type": "json_object"}
                    }
                    response = requests.post(self.api_config.get("api_url"), headers=headers, json=payload, timeout=self.api_config.get("request_timeout_seconds", 120))
                    response.raise_for_status()
                    
                    raw_mod_response_content = response.json()["choices"][0]["message"]["content"]
                    try:
                        llm_modification_response = json.loads(raw_mod_response_content)
                    except json.JSONDecodeError:
                         llm_modification_response = json.loads(raw_mod_response_content.strip("```json\n").strip("```"))

                    if llm_modification_response.get("status") == "success":
                        modified_code_for_response = llm_modification_response.get("modified_code", {})
                        modification_manual_for_response = llm_modification_response.get("modification_manual", "")
                        
                        # The LLM's response for "modules" here refers to the *target* of the modification.
                        # We need to store this modification against the correct module_id.
                        llm_reported_modified_modules = llm_modification_response.get("modules", [])
                        if llm_reported_modified_modules:
                            # Assuming the LLM correctly identifies the single module it modified as per the prompt.
                            target_module_id = llm_reported_modified_modules[0].get("id")
                            if target_module_id:
                                self.modified_modules[target_module_id] = {
                                    "modified_code": modified_code_for_response,
                                    "modification_manual": modification_manual_for_response
                                }
                                logging.info(f"Stored modification for module ID: {target_module_id}")
                            else:
                                logging.warning("LLM modification response did not specify a target module ID clearly.")
                        else:
                             logging.warning("LLM modification response did not list any modules as being modified.")
                    else:
                        logging.error(f"LLM reported an error during modification: {llm_modification_response.get('message')}")
                        modification_manual_for_response = f"LLM modification failed: {llm_modification_response.get('message')}"

                except requests.exceptions.RequestException as e:
                    logging.error(f"Error calling LLM for modification: {e}")
                    modification_manual_for_response = f"LLM API Error (Modification): {e}"
                except (json.JSONDecodeError, KeyError) as e:
                    logging.error(f"Error parsing LLM response for modification: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
                    modification_manual_for_response = f"LLM Response Parse Error (Modification): {e}"
        
        # --- Step 6: Prepare and return the response for the frontend ---
        # Frontend expects 'active_module_definitions' which are our 'self.module_definitions'
        # It also needs the skeleton, and any modification results.
        
        # Limit the number of definitions sent to frontend if necessary
        max_to_send = self.api_config.get("max_modules_to_process_frontend", len(self.module_definitions))
        definitions_for_frontend = self.module_definitions[:max_to_send]

        logging.info(f"Analysis complete. Returning {len(definitions_for_frontend)} module definitions to frontend.")
        return {
            "status": "success",
            "message": f"分析完成，识别到 {len(self.module_definitions)} 个模块，将向前端发送 {len(definitions_for_frontend)} 个。(Analysis complete, identified {len(self.module_definitions)} modules, sending {len(definitions_for_frontend)} to frontend.)",
            "active_module_definitions": definitions_for_frontend, # These include 'original_content'
            "html_skeleton": self.html_skeleton,
            "modified_code": modified_code_for_response, # This is the specific modification from the instruction
            "modification_manual": modification_manual_for_response
        }

    def integrate_modules(self):
        logging.info("Python API: integrate_modules called.")
        
        if not self.html_skeleton:
            logging.warning("HTML skeleton is not available. Cannot integrate. Ensure analyze_html was called successfully.")
            # Fallback to original_html_content_py if skeleton is missing, though this means placeholders won't be used.
            # Or, more correctly, return an error or the last known "good" state.
            # For now, let's assume original_html_content_py might be the raw HTML if skeleton failed.
            return getattr(self, 'original_html_content_py', "Error: HTML skeleton not generated.")

        final_html = self.html_skeleton # Start with the skeleton

        # For collecting CSS and JS from all modified modules
        all_modified_css = []
        all_modified_js = []

        logging.debug(f"Starting integration with skeleton: {final_html[:200]}...")
        logging.debug(f"Available module definitions for integration: {len(self.module_definitions)}")
        logging.debug(f"Modified modules by instruction: {list(self.modified_modules.keys())}")


        for module_def in self.module_definitions:
            module_id = module_def.get("id")
            if not module_id:
                logging.warning("Found a module definition without an ID during integration. Skipping.")
                continue

            placeholder = f""
            content_to_insert = ""

            if module_id in self.modified_modules:
                # This module was targeted by the specific_instruction in analyze_html
                module_mod_data = self.modified_modules[module_id]
                content_to_insert = module_mod_data.get("modified_code", {}).get("html", "")
                
                # Collect CSS and JS if present from this specifically modified module
                if module_mod_data.get("modified_code", {}).get("css"):
                    all_modified_css.append(f"/* CSS for module: {module_id} (modified by instruction) */\n{module_mod_data['modified_code']['css']}")
                if module_mod_data.get("modified_code", {}).get("js"):
                    all_modified_js.append(f"// JS for module: {module_id} (modified by instruction)\n{module_mod_data['modified_code']['js']}")
                
                logging.info(f"Module '{module_id}' was modified by instruction. Using its new HTML.")
            else:
                # This module was not targeted by a specific_instruction, use its original content
                content_to_insert = module_def.get("original_content", "")
                # logging.debug(f"Module '{module_id}' not in modified_modules. Using its original_content.")


            if placeholder in final_html:
                final_html = final_html.replace(placeholder, content_to_insert, 1) # Replace only the first occurrence
                logging.debug(f"Replaced placeholder for module '{module_id}'.")
            else:
                logging.warning(f"Placeholder '{placeholder}' for module '{module_id}' not found in the HTML skeleton. Integration for this module might be incomplete.")
        
        # --- Inject collected CSS and JS ---
        # This is a basic injection strategy. More sophisticated methods might be needed
        # depending on the HTML structure and where styles/scripts should go.
        
        # Inject CSS: Look for </head> or <style> or create a new <style> tag
        if all_modified_css:
            css_block = "\n<style type=\"text/css\">\n" + "\n\n".join(all_modified_css) + "\n</style>\n"
            if "</head>" in final_html:
                final_html = final_html.replace("</head>", css_block + "</head>", 1)
            elif "<body" in final_html: # Fallback: put it before body if no head
                 final_html = css_block + final_html
            else: # Absolute fallback: append
                final_html += css_block
            logging.info("Injected collected CSS into final HTML.")

        # Inject JS: Look for </body> or <script> or create a new <script> tag
        if all_modified_js:
            js_block = "\n<script type=\"text/javascript\">\n//<![CDATA[\n" + "\n\n".join(all_modified_js) + "\n//]]>\n</script>\n"
            if "</body>" in final_html:
                final_html = final_html.replace("</body>", js_block + "</body>", 1)
            else: # Fallback: append if no body tag
                final_html += js_block
            logging.info("Injected collected JS into final HTML.")

        logging.info("Module integration complete.")
        logging.debug(f"Final integrated HTML (first 200 chars): {final_html[:200]}...")
        return final_html


    def get_modification_manual(self, module_id):
        # Retrieves the modification manual for a specific module if it was modified.
        # This function might not be directly used by the current frontend flow but can be useful.
        return self.modified_modules.get(module_id, {}).get("modification_manual", "No modification manual available for this module.")

    def get_prompt_template_for_frontend(self):
        # Returns the base LLM prompt template, with placeholders for user HTML and instruction.
        # This is for display/informational purposes on the frontend.
        logging.debug("get_prompt_template_for_frontend called by frontend.")
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code}", "[用户 HTML 在此]").replace("{specific_instruction}", "[修改指令在此]")

    # The integrate_html method was part of the old logic and seems redundant now
    # with the revised integrate_modules. If it's still called by the frontend,
    # it needs to be updated or removed. For now, commenting out.
    # def integrate_html(self, skeleton_html, modified_modules_json_string):
    #     logging.warning("DEPRECATED: integrate_html was called. This should ideally use integrate_modules.")
    #     # ... (old logic)


if __name__ == '__main__':
    api = Api()
    logging.info("Starting PyWebview window...")
    window = webview.create_window(
        '代码智能装配流水线 (Code Smart Assembly Line)', # Window Title
        'gui.html',        # HTML file to load
        js_api=api,        # Expose the Api class instance to JavaScript
        width=1200,
        height=850,
        resizable=True
    )
    logging.info("PyWebview window created. Starting application...")
    webview.start(debug=True) # Enable debug mode for more detailed logs from pywebview
    logging.info("PyWebview application has been closed.")
