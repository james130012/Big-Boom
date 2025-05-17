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
    "llm_max_tokens": 4096,
    "max_modules_to_process_frontend": 10
}

class Api:
    def __init__(self):
        self.original_html_content_py = "" 
        self.html_skeleton = ""            
        self.api_config = self._load_api_config()
        self.site_url = os.getenv("YOUR_SITE_URL", "http://localhost:8003/default-app") 
        self.site_name = os.getenv("YOUR_SITE_NAME", "DefaultModularizerAppV3") 
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.modified_modules = {}  
        self.module_definitions = [] 

    def _load_api_config(self, config_path="api_config.json"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logging.info(f"Successfully loaded API config file: {config_path}")
                return {**DEFAULT_API_CONFIG, **config} 
        except FileNotFoundError:
            logging.warning(f"API config file '{config_path}' not found. Using default config.")
            return DEFAULT_API_CONFIG
        except json.JSONDecodeError:
            logging.warning(f"API config file '{config_path}' is malformed. Using default config.")
            return DEFAULT_API_CONFIG
        except Exception as e:
            logging.warning(f"Error loading API config file: {e}. Using default config.")
            return DEFAULT_API_CONFIG

    def _add_comments_to_html_revised(self, original_html, definitions_from_llm):
        # Revised function to add comments more robustly.
        # It builds the HTML by piecing together original segments and new comment tags.
        if not definitions_from_llm:
            logging.debug("_add_comments_to_html_revised: No definitions provided.")
            return original_html

        # Prepare definitions: calculate absolute char positions from original_html
        # and store full tag text.
        processed_defs = []
        original_lines = original_html.splitlines(keepends=True)

        for i, d_orig in enumerate(definitions_from_llm):
            d = d_orig.copy() # Work on a copy
            module_id = d.get("id", f"unknown_module_{i}") # Ensure an ID for logging
            start_comment_text = d.get("start_comment", "").strip()
            end_comment_text = d.get("end_comment", "").strip()

            if not all([module_id, start_comment_text, end_comment_text]):
                logging.warning(f"Module '{module_id}' in _add_comments_to_html_revised: incomplete comment texts. Skipping.")
                continue

            s_char, e_char = -1, -1
            if "start_char" in d and "end_char" in d:
                s_char, e_char = d["start_char"], d["end_char"]
                logging.debug(f"Module '{module_id}': Using char positions from LLM: s_char={s_char}, e_char={e_char}")
            elif "start_line" in d and "end_line" in d:
                s_line, e_line = d["start_line"], d["end_line"]
                logging.debug(f"Module '{module_id}': Using line positions from LLM: s_line={s_line}, e_line={e_line}")
                if not (1 <= s_line <= len(original_lines) and 1 <= e_line <= len(original_lines) and s_line <= e_line):
                    logging.warning(f"Module '{module_id}' has invalid line numbers ({s_line}-{e_line}) for {len(original_lines)} lines. Skipping.")
                    continue
                s_char = sum(len(line) for line in original_lines[:s_line - 1])
                e_char = sum(len(line) for line in original_lines[:e_line]) # end_char is exclusive for slice, so take up to end of e_line
                logging.debug(f"Module '{module_id}': Calculated char positions: s_char={s_char}, e_char={e_char}")
            else:
                logging.warning(f"Module '{module_id}' lacks char/line positions. Skipping.")
                continue

            if not (0 <= s_char <= e_char <= len(original_html)):
                logging.warning(f"Module '{module_id}' has invalid char positions ({s_char}, {e_char}) for original_html length {len(original_html)}. Skipping.")
                continue
            
            d["s_char_final"] = s_char
            d["e_char_final"] = e_char
            # Define the exact tags to be inserted
            d["start_marker_tag_full"] = f"\n"
            d["end_marker_tag_full"] = f"\n"
            processed_defs.append(d)

        # Sort definitions by their start character position in the original HTML.
        # This is crucial for correctly assembling the pieces.
        processed_defs.sort(key=lambda x: x["s_char_final"])

        result_parts = []
        current_pos_in_original = 0
        for defi in processed_defs:
            s_char = defi["s_char_final"]
            e_char = defi["e_char_final"]

            # Add text from original_html that comes before the current module's start tag
            if s_char > current_pos_in_original:
                result_parts.append(original_html[current_pos_in_original:s_char])
            
            # Add the start comment tag
            result_parts.append(defi["start_marker_tag_full"])
            # Add the original content of the module itself
            result_parts.append(original_html[s_char:e_char])
            # Add the end comment tag
            result_parts.append(defi["end_marker_tag_full"])
            
            current_pos_in_original = e_char # Update current position to the end of this module's content in original_html

            logging.debug(f"Added comments for module '{defi['id']}'. Original span: {s_char}-{e_char}. Current_pos now: {current_pos_in_original}")

        # Add any remaining text from original_html after the last processed module
        if current_pos_in_original < len(original_html):
            result_parts.append(original_html[current_pos_in_original:])
        
        final_html = "".join(result_parts)
        logging.debug(f"_add_comments_to_html_revised output (first 300 chars): {final_html[:300]}...")
        return final_html

    def _extract_module_content_from_string(self, html_string_with_llm_comments, module_def):
        module_id = module_def.get('id', 'N/A')
        # These texts are e.g., "LLM_MODULE_START: module_id"
        start_comment_text = module_def.get('start_comment', '').strip() 
        end_comment_text = module_def.get('end_comment', '').strip()

        logging.debug(f"Extracting content for module ID: '{module_id}'")
        logging.debug(f"  Using start_comment_text for search: '{start_comment_text}'")
        logging.debug(f"  Using end_comment_text for search: '{end_comment_text}'")

        if not start_comment_text or not end_comment_text:
            logging.warning(f"Module '{module_id}' is missing start_comment or end_comment text in its definition. Cannot extract content.")
            return ""

        # Construct the full comment tags as they were inserted by _add_comments_to_html_revised
        # Content is between "\n" and "\n"
        effective_start_marker = f"\n"
        effective_end_marker_prefix = f"\n" # The content ends *before* this

        start_marker_find_idx = html_string_with_llm_comments.find(effective_start_marker)
        
        if start_marker_find_idx == -1:
            logging.warning(f"  Effective start marker '{effective_start_marker.strip()}' for module '{module_id}' NOT FOUND in HTML provided for extraction.")
            logging.debug(f"    Searched in (first 300 chars): {html_string_with_llm_comments[:300]}")
            return ""

        # The actual content begins immediately after the effective_start_marker
        content_actual_start_idx = start_marker_find_idx + len(effective_start_marker)
        
        # The content ends at the beginning of the effective_end_marker_prefix, searched *after* the content started
        content_actual_end_idx = html_string_with_llm_comments.find(effective_end_marker_prefix, content_actual_start_idx)

        if content_actual_end_idx == -1:
            logging.warning(f"  Effective end marker prefix '{effective_end_marker_prefix.strip()}' for module '{module_id}' NOT FOUND after content_actual_start_idx ({content_actual_start_idx}).")
            logging.debug(f"    Searched in (from content_actual_start_idx, next 300 chars): {html_string_with_llm_comments[content_actual_start_idx:content_actual_start_idx+300]}")
            return ""

        extracted_content = html_string_with_llm_comments[content_actual_start_idx:content_actual_end_idx]
        logging.debug(f"  Raw extracted content for '{module_id}' (len {len(extracted_content)}): '{extracted_content[:100].replace('\n', '\\n')}...'")
        
        return extracted_content.strip() # Strip any leading/trailing whitespace from the extracted segment

    def _generate_skeleton_from_string(self, html_string_with_llm_comments, modules_to_skeletonize):
        skeleton = html_string_with_llm_comments
        
        # Sort modules by start_char in reverse to handle replacements correctly without shifting indices for subsequent ops.
        # The s_char_final should be present if modules_to_skeletonize comes from self.module_definitions
        # which are processed by _add_comments_to_html_revised's prep step.
        # If not, ensure s_char_final is calculated or fallback to another sorting key.
        # For now, assuming modules_to_skeletonize contains s_char_final.
        
        # Create a temporary list with s_char_final for sorting if not already present
        temp_modules_for_skeleton = []
        original_lines_for_skel = html_string_with_llm_comments.splitlines(keepends=True) # Approx for char calc if needed

        for m_def in modules_to_skeletonize:
            m_copy = m_def.copy()
            if "s_char_final" not in m_copy: # Calculate if missing (e.g. if definitions are raw)
                s_char, e_char = -1, -1
                if "start_char" in m_copy and "end_char" in m_copy:
                    s_char = m_copy["start_char"]
                elif "start_line" in m_copy and "end_line" in m_copy:
                    s_line, e_line = m_copy["start_line"], m_copy["end_line"]
                    if (1 <= s_line <= len(original_lines_for_skel) and 1 <= e_line <= len(original_lines_for_skel) and s_line <= e_line):
                        s_char = sum(len(line) for line in original_lines_for_skel[:s_line - 1])
                m_copy["s_char_final"] = s_char # Store for sorting
            temp_modules_for_skeleton.append(m_copy)

        sorted_modules = sorted(
            temp_modules_for_skeleton,
            key=lambda x: x.get("s_char_final", 0), 
            reverse=True
        )

        for module_def in sorted_modules:
            module_id = module_def.get('id', '').strip()
            # These are the comment *texts*, e.g., "LLM_MODULE_START: module_id"
            start_comment_text = module_def.get('start_comment', '').strip()
            end_comment_text = module_def.get('end_comment', '').strip()

            if not module_id or not start_comment_text or not end_comment_text:
                logging.warning(f"Skipping skeletonization for module due to missing id or comment texts: {module_def.get('id')}")
                continue

            # These are the full comment tags including newlines, as inserted by _add_comments_to_html_revised
            full_start_marker = f"\n"
            full_end_marker = f"\n"
            placeholder = f""
            
            # Find the start of the start marker
            start_idx_of_start_marker = skeleton.find(full_start_marker)
            if start_idx_of_start_marker == -1:
                logging.warning(f"Could not find full start marker for module '{module_id}' in skeleton generation. Marker: '{full_start_marker.strip()}'")
                continue
            
            # The content to replace starts *at* full_start_marker.
            # It ends *after* full_end_marker.
            # Find the start of the end marker, searching *after* the start marker has ended.
            # End of start marker = start_idx_of_start_marker + len(full_start_marker)
            search_for_end_from = start_idx_of_start_marker + len(full_start_marker)
            start_idx_of_end_marker = skeleton.find(full_end_marker, search_for_end_from)
            
            if start_idx_of_end_marker == -1:
                logging.warning(f"Could not find full end marker for module '{module_id}' after start marker in skeleton generation. Marker: '{full_end_marker.strip()}'")
                continue
            
            # The block to replace is from the beginning of full_start_marker to the end of full_end_marker
            content_to_replace_start_idx = start_idx_of_start_marker
            content_to_replace_end_idx = start_idx_of_end_marker + len(full_end_marker)
            
            skeleton = skeleton[:content_to_replace_start_idx] + placeholder + skeleton[content_to_replace_end_idx:]
            logging.debug(f"Replaced module '{module_id}' with placeholder in skeleton.")
            
        return skeleton

    def analyze_html(self, original_code, specific_instruction=""):
        logging.info("Python API: analyze_html called.")
        logging.info(f"Received original_code (first 100 chars): {original_code[:100]}...")
        logging.info(f"Received specific_instruction: {specific_instruction}")
        
        raw_original_code = original_code.strip() if original_code else ""

        if not raw_original_code:
            # Handle empty input
            # ... (same as before)
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

        # --- Step 1: LLM Call for Module Definitions ---
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
        
        llm_module_definitions_response = None 
        raw_definitions_from_llm = []

        if not self.openrouter_api_key:
            # Mock data if API key is missing
            # ... (same as before, ensure mock data is valid for new logic)
            logging.warning("OPENROUTER_API_KEY is not set. Using mock data for module definitions.")
            # Example: LLM might return definitions for the default HTML in gui.html
            mock_defs = [
                { # header
                    "id": "header_section", "description": "网站Logo和主要标题",
                    "start_line": 14, "end_line": 14, # <header><h1>网站Logo和主要标题</h1></header>
                    "start_char": 500, "end_char": 556, # Approximate, adjust to actual default HTML
                    "start_comment": "LLM_MODULE_START: header_section",
                    "end_comment": "LLM_MODULE_END: header_section"
                },
                { # anim1-box content
                    "id": "animation_module_1_content", "description": "动画1的占位内容",
                    "start_line": 20, "end_line": 22, # <div class="animation-box" id="anim1-box"> ... </p> </div>
                    "start_char": 765, "end_char": 864, # Approximate
                    "start_comment": "LLM_MODULE_START: animation_module_1_content",
                    "end_comment": "LLM_MODULE_END: animation_module_1_content"
                },
                { # footer
                    "id": "footer_section", "description": "版权所有",
                    "start_line": 31, "end_line": 31, # <footer><p>版权所有 &copy; 2025 MyCompany</p></footer>
                    "start_char": 1118, "end_char": 1174, # Approximate
                    "start_comment": "LLM_MODULE_START: footer_section",
                    "end_comment": "LLM_MODULE_END: footer_section"
                }
            ]
            # Adjust char/line numbers based on the actual default HTML in gui.html for better mock.
            # The provided char numbers are placeholders.
            llm_module_definitions_response = {"module_count_suggestion": len(mock_defs), "definitions": mock_defs}
            raw_definitions_from_llm = llm_module_definitions_response.get("definitions", [])
        else:
            # Actual LLM call
            # ... (same as before)
            try:
                logging.info("Calling LLM for module definitions...")
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.site_url, 
                    "X-Title": self.site_name    
                }
                payload = {
                    "model": self.api_config.get("default_model"),
                    "messages": [{"role": "user", "content": module_definition_prompt}],
                    "temperature": self.api_config.get("llm_temperature", 0.1),
                    "max_tokens": self.api_config.get("llm_max_tokens", 4096),
                    "response_format": {"type": "json_object"} 
                }
                response = requests.post(
                    self.api_config.get("api_url"), 
                    headers=headers, 
                    json=payload, 
                    timeout=self.api_config.get("request_timeout_seconds", 120)
                )
                response.raise_for_status() 
                
                raw_response_content = response.json()["choices"][0]["message"]["content"]
                try:
                    llm_module_definitions_response = json.loads(raw_response_content)
                except json.JSONDecodeError:
                    llm_module_definitions_response = json.loads(raw_response_content.strip("```json\n").strip("```"))
                
                raw_definitions_from_llm = llm_module_definitions_response.get("definitions", [])
                logging.info(f"LLM returned {len(raw_definitions_from_llm)} module definitions.")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error calling LLM for module definitions: {e}")
                return {"status": "error", "message": f"LLM API Error (Definitions): {e}", "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Error parsing LLM response for module definitions: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
                return {"status": "error", "message": f"LLM Response Parse Error (Definitions): {e}", "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}


        # --- Step 2: Add LLM's internal comments to the HTML using the revised method ---
        self.original_html_content_py = self._add_comments_to_html_revised(raw_original_code, raw_definitions_from_llm)
        # logging.debug(f"HTML with LLM comments (self.original_html_content_py): \n{self.original_html_content_py}\n")


        # --- Step 3: Populate self.module_definitions with original_content ---
        temp_processed_definitions = []
        for module_def_llm in raw_definitions_from_llm: # Iterate over definitions from LLM
            # Extract content based on the *newly commented* HTML and the LLM definition
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def_llm)
            if content or content == "": # Allow empty content if module is empty, but still add definition
                temp_processed_definitions.append({**module_def_llm, "original_content": content})
                logging.info(f"Successfully extracted content for module ID: {module_def_llm.get('id')}. Length: {len(content)}")
            else:
                # This case (content is None or False, but not empty string) should ideally not be hit if extraction works
                logging.warning(f"Could not extract original content for module ID: {module_def_llm.get('id')}. It will be excluded from self.module_definitions.")
        
        self.module_definitions = temp_processed_definitions 
        logging.info(f"Processed {len(self.module_definitions)} modules and stored with their original content.")


        # --- Step 4: Generate HTML Skeleton ---
        # The skeleton uses # It should operate on self.original_html_content_py (HTML with LLM comments)
        # and use self.module_definitions (which now have original_content, but skeletonizer needs comment texts)
        self.html_skeleton = self._generate_skeleton_from_string(self.original_html_content_py, self.module_definitions)
        logging.debug(f"Generated HTML skeleton (first 300 chars): {self.html_skeleton[:300]}...")

        # --- Step 5: Handle Specific Modification Instruction (if provided) ---
        # ... (same as before)
        modified_code_for_response = {}
        modification_manual_for_response = ""
        self.modified_modules = {} 

        if specific_instruction:
            logging.info(f"Processing specific instruction: {specific_instruction}")
            modification_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", raw_original_code).replace("{specific_instruction}", specific_instruction)
            
            if not self.openrouter_api_key:
                logging.warning("OPENROUTER_API_KEY not set. Skipping LLM call for modification, returning mock modification.")
                if self.module_definitions: 
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
                        
                        llm_reported_modified_modules = llm_modification_response.get("modules", [])
                        if llm_reported_modified_modules:
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
        max_to_send = self.api_config.get("max_modules_to_process_frontend", len(self.module_definitions))
        definitions_for_frontend = self.module_definitions[:max_to_send]

        logging.info(f"Analysis complete. Returning {len(definitions_for_frontend)} module definitions to frontend.")
        return {
            "status": "success",
            "message": f"分析完成，识别到 {len(self.module_definitions)} 个模块，将向前端发送 {len(definitions_for_frontend)} 个。(Analysis complete, identified {len(self.module_definitions)} modules, sending {len(definitions_for_frontend)} to frontend.)",
            "active_module_definitions": definitions_for_frontend, 
            "html_skeleton": self.html_skeleton,
            "modified_code": modified_code_for_response, 
            "modification_manual": modification_manual_for_response
        }

    def integrate_modules(self):
        # ... (same as before, should be fine if html_skeleton and module_definitions are correct)
        logging.info("Python API: integrate_modules called.")
        
        if not self.html_skeleton:
            logging.warning("HTML skeleton is not available. Cannot integrate. Ensure analyze_html was called successfully.")
            return getattr(self, 'original_html_content_py', "Error: HTML skeleton not generated.")

        final_html = self.html_skeleton 

        all_modified_css = []
        all_modified_js = []

        logging.debug(f"Starting integration with skeleton: {final_html[:200]}...")
        logging.debug(f"Available module definitions for integration: {len(self.module_definitions)}")
        logging.debug(f"Modified modules by instruction: {list(self.modified_modules.keys())}")

        for module_def in self.module_definitions: # These now have 'original_content'
            module_id = module_def.get("id")
            if not module_id:
                logging.warning("Found a module definition without an ID during integration. Skipping.")
                continue

            placeholder = f""
            content_to_insert = ""

            if module_id in self.modified_modules:
                module_mod_data = self.modified_modules[module_id]
                content_to_insert = module_mod_data.get("modified_code", {}).get("html", "")
                
                if module_mod_data.get("modified_code", {}).get("css"):
                    all_modified_css.append(f"/* CSS for module: {module_id} (modified by instruction) */\n{module_mod_data['modified_code']['css']}")
                if module_mod_data.get("modified_code", {}).get("js"):
                    all_modified_js.append(f"// JS for module: {module_id} (modified by instruction)\n{module_mod_data['modified_code']['js']}")
                
                logging.info(f"Module '{module_id}' was modified by instruction. Using its new HTML.")
            else:
                content_to_insert = module_def.get("original_content", "") # Use stored original_content
                logging.debug(f"Module '{module_id}' not in modified_modules. Using its original_content (len: {len(content_to_insert)}).")


            if placeholder in final_html:
                final_html = final_html.replace(placeholder, content_to_insert, 1) 
                logging.debug(f"Replaced placeholder for module '{module_id}'.")
            else:
                logging.warning(f"Placeholder '{placeholder}' for module '{module_id}' not found in the HTML skeleton. Integration for this module might be incomplete.")
        
        if all_modified_css:
            css_block = "\n<style type=\"text/css\">\n" + "\n\n".join(all_modified_css) + "\n</style>\n"
            if "</head>" in final_html:
                final_html = final_html.replace("</head>", css_block + "</head>", 1)
            elif "<body" in final_html: 
                 final_html = css_block + final_html
            else: 
                final_html += css_block
            logging.info("Injected collected CSS into final HTML.")

        if all_modified_js:
            js_block = "\n<script type=\"text/javascript\">\n//<![CDATA[\n" + "\n\n".join(all_modified_js) + "\n//]]>\n</script>\n"
            if "</body>" in final_html:
                final_html = final_html.replace("</body>", js_block + "</body>", 1)
            else: 
                final_html += js_block
            logging.info("Injected collected JS into final HTML.")

        logging.info("Module integration complete.")
        logging.debug(f"Final integrated HTML (first 200 chars): {final_html[:200]}...")
        return final_html

    def get_modification_manual(self, module_id):
        # ... (same as before)
        return self.modified_modules.get(module_id, {}).get("modification_manual", "No modification manual available for this module.")

    def get_prompt_template_for_frontend(self):
        # ... (same as before)
        logging.debug("get_prompt_template_for_frontend called by frontend.")
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code}", "[用户 HTML 在此]").replace("{specific_instruction}", "[修改指令在此]")

if __name__ == '__main__':
    api = Api()
    logging.info("Starting PyWebview window...")
    window = webview.create_window(
        '代码智能装配流水线 (Code Smart Assembly Line)', 
        'gui.html',        
        js_api=api,        
        width=1200,
        height=850,
        resizable=True
    )
    logging.info("PyWebview window created. Starting application...")
    webview.start(debug=True) 
    logging.info("PyWebview application has been closed.")
