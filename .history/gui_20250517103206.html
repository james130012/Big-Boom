<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码智能装配流水线</title>
    <script src="[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)"></script>
    <link href="[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap)" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6; /* Light gray background */
            margin: 0;
        }
        .resizable-textarea {
            resize: vertical;
            min-height: 150px;
        }
        .module-display, .prompt-display, .modification-display {
            border: 1px solid #d1d5db; /* Tailwind gray-300 */
            background-color: #f9fafb; /* Tailwind gray-50 */
            padding: 8px;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 200px;
            overflow-y: auto;
        }
        .modification-input { /* This class was defined but not used, kept for potential future use */
            border: 1px solid #9ca3af; /* Tailwind gray-400 */
            padding: 8px;
            border-radius: 4px;
            font-family: monospace;
            width: 100%;
            min-height: 80px;
        }
        .section-title {
            font-size: 1.25rem; /* text-xl */
            font-weight: 600; /* font-semibold */
            color: #1f2937; /* Tailwind gray-800 */
            margin-bottom: 0.75rem; /* mb-3 */
            padding-bottom: 0.5rem; /* pb-2 */
            border-bottom: 2px solid #3b82f6; /* Tailwind blue-500 */
        }
        .btn {
            padding: 0.6rem 1.2rem;
            border-radius: 0.375rem; /* rounded-md */
            font-weight: 500; /* font-medium */
            transition: background-color 0.2s;
            cursor: pointer;
        }
        .btn-primary {
            background-color: #3b82f6; /* Tailwind blue-500 */
            color: white;
        }
        .btn-primary:hover {
            background-color: #2563eb; /* Tailwind blue-600 */
        }
        .info-text {
            font-size: 0.875rem; /* text-sm */
            color: #4b5563; /* Tailwind gray-600 */
        }
        .main-content-wrapper {
            max-width: 80rem; /* Tailwind max-w-screen-xl approx */
            margin-left: auto;
            margin-right: auto;
            background-color: white;
            padding: 1.5rem 2rem; /* p-6 md:p-8 */
            border-radius: 0.75rem; /* rounded-xl */
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04); /* Tailwind shadow-2xl */
            margin-top: 1rem; /* mt-4 */
            margin-bottom: 1rem; /* mb-4 */
        }
    </style>
</head>
<body>
    <div class="main-content-wrapper">
        <header class="mb-8 text-center">
            <h1 class="text-3xl md:text-4xl font-bold text-gray-800">代码智能装配流水线 (LLM集成)</h1>
            <p class="text-gray-600 mt-2">通过LLM分析HTML，进行模块化修改与智能整合。</p>
        </header>

        <section class="mb-6">
            <h3 class="text-lg font-medium text-gray-700 mb-2">LLM提示词模板预览：</h3>
            <div id="promptTemplateDisplay" class="prompt-display bg-blue-50 border-blue-200">
                正在加载提示词模板...
            </div>
        </section>

        <section class="mb-8">
            <h2 class="section-title">① 原始HTML代码输入</h2>
            <textarea id="originalCodeInput" class="w-full p-3 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resizable-textarea" rows="12" placeholder="在此粘贴你的HTML原始代码..."></textarea>
            <h3 class="text-md font-medium text-gray-700 mt-4 mb-2">修改指令 (可选)</h3>
            <textarea id="instructionInput" class="w-full p-3 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resizable-textarea" rows="4" placeholder="请输入修改指令，例如：将动画1替换为旋转立方体，点击改变颜色（蓝→红→绿）。如果留空，则仅进行模块识别和骨架生成。"></textarea>
            <button id="analyzeBtn" class="btn btn-primary mt-3">② LLM分析与修改 (调用Python)</button>
            <p id="llmStatus" class="mt-2 info-text"></p>
        </section>

        <section id="modulesArea" class="mb-8 hidden">
            <h2 class="section-title">③④⑤ 模块展示与修改结果</h2>
            <p class="mb-3 info-text">以下是识别出的模块列表。如果提供了修改指令，相关的修改结果也会在此显示。</p>
            <div id="moduleList" class="mb-4">
                <h4 class="text-md font-medium text-gray-800 mb-2">模块列表</h4>
                <ul id="moduleListItems" class="list-disc pl-5 text-gray-700"></ul>
            </div>
            <div id="modificationResult" class="hidden"> <h4 class="text-md font-medium text-gray-800 mb-2">修改结果 (基于指令)</h4>
                <div class="font-semibold text-gray-700 mt-3 mb-1">修改后的HTML预览:</div>
                <div class="module-display modification-display mb-2" id="modifiedHtmlDisplay">修改后的HTML将显示在此...</div>
                <div class="font-semibold text-gray-700 mt-3 mb-1">修改说明书:</div>
                <div class="module-display modification-display" id="modificationManualDisplay">修改说明书将显示在此...</div>
            </div>
        </section>

        <section id="integrationArea" class="mb-8 hidden">
            <h2 class="section-title">⑥ 整合预览大窗口</h2>
            <button id="integrateBtn" class="btn btn-primary mb-3">整合所有模块 (调用Python)</button>
            <textarea id="integratedCodeOutput" class="w-full p-3 border border-gray-300 rounded-md shadow-sm bg-gray-50 resizable-textarea" rows="18" readonly placeholder="整合后的HTML代码将在此显示..."></textarea>
        </section>
    </div>

    <script>
        let activeModuleDefinitions = [];
        let htmlSkeleton = '';
        // These are populated by analyze_html response if an instruction was given
        let modifiedCodeFromInstruction = {}; 
        let modificationManualFromInstruction = '';

        const originalCodeInput = document.getElementById('originalCodeInput');
        const instructionInput = document.getElementById('instructionInput');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const llmStatus = document.getElementById('llmStatus');
        const modulesArea = document.getElementById('modulesArea');
        const moduleListItems = document.getElementById('moduleListItems');
        const modificationResult = document.getElementById('modificationResult'); // The container div
        const modifiedHtmlDisplay = document.getElementById('modifiedHtmlDisplay');
        const modificationManualDisplay = document.getElementById('modificationManualDisplay');
        const integrationArea = document.getElementById('integrationArea');
        const integrateBtn = document.getElementById('integrateBtn');
        const integratedCodeOutput = document.getElementById('integratedCodeOutput');
        const promptTemplateDisplay = document.getElementById('promptTemplateDisplay');

        async function loadPromptTemplate() {
            try {
                if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_prompt_template_for_frontend === 'function') {
                    const template = await window.pywebview.api.get_prompt_template_for_frontend();
                    promptTemplateDisplay.textContent = template || "提示词模板为空。";
                } else {
                    promptTemplateDisplay.textContent = "PyWebview 未加载或API不可用。请检查后端是否正确启动。\n\n示例结构：\n你是一个专业的Web前端开发助手...\n...";
                }
            } catch (error) {
                console.error("Error loading prompt template:", error);
                promptTemplateDisplay.textContent = "加载提示词模板时出错：" + error.message;
            }
        }

        window.addEventListener('pywebviewready', loadPromptTemplate);
        // Also call it on DOMContentLoaded as a fallback, in case pywebviewready fires too early or too late for some setups.
        window.addEventListener('DOMContentLoaded', () => {
            // If pywebview is already available, loadPromptTemplate might run.
            // If not, pywebviewready listener should catch it.
            // A small delay might help ensure API is injected if DOMContentLoaded fires before pywebviewready.
            setTimeout(loadPromptTemplate, 100); 
        });


        async function waitForPywebviewApi(maxAttempts = 10, delay = 500) { // Reduced delay
            for (let i = 0; i < maxAttempts; i++) {
                if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.analyze_html === 'function') {
                    console.log("PyWebview API is ready.");
                    return true;
                }
                console.log(`Waiting for PyWebview API... Attempt ${i + 1}/${maxAttempts}`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
            console.error("PyWebview API not available after maximum attempts.");
            return false;
        }

        analyzeBtn.addEventListener('click', async () => {
            const originalHtml = originalCodeInput.value;
            const instruction = instructionInput.value.trim(); // Trim instruction

            if (!originalHtml.trim()) {
                llmStatus.textContent = '错误：请输入原始HTML代码。';
                llmStatus.className = 'mt-2 text-sm text-red-600';
                return;
            }

            llmStatus.textContent = 'Python后端正在分析中 (LLM调用可能需要一些时间)...';
            llmStatus.className = 'mt-2 info-text text-blue-600';
            analyzeBtn.disabled = true;
            
            // Reset UI elements
            modulesArea.classList.add('hidden');
            integrationArea.classList.add('hidden');
            modificationResult.classList.add('hidden'); // Hide modification section initially
            moduleListItems.innerHTML = '';
            modifiedHtmlDisplay.textContent = '修改后的HTML将显示在此...';
            modificationManualDisplay.textContent = '修改说明书将显示在此...';
            integratedCodeOutput.value = '';


            const apiReady = await waitForPywebviewApi();
            if (!apiReady) {
                llmStatus.textContent = '错误：无法连接到后端 PyWebview API。请确保Python应用正在运行。';
                llmStatus.className = 'mt-2 text-sm text-red-600';
                analyzeBtn.disabled = false;
                return;
            }

            try {
                const response = await window.pywebview.api.analyze_html(originalHtml, instruction);
                console.log("Response from Python analyze_html:", response);

                if (response && response.status === "success") {
                    activeModuleDefinitions = response.active_module_definitions || [];
                    htmlSkeleton = response.html_skeleton || '';
                    // These are from the specific instruction processing
                    modifiedCodeFromInstruction = response.modified_code || {}; 
                    modificationManualFromInstruction = response.modification_manual || '';

                    llmStatus.textContent = response.message || '分析完成。';
                    llmStatus.className = 'mt-2 info-text text-green-600';

                    if (activeModuleDefinitions.length === 0) {
                        llmStatus.textContent += ' 未能识别出可处理的模块。';
                        llmStatus.className = 'mt-2 info-text text-yellow-600';
                        // Keep modulesArea hidden if no modules
                    } else {
                        renderModuleList();
                        modulesArea.classList.remove('hidden');
                        integrationArea.classList.remove('hidden'); // Show integration area if modules exist
                        
                        // **Enhanced logic for displaying modification results**
                        if (instruction !== "") { // If an instruction was provided
                            modifiedHtmlDisplay.textContent = modifiedCodeFromInstruction.html || "没有生成修改后的HTML (No modified HTML was generated for this instruction).";
                            modificationManualDisplay.textContent = modificationManualFromInstruction || "没有可用的修改说明 (No modification manual provided for this instruction).";
                            modificationResult.classList.remove('hidden'); // Show the modification section
                        } else {
                            modificationResult.classList.add('hidden'); // Ensure it's hidden if no instruction
                        }
                    }
                } else {
                    llmStatus.textContent = 'Python分析出错: ' + (response ? response.message : "未知错误从后端返回 (Unknown error returned from backend)");
                    llmStatus.className = 'mt-2 text-sm text-red-600';
                }
            } catch (error) {
                console.error("Error calling Python API (analyze_html):", error);
                llmStatus.textContent = '调用Python API (analyze_html) 时发生JavaScript错误：' + error.message;
                llmStatus.className = 'mt-2 text-sm text-red-600';
            } finally {
                analyzeBtn.disabled = false;
            }
        });

        function renderModuleList() {
            moduleListItems.innerHTML = ''; // Clear previous items
            if (activeModuleDefinitions.length === 0) {
                const li = document.createElement('li');
                li.textContent = "没有识别到模块 (No modules identified).";
                moduleListItems.appendChild(li);
                return;
            }
            activeModuleDefinitions.forEach((moduleDef, index) => {
                const li = document.createElement('li');
                // Displaying module ID and description. Original content is available in moduleDef.original_content
                li.innerHTML = `<span class="font-medium">模块 ${index + 1}: ${escapeHtml(moduleDef.id)}</span> - ${escapeHtml(moduleDef.description)}`;
                moduleListItems.appendChild(li);
            });
        }

        function escapeHtml(unsafe) {
            if (typeof unsafe !== 'string') return String(unsafe); // Ensure it's a string
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        integrateBtn.addEventListener('click', async () => {
            if (!htmlSkeleton) {
                integratedCodeOutput.value = "错误：HTML骨架未生成。请先成功进行LLM分析。";
                return;
            }
            integrateBtn.disabled = true;
            integratedCodeOutput.value = "正在整合模块 (Integrating modules)...";

            try {
                // integrate_modules in Python now uses its internal state (self.html_skeleton, self.module_definitions, self.modified_modules)
                const finalHtml = await window.pywebview.api.integrate_modules();
                console.log("Response from Python integrate_modules (final HTML):", finalHtml);

                if (finalHtml) { // Expecting the HTML string directly
                    integratedCodeOutput.value = finalHtml;
                } else {
                    integratedCodeOutput.value = "Python整合出错: 后端未能返回整合后的HTML (Backend did not return integrated HTML).";
                }
            } catch (error) {
                console.error("Error calling Python API (integrate_modules):", error);
                integratedCodeOutput.value = '调用Python API进行整合时发生JavaScript错误：' + error.message;
            } finally {
                integrateBtn.disabled = false;
            }
        });

        // Default HTML for quick testing
        originalCodeInput.value = `<!DOCTYPE html>
<html>
<head><title>示例页面</title>
<style> 
body {font-family: sans-serif; margin: 20px; background-color: #f0f0f0;} 
header, footer {padding: 1em; background-color: #e0e0e0; text-align: center; border-radius: 8px; margin-bottom:15px;} 
nav { background-color: #d0d0d0; padding: 0.5em; border-radius: 8px; margin-bottom:15px; text-align: center;}
nav ul {list-style: none; padding:0; margin:0;} 
nav li {display: inline; margin: 0 15px;} 
nav a {text-decoration: none; color: #333;}
.main-area { padding: 15px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
.animation-container { margin-bottom: 20px; padding:10px; border:1px dashed #ccc; border-radius: 4px;}
h3 {margin-top:0;}
.animation-box {width: 90%; min-height: 150px; border: 1px solid #ccc; background-color:#e9e9e9; margin-top:10px; margin-bottom:10px; display:flex; align-items:center; justify-content:center; border-radius: 4px;} 
</style>
</head>
<body>
    <header><h1>网站Logo和主要标题</h1></header>
    <nav><ul><li><a href="#">首页</a></li><li><a href="#">产品介绍</a></li><li><a href="#">联系方式</a></li></ul></nav>
    <div class="main-area">
        <div class="animation-container" id="anim-container-1">
            <h3>动画模块 1</h3>
            <div class="animation-box" id="anim1-box">
                <p>这是动画1的占位内容。</p>
            </div>
            <button onclick="playAnim1()">播放动画1</button>
            <p>关于动画1的简短描述。</p>
        </div>
        <div class="animation-container" id="anim-container-2">
            <h3>文本模块</h3>
            <p id="text-block-1">这是一段重要的介绍性文本，可以被LLM识别和修改。</p>
            <p>更多内容...</p>
        </div>
    </div>
    <div style="clear:both;"></div>
    <footer><p>版权所有 &copy; 2025 MyCompany</p></footer>
<script>
function playAnim1() { 
    const box = document.getElementById('anim1-box');
    box.innerHTML = "<p>动画1正在播放！ (模拟)</p>";
    console.log("playAnim1 called"); 
}
// 更多脚本可以放在这里
</script>
</body>
</html>`;
    </script>
</body>
</html>