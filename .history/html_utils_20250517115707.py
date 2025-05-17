# html_utils.py
import logging

def add_markers_to_html(original_html, definitions_from_llm):
    """
    Adds HTML comment markers around identified modules in the original HTML.
    Uses 'start_comment' and 'end_comment' fields from LLM definitions.
    """
    if not definitions_from_llm:
        return original_html

    processed_defs = []
    original_lines = original_html.splitlines(keepends=True)

    for i, d_orig in enumerate(definitions_from_llm):
        d = d_orig.copy()
        module_id = d.get("id", f"unknown_module_{i}")
        # These are the comment *contents* provided by the LLM
        start_comment_content = d.get("start_comment", "").strip()
        end_comment_content = d.get("end_comment", "").strip()

        if not all([module_id, start_comment_content, end_comment_content]):
            logging.warning(f"Module '{module_id}' in add_markers_to_html: incomplete comment content. Skipping.")
            continue

        s_char, e_char = d.get("start_char"), d.get("end_char")
        if s_char is None or e_char is None:
            # Fallback or error if char positions aren't provided (though prompt requires them)
            logging.warning(f"Module '{module_id}' has missing char numbers. Skipping marker insertion.")
            continue

        if not (0 <= s_char <= e_char <= len(original_html)):
            logging.warning(f"Module '{module_id}' invalid char positions ({s_char}-{e_char}) for HTML length {len(original_html)}. Skipping marker insertion.")
            continue

        d["s_char_final"], d["e_char_final"] = s_char, e_char
        # Construct full HTML comments
        d["start_marker_tag_full"] = f"\n\n"
        d["end_marker_tag_full"] = f"\n\n"
        processed_defs.append(d)

    # Sort by start character to process in order
    processed_defs.sort(key=lambda x: x["s_char_final"])

    result_parts = []
    current_pos_in_original = 0
    for defi in processed_defs:
        s_char, e_char = defi["s_char_final"], defi["e_char_final"]
        # Add HTML segment before the current module
        if s_char > current_pos_in_original:
            result_parts.append(original_html[current_pos_in_original:s_char])
        
        result_parts.append(defi["start_marker_tag_full"])  # Add start marker
        result_parts.append(original_html[s_char:e_char])   # Add module content
        result_parts.append(defi["end_marker_tag_full"])    # Add end marker
        current_pos_in_original = e_char

    # Add any remaining part of the HTML
    if current_pos_in_original < len(original_html):
        result_parts.append(original_html[current_pos_in_original:])

    final_html_with_markers = "".join(result_parts)
    logging.debug(f"add_markers_to_html output (first 300 chars): {final_html_with_markers[:300]}...")
    return final_html_with_markers

def extract_module_content_by_markers(html_with_markers, module_definition):
    """
    Extracts the content of a specific module from HTML based on its comment markers.
    """
    module_id = module_definition.get('id', 'N/A')
    start_comment_content = module_definition.get('start_comment', '').strip()
    end_comment_content = module_definition.get('end_comment', '').strip()

    if not start_comment_content or not end_comment_content:
        logging.warning(f"Module '{module_id}' missing comment content for extraction.")
        return None

    # Construct the full HTML comment markers to search for
    effective_start_marker = f""
    effective_end_marker = f""

    start_idx = html_with_markers.find(effective_start_marker)
    if start_idx == -1:
        logging.warning(f"Start marker for '{module_id}' not found during extraction. Searched for: '{effective_start_marker}'")
        return None
    
    # Content starts after the start marker
    content_start_idx = start_idx + len(effective_start_marker)
    
    # Content ends before the end marker
    content_end_idx = html_with_markers.find(effective_end_marker, content_start_idx)
    if content_end_idx == -1:
        logging.warning(f"End marker for '{module_id}' not found during extraction. Searched for: '{effective_end_marker}'")
        return None
        
    # Adjust indices if newlines were part of the marker tags added by add_markers_to_html
    # Assuming markers were added as `\n\n`
    # The content is between `\n\n` [content] `\n\n`
    # So, we need to adjust for the trailing newline of the start marker and the leading newline of the end marker.
    
    # Find the end of the start marker tag (including its trailing newline)
    actual_content_start = html_with_markers.find('\n', content_start_idx)
    if actual_content_start != -1 and actual_content_start < content_end_idx:
         actual_content_start += 1 # Move past the newline
    else: # Should not happen if markers were added correctly
        actual_content_start = content_start_idx


    # Find the beginning of the end marker tag (including its preceding newline)
    # This is simply content_end_idx if the search was for ``
    # If `\n` was searched, content_end_idx is correct.
    # The search should be for the content *between* the full marker tags.

    # Let's re-evaluate:
    # HTML: ... pre_marker_stuff \n\n MODULE_CONTENT \n\n post_marker_stuff ...
    # start_idx points to the start of ""
    # content_start_idx points after ""
    # content_end_idx points to the start of ""
    
    # If add_markers_to_html adds `\nCOMMENT\n`, then the actual content is between these newlines.
    # The `find` for `effective_start_marker` will give index of ``.
    # The content is after `...\n` and before `\n...`
    
    # Simplified extraction: if `add_markers_to_html` places `\nMARKER_TAG\nCONTENT\nMARKER_TAG\n`
    # then the content is from `idx_after_start_marker_and_newline` to `idx_before_end_marker_and_newline`
    
    search_block_start = html_with_markers.find(effective_start_marker)
    if search_block_start == -1: return None # Already checked, but for clarity
    
    search_block_content_starts_after_marker = search_block_start + len(effective_start_marker)
    
    # We expect a newline after the start marker if `add_markers_to_html` added one
    if html_with_markers[search_block_content_starts_after_marker:].startswith('\n'):
        final_content_start = search_block_content_starts_after_marker + 1
    else:
        final_content_start = search_block_content_starts_after_marker

    search_block_end_marker_starts_at = html_with_markers.find(effective_end_marker, final_content_start)
    if search_block_end_marker_starts_at == -1: return None # Already checked

    # We expect a newline before the end marker
    final_content_end = search_block_end_marker_starts_at
    if final_content_end > 0 and html_with_markers[final_content_end-1] == '\n':
        final_content_end -=1

    if final_content_start >= final_content_end:
        logging.warning(f"Calculated empty content for module '{module_id}'. Start: {final_content_start}, End: {final_content_end}")
        return "" # Or None, depending on desired behavior for empty content

    return html_with_markers[final_content_start:final_content_end]


def generate_skeleton_with_placeholders(html_with_markers, module_definitions):
    """
    Replaces module content (between markers) with placeholders in the HTML.
    Sorts modules by start position in reverse to avoid index issues during replacement.
    """
    skeleton = html_with_markers
    
    # Create a list of tuples: (start_char_of_marker, end_char_of_marker_block, placeholder_text)
    # This requires finding the exact start of the start marker and exact end of the end marker.
    
    regions_to_replace = []
    for module_def in module_definitions:
        module_id = module_def.get('id')
        start_comment_content = module_def.get('start_comment', '').strip()
        end_comment_content = module_def.get('end_comment', '').strip()

        if not module_id or not start_comment_content or not end_comment_content:
            logging.warning(f"Skipping module '{module_id}' in skeleton generation due to missing info.")
            continue

        full_start_marker = f"" # Actual comment tag
        full_end_marker = f""     # Actual comment tag
        placeholder = f""

        start_marker_idx = skeleton.find(full_start_marker)
        if start_marker_idx == -1:
            logging.warning(f"Full start marker for '{module_id}' not found in skeleton generation. Searched: '{full_start_marker}'")
            continue
        
        # The block to replace is from the start of the start_marker up to the end of the end_marker
        # Including the newlines that `add_markers_to_html` might have added around them.
        
        # Start of the block is the start of the newline preceding the start marker (if any)
        block_start_idx = start_marker_idx
        if block_start_idx > 0 and skeleton[block_start_idx-1] == '\n':
            block_start_idx -=1 

        end_marker_idx = skeleton.find(full_end_marker, start_marker_idx + len(full_start_marker))
        if end_marker_idx == -1:
            logging.warning(f"Full end marker for '{module_id}' not found in skeleton generation. Searched: '{full_end_marker}'")
            continue
            
        # End of the block is after the end marker and its trailing newline (if any)
        block_end_idx = end_marker_idx + len(full_end_marker)
        if block_end_idx < len(skeleton) and skeleton[block_end_idx] == '\n':
            block_end_idx += 1
        
        regions_to_replace.append({
            "module_id": module_id,
            "block_start": block_start_idx, # Start of the entire marked block
            "block_end": block_end_idx,     # End of the entire marked block
            "placeholder": placeholder
        })

    # Sort by block_start in reverse order to avoid index shifts during replacement
    regions_to_replace.sort(key=lambda x: x["block_start"], reverse=True)

    for region in regions_to_replace:
        skeleton = skeleton[:region["block_start"]] + region["placeholder"] + skeleton[region["block_end"]:]
        logging.debug(f"Replaced module block for '{region['module_id']}' with placeholder in skeleton.")
    
    return skeleton

def integrate_final_code(
    html_skeleton,
    module_definitions,
    user_edited_modules,
    llm_modified_code_store, # Assuming this is a dict {module_id: {"modified_code": {...}, "manual": "..."}}
    default_original_html_if_skeleton_missing):
    """
    Integrates module content (from user edits, LLM modifications, or original)
    into the HTML skeleton. Also aggregates CSS and JS from LLM modifications.
    """
    if not html_skeleton:
        logging.warning("HTML skeleton is missing. Falling back to default original HTML (which might be empty).")
        # This might not be ideal if the original HTML also had markers.
        # The fallback should ideally be the raw original HTML before any processing if skeletonization failed.
        # However, the calling context (Api class) will manage `self.original_html_content_py` vs `raw_original_code`
        return default_original_html_if_skeleton_missing # Or handle error appropriately

    final_html = html_skeleton
    all_modified_css = []
    all_modified_js = []

    for module_def in module_definitions: # Iterate in definition order for predictability
        module_id = module_def.get("id")
        if not module_id:
            continue

        placeholder = f""
        content_to_insert = ""
        source = "unknown"

        if module_id in user_edited_modules and "html" in user_edited_modules[module_id]:
            content_to_insert = user_edited_modules[module_id]["html"]
            source = "user_edit"
        elif module_id in llm_modified_code_store and "modified_code" in llm_modified_code_store[module_id]:
            llm_mod_data = llm_modified_code_store[module_id]["modified_code"]
            content_to_insert = llm_mod_data.get("html", "")
            if llm_mod_data.get("css"):
                all_modified_css.append(f"/* CSS for module: {module_id} (LLM) */\n{llm_mod_data['css']}")
            if llm_mod_data.get("js"):
                all_modified_js.append(f"/* JS for module: {module_id} (LLM) */\n{llm_mod_data['js']}")
            source = "llm_edit"
        else:
            content_to_insert = module_def.get("original_content", f"")
            source = "original"
        
        if placeholder in final_html:
            final_html = final_html.replace(placeholder, content_to_insert, 1)
            logging.debug(f"Integrated module '{module_id}' (source: {source}) into final HTML.")
        else:
            logging.warning(f"Placeholder for module '{module_id}' not found in skeleton during integration.")

    # Add aggregated CSS to <head>
    if all_modified_css:
        css_block = "\n<style type=\"text/css\">\n" + "\n\n".join(all_modified_css) + "\n</style>\n"
        if "</head>" in final_html:
            final_html = final_html.replace("</head>", css_block + "</head>", 1)
        else: # Fallback if no </head> tag
            final_html = css_block + final_html
        logging.info("Aggregated LLM CSS added to final HTML.")

    # Add aggregated JS before </body>
    if all_modified_js:
        # Proper CDATA wrapping for inline scripts if they might contain <, >, &
        js_content_processed = "\n\n".join(all_modified_js)
        # Basic check if CDATA is already likely present for the whole block
        if not (js_content_processed.strip().startswith("//<![CDATA[") and js_content_processed.strip().endswith("//]]>")):
             js_content_processed = f"//<![CDATA[\n{js_content_processed}\n//]]>"

        js_block = f"\n<script type=\"text/javascript\">\n{js_content_processed}\n</script>\n"
        if "</body>" in final_html:
            final_html = final_html.replace("</body>", js_block + "</body>", 1)
        else: # Fallback if no </body> tag
            final_html += js_block
        logging.info("Aggregated LLM JS added to final HTML.")
        
    return final_html

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # --- Test add_markers_to_html and extract_module_content_by_markers ---
    test_html = "<header><h1>Title</h1></header><main><p>Content</p></main><footer>End</footer>"
    test_defs = [
        {"id": "header", "description": "Header section", "start_char": 0, "end_char": 30, 
         "start_comment": "LLM_MODULE_START: header", "end_comment": "LLM_MODULE_END: header"},
        {"id": "main_content", "description": "Main area", "start_char": 30, "end_char": 54,
         "start_comment": "LLM_MODULE_START: main_content", "end_comment": "LLM_MODULE_END: main_content"}
    ]
    html_with_markers = add_markers_to_html(test_html, test_defs)
    print("\n--- HTML with Markers ---")
    print(html_with_markers)

    if html_with_markers:
        print("\n--- Extracted Content (header) ---")
        header_content = extract_module_content_by_markers(html_with_markers, test_defs[0])
        print(header_content)
        assert header_content == "<h1>Title</h1>"
        
        print("\n--- Extracted Content (main_content) ---")
        main_content = extract_module_content_by_markers(html_with_markers, test_defs[1])
        print(main_content)
        assert main_content == "<p>Content</p>"

        # --- Test generate_skeleton_with_placeholders ---
        test_module_defs_for_skeleton = [ # Simulate having original_content already if needed by caller
            {**test_defs[0], "original_content": header_content},
            {**test_defs[1], "original_content": main_content}
        ]
        skeleton = generate_skeleton_with_placeholders(html_with_markers, test_module_defs_for_skeleton)
        print("\n--- Generated Skeleton ---")
        print(skeleton)
        assert "" in skeleton
        assert "" in skeleton
        assert "<h1>Title</h1>" not in skeleton

        # --- Test integrate_final_code ---
        user_edits = {"header": {"html": "<h1>New User Header</h1>"}}
        llm_mods = {
            "main_content": {
                "modified_code": {
                    "html": "<p>LLM Modified Content</p>", 
                    "css": ".llm-class { color: blue; }", 
                    "js": "console.log('LLM JS');"
                },
                "modification_manual": "..."
            }
        }
        final_integrated_html = integrate_final_code(skeleton, test_module_defs_for_skeleton, user_edits, llm_mods, test_html)
        print("\n--- Final Integrated HTML ---")
        print(final_integrated_html)
        assert "<h1>New User Header</h1>" in final_integrated_html
        assert "<p>LLM Modified Content</p>" in final_integrated_html
        assert ".llm-class { color: blue; }" in final_integrated_html
        assert "console.log('LLM JS');" in final_integrated_html

    print("\nHTML Utils Tests Completed.")