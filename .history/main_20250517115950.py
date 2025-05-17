import webview
import json
import os
import logging
from dotenv import load_dotenv

# New modular imports
from config_loader import load_api_config, DEFAULT_API_CONFIG #DEFAULT_API_CONFIG for fallback
from html_utils import (
    add_markers_to_html,
    extract_module_content_by_markers,
    generate_skeleton_with_placeholders,
    integrate_final_code
)
from llm_handler import LLMHandler, PROMPT_TEMPLATE_BASE_MODIFICATION # For frontend display

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

class Api:
    def __init__(self):
        self.raw_original_html_content = "" # The very first HTML input by user
        self.html_content_with_markers = "" # HTML after LLM defs and marker insertion
        self.html_skeleton = ""
        self.api_config = load_api_config("api_config.json") # Uses new loader
        
        # Initialize LLMHandler
        self.llm_handler = LLMHandler(
            api_config=self.api_config,
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            site_url=os.getenv("YOUR_SITE_URL", "http://localhost:8003/default-app"), # From old main
            site_name=os.getenv("YOUR_SITE_NAME", "DefaultModularizerAppV3") # From old main
        )
        
        self.llm_defined_modules = [] # Stores {id, description, start_char, end_char, start_comment, end_comment, original_content}
        self.llm_modification_results = {} # Stores {module_id (if targeted): {"modified_code": {...}, "modification_manual": "...", "affected_modules_by_llm": []}}
                                           # Or a general structure if not module-specific: {"modified_code": {...}, "modification_manual": "..."}


    def analyze_html(self, original_code_from_frontend, specific_instruction=""):
        logging.info("Python API: analyze_html called.")
        self.raw_original_html_content = original_code_from_frontend.strip() if original_code_from_frontend else ""

        if not self.raw_original_html_content:
            return {"status": "error", "message": "无效或空HTML", "active_module_definitions": [], 
                    "html_skeleton": "", "modified_code": {}, "modification_manual": ""}

        # Reset state for new analysis
        self.html_content_with_markers = ""
        self.html_skeleton = ""
        self.llm_defined_modules = []
        self.llm_modification_results = {}

        # 1. Get module definitions from LLM
        logging.info("Step 1: Getting module definitions from LLM.")
        definition_response = self.llm_handler.get_module_definitions(self.raw_original_html_content)

        if definition_response["status"] != "success":
            return {"status": "error", "message": f"LLM未能定义模块: {definition_response['message']}",
                    "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}
        
        raw_definitions_from_llm = definition_response["definitions"]
        if not raw_definitions_from_llm:
            return {"status": "warning", "message": "LLM未识别出任何模块定义。",
                    "active_module_definitions": [], "html_skeleton": self.raw_original_html_content, # Return raw if no defs
                     "modified_code": {}, "modification_manual": ""}

        # 2. Add markers to HTML based on LLM definitions
        logging.info("Step 2: Adding markers to HTML.")
        self.html_content_with_markers = add_markers_to_html(self.raw_original_html_content, raw_definitions_from_llm)
        if not self.html_content_with_markers: # Should not happen if raw_original_html_content exists
             self.html_content_with_markers = self.raw_original_html_content # Fallback
             logging.warning("add_markers_to_html returned empty, using raw HTML for marked content.")


        # 3. Extract original content for each module and store definitions
        logging.info("Step 3: Extracting original content for each module.")
        temp_processed_definitions = []
        for module_def_llm in raw_definitions_from_llm:
            # Ensure the id from the comment matches the module id for consistency
            if module_def_llm.get("id") not in module_def_llm.get("start_comment", ""):
                logging.warning(f"Mismatch between module ID '{module_def_llm.get('id')}' and start_comment '{module_def_llm.get('start_comment')}'. Fixing comment for internal use.")
                module_def_llm["start_comment"] = f"LLM_MODULE_START: {module_def_llm.get('id')}"
                module_def_llm["end_comment"] = f"LLM_MODULE_END: {module_def_llm.get('id')}"

            content = extract_module_content_by_markers(self.html_content_with_markers, module_def_llm)
            if content is not None:
                temp_processed_definitions.append({**module_def_llm, "original_content": content.strip()})
                logging.debug(f"  Module '{module_def_llm.get('id')}': Original Content (first 100 chars): '{content.strip()[:100]}'")
            else:
                logging.warning(f"Could not extract original content for module ID: {module_def_llm.get('id')}. It will be excluded from active definitions for frontend.")
        
        self.llm_defined_modules = temp_processed_definitions
        logging.info(f"Processed {len(self.llm_defined_modules)} modules and stored with their original content.")

        if not self.llm_defined_modules: # If all extractions failed
             return {"status": "warning", "message": "LLM定义了模块，但无法从中提取内容。",
                    "active_module_definitions": [], "html_skeleton": self.raw_original_html_content,
                     "modified_code": {}, "modification_manual": ""}


        # 4. Generate HTML skeleton
        logging.info("Step 4: Generating HTML skeleton.")
        self.html_skeleton = generate_skeleton_with_placeholders(self.html_content_with_markers, self.llm_defined_modules)
        if not self.html_skeleton:
            logging.error("Failed to generate HTML skeleton. This is unexpected if markers were added.")
            # Fallback or error, for now, let's allow proceeding if some modules are defined.
            # The frontend might not be able to integrate if skeleton is missing.

        # 5. Handle specific modification instruction if provided
        modified_code_for_response = {}
        modification_manual_for_response = ""

        if specific_instruction:
            logging.info(f"Step 5: Processing specific instruction with LLM: {specific_instruction}")
            modification_call_result = self.llm_handler.get_code_modification(
                self.raw_original_html_content, # Pass the original clean HTML for modification context
                specific_instruction
            )
            
            if modification_call_result["status"] == "success":
                self.llm_modification_results = modification_call_result # Store the whole result
                modified_code_for_response = modification_call_result.get("modified_code", {})
                modification_manual_for_response = modification_call_result.get("modification_manual", "")
                # If LLM indicates specific modules it modified, we could store that:
                # affected_by_llm = modification_call_result.get("affected_modules_by_llm", [])
                # For now, `self.llm_modification_results` holds this if needed for integration logic.
                logging.info("LLM successfully processed modification instruction.")
            elif modification_call_result["status"] == "error":
                logging.error(f"LLM modification failed: {modification_call_result['message']}")
                modification_manual_for_response = f"LLM 修改指令处理失败: {modification_call_result['message']}"
                # Keep empty modified_code_for_response
            else: // "skipped" or other
                logging.info(f"LLM modification skipped or other status: {modification_call_result['message']}")
                modification_manual_for_response = modification_call_result['message']


        # Prepare response for frontend
        # `active_module_definitions` for frontend should be {id, description, original_content}
        frontend_module_defs = [
            {"id": m["id"], "description": m["description"], "original_content": m["original_content"]}
            for m in self.llm_defined_modules
        ]

        max_modules_frontend = self.api_config.get("max_modules_to_process_frontend", 20)

        return {
            "status": "success",
            "message": f"分析完成, 识别到 {len(self.llm_defined_modules)} 个模块。",
            "active_module_definitions": frontend_module_defs[:max_modules_frontend],
            "html_skeleton": self.html_skeleton, # Send skeleton for potential later use or debug
            "modified_code": modified_code_for_response, # This is LLM's direct modification output
            "modification_manual": modification_manual_for_response
        }

    def integrate_modules_with_user_edits(self, user_edited_modules_json_string="{}"):
        logging.info("Python API: integrate_modules_with_user_edits called.")
        user_edited_modules_dict = {}
        try:
            if user_edited_modules_json_string:
                user_edited_modules_dict = json.loads(user_edited_modules_json_string)
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing user_edited_modules_json_string: {e}")
            return f"错误：用户编辑数据解析失败 - {e}"

        if not self.html_skeleton:
            logging.error("Integration called but HTML skeleton is not available.")
            return getattr(self, 'raw_original_html_content', "错误：HTML骨架未生成，且无原始HTML。")

        # The llm_modification_results might contain one block of modified_code,
        # or it might be structured per module if the LLM identifies a target.
        # For now, assume it's a single block if `specific_instruction` was given.
        # The `integrate_final_code` needs a store like {module_id: {"modified_code": ...}}
        # The current `self.llm_modification_results` directly holds the `modified_code` and `manual`.
        # If the LLM's modification is meant to replace a *specific* module it identified,
        # we need to map it. The `PROMPT_TEMPLATE_BASE_MODIFICATION` asks LLM to output `modules` array.
        # Let's use the first module ID from that if present.

        llm_targeted_mod_store = {}
        if self.llm_modification_results and self.llm_modification_results.get("status") == "success":
            llm_data = self.llm_modification_results
            # If LLM specified modules it touched in "affected_modules_by_llm"
            affected_llm_modules = llm_data.get("affected_modules_by_llm", [])
            if affected_llm_modules and isinstance(affected_llm_modules, list) and len(affected_llm_modules) > 0:
                # Assume the first module in that list is the primary target for the `modified_code`
                target_module_id = affected_llm_modules[0].get("id")
                if target_module_id:
                    llm_targeted_mod_store[target_module_id] = {
                        "modified_code": llm_data.get("modified_code", {}),
                        "modification_manual": llm_data.get("modification_manual", "")
                    }
                    logging.info(f"LLM modification will target module ID: {target_module_id} for integration.")
                else:
                    logging.warning("LLM indicated affected modules but no ID found for the primary one.")
            else:
                # If LLM doesn't specify a target module for its `modified_code`, this is problematic for integration
                # unless the modification is wholesale or affects non-modular parts.
                # For now, we won't automatically apply it if no target module ID is clear from LLM.
                logging.warning("LLM modification occurred but no specific target module ID was identified by LLM in 'modules' list. LLM's direct 'modified_code' will not be automatically integrated by module ID.")


        final_html = integrate_final_code(
            html_skeleton=self.html_skeleton,
            module_definitions=self.llm_defined_modules, # Contains original_content
            user_edited_modules=user_edited_modules_dict,
            llm_modified_code_store=llm_targeted_mod_store, # Pass the mapped store
            default_original_html_if_skeleton_missing=self.raw_original_html_content
        )
        return final_html

    def get_prompt_template_for_frontend(self):
        # Use the method from LLMHandler to get the template
        if self.llm_handler:
            return self.llm_handler.get_prompt_template_for_frontend()
        # Fallback if llm_handler somehow not initialized (should not happen)
        return PROMPT_TEMPLATE_BASE_MODIFICATION.replace("{user_html_code}", "[N/A]").replace("{specific_instruction}", "[N/A]")


if __name__ == '__main__':
    api = Api()
    # For debugging the API class methods directly:
    # sample_html_input = """<!DOCTYPE html><html><head><title>Test</title></head><body><div id="block1">Content 1</div><div id="block2">Content 2</div></body></html>"""
    # analysis_result = api.analyze_html(sample_html_input, "Change Content 1 to 'New Content 1'")
    # print("--- Analysis Result ---")
    # print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
    # if analysis_result["status"] == "success":
    #     user_edits = {} # '{"block2": {"html": "<div>User Edited Content 2</div>"}}'
    #     print("\n--- Integration Result ---")
    #     integrated_html = api.integrate_modules_with_user_edits(json.dumps(user_edits))
    #     print(integrated_html)

    webview.create_window('代码智能装配流水线', 'gui.html', js_api=api, width=1300, height=900, resizable=True)
    webview.start(debug=True) # Set debug=False for production