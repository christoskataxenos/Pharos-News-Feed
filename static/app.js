document.addEventListener("DOMContentLoaded", () => {
    const articleGrid = document.getElementById("article-grid");
    const categoryList = document.getElementById("category-list");
    const refreshBtn = document.getElementById("refresh-btn");
    const sidebarToggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");
    
    // Modal Elements
    const readerModal = document.getElementById('reader-modal');
    const settingsModal = document.getElementById('settings-modal');
    const langSelect = document.getElementById('lang-select');
    
    let currentCategoryId = null;
    let currentArticleId = null;
    let lastDate = null;
    let isLoading = false;
    let hasMore = true;
    let globalFeeds = [];

    // Initialize language preference
    const savedLang = localStorage.getItem('pharos_lang') || '';
    if(langSelect) langSelect.value = savedLang;

    // Mobile sidebar toggle
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });
        
        document.addEventListener("click", (e) => {
            if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove("open");
            }
        });
    }

    // Reader Logic
    async function openReader(id, url) {
        currentArticleId = id;
        
        // Show the modal immediately so the user knows it opened
        readerModal.classList.remove('hidden');
        document.getElementById('reader-title').textContent = "Opening article...";
        document.getElementById('reader-original-link').href = url;
        
        // Use the existing lighthouse animation inside the reader body!
        document.getElementById('reader-body').innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px;" id="reader-lighthouse-container">
                <!-- Canvas will be moved here -->
                <div style="color: var(--accent); font-family: var(--font-display); font-style: italic; font-size: 18px; margin-top: 15px;">
                    Aligning light beam...
                </div>
            </div>
        `;
        
        // Move the canvas to the reader modal
        const canvas = document.getElementById('lighthouse-canvas');
        if (canvas) {
            const container = document.getElementById('reader-lighthouse-container');
            container.insertBefore(canvas, container.firstChild);
        }
        
        // Initialize the 3D lighthouse
        if (window.initLighthouse) {
            window.initLighthouse();
            if (window.startLighthouseAnimation) {
                window.startLighthouseAnimation(); 
            }
        }

        const lang = langSelect.value;
        let endpoint = `/api/article/${id}/read` + (lang ? `?lang=${lang}` : "");
        
        try {
            const res = await fetch(endpoint);
            const data = await res.json();
            
            if (window.stopLighthouseAnimation) window.stopLighthouseAnimation();
            
            // Move canvas back to its original home just in case
            if (canvas) {
                const originalHome = document.querySelector('.lighthouse-card');
                if (originalHome) originalHome.insertBefore(canvas, originalHome.firstChild);
            }
            
            if(data.error) throw new Error(data.error);

            // Update modal with actual data
            document.getElementById('reader-title').textContent = data.title;
            document.getElementById('reader-body').innerHTML = DOMPurify.sanitize(data.content);
            
            // Mark read via API
            fetch(`/api/mark_read/${id}`, {method: 'POST'}).catch(()=>{});
        } catch (e) {
            if (window.stopLighthouseAnimation) window.stopLighthouseAnimation();
            
            // Move canvas back to its original home just in case
            const canvas = document.getElementById('lighthouse-canvas');
            if (canvas) {
                const originalHome = document.querySelector('.lighthouse-card');
                if (originalHome) originalHome.insertBefore(canvas, originalHome.firstChild);
            }
            
            document.getElementById('reader-title').textContent = "Error";
            document.getElementById('reader-body').innerHTML = `<p style="color:#ef4444">Failed to extract content: ${e.message}</p>`;
        }
    }

    // Settings Logic
    function openSettings() {
        settingsModal.classList.remove('hidden');
        renderManageFeeds();
    }

    function renderManageFeeds() {
        const list = document.getElementById('manage-feeds-list');
        list.innerHTML = '';
        globalFeeds.forEach(cat => {
            cat.feeds.forEach(f => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div>
                        <strong>${f.title}</strong>
                        <div style="font-size: 12px; color: var(--text-muted)">Cat: ${cat.name}</div>
                    </div>
                    <button class="del-feed-btn" onclick="deleteFeed(${f.id})"><i class="ph ph-trash"></i></button>
                `;
                list.appendChild(li);
            });
        });
    }

    window.deleteFeed = async function(id) {
        if(!confirm("Delete this feed and all its articles?")) return;
        await fetch(`/api/feeds/${id}`, { method: 'DELETE' });
        await initApp();
        renderManageFeeds();
    }

    document.getElementById('add-feed-btn').onclick = async () => {
        const url = document.getElementById('new-feed-url').value;
        const title = document.getElementById('new-feed-title').value;
        const catName = document.getElementById('new-feed-category').value;
        if(!url || !title || !catName) return alert("Fill all fields");
        
        const res = await fetch('/api/feeds', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url: url, title: title, category_name: catName})
        });
        if(res.ok) {
            alert("Feed added!");
            await initApp();
            renderManageFeeds();
        }
    };

    // Load initial skeleton
    renderSkeletons(6);
    
    // Fetch initial data
    initApp();

    refreshBtn.addEventListener("click", async () => {
        const icon = refreshBtn.querySelector('i');
        icon.classList.add('ph-spin');
        if (window.showLighthouse) window.showLighthouse();
        
        try {
            const res = await fetch("/api/refresh", { method: 'POST' });
            if(res.ok) {
                setTimeout(async () => {
                    lastDate = null;
                    hasMore = true;
                    await fetchArticles(currentCategoryId, true);
                    icon.classList.remove('ph-spin');
                    if (window.hideLighthouse) window.hideLighthouse();
                }, 2000);
            } else {
                icon.classList.remove('ph-spin');
                if (window.hideLighthouse) window.hideLighthouse();
            }
        } catch(e) {
            console.error(e);
            icon.classList.remove('ph-spin');
            if (window.hideLighthouse) window.hideLighthouse();
        }
    });

    async function initApp() {
        try {
            const res = await fetch("/api/init_data");
            const data = await res.json();
            globalFeeds = data;
            renderCategories(data);
            
            let totalFeeds = 0;
            data.forEach(cat => totalFeeds += cat.feeds.length);
            const statsFeedsEl = document.getElementById("stats-total-feeds");
            if (statsFeedsEl) statsFeedsEl.innerText = totalFeeds;

            fetchArticles(null, true);
        } catch (e) {
            console.error("Failed to init app", e);
        }
    }

    async function fetchArticles(catId = null, reset = false) {
        if (isLoading || (!hasMore && !reset)) return;
        isLoading = true;
        currentCategoryId = catId;
        
        if (reset) {
            lastDate = null;
            hasMore = true;
            renderSkeletons(6);
        } else {
            const loader = document.createElement("div");
            loader.className = "article-card glass-panel skeleton-loader-more";
            loader.innerHTML = `<div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div>`;
            articleGrid.appendChild(loader);
        }

        let url = `/api/articles?`;
        if (lastDate) url += `last_date=${encodeURIComponent(lastDate)}&`;
        if (catId) url += `category_id=${catId}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            
            if (data.articles.length === 0) {
                hasMore = false;
            } else {
                lastDate = data.articles[data.articles.length - 1].raw_published;
            }
            
            renderArticles(data.articles, reset);
            
            const totalArticlesEl = document.getElementById("total-articles-count");
            if (totalArticlesEl && data.total !== undefined) {
                totalArticlesEl.innerText = data.total;
            }
        } catch (e) {
            console.error("Failed to fetch articles", e);
            if (reset) articleGrid.innerHTML = `<p style="text-align:center; color: var(--text-muted); width: 100%;">Failed to load feed. Is the server running?</p>`;
        } finally {
            isLoading = false;
        }
    }

    window.addEventListener("scroll", () => {
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
            fetchArticles(currentCategoryId, false);
        }
    });

    function renderSkeletons(count) {
        articleGrid.innerHTML = "";
        for(let i=0; i<count; i++) {
            const skel = document.createElement("div");
            skel.className = "article-card glass-panel";
            skel.innerHTML = `
                <div class="skeleton skeleton-img"></div>
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text short"></div>
            `;
            articleGrid.appendChild(skel);
        }
    }

    function renderArticles(articles, reset) {
        if (reset) articleGrid.innerHTML = "";
        const loader = document.querySelector(".skeleton-loader-more");
        if (loader) loader.remove();

        if(articles.length === 0 && reset) {
            articleGrid.innerHTML = `<p style="text-align:center; color: var(--text-muted); width: 100%; margin-top:40px;">No articles found. Try syncing!</p>`;
            return;
        }

        articles.forEach((art, index) => {
            const card = document.createElement("div");
            card.className = "article-card glass-panel" + (art.is_read ? " is-read" : "");
            
            const imageHtml = art.image_url 
                ? `<img src="${art.image_url}" alt="Cover" class="article-image" loading="lazy" onerror="this.onerror=null; this.outerHTML='<div class=\\'article-image\\' style=\\'background: linear-gradient(135deg, rgba(10, 25, 40, 0.8), rgba(0, 180, 216, 0.2)); display: flex; align-items:center; justify-content:center;\\'><i class=\\'ph ph-image-broken\\' style=\\'font-size: 48px; color: rgba(255,255,255,0.15);\\'></i></div>';">` 
                : `<div class="article-image" style="background: linear-gradient(135deg, rgba(10, 25, 40, 0.8), rgba(0, 180, 216, 0.2)); display: flex; align-items:center; justify-content:center;"><i class="ph ph-newspaper" style="font-size: 48px; color: rgba(255,255,255,0.15);"></i></div>`;

            card.innerHTML = `
                ${imageHtml}
                <div class="article-content">
                    <span class="feed-tag">${art.feed_title}</span>
                    <h2 class="article-title">${art.title}</h2>
                    <p class="article-summary">${art.summary || ''}</p>
                    <div class="article-meta">
                        <span><i class="ph ph-calendar-blank"></i> ${art.published}</span>
                    </div>
                </div>
            `;
            
            card.addEventListener('click', () => {
                card.classList.add("is-read");
                openReader(art.id, art.link);
            });

            // Εφέ 3D Tilt & Image Parallax
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const xc = rect.width / 2;
                const yc = rect.height / 2;
                
                // Υπολογισμός γωνίας περιστροφής (max 10 μοίρες)
                const angleX = -(yc - y) / 10;
                const angleY = (xc - x) / 10;
                
                card.style.transition = 'transform 0.05s ease-out, border-color 0.3s, box-shadow 0.3s';
                card.style.transform = `perspective(1000px) rotateX(${angleX}deg) rotateY(${angleY}deg) scale3d(1.02, 1.02, 1.02)`;
                
                const img = card.querySelector('.article-image');
                if (img) {
                    img.style.transition = 'transform 0.05s ease-out';
                    // Μετατόπιση εικόνας προς την αντίθετη κατεύθυνση για parallax αίσθηση βάθους
                    const transX = (xc - x) / 15;
                    const transY = (yc - y) / 15;
                    img.style.transform = `translate3d(${transX}px, ${transY}px, 0px) scale(1.15)`;
                }
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transition = 'transform 0.5s cubic-bezier(0.25, 1, 0.5, 1), border-color 0.3s, box-shadow 0.3s';
                card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
                
                const img = card.querySelector('.article-image');
                if (img) {
                    img.style.transition = 'transform 0.5s cubic-bezier(0.25, 1, 0.5, 1)';
                    img.style.transform = 'translate3d(0, 0, 0) scale(1)';
                }
            });

            articleGrid.appendChild(card);
        });
    }

    function renderCategories(categories) {
        categoryList.innerHTML = '';
        const allStreams = document.createElement("li");
        allStreams.className = "category-header active";
        allStreams.setAttribute("data-id", "all");
        allStreams.innerHTML = `<i class="ph ph-squares-four"></i> Open Sea`;
        allStreams.addEventListener('click', () => {
            document.querySelectorAll('.category-header').forEach(el => el.classList.remove('active'));
            allStreams.classList.add('active');
            fetchArticles(null, true);
            if(window.innerWidth <= 900) sidebar.classList.remove("open");
        });
        categoryList.appendChild(allStreams);

        categories.forEach(cat => {
            const li = document.createElement("li");
            li.className = "category-header";
            li.setAttribute("data-id", cat.id);
            li.innerHTML = `<i class="ph ph-hash"></i> ${cat.name}`;
            li.addEventListener('click', () => {
                document.querySelectorAll('.category-header').forEach(el => el.classList.remove('active'));
                li.classList.add('active');
                fetchArticles(cat.id, true);
                if(window.innerWidth <= 900) sidebar.classList.remove("open");
            });
            categoryList.appendChild(li);
        });
    }
    
    // Modal Event Listeners
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.onclick = function() {
            this.closest('.modal-overlay').classList.add('hidden');
        }
    });
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if(e.target === this) this.classList.add('hidden');
        });
    });
    document.getElementById('settings-btn').onclick = openSettings;
    langSelect.onchange = (e) => localStorage.setItem('pharos_lang', e.target.value);
    document.getElementById('translate-btn').onclick = () => {
        const lang = langSelect.value;
        openReader(currentArticleId, document.getElementById('reader-original-link').href);
    };

});

// Add keyframes for staggered entry
const style = document.createElement('style');
style.innerHTML = `
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
`;
document.head.appendChild(style);
