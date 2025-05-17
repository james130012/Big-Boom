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
    "api_url": "[https://openrouter.ai/api/v1/chat/completions](https://openrouter.ai/api/v1/chat/completions)", # Corrected: Removed Markdown
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
        self.modified_modules = {}  # Stores LLM modifications from 'specific_instruction'
        self.module_definitions = [] # Stores all identified modules with their 'original_content'

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
        if not definitions_from_llm:
            logging.debug("_add_comments_to_html_revised: No definitions provided.")
            return original_html

        processed_defs = []
        original_lines = original_html.splitlines(keepends=True)

        for i, d_orig in enumerate(definitions_from_llm):
            d = d_orig.copy() 
            module_id = d.get("id", f"unknown_module_{i}") 
            start_comment_text = d.get("start_comment", "").strip() # e.g., "LLM_MODULE_START: module_id"
            end_comment_text = d.get("end_comment", "").strip()   # e.g., "LLM_MODULE_END: module_id"

            if not all([module_id, start_comment_text, end_comment_text]):
                logging.warning(f"Module '{module_id}' in _add_comments_to_html_revised: incomplete comment texts. Skipping.")
                continue

            s_char, e_char = -1, -1
            if "start_char" in d and "end_char" in d:
                s_char, e_char = d["start_char"], d["end_char"]
            elif "start_line" in d and "end_line" in d:
                s_line, e_line = d["start_line"], d["end_line"]
                if not (1 <= s_line <= len(original_lines) and 1 <= e_line <= len(original_lines) and s_line <= e_line):
                    logging.warning(f"Module '{module_id}' has invalid line numbers ({s_line}-{e_line}) for {len(original_lines)} lines. Skipping.")
                    continue
                s_char = sum(len(line) for line in original_lines[:s_line - 1])
                e_char = sum(len(line) for line in original_lines[:e_line]) 
            else:
                logging.warning(f"Module '{module_id}' lacks char/line positions. Skipping.")
                continue

            if not (0 <= s_char <= e_char <= len(original_html)):
                logging.warning(f"Module '{module_id}' has invalid char positions ({s_char}, {e_char}) for original_html length {len(original_html)}. Skipping.")
                continue
            
            d["s_char_final"] = s_char
            d["e_char_final"] = e_char
            # Corrected: Define the exact HTML comment tags to be inserted
            d["start_marker_tag_full"] = f"\n"
            d["end_marker_tag_full"] = f"\n"
            processed_defs.append(d)

        processed_defs.sort(key=lambda x: x["s_char_final"])

        result_parts = []
        current_pos_in_original = 0
        for defi in processed_defs:
            s_char = defi["s_char_final"]
            e_char = defi["e_char_final"]

            if s_char > current_pos_in_original:
                result_parts.append(original_html[current_pos_in_original:s_char])
            
            result_parts.append(defi["start_marker_tag_full"])
            result_parts.append(original_html[s_char:e_char]) # This is the module's original content
            result_parts.append(defi["end_marker_tag_full"])
            
            current_pos_in_original = e_char 

        if current_pos_in_original < len(original_html):
            result_parts.append(original_html[current_pos_in_original:])
        
        final_html = "".join(result_parts)
        logging.debug(f"_add_comments_to_html_revised output (first 300 chars): {final_html[:300]}...")
        return final_html

    def _extract_module_content_from_string(self, html_string_with_llm_comments, module_def):
        module_id = module_def.get('id', 'N/A')
        start_comment_text = module_def.get('start_comment', '').strip() 
        end_comment_text = module_def.get('end_comment', '').strip()

        if not start_comment_text or not end_comment_text:
            logging.warning(f"Module '{module_id}' is missing start_comment or end_comment text. Cannot extract content.")
            return ""

        # Corrected: Construct the full comment tags as they were inserted
        effective_start_marker = f"\n"
        effective_end_marker_prefix = f"\n" 

        start_marker_find_idx = html_string_with_llm_comments.find(effective_start_marker)
        
        if start_marker_find_idx == -1:
            logging.warning(f"Effective start marker for module '{module_id}' NOT FOUND. Marker: '{effective_start_marker.strip()}'")
            return ""

        content_actual_start_idx = start_marker_find_idx + len(effective_start_marker)
        content_actual_end_idx = html_string_with_llm_comments.find(effective_end_marker_prefix, content_actual_start_idx)

        if content_actual_end_idx == -1:
            logging.warning(f"Effective end marker for module '{module_id}' NOT FOUND. Marker prefix: '{effective_end_marker_prefix.strip()}'")
            return ""

        extracted_content = html_string_with_llm_comments[content_actual_start_idx:content_actual_end_idx]
        return extracted_content # Return raw content, stripping will be done by caller if needed, or here.
                                 # The prompt asks LLM for HTML, so it might have its own formatting.

    def _generate_skeleton_from_string(self, html_string_with_llm_comments, modules_to_skeletonize):
        skeleton = html_string_with_llm_comments
        
        temp_modules_for_skeleton = []
        # s_char_final should be present from the processing in _add_comments_to_html_revised
        for m_def in modules_to_skeletonize:
            m_copy = m_def.copy()
            if "s_char_final" not in m_copy: # Fallback if somehow missing
                s_char = m_copy.get("start_char", 0) # Basic fallback
                m_copy["s_char_final"] = s_char
            temp_modules_for_skeleton.append(m_copy)

        sorted_modules = sorted(
            temp_modules_for_skeleton,
            key=lambda x: x.get("s_char_final", 0), 
            reverse=True # Process from end to start to avoid index shifting issues on 'skeleton'
        )

        for module_def in sorted_modules:
            module_id = module_def.get('id', '').strip()
            start_comment_text = module_def.get('start_comment', '').strip()
            end_comment_text = module_def.get('end_comment', '').strip()

            if not module_id or not start_comment_text or not end_comment_text:
                logging.warning(f"Skipping skeletonization for module due to missing id or comment texts: {module_def.get('id')}")
                continue

            # Corrected: These are the full comment tags as inserted
            full_start_marker = f"\n"
            full_end_marker = f"\n"
            # Corrected: This is the placeholder for the skeleton
            placeholder = f"" 
            
            start_idx_of_start_marker = skeleton.find(full_start_marker)
            if start_idx_of_start_marker == -1:
                logging.warning(f"Could not find full start marker for module '{module_id}' in skeleton generation. Marker: '{full_start_marker.strip()}'")
                continue
            
            search_for_end_from = start_idx_of_start_marker + len(full_start_marker)
            start_idx_of_end_marker = skeleton.find(full_end_marker, search_for_end_from)
            
            if start_idx_of_end_marker == -1:
                logging.warning(f"Could not find full end marker for module '{module_id}' after start marker in skeleton generation. Marker: '{full_end_marker.strip()}'")
                continue
            
            content_to_replace_start_idx = start_idx_of_start_marker
            content_to_replace_end_idx = start_idx_of_end_marker + len(full_end_marker)
            
            skeleton = skeleton[:content_to_replace_start_idx] + placeholder + skeleton[content_to_replace_end_idx:]
            logging.debug(f"Replaced module block for '{module_id}' with placeholder in skeleton.")
            
        return skeleton

    def analyze_html(self, original_code, specific_instruction=""):
        logging.info("Python API: analyze_html called.")
        raw_original_code = original_code.strip() if original_code else ""

        if not raw_original_code:
            logging.warning("Received empty HTML. Returning error response.")
            self.original_html_content_py = ""
            self.html_skeleton = ""
            self.module_definitions = []
            self.modified_modules = {}
            return {
                "status": "error", "message": "无效或空HTML",
                "active_module_definitions": [], "html_skeleton": "",
                "modified_code": {}, "modification_manual": ""
            }

        # Step 1: LLM Call for Module Definitions
        module_definition_prompt_filled = PROMPT_TEMPLATE_BASE.split("输入HTML：")[0].strip() + \
                                     f"\n输入HTML：\n```html\n{raw_original_code}\n```\n" + \
                                     PROMPT_TEMPLATE_BASE.split("修改指令：")[1].split("请严格按上述JSON结构返回结果。")[0].strip().replace("{specific_instruction}", "仅模块识别，无需修改。") + \
                                     "\n请严格按上述JSON结构返回结果。" # Simplified prompt for just definitions
        
        # This is a simplified prompt for the first call (module identification)
        # The full PROMPT_TEMPLATE_BASE is complex. We need a variant for just definitions.
        # For now, using a simplified approach for the definition prompt.
        # A more robust solution would be a separate, dedicated prompt for definitions.
        # Using a placeholder for the actual definition prompt for brevity here.
        # IMPORTANT: The actual module_definition_prompt should be designed to *only* return definitions.
        temp_definition_prompt = f"""分析以下HTML代码，识别潜在的模块（如动画、页眉、页脚、文本块），返回模块定义列表，每个模块包含：
- id：唯一标识（小写蛇形命名法，例如 animation_box_1, header_section）
- description：模块描述（中文，例如 “动画1模块”）
- start_line/end_line：模块在原始HTML中的起止行号（1-based, inclusive）。
- start_char/end_char：模块在原始HTML中的起止字符位置（0-based, start inclusive, end exclusive）。
- start_comment：建议的起始注释标记文本 (例如 "LLM_MODULE_START: animation_box_1")
- end_comment：建议的结束注释标记文本 (例如 "LLM_MODULE_END: animation_box_1")
确保 start_char 和 end_char 精确地包围模块的HTML内容，不包括模块外的空白或标签。
返回JSON格式：
{{
  "module_count_suggestion": <建议处理的模块数>,
  "definitions": [
    {{
      "id": "<模块ID>",
      "description": "<描述>",
      "start_line": <起始行>,
      "end_line": <结束行>,
      "start_char": <起始字符>,
      "end_char": <结束字符>,
      "start_comment": "<起始注释文本>",
      "end_comment": "<结束注释文本>"
    }}
  ]
}}
HTML代码：
{raw_original_code}
"""

        raw_definitions_from_llm = []
        if not self.openrouter_api_key:
            logging.warning("OPENROUTER_API_KEY is not set. Using mock data for module definitions.")
            # Example mock definitions (ensure these are accurate for your test HTML)
            mock_defs = [
                {"id": "header_section", "description": "网站Logo和主要标题", "start_char": 500, "end_char": 556, "start_comment": "LLM_MODULE_START: header_section", "end_comment": "LLM_MODULE_END: header_section"},
                {"id": "anim1_box", "description": "动画1的容器", "start_char": 765, "end_char": 864, "start_comment": "LLM_MODULE_START: anim1_box", "end_comment": "LLM_MODULE_END: anim1_box"},
                {"id": "footer_section", "description": "页脚版权", "start_char": 1118, "end_char": 1174, "start_comment": "LLM_MODULE_START: footer_section", "end_comment": "LLM_MODULE_END: footer_section"}
            ] # These char numbers are illustrative
            raw_definitions_from_llm = mock_defs
        else:
            try:
                logging.info("Calling LLM for module definitions...")
                headers = {"Authorization": f"Bearer {self.openrouter_api_key}", "Content-Type": "application/json", "HTTP-Referer": self.site_url, "X-Title": self.site_name}
                payload = {"model": self.api_config.get("default_model"), "messages": [{"role": "user", "content": temp_definition_prompt}], "temperature": self.api_config.get("llm_temperature", 0.1), "max_tokens": self.api_config.get("llm_max_tokens", 4096), "response_format": {"type": "json_object"}}
                response = requests.post(self.api_config.get("api_url"), headers=headers, json=payload, timeout=self.api_config.get("request_timeout_seconds", 120))
                response.raise_for_status()
                llm_response_data = json.loads(response.json()["choices"][0]["message"]["content"].strip("```json").strip("```"))
                raw_definitions_from_llm = llm_response_data.get("definitions", [])
                logging.info(f"LLM returned {len(raw_definitions_from_llm)} module definitions.")
            except Exception as e: # Catch broader exceptions for LLM call
                logging.error(f"Error during LLM call for definitions or parsing: {e}")
                return {"status": "error", "message": f"LLM API/Parse Error (Definitions): {e}", "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}

        self.original_html_content_py = self._add_comments_to_html_revised(raw_original_code, raw_definitions_from_llm)
        
        temp_processed_definitions = []
        for module_def_llm in raw_definitions_from_llm:
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def_llm)
            # content can be an empty string for an empty module, which is valid.
            # The check should be for None, indicating extraction failure.
            if content is not None: 
                temp_processed_definitions.append({**module_def_llm, "original_content": content.strip()}) # Store stripped content
                logging.info(f"Successfully extracted content for module ID: {module_def_llm.get('id')}. Length: {len(content)}")
            else:
                logging.warning(f"Could not extract original content for module ID: {module_def_llm.get('id')}. It will be excluded.")
        
        self.module_definitions = temp_processed_definitions
        logging.info(f"Processed {len(self.module_definitions)} modules and stored with their original content.")

        self.html_skeleton = self._generate_skeleton_from_string(self.original_html_content_py, self.module_definitions)
        
        modified_code_for_response = {}
        modification_manual_for_response = ""
        self.modified_modules = {} 

        if specific_instruction:
            logging.info(f"Processing specific instruction: {specific_instruction}")
            modification_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", raw_original_code).replace("{specific_instruction}", specific_instruction)
            
            if not self.openrouter_api_key:
                # Mock LLM modification
                # ... (same as before)
                pass
            else:
                try:
                    # Actual LLM call for modification
                    # ... (same as before)
                    logging.info("Calling LLM for code modification...")
                    headers = {"Authorization": f"Bearer {self.openrouter_api_key}", "Content-Type": "application/json", "HTTP-Referer": self.site_url, "X-Title": self.site_name}
                    payload = {"model": self.api_config.get("default_model"), "messages": [{"role": "user", "content": modification_prompt}], "temperature": self.api_config.get("llm_temperature", 0.1), "max_tokens": self.api_config.get("llm_max_tokens", 4096), "response_format": {"type": "json_object"}}
                    response = requests.post(self.api_config.get("api_url"), headers=headers, json=payload, timeout=self.api_config.get("request_timeout_seconds", 120))
                    response.raise_for_status()
                    llm_modification_response = json.loads(response.json()["choices"][0]["message"]["content"].strip("```json").strip("```"))

                    if llm_modification_response.get("status") == "success":
                        modified_code_for_response = llm_modification_response.get("modified_code", {})
                        modification_manual_for_response = llm_modification_response.get("modification_manual", "")
                        llm_reported_modified_modules = llm_modification_response.get("modules", [])
                        if llm_reported_modified_modules:
                            target_module_id = llm_reported_modified_modules[0].get("id")
                            if target_module_id:
                                self.modified_modules[target_module_id] = {"modified_code": modified_code_for_response, "modification_manual": modification_manual_for_response}
                                logging.info(f"Stored LLM modification for module ID: {target_module_id}")
                    # ... error handling for LLM modification ...
                except Exception as e: # Catch broader exceptions
                    logging.error(f"Error during LLM call for modification or parsing: {e}")
                    modification_manual_for_response = f"LLM API/Parse Error (Modification): {e}"


        max_to_send = self.api_config.get("max_modules_to_process_frontend", len(self.module_definitions))
        definitions_for_frontend = self.module_definitions[:max_to_send]

        return {
            "status": "success",
            "message": f"分析完成，识别到 {len(self.module_definitions)} 个模块。",
            "active_module_definitions": definitions_for_frontend, 
            "html_skeleton": self.html_skeleton,
            "modified_code": modified_code_for_response, 
            "modification_manual": modification_manual_for_response
        }

    def integrate_modules_with_user_edits(self, user_edited_modules_json_string="{}"):
        logging.info("Python API: integrate_modules_with_user_edits called.")
        
        user_edited_modules_dict = {}
        try:
            if user_edited_modules_json_string:
                user_edited_modules_dict = json.loads(user_edited_modules_json_string)
            logging.info(f"Received {len(user_edited_modules_dict)} user-edited modules.")
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing user_edited_modules_json_string: {e}")
            # Potentially return an error or integrate without user edits
            # For now, proceed without user edits if JSON is malformed.

        if not self.html_skeleton:
            logging.warning("HTML skeleton is not available for integration.")
            return getattr(self, 'original_html_content_py', "Error: HTML skeleton not generated.")

        final_html = self.html_skeleton 
        all_modified_css = [] # To collect CSS from LLM-modified or user-modified modules
        all_modified_js = []  # To collect JS

        for module_def in self.module_definitions:
            module_id = module_def.get("id")
            if not module_id:
                logging.warning("Found a module definition without an ID during integration. Skipping.")
                continue

            placeholder = f"" # Corrected placeholder
            content_to_insert = ""
            source_of_content = "original" # For logging

            # Priority: 1. User Edit, 2. LLM Edit, 3. Original
            if module_id in user_edited_modules_dict:
                content_to_insert = user_edited_modules_dict[module_id].get("html", "") # Assuming user edit provides HTML
                # Note: User edits might also provide CSS/JS. This needs a more complex structure for user_edited_modules_dict
                # For now, assume user edit is HTML only for the main content. CSS/JS from LLM mods are handled separately.
                source_of_content = "user_edit"
                logging.info(f"Module '{module_id}': Using user-edited HTML.")
            elif module_id in self.modified_modules: # LLM modification from initial instruction
                llm_mod_data = self.modified_modules[module_id]
                content_to_insert = llm_mod_data.get("modified_code", {}).get("html", "")
                
                # Collect CSS/JS from LLM's modification
                if llm_mod_data.get("modified_code", {}).get("css"):
                    all_modified_css.append(f"/* CSS for module: {module_id} (LLM modified) */\n{llm_mod_data['modified_code']['css']}")
                if llm_mod_data.get("modified_code", {}).get("js"):
                    all_modified_js.append(f"// JS for module: {module_id} (LLM modified)\n{llm_mod_data['modified_code']['js']}")
                source_of_content = "llm_instruction_edit"
                logging.info(f"Module '{module_id}': Using LLM-instructed modified HTML.")
            else:
                content_to_insert = module_def.get("original_content", "")
                logging.debug(f"Module '{module_id}': Using original content.")

            if placeholder in final_html:
                final_html = final_html.replace(placeholder, content_to_insert, 1) 
                logging.debug(f"Replaced placeholder for module '{module_id}' using content from {source_of_content}.")
            else:
                logging.warning(f"Placeholder '{placeholder}' for module '{module_id}' not found in skeleton.")
        
        # CSS and JS Injection (same as before, collects from LLM modifications)
        if all_modified_css:
            css_block = "\n<style type=\"text/css\">\n" + "\n\n".join(all_modified_css) + "\n</style>\n"
            if "</head>" in final_html: final_html = final_html.replace("</head>", css_block + "</head>", 1)
            elif "<body" in final_html: final_html = css_block + final_html
            else: final_html += css_block
            logging.info("Injected collected CSS into final HTML.")

        if all_modified_js:
            js_block = "\n<script type=\"text/javascript\">\n//<![CDATA[\n" + "\n\n".join(all_modified_js) + "\n//]]>\n</script>\n"
            if "</body>" in final_html: final_html = final_html.replace("</body>", js_block + "</body>", 1)
            else: final_html += js_block
            logging.info("Injected collected JS into final HTML.")

        logging.info("Module integration with user edits complete.")
        return final_html

    # Keep the old integrate_modules if it's still somehow called or for backward compatibility,
    # but new flow should use integrate_modules_with_user_edits.
    # For simplicity, I'll remove the old one, assuming frontend will be updated.
    # def integrate_modules(self): ...

    def get_prompt_template_for_frontend(self):
        logging.debug("get_prompt_template_for_frontend called by frontend.")
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code}", "[用户 HTML 在此]").replace("{specific_instruction}", "[修改指令在此]")

if __name__ == '__main__':
    api = Api()
    logging.info("Starting PyWebview window...")
    window = webview.create_window(
        '代码智能装配流水线 (Code Smart Assembly Line)', 
        'gui.html',        
        js_api=api,        
        width=1300, # Slightly wider for new edit area
        height=900, # Slightly taller
        resizable=True
    )
    logging.info("PyWebview window created. Starting application...")
    webview.start(debug=True) 
    logging.info("PyWebview application has been closed.")
