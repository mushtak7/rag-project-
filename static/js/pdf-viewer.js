/* ══════════════════════════════════════════════════════════════
   DocIntel — PDF Viewer with Text Highlighting
   Uses pdf.js from CDN to render PDFs and highlight source text
   ══════════════════════════════════════════════════════════════ */

(function () {
    const pdfPanel = document.getElementById('pdfPanel');
    const pdfViewerTitle = document.getElementById('pdfViewerTitle');
    const pdfCanvasContainer = document.getElementById('pdfCanvasContainer');

    let pdfjsLib = null;
    let currentPdfDoc = null;
    let currentFilename = null;

    // Dynamically load pdf.js library
    async function ensurePdfJs() {
        if (pdfjsLib) return pdfjsLib;

        try {
            pdfjsLib = await import('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs');
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs';
            return pdfjsLib;
        } catch (err) {
            console.error('Failed to load pdf.js:', err);
            return null;
        }
    }

    async function loadPdf(filename, token, highlightText) {
        const lib = await ensurePdfJs();
        if (!lib) {
            pdfCanvasContainer.innerHTML = '<p style="color: var(--text-muted); padding: 2rem;">Failed to load PDF viewer library.</p>';
            pdfPanel.classList.remove('hidden');
            return;
        }

        pdfPanel.classList.remove('hidden');
        pdfViewerTitle.textContent = filename;
        pdfCanvasContainer.innerHTML = '<div style="padding: 2rem; color: var(--text-muted); display:flex; align-items:center; gap:0.5rem;"><span class="spinner"></span> Loading PDF...</div>';

        try {
            // Only reload if different file
            if (currentFilename !== filename) {
                const response = await fetch(`/api/pdf/${encodeURIComponent(filename)}`, {
                    headers: { 'Authorization': `Bearer ${token}` },
                });

                if (!response.ok) throw new Error('Failed to fetch PDF');

                const blob = await response.blob();
                const arrayBuffer = await blob.arrayBuffer();
                const pdf = await lib.getDocument({ data: arrayBuffer }).promise;
                currentPdfDoc = pdf;
                currentFilename = filename;
            }

            await renderAllPages(currentPdfDoc, highlightText);
        } catch (err) {
            console.error('PDF load error:', err);
            const errEl = document.createElement('p');
            errEl.style.cssText = 'color: var(--error); padding: 2rem;';
            errEl.textContent = 'Error loading PDF: ' + err.message;
            pdfCanvasContainer.innerHTML = '';
            pdfCanvasContainer.appendChild(errEl);
        }
    }

    async function renderAllPages(pdfDoc, highlightText) {
        pdfCanvasContainer.innerHTML = '';

        for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
            const page = await pdfDoc.getPage(pageNum);
            const scale = 1.5;
            const viewport = page.getViewport({ scale });

            // Page wrapper
            const pageWrapper = document.createElement('div');
            pageWrapper.style.position = 'relative';
            pageWrapper.style.marginBottom = '0.5rem';

            // Canvas
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            canvas.style.maxWidth = '100%';
            canvas.style.height = 'auto';

            await page.render({ canvasContext: ctx, viewport }).promise;

            pageWrapper.appendChild(canvas);

            // Text layer for highlighting
            if (highlightText) {
                const textContent = await page.getTextContent();
                const pageText = textContent.items.map(item => item.str).join(' ');

                // Normalize for comparison
                const normalizedHighlight = highlightText.replace(/\s+/g, ' ').trim().toLowerCase();
                const normalizedPage = pageText.replace(/\s+/g, ' ').trim().toLowerCase();

                if (normalizedPage.includes(normalizedHighlight.substring(0, 60))) {
                    // Found a match on this page — create highlight overlays
                    const overlayDiv = document.createElement('div');
                    overlayDiv.style.position = 'absolute';
                    overlayDiv.style.top = '0';
                    overlayDiv.style.left = '0';
                    overlayDiv.style.width = '100%';
                    overlayDiv.style.height = '100%';
                    overlayDiv.style.pointerEvents = 'none';

                    // Try to find matching text items and highlight them
                    const highlightWords = normalizedHighlight.substring(0, 40).split(' ').filter(w => w.length > 2);
                    let highlighted = false;

                    textContent.items.forEach(item => {
                        const itemText = item.str.toLowerCase();
                        const isMatch = highlightWords.some(word => itemText.includes(word));

                        if (isMatch && item.transform) {
                            const [a, b, c, d, tx, ty] = item.transform;
                            // Transform PDF coordinates to canvas coordinates
                            const x = (tx * scale) / viewport.width * 100;
                            const y = ((viewport.height / scale - ty) * scale) / viewport.height * 100;
                            const width = (item.width * scale) / viewport.width * 100;
                            const height = (Math.abs(d) * scale) / viewport.height * 100;

                            const rect = document.createElement('div');
                            rect.className = 'pdf-highlight-overlay';
                            rect.style.left = `${x}%`;
                            rect.style.top = `${y - height}%`;
                            rect.style.width = `${Math.max(width, 5)}%`;
                            rect.style.height = `${Math.max(height, 1.5)}%`;
                            overlayDiv.appendChild(rect);
                            highlighted = true;
                        }
                    });

                    if (highlighted) {
                        pageWrapper.appendChild(overlayDiv);
                        // Scroll this page into view
                        setTimeout(() => pageWrapper.scrollIntoView({ behavior: 'smooth', block: 'center' }), 200);
                    }
                }
            }

            pdfCanvasContainer.appendChild(pageWrapper);
        }
    }

    // Expose globally for app.js
    window.DocIntelPDF = { loadPdf };
})();
