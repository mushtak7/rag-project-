/* ══════════════════════════════════════════════════════════════
   DocIntel — Main Application Script
   ══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    // ── DOM References ────────────────────────────────────────
    const authOverlay     = document.getElementById('authOverlay');
    const appContainer    = document.getElementById('appContainer');
    const loginForm       = document.getElementById('loginForm');
    const registerForm    = document.getElementById('registerForm');
    const showRegister    = document.getElementById('showRegister');
    const showLogin       = document.getElementById('showLogin');
    const loginError      = document.getElementById('loginError');
    const regError        = document.getElementById('regError');
    const userEmailEl     = document.getElementById('userEmail');
    const logoutBtn       = document.getElementById('logoutBtn');

    const uploadZone      = document.getElementById('uploadZone');
    const fileInput       = document.getElementById('fileInput');
    const uploadStatus    = document.getElementById('uploadStatus');
    const docList         = document.getElementById('docList');

    const chatForm        = document.getElementById('chatForm');
    const chatInput       = document.getElementById('chatInput');
    const sendBtn         = document.getElementById('sendBtn');
    const chatHistory     = document.getElementById('chatHistory');
    const clearChatBtn    = document.getElementById('clearChatBtn');

    const pdfPanel        = document.getElementById('pdfPanel');
    const closePdfPanel   = document.getElementById('closePdfPanel');
    const pdfViewerTitle  = document.getElementById('pdfViewerTitle');

    // Mobile navigation references
    const menuToggleBtn   = document.getElementById('menuToggleBtn');
    const sidebar         = document.querySelector('.sidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    let token = localStorage.getItem('docintel_token');
    let userEmail = localStorage.getItem('docintel_email');
    let hasDocuments = false;

    // ── Auth-aware fetch wrapper ─────────────────────────────
    async function authFetch(url, options = {}) {
        if (!options.headers) options.headers = {};
        if (token) options.headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(url, options);
        if (res.status === 401) {
            // Token is invalid or expired — force re-login
            localStorage.removeItem('docintel_token');
            localStorage.removeItem('docintel_email');
            token = null;
            userEmail = null;
            authOverlay.classList.remove('hidden');
            appContainer.classList.add('hidden');
            loginError.textContent = 'Session expired. Please sign in again.';
            loginError.classList.remove('hidden');
            throw new Error('Session expired');
        }
        return res;
    }

    // ── Init ──────────────────────────────────────────────────
    if (token && userEmail) {
        showApp();
    }

    // ══════════════════════════════════════════════════════════
    // AUTH
    // ══════════════════════════════════════════════════════════

    showRegister.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.classList.remove('active');
        registerForm.classList.add('active');
        loginError.classList.add('hidden');
    });

    showLogin.addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.classList.remove('active');
        loginForm.classList.add('active');
        regError.classList.add('hidden');
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginError.classList.add('hidden');
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        const btn = document.getElementById('loginBtn');
        btn.disabled = true;
        btn.textContent = 'Signing in...';

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Login failed');

            token = data.token;
            userEmail = data.email;
            localStorage.setItem('docintel_token', token);
            localStorage.setItem('docintel_email', userEmail);
            showApp();
        } catch (err) {
            loginError.textContent = err.message;
            loginError.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        regError.classList.add('hidden');
        const email = document.getElementById('regEmail').value;
        const password = document.getElementById('regPassword').value;
        const btn = document.getElementById('regBtn');
        btn.disabled = true;
        btn.textContent = 'Creating...';

        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Registration failed');

            token = data.token;
            userEmail = data.email;
            localStorage.setItem('docintel_token', token);
            localStorage.setItem('docintel_email', userEmail);
            showApp();
        } catch (err) {
            regError.textContent = err.message;
            regError.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }
    });

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('docintel_token');
        localStorage.removeItem('docintel_email');
        token = null;
        userEmail = null;
        location.reload();
    });

    function showApp() {
        authOverlay.classList.add('hidden');
        appContainer.classList.remove('hidden');
        userEmailEl.textContent = userEmail;
        loadDocuments();
    }

    // ── Mobile Sidebar Menu Toggle ───────────────────────────
    if (menuToggleBtn && sidebar && sidebarBackdrop) {
        const closeSidebar = () => {
            sidebar.classList.remove('open');
            sidebarBackdrop.classList.remove('active');
        };

        menuToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.add('open');
            sidebarBackdrop.classList.add('active');
        });

        sidebarBackdrop.addEventListener('click', closeSidebar);

        // Click-away listener: close sidebar when clicking outside of it
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('open') && 
                !sidebar.contains(e.target) && 
                !menuToggleBtn.contains(e.target)) {
                closeSidebar();
            }
        });

        // Expose globally so that we can call it on click events or other events if needed
        window.closeDocIntelSidebar = closeSidebar;
    }

    // ══════════════════════════════════════════════════════════
    // FILE UPLOAD (Multi-PDF)
    // ══════════════════════════════════════════════════════════

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleUpload(e.target.files);
    });

    async function handleUpload(files) {
        const pdfFiles = Array.from(files).filter(f => f.type === 'application/pdf');
        if (pdfFiles.length === 0) {
            showStatus('Only PDF files are accepted.', 'error');
            return;
        }

        const formData = new FormData();
        pdfFiles.forEach(f => formData.append('files', f));

        showStatus(`<span class="spinner"></span> Processing ${pdfFiles.length} file(s)...`, 'loading');

        try {
            const res = await authFetch('/api/upload', {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Upload failed');

            showStatus(`✓ ${escapeHTML(data.message)}`, 'success');
            enableChat();
            loadDocuments();
            addMessage('system', `Documents indexed! ${data.details.total_chunks} chunks created across ${pdfFiles.length} file(s). You can now ask questions.`);
        } catch (err) {
            showStatus(err.message, 'error');
        }

        fileInput.value = '';
    }

    function showStatus(html, type) {
        uploadStatus.innerHTML = html;
        uploadStatus.className = `status-msg ${type}`;
        uploadStatus.classList.remove('hidden');
        if (type !== 'loading') {
            setTimeout(() => uploadStatus.classList.add('hidden'), 5000);
        }
    }

    async function loadDocuments() {
        try {
            const res = await authFetch('/api/documents');
            const data = await res.json();
            if (data.documents && data.documents.length > 0) {
                hasDocuments = true;
                enableChat();
                docList.innerHTML = '';
                data.documents.forEach(name => {
                    const li = document.createElement('li');

                    const docInfo = document.createElement('div');
                    docInfo.className = 'doc-info';
                    docInfo.innerHTML = `<svg class="doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg><span>${escapeHTML(name)}</span>`;
                    docInfo.addEventListener('click', () => {
                        if (window.DocIntelPDF) window.DocIntelPDF.loadPdf(name, token);
                        if (window.closeDocIntelSidebar) window.closeDocIntelSidebar();
                    });

                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'doc-delete-btn';
                    deleteBtn.title = 'Remove document';
                    deleteBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
                    deleteBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        deleteDocument(name, li);
                    });

                    li.appendChild(docInfo);
                    li.appendChild(deleteBtn);
                    docList.appendChild(li);
                });
            } else {
                hasDocuments = false;
                docList.innerHTML = '<li class="doc-empty">No documents uploaded yet</li>';
                chatInput.disabled = true;
                sendBtn.disabled = true;
                chatInput.placeholder = 'Upload a document first...';
            }
        } catch (err) {
            console.error('Failed to load documents:', err);
        }
    }

    async function deleteDocument(filename, liElement) {
        if (!confirm(`Delete "${filename}"?\n\nThis will remove the document and re-index your remaining files.`)) {
            return;
        }

        // Show deleting state
        liElement.classList.add('deleting');

        try {
            const res = await authFetch(`/api/documents/delete?filename=${encodeURIComponent(filename)}`, {
                method: 'DELETE',
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Delete failed');

            addMessage('system', `Document "${filename}" has been removed.`);
            loadDocuments();
        } catch (err) {
            liElement.classList.remove('deleting');
            addMessage('system', `Error deleting document: ${err.message}`);
        }
    }

    function enableChat() {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.placeholder = 'Ask about your documents...';
    }

    // ══════════════════════════════════════════════════════════
    // CHAT (Memory-Aware)
    // ══════════════════════════════════════════════════════════

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;

        addMessage('user', message);
        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;

        const typing = showTyping();

        try {
            const res = await authFetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message }),
            });
            const data = await res.json();
            typing.remove();
            if (!res.ok) throw new Error(data.detail || 'Chat error');

            addMessage('assistant', data.answer, data.sources);
        } catch (err) {
            typing.remove();
            addMessage('system', `Error: ${err.message}`);
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });

    clearChatBtn.addEventListener('click', async () => {
        if (window.closeDocIntelSidebar) window.closeDocIntelSidebar();
        try {
            await authFetch('/api/chat/clear', {
                method: 'DELETE',
            });
            chatHistory.innerHTML = '';
            addMessage('system', 'Chat history cleared. Conversation memory has been reset.');
        } catch (err) {
            console.error('Failed to clear chat:', err);
        }
    });

    // ── Message Rendering ────────────────────────────────────

    function addMessage(role, content, sources = []) {
        const div = document.createElement('div');
        div.className = `message ${role}`;

        const avatarSvg = role === 'user'
            ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
            : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg>';

        const avatarClass = role === 'assistant' ? 'avatar' : role === 'system' ? 'avatar system-avatar' : 'avatar';

        let contentHTML = escapeHTML(content);

        // Source Attribution with Pills
        if (sources && sources.length > 0) {
            // Get unique filenames
            const uniqueFiles = [...new Set(sources.map(s => s.filename))];

            let pillsHTML = '<div class="source-pills">';
            uniqueFiles.forEach(fname => {
                pillsHTML += `<span class="source-pill" data-filename="${escapeHTML(fname)}" data-text="${escapeHTML(sources.find(s => s.filename === fname).text.substring(0, 100))}">${escapeHTML(fname)}</span>`;
            });
            pillsHTML += '</div>';

            const chunksId = 'chunks_' + Date.now();
            let chunksHTML = '<div class="source-chunks hidden" id="' + chunksId + '">';
            sources.forEach((src, i) => {
                chunksHTML += `<div class="chunk"><div class="chunk-source-label">${escapeHTML(src.filename)}</div>${escapeHTML(src.text)}</div>`;
            });
            chunksHTML += '</div>';

            contentHTML += `
                <div class="source-attribution">
                    ${pillsHTML}
                    <button class="source-toggle-btn" onclick="toggleSources(this)">
                        View source context
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </button>
                    ${chunksHTML}
                </div>`;
        }

        div.innerHTML = `
            <div class="${avatarClass}">${avatarSvg}</div>
            <div class="msg-content">${contentHTML}</div>
        `;

        // Attach pill click events
        div.querySelectorAll('.source-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const filename = pill.dataset.filename;
                const text = pill.dataset.text;
                if (window.DocIntelPDF) {
                    window.DocIntelPDF.loadPdf(filename, token, text);
                }
            });
        });

        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function showTyping() {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="avatar"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg></div>
            <div class="msg-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return div;
    }

    // ── PDF Panel Toggle ─────────────────────────────────────
    closePdfPanel.addEventListener('click', () => {
        pdfPanel.classList.add('hidden');
    });

    // ── Helpers ───────────────────────────────────────────────

    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":"&#39;",'"':'&quot;'}[c] || c));
    }
});

// Global function for inline onclick handlers
function toggleSources(btn) {
    btn.classList.toggle('open');
    const chunks = btn.nextElementSibling;
    if (chunks) chunks.classList.toggle('hidden');
}
