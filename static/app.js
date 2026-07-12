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
    
    // Στοιχεία DOM για την εμφάνιση του τίτλου και υπότιτλου της τρέχουσας ροής ειδήσεων
    const currentViewTitle = document.querySelector(".current-view h1");
    const currentViewSubtitle = document.querySelector(".current-view .subtitle");

    // Συνάρτηση για τη δυναμική αλλαγή του τίτλου και του υπότιτλου στην κορυφή
    function updateHeaderTitle(title, subtitle) {
        if (currentViewTitle) {
            currentViewTitle.textContent = title;
        }
        if (currentViewSubtitle) {
            currentViewSubtitle.textContent = subtitle;
        }
    }

    let currentCategoryId = null;
    let currentArticleId = null;
    let lastDate = null;
    let isLoading = false;
    let hasMore = true;
    let globalFeeds = [];
    let showFiltered = false;

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
            if (!navigator.onLine) {
                throw new Error("Offline");
            }
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
            
            // Offline/Fail Fallback: Try loading from IndexedDB
            const offlineArt = await getArticleFromIndexedDB(id);
            if (offlineArt) {
                document.getElementById('reader-title').textContent = offlineArt.title;
                document.getElementById('reader-body').innerHTML = `
                    <div style="background: rgba(249, 115, 22, 0.1); border: 1px solid rgba(249, 115, 22, 0.2); color: #f97316; padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                        <i class="ph ph-wifi-slash" style="font-size: 20px;"></i>
                        <span>Offline Mode: Εμφάνιση της περίληψης του άρθρου. Συνδεθείτε στο διαδίκτυο για να φορτώσει όλο το κείμενο.</span>
                    </div>
                    <div class="summary-content">
                        ${offlineArt.summary || 'Δεν υπάρχει διαθέσιμη περίληψη.'}
                    </div>
                `;
                // Queue mark read action
                queueOfflineAction("read", id);
                
                // Update local UI state
                const card = document.querySelector(`.article-card[data-article-id="${id}"]`);
                if (card) card.classList.add("is-read");
            } else {
                document.getElementById('reader-title').textContent = "Error";
                document.getElementById('reader-body').innerHTML = `<p style="color:#ef4444">Failed to extract content: ${e.message}</p>`;
            }
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
            let data;
            if (navigator.onLine) {
                const res = await fetch("/api/init_data");
                data = await res.json();
                localStorage.setItem("pharos_categories_cache", JSON.stringify(data));
            } else {
                data = JSON.parse(localStorage.getItem("pharos_categories_cache") || "[]");
            }
            globalFeeds = data;
            renderCategories(data);
            renderOfflineCategoriesOptions(data);
            
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
        if (catId) {
            if (typeof catId === 'string' && catId.includes(',')) {
                url += `category_ids=${catId}&`;
            } else {
                url += `category_id=${catId}&`;
            }
        }
        if (showFiltered) url += `show_filtered=true`;

        try {
            if (!navigator.onLine) {
                throw new Error("Offline");
            }
            const res = await fetch(url);
            const data = await res.json();
            
            if (data.articles.length === 0) {
                hasMore = false;
            } else {
                lastDate = data.articles[data.articles.length - 1].raw_published;
            }
            
            renderArticles(data.articles, reset);

            // Update offline cache for selected categories
            if (reset) {
                cacheTopArticlesOffline();
            }
            
            const totalArticlesEl = document.getElementById("total-articles-count");
            if (totalArticlesEl && data.total !== undefined) {
                totalArticlesEl.innerText = data.total;
            }
        } catch (e) {
            console.error("Failed to fetch articles", e);
            if (reset) {
                const offlineArticles = await getOfflineArticles();
                if (offlineArticles.length > 0) {
                    let filtered = offlineArticles;
                    if (catId) {
                        const targetIds = (typeof catId === 'string') 
                            ? catId.split(',').map(x => parseInt(x.trim()))
                            : [catId];
                        
                        filtered = offlineArticles.filter(art => {
                            return globalFeeds.some(cat => {
                                if (!targetIds.includes(cat.id)) return false;
                                return cat.feeds.some(f => f.title === art.feed_title);
                            });
                        });
                    }
                    renderArticles(filtered, true);
                    hasMore = false;
                    const totalArticlesEl = document.getElementById("total-articles-count");
                    if (totalArticlesEl) {
                        totalArticlesEl.innerText = filtered.length;
                    }
                } else {
                    articleGrid.innerHTML = `<p style="text-align:center; color: var(--text-muted); width: 100%; margin-top:40px;">Failed to load feed. You are offline and have no cached articles.</p>`;
                }
            } else {
                const loader = document.querySelector(".skeleton-loader-more");
                if (loader) loader.remove();
            }
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
            card.setAttribute("data-article-id", art.id);
            
            const imageHtml = art.image_url 
                ? `<img src="${art.image_url}" alt="Cover" class="article-image" loading="lazy" onerror="this.onerror=null; this.outerHTML='<div class=\\'article-image\\' style=\\'background: linear-gradient(135deg, rgba(10, 25, 40, 0.8), rgba(0, 180, 216, 0.2)); display: flex; align-items:center; justify-content:center;\\'><i class=\\'ph ph-image-broken\\' style=\\'font-size: 48px; color: rgba(255,255,255,0.15);\\'></i></div>';">` 
                : `<div class="article-image" style="background: linear-gradient(135deg, rgba(10, 25, 40, 0.8), rgba(0, 180, 216, 0.2)); display: flex; align-items:center; justify-content:center;"><i class="ph ph-newspaper" style="font-size: 48px; color: rgba(255,255,255,0.15);"></i></div>`;

            // Γραμμή ποιότητας στην κορυφή του card
            const qs = art.quality_score != null ? art.quality_score : 1.0;
            let qClass = 'quality-high';
            if (qs < 0.4) qClass = 'quality-low';
            else if (qs < 0.7) qClass = 'quality-mid';

            card.innerHTML = `
                <div class="quality-bar ${qClass}" title="Quality: ${(qs * 100).toFixed(0)}%${art.filter_flags ? ' — ' + art.filter_flags : ''}"></div>
                ${imageHtml}
                <div class="article-content">
                    <span class="feed-tag">${art.feed_title}</span>
                    <h2 class="article-title">${art.title}</h2>
                    <p class="article-summary">${art.summary || ''}</p>
                    <div class="article-meta">
                        <span><i class="ph ph-calendar-blank"></i> ${art.published}</span>
                        <span class="quality-badge ${qClass}">Article Quality: ${(qs * 100).toFixed(0)}%</span>
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

    // Global stack definitions for grouping and 3D visualizer
    const STACK_DEFINITIONS = {
        'dev-ops': {
            name: 'Code & Infrastructure',
            keywords: ['dev', 'code', 'programm', 'engineer', 'linux', 'sys', 'ops', 'homelab', 'network', 'secur', 'cloud', 'host', 'docker', 'k8s', 'rust', 'python', 'go', 'software', 'git', 'terminal'],
            color: '#00B4D8',
            geometryType: 'torusKnot'
        },
        'science-tech': {
            name: 'Discovery & Science',
            keywords: ['science', 'tech', 'research', 'school', 'uni', 'academia', 'hack', 'innovat', 'learn', 'institute', 'lab', 'space', 'nasa', 'esa', 'cern', 'nature', 'math', 'physic'],
            color: '#9d4edd',
            geometryType: 'dodecahedron'
        },
        'media-podcasts': {
            name: 'Voices & Play',
            keywords: ['podcast', 'audio', 'show', 'media', 'game', 'gaming', 'play', 'music', 'video', 'youtube', 'stream', 'listen', 'talk', 'news'],
            color: '#f4a261',
            geometryType: 'octahedron'
        },
        'general': {
            name: 'Open Currents',
            keywords: [],
            color: '#2a9d8f',
            geometryType: 'sphere'
        }
    };

    let currentGroups = {};

    function groupCategories(categories) {
        const groups = {
            'dev-ops': { id: 'dev-ops', ...STACK_DEFINITIONS['dev-ops'], categories: [] },
            'science-tech': { id: 'science-tech', ...STACK_DEFINITIONS['science-tech'], categories: [] },
            'media-podcasts': { id: 'media-podcasts', ...STACK_DEFINITIONS['media-podcasts'], categories: [] },
            'general': { id: 'general', ...STACK_DEFINITIONS['general'], categories: [] }
        };

        categories.forEach(cat => {
            const nameLower = cat.name.toLowerCase();
            let matched = false;

            for (const kw of STACK_DEFINITIONS['dev-ops'].keywords) {
                if (nameLower.includes(kw)) {
                    groups['dev-ops'].categories.push(cat);
                    matched = true;
                    break;
                }
            }

            if (!matched) {
                for (const kw of STACK_DEFINITIONS['science-tech'].keywords) {
                    if (nameLower.includes(kw)) {
                        groups['science-tech'].categories.push(cat);
                        matched = true;
                        break;
                    }
                }
            }

            if (!matched) {
                for (const kw of STACK_DEFINITIONS['media-podcasts'].keywords) {
                    if (nameLower.includes(kw)) {
                        groups['media-podcasts'].categories.push(cat);
                        matched = true;
                        break;
                    }
                }
            }

            if (!matched) {
                groups['general'].categories.push(cat);
            }
        });

        return groups;
    }

    function renderCategories(categories) {
        categoryList.innerHTML = '';
        currentGroups = groupCategories(categories);

        // Open Sea
        const allStreams = document.createElement("li");
        allStreams.className = "category-header active";
        allStreams.setAttribute("data-id", "all");
        allStreams.innerHTML = `# Open Sea`;
        allStreams.addEventListener('click', () => {
            document.querySelectorAll('.category-header').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.stack-group-header').forEach(el => el.classList.remove('active'));
            allStreams.classList.add('active');
            
            // Επαναφορά του τίτλου στην αρχική προβολή "Open Sea"
            updateHeaderTitle("Open Sea", "News currents from the open sea");
            
            fetchArticles(null, true);
            if(window.innerWidth <= 900) sidebar.classList.remove("open");
        });
        categoryList.appendChild(allStreams);

        // Render groups
        Object.keys(currentGroups).forEach(groupId => {
            const group = currentGroups[groupId];
            if (group.categories.length === 0) return;

            const stackContainer = document.createElement("div");
            stackContainer.className = "stack-group";
            stackContainer.setAttribute("data-group-id", groupId);

            const header = document.createElement("div");
            header.className = "stack-group-header collapsed";
            header.innerHTML = `
                <span class="stack-name"># ${group.name}</span>
                <span class="stack-arrow">[+]</span>
            `;

            const list = document.createElement("ul");
            list.className = "stack-category-list collapsed";

            group.categories.forEach(cat => {
                const li = document.createElement("li");
                li.className = "category-header";
                li.setAttribute("data-id", cat.id);
                li.innerHTML = `* ${cat.name}`;
                li.addEventListener('click', (e) => {
                    e.stopPropagation();
                    document.querySelectorAll('.category-header').forEach(el => el.classList.remove('active'));
                    document.querySelectorAll('.stack-group-header').forEach(el => el.classList.remove('active'));
                    li.classList.add('active');
                    header.classList.add('active');
                    
                    // Ενημέρωση του τίτλου με το όνομα του συγκεκριμένου λιμανιού (harbor / category)
                    updateHeaderTitle(cat.name, `Harbor: articles from ${cat.name}`);
                    
                    fetchArticles(cat.id, true);
                    if(window.innerWidth <= 900) sidebar.classList.remove("open");
                });
                list.appendChild(li);
            });

            header.addEventListener('click', () => {
                const isCollapsed = list.classList.toggle("collapsed");
                header.className.toggle("collapsed", isCollapsed);
                header.querySelector(".stack-arrow").textContent = isCollapsed ? "[+]" : "[-]";

                document.querySelectorAll('.category-header').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.stack-group-header').forEach(el => el.classList.remove('active'));
                header.classList.add('active');

                // Ενημέρωση του τίτλου με το όνομα του αρχιπελάγους (category group)
                updateHeaderTitle(group.name, `Archipelago: exploring ${group.name}`);

                const catIds = group.categories.map(c => c.id).join(',');
                fetchArticles(catIds, true);
            });

            header.addEventListener('mouseenter', () => {
                if (window.highlightStack3D) {
                    window.highlightStack3D(groupId);
                }
            });
            header.addEventListener('mouseleave', () => {
                if (window.highlightStack3D) {
                    window.highlightStack3D(null);
                }
            });

            stackContainer.appendChild(header);
            stackContainer.appendChild(list);
            categoryList.appendChild(stackContainer);
        });

        // Initialize 3D Visualizer
        if (window.initStacks3D) {
            window.initStacks3D(currentGroups);
        }
    }

    window.selectStackFrom3D = (groupId) => {
        const stackGroup = document.querySelector(`.stack-group[data-group-id="${groupId}"]`);
        if (stackGroup) {
            const header = stackGroup.querySelector('.stack-group-header');
            if (header) {
                header.click();
                const list = stackGroup.querySelector('.stack-category-list');
                if (list && list.classList.contains('collapsed')) {
                    header.click();
                }
            }
        }
    };
    
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

    // =====================================================================
    // PWA & IndexedDB & Reader Mode Customizer Logic
    // =====================================================================

    const DB_NAME = "pharos-db";
    const DB_VERSION = 1;
    let dbInstance = null;

    function initDB() {
        return new Promise((resolve) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);
            request.onerror = (e) => {
                console.error("IndexedDB error:", e);
                resolve(null);
            };
            request.onsuccess = (e) => {
                dbInstance = e.target.result;
                resolve(dbInstance);
            };
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains("articles")) {
                    db.createObjectStore("articles", { keyPath: "id" });
                }
                if (!db.objectStoreNames.contains("pending-actions")) {
                    db.createObjectStore("pending-actions", { autoIncrement: true });
                }
            };
        });
    }

    function saveArticlesToOffline(articles) {
        if (!dbInstance) return;
        const tx = dbInstance.transaction("articles", "readwrite");
        const store = tx.objectStore("articles");
        articles.forEach(art => {
            store.put(art);
        });
    }

    function getOfflineArticles() {
        return new Promise((resolve) => {
            if (!dbInstance) return resolve([]);
            const tx = dbInstance.transaction("articles", "readonly");
            const store = tx.objectStore("articles");
            const request = store.getAll();
            request.onsuccess = () => {
                const sorted = request.result.sort((a, b) => new Date(b.raw_published) - new Date(a.raw_published));
                resolve(sorted);
            };
            request.onerror = () => resolve([]);
        });
    }

    function getArticleFromIndexedDB(id) {
        return new Promise((resolve) => {
            if (!dbInstance) return resolve(null);
            const tx = dbInstance.transaction("articles", "readonly");
            const store = tx.objectStore("articles");
            const request = store.get(id);
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => resolve(null);
        });
    }

    function pruneOfflineArticles(maxLimit = 100) {
        if (!dbInstance) return;
        const tx = dbInstance.transaction("articles", "readwrite");
        const store = tx.objectStore("articles");
        const request = store.getAll();
        request.onsuccess = () => {
            const all = request.result;
            if (all.length <= maxLimit) return;
            all.sort((a, b) => new Date(b.raw_published) - new Date(a.raw_published));
            const toDelete = all.slice(maxLimit);
            const deleteTx = dbInstance.transaction("articles", "readwrite");
            const deleteStore = deleteTx.objectStore("articles");
            toDelete.forEach(art => {
                deleteStore.delete(art.id);
            });
        };
    }

    function clearOfflineDB() {
        return new Promise((resolve) => {
            if (!dbInstance) return resolve();
            const tx = dbInstance.transaction("articles", "readwrite");
            const store = tx.objectStore("articles");
            const request = store.clear();
            request.onsuccess = () => {
                console.log("Offline database cleared.");
                resolve();
            };
        });
    }

    function queueOfflineAction(action, articleId) {
        if (!dbInstance) return;
        const tx = dbInstance.transaction("pending-actions", "readwrite");
        const store = tx.objectStore("pending-actions");
        store.add({ action, articleId, timestamp: Date.now() });
    }

    async function syncPendingActions() {
        if (!dbInstance || !navigator.onLine) return;
        const tx = dbInstance.transaction("pending-actions", "readonly");
        const store = tx.objectStore("pending-actions");
        const request = store.getAll();
        
        request.onsuccess = async () => {
            const actions = request.result;
            if (actions.length === 0) return;
            
            const statusEl = document.getElementById("network-status");
            if (statusEl) {
                statusEl.className = "network-status syncing";
                statusEl.querySelector(".status-text").textContent = "Συγχρονισμός...";
            }
            
            for (const item of actions) {
                try {
                    let endpoint = "";
                    if (item.action === "read") {
                        endpoint = `/api/mark_read/${item.articleId}`;
                    }
                    if (endpoint) {
                        await fetch(endpoint, { method: "POST" });
                    }
                } catch (e) {
                    console.error("Failed to sync offline action:", item, e);
                }
            }
            
            const clearTx = dbInstance.transaction("pending-actions", "readwrite");
            clearTx.objectStore("pending-actions").clear();
            
            updateNetworkStatus();
        };
    }

    function updateNetworkStatus() {
        const statusEl = document.getElementById("network-status");
        if (!statusEl) return;
        
        if (navigator.onLine) {
            statusEl.className = "network-status online";
            statusEl.querySelector(".status-text").textContent = "Online";
            syncPendingActions();
        } else {
            statusEl.className = "network-status offline";
            statusEl.querySelector(".status-text").textContent = "Offline";
        }
    }

    window.addEventListener("online", updateNetworkStatus);
    window.addEventListener("offline", updateNetworkStatus);

    function renderOfflineCategoriesOptions(categories) {
        const container = document.getElementById("offline-categories-container");
        if (!container) return;
        
        container.innerHTML = "";
        const selectedCats = JSON.parse(localStorage.getItem("pharos_offline_cats") || "[]");
        
        categories.forEach(cat => {
            const chip = document.createElement("label");
            const isActive = selectedCats.includes(cat.id) || selectedCats.length === 0;
            chip.className = `offline-cat-chip${isActive ? " active" : ""}`;
            chip.innerHTML = `
                 <input type="checkbox" value="${cat.id}" ${isActive ? "checked" : ""}>
                 <span>${cat.name}</span>
            `;
            
            chip.querySelector("input").addEventListener("change", (e) => {
                let currentSelected = JSON.parse(localStorage.getItem("pharos_offline_cats") || "[]");
                const catId = parseInt(e.target.value);
                
                if (e.target.checked) {
                    if (!currentSelected.includes(catId)) currentSelected.push(catId);
                    chip.classList.add("active");
                } else {
                    currentSelected = currentSelected.filter(id => id !== catId);
                    chip.classList.remove("active");
                }
                
                localStorage.setItem("pharos_offline_cats", JSON.stringify(currentSelected));
                cacheTopArticlesOffline();
            });
            
            container.appendChild(chip);
        });
    }

    async function cacheTopArticlesOffline() {
        if (!dbInstance || !navigator.onLine) return;
        
        const selectedCats = JSON.parse(localStorage.getItem("pharos_offline_cats") || "[]");
        let url = `/api/articles?`;
        if (selectedCats.length > 0) {
            url += `category_ids=${selectedCats.join(",")}&`;
        }
        
        try {
            const res = await fetch(url);
            const data = await res.json();
            if (data.articles) {
                saveArticlesToOffline(data.articles);
                pruneOfflineArticles(100);
                
                // Prefetch images for service worker caching
                data.articles.forEach(art => {
                    if (art.image_url) {
                        fetch(art.image_url, { mode: "no-cors" }).catch(() => {});
                    }
                });
            }
        } catch (e) {
            console.error("Failed to cache offline articles", e);
        }
    }

    function initReaderCustomizer() {
        const btnSerif = document.getElementById("reader-font-serif");
        const btnSans = document.getElementById("reader-font-sans");
        const btnZoomOut = document.getElementById("reader-zoom-out");
        const btnZoomIn = document.getElementById("reader-zoom-in");
        const zoomLevelText = document.getElementById("reader-zoom-level");
        const readerBody = document.getElementById("reader-body");
        const readerContent = document.querySelector(".reader-content");
        const themeBtns = document.querySelectorAll(".theme-btn");

        let savedFont = localStorage.getItem("pharos_reader_font") || "serif";
        let savedZoom = parseInt(localStorage.getItem("pharos_reader_zoom") || "100");
        let savedTheme = localStorage.getItem("pharos_reader_theme") || "light";

        function applySettings() {
            if (savedFont === "serif") {
                readerBody.classList.remove("font-sans");
                readerBody.classList.add("font-serif");
                if (btnSerif) btnSerif.classList.add("active");
                if (btnSans) btnSans.classList.remove("active");
            } else {
                readerBody.classList.remove("font-serif");
                readerBody.classList.add("font-sans");
                if (btnSans) btnSans.classList.add("active");
                if (btnSerif) btnSerif.classList.remove("active");
            }

            document.documentElement.style.setProperty("--reader-font-size", `${savedZoom * 0.18}px`);
            if (zoomLevelText) zoomLevelText.textContent = `${savedZoom}%`;

            if (readerContent) {
                readerContent.className = "modal-content glass-panel reader-content " + `theme-${savedTheme}`;
            }
            themeBtns.forEach(btn => {
                if (btn.getAttribute("data-theme") === savedTheme) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });
        }

        applySettings();

        if (btnSerif) {
            btnSerif.onclick = () => {
                savedFont = "serif";
                localStorage.setItem("pharos_reader_font", "serif");
                applySettings();
            };
        }
        if (btnSans) {
            btnSans.onclick = () => {
                savedFont = "sans";
                localStorage.setItem("pharos_reader_font", "sans");
                applySettings();
            };
        }

        if (btnZoomOut) {
            btnZoomOut.onclick = () => {
                if (savedZoom > 60) {
                    savedZoom -= 10;
                    localStorage.setItem("pharos_reader_zoom", savedZoom);
                    applySettings();
                }
            };
        }
        if (btnZoomIn) {
            btnZoomIn.onclick = () => {
                if (savedZoom < 200) {
                    savedZoom += 10;
                    localStorage.setItem("pharos_reader_zoom", savedZoom);
                    applySettings();
                }
            };
        }

        themeBtns.forEach(btn => {
            btn.onclick = () => {
                savedTheme = btn.getAttribute("data-theme");
                localStorage.setItem("pharos_reader_theme", savedTheme);
                applySettings();
            };
        });
    }

    // Clear Offline Cache Button Click
    const clearOfflineBtn = document.getElementById("clear-offline-btn");
    if (clearOfflineBtn) {
        clearOfflineBtn.onclick = async () => {
            if (confirm("Θέλετε σίγουρα να διαγράψετε όλη την offline βάση και τις αποθηκευμένες εικόνες;")) {
                await clearOfflineDB();
                if ('caches' in window) {
                    await caches.delete("pharos-images-v1");
                }
                alert("Η offline cache καθαρίστηκε με επιτυχία!");
            }
        };
    }

    // Register Service Worker
    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
            navigator.serviceWorker.register("/static/sw.js")
                .then(reg => console.log("Service Worker registered successfully:", reg.scope))
                .catch(err => console.error("Service Worker registration failed:", err));
        });
    }

    // Initialization
    initDB().then(() => {
        updateNetworkStatus();
        initReaderCustomizer();
    });

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
