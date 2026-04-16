const dpApp = {
    // Initial State and Dummy Data
    state: {
        channel: {
            name: 'Drama Vibes',
            niche: 'Mother-in-law & Daughter-in-law',
            audience: 'Women 25-55, fans of family drama and soap operas',
            tone: 'Dramatic, Suspenseful, Emotional',
            frequency: 'Daily',
            goals: 'Build a loyal audience, drive engagement via dramatic cliffhangers'
        },
        characters: [
            { id: 'c1', name: 'Martha', role: 'Mother-in-law', age: '58', style: 'Traditional, conservative, elegant', personality: 'Controlling, proud, secretly insecure, manipulative', visual: 'Short grey hair, always wears pearls, sharp features', relationships: 'Dislikes Linda, overprotective of David' },
            { id: 'c2', name: 'Linda', role: 'Daughter-in-law', age: '29', style: 'Modern, casual but neat', personality: 'Independent, patient but has limits, smart', visual: 'Long dark hair, expressive eyes', relationships: 'Loves David, tries to keep peace with Martha but fails' },
            { id: 'c3', name: 'David', role: 'Husband/Son', age: '32', style: 'Business casual', personality: 'Avoids conflict, easily manipulated by his mother, loves his wife', visual: 'Tall, neat beard, tired expression', relationships: 'Caught in the middle' },
            { id: 'c4', name: 'Sarah', role: 'Sister-in-law', age: '25', style: 'Trendy, flashy', personality: 'Gossip, instigator, opportunistic', visual: 'Bright dyed hair, heavy makeup', relationships: 'Martha\'s favorite, actively undermines Linda' }
        ],
        episodes: [
            // Week 1
            { id: 'e1', week: 1, title: 'The Stolen Recipe', status: 'Produced', summary: 'Martha claims Linda stole her secret family recipe for a dinner party.', conflict: 'Martha confronts Linda in front of guests.', beginning: 'Dinner preparation.', middle: 'Martha discovers her recipe card in Linda\'s purse (placed by Sarah).', ending: 'Linda is humiliated.', cliffhanger: 'Linda finds footage of Sarah placing the card.' },
            { id: 'e2', week: 1, title: 'The Camera Footage', status: 'Ready', summary: 'Linda uses the footage to clear her name.', conflict: 'Revealing the truth to David without sounding crazy.', beginning: 'Linda shows David the video.', middle: 'David confronts Sarah, Martha defends Sarah.', ending: 'Martha fakes a health issue to stop the argument.', cliffhanger: 'Doctor arrives and gives surprising news.' },
            // Add a few more
            { id: 'e3', week: 2, title: 'The Inheritance Trick', status: 'Drafting', summary: 'Martha rewrites the will to exclude Linda.', conflict: 'Money control.', beginning: 'Lawyer visits.', middle: 'Linda finds the documents.', ending: 'David is oblivious.', cliffhanger: 'Linda packs her bags.' },
            { id: 'e4', week: 2, title: 'Leaving the House', status: 'Idea', summary: 'Linda stays at a hotel, David investigates.', conflict: '', beginning: '', middle: '', ending: '', cliffhanger: '' }
        ],
        scenes: [
            { id: 's1', episodeId: 'e1', num: '1A', location: 'Kitchen', chars: 'Martha, Linda', emotion: 'Tense', visual: 'Steaming pots, tight shots on chopping', dialogue: 'Martha criticizes Linda\'s knife skills.', angle: 'Over the shoulder', prompt: 'Two women arguing in a modern kitchen, cinematic lighting, 4k' }
        ],
        continuity: {
            relationships: 'Martha and Linda are currently openly hostile after the recipe incident.',
            conflicts: 'The inheritance document is still hidden.',
            events: 'Martha faked a heart attack in week 1.',
            visuals: 'Martha always wears her pearl necklace. Linda\'s wedding ring is missing since episode 3.',
            rules: 'David never takes Linda\'s side immediately.'
        },
        settings: {
            theme: 'dark',
            accent: '#6366f1'
        }
    },

    // Initialization
    init() {
        this.loadData();
        this.applySettings();
        this.setupNavigation();
        this.renderAllViews();
        console.log('Drama Planner initialized.');
    },

    // Persistence
    saveData() {
        localStorage.setItem('dramaPlannerData', JSON.stringify(this.state));
    },

    loadData() {
        const stored = localStorage.getItem('dramaPlannerData');
        if (stored) {
            this.state = JSON.parse(stored);
        } else {
            this.saveData(); // Save dummy data on first load
        }
    },

    // UI Updates
    applySettings() {
        const app = document.getElementById('drama-planner-app');
        app.className = `dp-theme-${this.state.settings.theme}`;
        app.style.setProperty('--dp-accent', this.state.settings.accent);
        
        // Update inputs
        const themeSelect = document.getElementById('dp-theme-toggle');
        if (themeSelect) themeSelect.value = this.state.settings.theme;
        
        const colorPicker = document.getElementById('dp-accent-color');
        if (colorPicker) colorPicker.value = this.state.settings.accent || '#6366f1';
    },

    toggleTheme(theme) {
        this.state.settings.theme = theme;
        this.saveData();
        this.applySettings();
    },

    updateAccentColor(color) {
        this.state.settings.accent = color;
        this.saveData();
        this.applySettings();
    },

    // Navigation and Layout
    setupNavigation() {
        const links = document.querySelectorAll('.dp-nav-link');
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = e.target.getAttribute('data-target');
                this.switchView(target);
                
                // Active state
                links.forEach(l => l.classList.remove('active'));
                e.target.classList.add('active');

                // Close mobile sidebar if open
                const sidebar = document.getElementById('dp-sidebar');
                if (sidebar) sidebar.classList.remove('active');
            });
        });

        // Mobile Menu Toggle
        document.getElementById('dp-mobile-menu-btn')?.addEventListener('click', () => {
            document.getElementById('dp-sidebar').classList.add('active');
        });
        document.getElementById('dp-close-sidebar-btn')?.addEventListener('click', () => {
            document.getElementById('dp-sidebar').classList.remove('active');
        });
    },

    switchView(viewId) {
        document.querySelectorAll('.dp-view').forEach(view => {
            view.classList.remove('active');
        });
        const targetView = document.getElementById(`dp-view-${viewId}`);
        if(targetView) {
            targetView.classList.add('active');
            this.renderView(viewId);
        }
    },

    renderAllViews() {
        this.renderDashboard();
        this.renderCharacters();
        this.renderMonthlyPlan();
        this.renderEpisodes();
        this.renderScenePlanner();
        this.renderContinuity();
    },

    renderView(viewId) {
        switch(viewId) {
            case 'dashboard': this.renderDashboard(); break;
            case 'characters': this.renderCharacters(); break;
            case 'monthly-plan': this.renderMonthlyPlan(); break;
            case 'episodes': this.renderEpisodes(); break;
            case 'scene-planner': this.renderScenePlanner(); break;
            case 'continuity': this.renderContinuity(); break;
        }
    },

    // Generators (UUID)
    generateId() {
        return Math.random().toString(36).substring(2, 9);
    },

    // --- DASHBOARD ---
    renderDashboard() {
        document.getElementById('dp-channel-name').value = this.state.channel.name || '';
        document.getElementById('dp-channel-niche').value = this.state.channel.niche || '';
        document.getElementById('dp-channel-audience').value = this.state.channel.audience || '';
        document.getElementById('dp-channel-tone').value = this.state.channel.tone || '';
        document.getElementById('dp-channel-frequency').value = this.state.channel.frequency || '';
        document.getElementById('dp-channel-goals').value = this.state.channel.goals || '';
    },

    saveChannelInfo() {
        this.state.channel.name = document.getElementById('dp-channel-name').value;
        this.state.channel.niche = document.getElementById('dp-channel-niche').value;
        this.state.channel.audience = document.getElementById('dp-channel-audience').value;
        this.state.channel.tone = document.getElementById('dp-channel-tone').value;
        this.state.channel.frequency = document.getElementById('dp-channel-frequency').value;
        this.state.channel.goals = document.getElementById('dp-channel-goals').value;
        this.saveData();
        alert('Channel info saved!');
    },

    // --- CHARACTERS ---
    renderCharacters() {
        const list = document.getElementById('dp-characters-list');
        list.innerHTML = '';
        this.state.characters.forEach(char => {
            const card = document.createElement('div');
            card.className = 'dp-card';
            card.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
                    <div>
                        <h3 style="margin:0">${char.name}</h3>
                        <span class="dp-badge" style="margin-top:4px">${char.role}</span>
                    </div>
                    <div>
                        <button class="dp-btn dp-btn-icon" onclick="dpApp.editCharacter('${char.id}')">✎</button>
                        <button class="dp-btn dp-btn-icon" onclick="dpApp.deleteCharacter('${char.id}')">🗑</button>
                    </div>
                </div>
                <p style="font-size:0.9rem;color:var(--dp-text-secondary);margin:4px 0;"><strong>Age:</strong> ${char.age}</p>
                <p style="font-size:0.9rem;color:var(--dp-text-secondary);margin:4px 0;"><strong>Personality:</strong> ${char.personality}</p>
            `;
            list.appendChild(card);
        });
    },

    openCharacterModal(charInfo = null) {
        document.getElementById('dp-modal-character').classList.add('active');
        if (charInfo) {
            document.getElementById('dp-modal-character-title').innerText = 'Edit Character';
            document.getElementById('dp-char-id').value = charInfo.id;
            document.getElementById('dp-char-name').value = charInfo.name || '';
            document.getElementById('dp-char-role').value = charInfo.role || '';
            document.getElementById('dp-char-age').value = charInfo.age || '';
            document.getElementById('dp-char-style').value = charInfo.style || '';
            document.getElementById('dp-char-personality').value = charInfo.personality || '';
            document.getElementById('dp-char-visual').value = charInfo.visual || '';
            document.getElementById('dp-char-relationships').value = charInfo.relationships || '';
        } else {
            document.getElementById('dp-modal-character-title').innerText = 'Add Character';
            document.getElementById('dp-char-id').value = '';
            document.getElementById('dp-char-name').value = '';
            document.getElementById('dp-char-role').value = '';
            document.getElementById('dp-char-age').value = '';
            document.getElementById('dp-char-style').value = '';
            document.getElementById('dp-char-personality').value = '';
            document.getElementById('dp-char-visual').value = '';
            document.getElementById('dp-char-relationships').value = '';
        }
    },

    saveCharacter() {
        const id = document.getElementById('dp-char-id').value;
        const charData = {
            id: id || this.generateId(),
            name: document.getElementById('dp-char-name').value,
            role: document.getElementById('dp-char-role').value,
            age: document.getElementById('dp-char-age').value,
            style: document.getElementById('dp-char-style').value,
            personality: document.getElementById('dp-char-personality').value,
            visual: document.getElementById('dp-char-visual').value,
            relationships: document.getElementById('dp-char-relationships').value,
        };

        if (id) {
            const index = this.state.characters.findIndex(c => c.id === id);
            if (index !== -1) this.state.characters[index] = charData;
        } else {
            this.state.characters.push(charData);
        }

        this.saveData();
        this.renderCharacters();
        this.closeModal('dp-modal-character');
    },

    editCharacter(id) {
        const char = this.state.characters.find(c => c.id === id);
        if (char) this.openCharacterModal(char);
    },

    deleteCharacter(id) {
        if(confirm('Delete this character?')) {
            this.state.characters = this.state.characters.filter(c => c.id !== id);
            this.saveData();
            this.renderCharacters();
        }
    },

    // --- MONTHLY PLAN & EPISODES ---
    renderMonthlyPlan() {
        const container = document.getElementById('dp-monthly-plan-list');
        container.innerHTML = '';
        
        // Group by week (assuming 4 weeks)
        for (let week = 1; week <= 4; week++) {
            const weekEps = this.state.episodes.filter(ep => ep.week === week);
            if (weekEps.length === 0) continue;

            const weekDiv = document.createElement('div');
            weekDiv.className = 'dp-week-group';
            weekDiv.innerHTML = `<div class="dp-week-header">Week ${week}</div>`;
            
            const list = document.createElement('div');
            list.className = 'dp-list';

            weekEps.forEach(ep => {
                const item = document.createElement('div');
                item.className = 'dp-list-item';
                item.innerHTML = `
                    <div>
                        <div style="font-weight:600;margin-bottom:4px">${ep.title || 'Untitled'}</div>
                        <div style="font-size:0.85rem;color:var(--dp-text-secondary)">${ep.summary || 'No summary'}</div>
                    </div>
                    <span class="dp-badge dp-badge-status-${ep.status}">${ep.status || 'Idea'}</span>
                `;
                item.onclick = () => this.openEpisodePanel(ep.id);
                list.appendChild(item);
            });
            weekDiv.appendChild(list);
            container.appendChild(weekDiv);
        }
    },

    renderEpisodes() {
        const list = document.getElementById('dp-episodes-list');
        list.innerHTML = '';
        
        this.state.episodes.forEach((ep, index) => {
            const item = document.createElement('div');
            item.className = 'dp-list-item';
            item.innerHTML = `
                <div>
                    <span class="dp-badge" style="margin-right:8px">Ep ${index + 1}</span>
                    <span style="font-weight:600">${ep.title || 'Untitled'}</span>
                    <div style="font-size:0.85rem;color:var(--dp-text-secondary);margin-top:4px">Week ${ep.week} • Subplots: ${ep.conflict ? 'Yes' : 'No'}</div>
                </div>
                <button class="dp-btn dp-btn-secondary" onclick="dpApp.openEpisodePanel('${ep.id}')">Details</button>
            `;
            list.appendChild(item);
        });
    },

    openEpisodePanel(id) {
        const ep = this.state.episodes.find(e => e.id === id);
        if (!ep) return;

        const epIndex = this.state.episodes.findIndex(e => e.id === id);
        
        document.getElementById('dp-ep-panel-number').innerText = `Ep ${epIndex + 1}`;
        document.getElementById('dp-ep-panel-title').innerText = ep.title || 'Untitled';
        
        document.getElementById('dp-ep-edit-id').value = ep.id;
        document.getElementById('dp-ep-edit-title').value = ep.title || '';
        document.getElementById('dp-ep-edit-status').value = ep.status || 'Idea';
        document.getElementById('dp-ep-edit-summary').value = ep.summary || '';
        document.getElementById('dp-ep-edit-conflict').value = ep.conflict || '';
        document.getElementById('dp-ep-edit-beginning').value = ep.beginning || '';
        document.getElementById('dp-ep-edit-middle').value = ep.middle || '';
        document.getElementById('dp-ep-edit-ending').value = ep.ending || '';
        document.getElementById('dp-ep-edit-cliffhanger').value = ep.cliffhanger || '';

        document.getElementById('dp-panel-episode').classList.add('active');
    },

    saveEpisodeDetail() {
        const id = document.getElementById('dp-ep-edit-id').value;
        const ep = this.state.episodes.find(e => e.id === id);
        if (ep) {
            ep.title = document.getElementById('dp-ep-edit-title').value;
            ep.status = document.getElementById('dp-ep-edit-status').value;
            ep.summary = document.getElementById('dp-ep-edit-summary').value;
            ep.conflict = document.getElementById('dp-ep-edit-conflict').value;
            ep.beginning = document.getElementById('dp-ep-edit-beginning').value;
            ep.middle = document.getElementById('dp-ep-edit-middle').value;
            ep.ending = document.getElementById('dp-ep-edit-ending').value;
            ep.cliffhanger = document.getElementById('dp-ep-edit-cliffhanger').value;
            
            this.saveData();
            this.renderMonthlyPlan();
            this.renderEpisodes();
            
            // update title in panel dynamically
            document.getElementById('dp-ep-panel-title').innerText = ep.title || 'Untitled';
        }
    },

    // --- SCENE PLANNER ---
    renderScenePlanner() {
        const select = document.getElementById('dp-scene-episode-select');
        const currentEpId = select.value;
        
        // Populate select if empty
        if (select.options.length === 0) {
            this.state.episodes.forEach((ep, index) => {
                const opt = document.createElement('option');
                opt.value = ep.id;
                opt.text = `Ep ${index + 1}: ${ep.title}`;
                select.appendChild(opt);
            });
            if (this.state.episodes.length > 0) {
                select.value = this.state.episodes[0].id;
            }
        }

        const selectedEp = select.value;
        const list = document.getElementById('dp-scene-planner-list');
        list.innerHTML = '';
        
        if (!selectedEp) return;

        const epScenes = this.state.scenes.filter(s => s.episodeId === selectedEp);
        if (epScenes.length === 0) {
            list.innerHTML = '<p style="color:var(--dp-text-secondary)">No scenes planned for this episode yet. Click Add Scene to start.</p>';
        }

        epScenes.forEach(scene => {
            const item = document.createElement('div');
            item.className = 'dp-card';
            item.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
                    <h4 style="margin:0"><span class="dp-badge">${scene.num}</span> ${scene.location}</h4>
                    <div>
                        <button class="dp-btn dp-btn-icon" onclick="dpApp.editScene('${scene.id}')">✎</button>
                        <button class="dp-btn dp-btn-icon" onclick="dpApp.deleteScene('${scene.id}')">🗑</button>
                    </div>
                </div>
                <div style="font-size:0.9rem;color:var(--dp-text-secondary)">
                    <p><strong>Characters:</strong> ${scene.chars}</p>
                    <p><strong>Action:</strong> ${scene.visual}</p>
                    ${scene.prompt ? `<p><strong>Prompt:</strong> <em>${scene.prompt}</em></p>` : ''}
                </div>
            `;
            list.appendChild(item);
        });
    },

    openSceneModal(sceneInfo = null) {
        document.getElementById('dp-modal-scene').classList.add('active');
        const epId = document.getElementById('dp-scene-episode-select').value;
        
        if (sceneInfo) {
            document.getElementById('dp-modal-scene-title').innerText = 'Edit Scene';
            document.getElementById('dp-scene-id').value = sceneInfo.id;
            document.getElementById('dp-scene-num').value = sceneInfo.num || '';
            document.getElementById('dp-scene-location').value = sceneInfo.location || '';
            document.getElementById('dp-scene-chars').value = sceneInfo.chars || '';
            document.getElementById('dp-scene-emotion').value = sceneInfo.emotion || '';
            document.getElementById('dp-scene-visual').value = sceneInfo.visual || '';
            document.getElementById('dp-scene-dialogue').value = sceneInfo.dialogue || '';
            document.getElementById('dp-scene-angle').value = sceneInfo.angle || '';
            document.getElementById('dp-scene-prompt').value = sceneInfo.prompt || '';
        } else {
            document.getElementById('dp-modal-scene-title').innerText = 'Add Scene';
            document.getElementById('dp-scene-id').value = '';
            document.getElementById('dp-scene-num').value = '';
            document.getElementById('dp-scene-location').value = '';
            document.getElementById('dp-scene-chars').value = '';
            document.getElementById('dp-scene-emotion').value = '';
            document.getElementById('dp-scene-visual').value = '';
            document.getElementById('dp-scene-dialogue').value = '';
            document.getElementById('dp-scene-angle').value = '';
            document.getElementById('dp-scene-prompt').value = '';
        }
    },

    saveScene() {
        const id = document.getElementById('dp-scene-id').value;
        const epId = document.getElementById('dp-scene-episode-select').value;
        
        if (!epId) {
            alert('Please select an episode first.');
            return;
        }

        const sceneData = {
            id: id || this.generateId(),
            episodeId: epId,
            num: document.getElementById('dp-scene-num').value,
            location: document.getElementById('dp-scene-location').value,
            chars: document.getElementById('dp-scene-chars').value,
            emotion: document.getElementById('dp-scene-emotion').value,
            visual: document.getElementById('dp-scene-visual').value,
            dialogue: document.getElementById('dp-scene-dialogue').value,
            angle: document.getElementById('dp-scene-angle').value,
            prompt: document.getElementById('dp-scene-prompt').value,
        };

        if (id) {
            const index = this.state.scenes.findIndex(s => s.id === id);
            if (index !== -1) this.state.scenes[index] = sceneData;
        } else {
            this.state.scenes.push(sceneData);
        }

        this.saveData();
        this.renderScenePlanner();
        this.closeModal('dp-modal-scene');
    },

    editScene(id) {
        const scene = this.state.scenes.find(s => s.id === id);
        if (scene) this.openSceneModal(scene);
    },

    deleteScene(id) {
        if(confirm('Delete this scene?')) {
            this.state.scenes = this.state.scenes.filter(s => s.id !== id);
            this.saveData();
            this.renderScenePlanner();
        }
    },

    // --- CONTINUITY ---
    renderContinuity() {
        document.getElementById('dp-cont-relationships').value = this.state.continuity.relationships || '';
        document.getElementById('dp-cont-conflicts').value = this.state.continuity.conflicts || '';
        document.getElementById('dp-cont-events').value = this.state.continuity.events || '';
        document.getElementById('dp-cont-visuals').value = this.state.continuity.visuals || '';
        document.getElementById('dp-cont-rules').value = this.state.continuity.rules || '';
    },

    saveContinuity() {
        this.state.continuity.relationships = document.getElementById('dp-cont-relationships').value;
        this.state.continuity.conflicts = document.getElementById('dp-cont-conflicts').value;
        this.state.continuity.events = document.getElementById('dp-cont-events').value;
        this.state.continuity.visuals = document.getElementById('dp-cont-visuals').value;
        this.state.continuity.rules = document.getElementById('dp-cont-rules').value;
        this.saveData();
        alert('Continuity data saved!');
    },

    // --- PROMPT GENERATOR (Placeholder for API Integration) ---
    generateMonthlyStrategyPrompt() {
        const c = this.state.channel;
        const prompt = `System Prompt: You are a creative strategist for a short-form video platform.\n\nTask: Generate a 30-day content plan.\nContext:\n- Channel Niche: ${c.niche}\n- Tone: ${c.tone}\n- Target Audience: ${c.audience}\n- Goals: ${c.goals}\n\nExisting Universe Constraints:\n${this.state.continuity.rules}\n\nPlease generate week-by-week episode ideas prioritizing engagement and suspense.`;
        document.getElementById('dp-prompt-output').value = prompt;
    },

    generateEpisodePrompt() {
        const eps = this.state.episodes;
        if (eps.length === 0) {
            document.getElementById('dp-prompt-output').value = "No episodes defined. Please create an episode first.";
            return;
        }
        // Take the first drafting/idea one as an example
        const ep = eps.find(e => e.status !== 'Produced') || eps[0];
        
        const prompt = `System Prompt: You are a scriptwriter for viral dramatic short-form videos.\n\nTask: Write a detailed beat sheet for a 1-minute episode.\nBase Idea:\n- Title: ${ep.title}\n- Core Conflict: ${ep.conflict}\n- Hook: ${ep.beginning}\n- Desired Cliffhanger: ${ep.cliffhanger}\n\nCharacters involved:\n(Reference Character Bible)\n\nPlease generate a 5-scene breakdown.`;
        document.getElementById('dp-prompt-output').value = prompt;
    },

    generateScenePrompt() {
        const scenes = this.state.scenes;
        if (scenes.length === 0) {
            document.getElementById('dp-prompt-output').value = "No scenes defined. Please create a scene first.";
            return;
        }
        const s = scenes[0]; // Just an example
        
        const prompt = `Prompt for Image/Video AI Generation (e.g. Midjourney/Veo):\n\nCinematic shot, ${s.angle}, ${s.visual}, emotion: ${s.emotion}, location: ${s.location}, characters: ${s.chars}, lighting suited for a drama series, highly detailed, photorealistic, 4k.`;
        document.getElementById('dp-prompt-output').value = prompt;
    },

    copyPrompt() {
        const text = document.getElementById('dp-prompt-output').value;
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            alert('Copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    },

    // --- MODAL / PANEL UTILS ---
    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
    },

    closePanel(panelId) {
        document.getElementById(panelId).classList.remove('active');
    },

    // --- IMPORT / EXPORT ---
    exportData() {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.state, null, 2));
        const dlAnchorElem = document.createElement('a');
        dlAnchorElem.setAttribute("href", dataStr);
        dlAnchorElem.setAttribute("download", "drama_planner_backup.json");
        dlAnchorElem.click();
    },

    importData(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const newData = JSON.parse(e.target.result);
                if (newData && newData.channel) {
                    this.state = newData;
                    this.saveData();
                    this.applySettings();
                    this.renderAllViews();
                    alert('Data imported successfully!');
                } else {
                    alert('Invalid file format.');
                }
            } catch (err) {
                alert('Error parsing JSON file.');
            }
        };
        reader.readAsText(file);
    },

    downloadPlanTxt() {
        let txt = `CHANNEL OVERVIEW\n`;
        txt += `Name: ${this.state.channel.name}\nNiche: ${this.state.channel.niche}\n\n`;
        
        txt += `EPISODES\n`;
        this.state.episodes.forEach((ep, i) => {
            txt += `Ep ${i+1}: ${ep.title} [${ep.status}]\nSummary: ${ep.summary}\n\n`;
        });
        
        const dataStr = "data:text/plain;charset=utf-8," + encodeURIComponent(txt);
        const dlAnchorElem = document.createElement('a');
        dlAnchorElem.setAttribute("href", dataStr);
        dlAnchorElem.setAttribute("download", "drama_plan.txt");
        dlAnchorElem.click();
    },

    resetData() {
        if(confirm('WARNING: This will delete ALL your data and cannot be undone. Are you sure?')) {
            localStorage.removeItem('dramaPlannerData');
            location.reload();
        }
    }
};

// Initialize App when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    dpApp.init();
});
