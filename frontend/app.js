/* ============================================================
   Teacher Grading Agent – Frontend Application Logic
   ============================================================ */

const API_BASE = window.location.origin; // same-origin when served by FastAPI

// ---- State ----
const state = {
  history: [],          // OpenAI conversation history
  uploadedFiles: [],    // { fileId, filename, filePath }
  config: {
    apiKey: '',
    model: 'gpt-4o',
    rubric: '',
  },
};

// ---- DOM refs ----
const $chatMessages  = document.getElementById('chatMessages');
const $userInput     = document.getElementById('userInput');
const $sendBtn       = document.getElementById('sendBtn');
const $dropZone      = document.getElementById('dropZone');
const $fileInput     = document.getElementById('fileInput');
const $fileList      = document.getElementById('fileList');
const $pdfSelect     = document.getElementById('pdfSelect');
const $convertBtn    = document.getElementById('convertBtn');
const $convStatus    = document.getElementById('conversionStatus');
const $apiKey        = document.getElementById('apiKey');
const $modelSelect   = document.getElementById('modelSelect');
const $rubric        = document.getElementById('rubric');
const $saveConfig    = document.getElementById('saveConfig');

// ---- Config ----
function loadConfig() {
  const saved = localStorage.getItem('teacherAgentConfig');
  if (saved) {
    try {
      Object.assign(state.config, JSON.parse(saved));
      $apiKey.value       = state.config.apiKey   || '';
      $modelSelect.value  = state.config.model    || 'gpt-4o';
      $rubric.value       = state.config.rubric   || '';
    } catch (_) { /* ignore */ }
  }
}

$saveConfig.addEventListener('click', () => {
  state.config.apiKey  = $apiKey.value.trim();
  state.config.model   = $modelSelect.value;
  state.config.rubric  = $rubric.value.trim();
  localStorage.setItem('teacherAgentConfig', JSON.stringify(state.config));
  showStatus($convStatus, '✓ 已保存', 'ok');
  setTimeout(() => showStatus($convStatus, ''), 2000);
});

// ---- Utility ----
function showStatus(el, msg, cls = '') {
  el.textContent     = msg;
  el.className       = 'status-msg ' + cls;
}

function scrollToBottom() {
  $chatMessages.scrollTop = $chatMessages.scrollHeight;
}

// ---- Chat rendering ----
function appendMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  wrapper.appendChild(bubble);
  $chatMessages.appendChild(wrapper);
  scrollToBottom();
  return bubble;
}

function showTyping() {
  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant typing';
  wrapper.id = 'typingIndicator';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';

  wrapper.appendChild(bubble);
  $chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

// ---- Send message ----
async function sendMessage() {
  const text = $userInput.value.trim();
  if (!text) return;

  $userInput.value = '';
  $sendBtn.disabled = true;

  appendMessage('user', text);
  showTyping();

  // Prepend rubric context if configured and this is the first turn
  let message = text;
  if (state.config.rubric && state.history.length === 0) {
    message = `[评分标准 / Grading Rubric]\n${state.config.rubric}\n\n${text}`;
  }

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history: state.history }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }

    const data = await res.json();
    state.history = data.history;

    removeTyping();
    appendMessage('assistant', data.reply);
  } catch (err) {
    removeTyping();
    appendMessage('assistant', `⚠️ Error: ${err.message}`);
  } finally {
    $sendBtn.disabled = false;
    $userInput.focus();
  }
}

$sendBtn.addEventListener('click', sendMessage);
$userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ---- File upload ----
function updatePdfSelect() {
  $pdfSelect.innerHTML = '<option value="">-- 选择已上传文件 --</option>';
  state.uploadedFiles.forEach(f => {
    if (f.filename.toLowerCase().endsWith('.pdf')) {
      const opt = document.createElement('option');
      opt.value       = f.fileId;
      opt.textContent = f.filename;
      $pdfSelect.appendChild(opt);
    }
  });
}

async function uploadFile(file) {
  const li = document.createElement('li');
  const nameSpan = document.createElement('span');
  nameSpan.textContent = file.name;
  const tag = document.createElement('span');
  tag.className = 'tag';
  tag.textContent = '上传中…';
  li.appendChild(nameSpan);
  li.appendChild(tag);
  li.className = 'converting';
  $fileList.appendChild(li);

  const form = new FormData();
  form.append('file', file);

  try {
    const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();

    state.uploadedFiles.push({ fileId: data.file_id, filename: data.filename, filePath: data.file_path });
    tag.textContent  = '✓';
    li.className     = 'done';
    updatePdfSelect();
  } catch (err) {
    tag.textContent = '✗';
    li.className    = 'error';
    console.error('Upload failed:', err);
  }
}

$dropZone.addEventListener('click', () => $fileInput.click());
$fileInput.addEventListener('change', () => {
  [...$fileInput.files].forEach(uploadFile);
  $fileInput.value = '';
});

$dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  $dropZone.classList.add('drag-over');
});
$dropZone.addEventListener('dragleave', () => $dropZone.classList.remove('drag-over'));
$dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  $dropZone.classList.remove('drag-over');
  [...e.dataTransfer.files].forEach(uploadFile);
});

// ---- PDF → Markdown ----
$convertBtn.addEventListener('click', async () => {
  const fileId = $pdfSelect.value;
  if (!fileId) {
    showStatus($convStatus, '请先选择一个 PDF 文件', 'err');
    return;
  }

  $convertBtn.disabled = true;
  showStatus($convStatus, '转换中…');

  try {
    const res = await fetch(`${API_BASE}/api/pdf-to-md`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: fileId }),
    });
    const data = await res.json();

    if (!data.success) throw new Error(data.error || 'Conversion failed');

    showStatus($convStatus, `✓ 转换成功，共 ${data.pages} 页`, 'ok');

    // Insert the markdown into the chat so the agent can see it
    const filename = state.uploadedFiles.find(f => f.fileId === fileId)?.filename || 'document';
    const preview  = data.markdown.slice(0, 300) + (data.markdown.length > 300 ? '…' : '');
    appendMessage('assistant',
      `📄 **${filename}** 已转换为 Markdown（${data.pages} 页）。\n\n前 300 字符预览：\n${preview}`
    );

    // Auto-send the full markdown to the agent for analysis
    const autoMsg = `以下是学生作业 "${filename}" 的内容（Markdown 格式）：\n\n${data.markdown}\n\n请根据上述评分标准对这份作业进行评分和反馈。`;
    $userInput.value = autoMsg;
  } catch (err) {
    showStatus($convStatus, `✗ ${err.message}`, 'err');
  } finally {
    $convertBtn.disabled = false;
  }
});

// ---- Init ----
loadConfig();
