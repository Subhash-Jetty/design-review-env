/**
 * Design Review Engine — Client Application
 * 
 * Manages all UI state, API communication, expert agent step-through,
 * and real-time visualization updates.
 */

const COMP_ICONS = {
    chord: '🔩', member: '📏', beam: '🪵', column: '🏛️', brace: '⚡',
    connection: '🔗', bearing: '⭕', shell: '🛢️', nozzle: '🔧', flange: '💍',
    support: '🏗️', gear: '⚙️', pinion: '🔄', shaft: '🔩', housing: '📦',
    default: '🔷'
};

const DOMAIN_LABELS = {
    bridge_truss: '🌉 Bridge Truss',
    pressure_vessel: '🏭 Pressure Vessel',
    gear_assembly: '⚙️ Gear Assembly',
    building_frame: '🏢 Building Frame'
};

class DesignReviewApp {
    constructor() {
        this.domain = 'bridge_truss';
        this.difficulty = 'medium';
        this.seed = null;
        this.components = {};
        this.selectedComponent = null;
        this.inspectedComponents = [];
        this.flaggedComponents = [];
        this.isDemoRunning = false;
        this.autoPlayInterval = null;
        this.autoPlaySpeed = 1200;
        this.episodeDone = false;
        this.stepCount = 0;
        this.transcriptItems = [];

        this.initEventListeners();
    }

    initEventListeners() {
        // Domain buttons
        document.querySelectorAll('.domain-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.domain-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.domain = btn.dataset.domain;
            });
        });

        // Difficulty buttons
        document.querySelectorAll('.diff-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                btn.classList.add(btn.dataset.diff);
                this.difficulty = btn.dataset.diff;
            });
        });

        // Random seed
        document.getElementById('randomSeedBtn').addEventListener('click', () => {
            const seed = Math.floor(Math.random() * 99999) + 1;
            document.getElementById('seedInput').value = seed;
            this.seed = seed;
        });

        document.getElementById('seedInput').addEventListener('change', (e) => {
            this.seed = e.target.value ? parseInt(e.target.value) : null;
        });

        // Close modals on overlay click
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) overlay.classList.add('hidden');
            });
        });
    }

    // ── API Calls ──────────────────────────────────────────────────────

    async apiCall(endpoint, method = 'GET', body = null) {
        try {
            const opts = { method, headers: { 'Content-Type': 'application/json' } };
            if (body) opts.body = JSON.stringify(body);
            const res = await fetch(endpoint, opts);
            if (!res.ok) {
                const err = await res.json().catch(() => ({ error: res.statusText }));
                throw new Error(err.error || `HTTP ${res.status}`);
            }
            return await res.json();
        } catch (err) {
            console.error(`API error: ${endpoint}`, err);
            this.showFeedback(`❌ Error: ${err.message}`, 'error');
            throw err;
        }
    }

    // ── Reset Environment ──────────────────────────────────────────────

    async resetEnvironment() {
        const btn = document.getElementById('newDesignBtn');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner"></div> Generating...';
        this.setStatus('Generating design...', 'running');

        // Stop any running demo
        this.stopDemo();

        try {
            const seedVal = document.getElementById('seedInput').value;
            const data = await this.apiCall('/api/reset', 'POST', {
                domain: this.domain,
                difficulty: this.difficulty,
                seed: seedVal ? parseInt(seedVal) : null,
            });

            this.components = data.components || {};
            this.inspectedComponents = [];
            this.flaggedComponents = [];
            this.selectedComponent = null;
            this.episodeDone = false;
            this.stepCount = 0;
            this.transcriptItems = [];

            // Show dashboard
            document.getElementById('welcomeScreen').classList.add('hidden');
            document.getElementById('dashboardContent').classList.remove('hidden');

            // Populate briefing
            const obs = data.observation || {};
            this.updateBriefing(obs, data);
            this.renderComponents();
            this.updateMetrics(data.state || {});
            this.resetDimensions();

            // Enable demo button
            document.getElementById('runDemoBtn').disabled = false;

            // Clear panels
            document.getElementById('inspectionPanel').classList.add('hidden');
            document.getElementById('analysisPanel').classList.add('hidden');
            document.getElementById('feedbackBar').classList.add('hidden');
            document.getElementById('episodeBanner').classList.add('hidden');

            // Transcript
            this.clearTranscript();
            this.addTranscript('info', 'System', `Design ${obs.design_id} generated — ${Object.keys(this.components).length} components, ${this.difficulty.toUpperCase()} difficulty`);
            this.addTranscript('info', 'System', obs.step_feedback || 'Ready for review.');

            this.showFeedback(obs.step_feedback || 'Design generated successfully!');
            this.setStatus('Design loaded', 'active');
            this.enableActions(true);

        } catch (err) {
            console.error(err);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>🔧</span> Generate New Design';
        }
    }

    // ── Take Action ────────────────────────────────────────────────────

    async doAction(actionType) {
        if (this.episodeDone) return;

        if (actionType === 'inspect') {
            this.openInspectModal();
            return;
        }
        if (actionType === 'request_analysis') {
            this.openAnalysisModal();
            return;
        }
        if (actionType === 'request_info') {
            await this.executeStep({ action_type: 'request_info' });
            return;
        }
        if (actionType === 'approve' || actionType === 'reject') {
            await this.executeStep({ action_type: actionType });
            return;
        }
        if (actionType === 'compare_standard') {
            if (!this.selectedComponent) {
                this.showFeedback('⚠️ Select a component first by inspecting it.');
                return;
            }
            await this.executeStep({
                action_type: 'compare_standard',
                component_id: this.selectedComponent,
                parameter_name: 'depth_mm',
                parameter_value: 200,
                standard_code: 'AISC 360-22',
            });
            return;
        }
    }

    async executeStep(actionData) {
        if (this.episodeDone) return null;

        try {
            const data = await this.apiCall('/api/step', 'POST', actionData);
            this.stepCount++;

            const obs = data.observation || {};
            const state = data.state || {};

            // Update inspected/flagged tracking  
            if (obs.inspected_components) {
                this.inspectedComponents = obs.inspected_components;
            }

            // Update component cards
            this.renderComponents();

            // Show inspection data
            if (actionData.action_type === 'inspect' && obs.current_component) {
                this.showInspection(actionData.component_id, obs.current_component, obs.component_context);
            }

            // Show analysis
            if (actionData.action_type === 'request_analysis' && obs.analysis_results) {
                this.showAnalysis(obs.analysis_results);
            }

            // Update feedback
            this.showFeedback(obs.step_feedback || '');

            // Determine transcript type
            let tType = 'info';
            if (obs.step_feedback && obs.step_feedback.includes('CORRECT')) tType = 'correct';
            else if (obs.step_feedback && (obs.step_feedback.includes('FALSE') || obs.step_feedback.includes('DANGEROUS'))) tType = 'incorrect';
            else if (obs.step_feedback && obs.step_feedback.includes('⚠️')) tType = 'warning';

            this.addTranscript(tType, `Step ${this.stepCount}`,
                `${actionData.action_type}${actionData.component_id ? ` → ${actionData.component_id}` : ''} | Reward: ${data.reward >= 0 ? '+' : ''}${data.reward?.toFixed(2)}`
            );

            // Update metrics
            this.updateMetrics(state);

            // Check if done
            if (data.done) {
                this.episodeDone = true;
                this.enableActions(false);
                this.showEpisodeComplete(state);
                this.setStatus('Episode complete', 'inactive');
            }

            return data;
        } catch (err) {
            console.error(err);
            return null;
        }
    }

    // ── Expert Agent Demo ──────────────────────────────────────────────

    async startDemo() {
        const btn = document.getElementById('runDemoBtn');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner"></div> Starting...';

        this.stopDemo();

        try {
            const seedVal = document.getElementById('seedInput').value;
            const data = await this.apiCall('/api/demo/start', 'POST', {
                domain: this.domain,
                difficulty: this.difficulty,
                seed: seedVal ? parseInt(seedVal) : null,
            });

            this.components = data.components || {};
            this.inspectedComponents = [];
            this.flaggedComponents = [];
            this.selectedComponent = null;
            this.episodeDone = false;
            this.stepCount = 0;
            this.isDemoRunning = true;

            // Show dashboard
            document.getElementById('welcomeScreen').classList.add('hidden');
            document.getElementById('dashboardContent').classList.remove('hidden');
            document.getElementById('reasoningPanel').classList.remove('hidden');
            document.getElementById('episodeBanner').classList.add('hidden');

            // Populate UI
            const obs = data.observation || {};
            this.updateBriefing(obs, data);
            this.renderComponents();
            this.updateMetrics(data.state || {});
            this.resetDimensions();

            // Enable step controls
            document.getElementById('nextStepBtn').disabled = false;
            document.getElementById('autoPlayBtn').disabled = false;
            document.getElementById('demoControls').classList.remove('hidden');
            this.enableActions(false);

            // Transcript
            this.clearTranscript();
            this.addTranscript('info', '🤖 Agent', `Expert agent initialized for ${this.domain.replace(/_/g, ' ')} review`);

            this.showFeedback(obs.step_feedback || 'Expert agent ready. Click "Next Step" or "Auto Play".');
            this.setStatus('Agent ready', 'running');

        } catch (err) {
            console.error(err);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>🤖</span> Run Expert Agent';
        }
    }

    async demoNextStep() {
        if (!this.isDemoRunning || this.episodeDone) return;

        const btn = document.getElementById('nextStepBtn');
        btn.disabled = true;

        try {
            const data = await this.apiCall('/api/demo/next', 'POST');

            if (!data.action && data.done) {
                this.isDemoRunning = false;
                this.episodeDone = true;
                this.stopAutoPlay();
                this.showEpisodeComplete(data.state || {});
                this.setStatus('Demo complete', 'inactive');
                return;
            }

            this.stepCount++;
            const obs = data.observation || {};
            const state = data.state || {};
            const action = data.action || {};

            // Update reasoning panel
            if (data.agent_reasoning) {
                document.getElementById('reasoningText').textContent = data.agent_reasoning;
            }

            // Update inspected tracking
            if (obs.inspected_components) {
                this.inspectedComponents = obs.inspected_components;
            }

            // Update flagged
            if (obs.flagged_issues) {
                this.flaggedComponents = obs.flagged_issues
                    .filter(f => f.matched)
                    .map(f => f.component_id);
            }

            this.renderComponents();

            // Show inspection
            if (action.action_type === 'inspect' && obs.current_component) {
                this.showInspection(action.component_id, obs.current_component, obs.component_context);
            }

            // Show analysis
            if (action.action_type === 'request_analysis' && obs.analysis_results) {
                this.showAnalysis(obs.analysis_results);
            }

            // Feedback
            this.showFeedback(obs.step_feedback || '');

            // Transcript
            let tType = 'info';
            const fb = obs.step_feedback || '';
            if (fb.includes('CORRECT')) tType = 'correct';
            else if (fb.includes('FALSE') || fb.includes('DANGEROUS')) tType = 'incorrect';
            else if (fb.includes('⚠️') || fb.includes('MARGINAL')) tType = 'warning';

            const phaseLabel = data.phase ? `[${data.phase.toUpperCase()}]` : '';
            this.addTranscript(tType, `Step ${this.stepCount} ${phaseLabel}`,
                `${action.action_type || 'end'}${action.component_id ? ` → ${action.component_id}` : ''} | R: ${data.reward >= 0 ? '+' : ''}${data.reward?.toFixed(2)}`
            );

            // Metrics
            this.updateMetrics(state);

            // Done?
            if (data.done) {
                this.isDemoRunning = false;
                this.episodeDone = true;
                this.stopAutoPlay();
                this.showEpisodeComplete(state);
                this.setStatus('Demo complete', 'inactive');
            }

        } catch (err) {
            console.error(err);
        } finally {
            btn.disabled = false;
        }
    }

    toggleAutoPlay() {
        if (this.autoPlayInterval) {
            this.stopAutoPlay();
        } else {
            this.startAutoPlay();
        }
    }

    startAutoPlay() {
        const btn = document.getElementById('autoPlayBtn');
        btn.innerHTML = '<span>⏸️</span> Pause';
        this.autoPlayInterval = setInterval(() => {
            if (!this.isDemoRunning || this.episodeDone) {
                this.stopAutoPlay();
                return;
            }
            this.demoNextStep();
        }, this.autoPlaySpeed);
    }

    stopAutoPlay() {
        if (this.autoPlayInterval) {
            clearInterval(this.autoPlayInterval);
            this.autoPlayInterval = null;
        }
        const btn = document.getElementById('autoPlayBtn');
        if (btn) btn.innerHTML = '<span>▶️</span> Auto Play';
    }

    stopDemo() {
        this.isDemoRunning = false;
        this.stopAutoPlay();
        document.getElementById('reasoningPanel').classList.add('hidden');
        document.getElementById('demoControls').classList.add('hidden');
    }

    // ── UI Updates ─────────────────────────────────────────────────────

    updateBriefing(obs, data) {
        document.getElementById('designIdBadge').textContent = obs.design_id || '—';
        document.getElementById('briefDomain').textContent = DOMAIN_LABELS[obs.design_domain] || obs.design_domain || '—';
        document.getElementById('briefDifficulty').textContent = (obs.design_difficulty || '—').toUpperCase();
        document.getElementById('briefSummary').textContent = obs.design_summary || '—';
        document.getElementById('briefRequirements').textContent = obs.design_requirements || '—';

        const stdContainer = document.getElementById('briefStandards');
        stdContainer.innerHTML = '';
        const standards = data?.state?.flaw_manifest ? [] : [];
        // Extract standards from summary text
        const stdMatches = (obs.step_feedback || '').match(/Standards: (.+)/);
        if (stdMatches) {
            stdMatches[1].split(', ').forEach(s => {
                const tag = document.createElement('span');
                tag.className = 'standard-tag';
                tag.textContent = s;
                stdContainer.appendChild(tag);
            });
        } else {
            ['AISC 360-22', 'ASME BPVC VIII-1', 'AGMA 2001-D04', 'ASCE 7-22'].forEach(s => {
                if (obs.design_summary && (obs.design_summary.includes('AISC') && s.includes('AISC')) ||
                    (obs.design_summary && obs.design_summary.includes('ASME') && s.includes('ASME')) ||
                    (obs.design_summary && obs.design_summary.includes('AGMA') && s.includes('AGMA'))) {
                    const tag = document.createElement('span');
                    tag.className = 'standard-tag';
                    tag.textContent = s;
                    stdContainer.appendChild(tag);
                }
            });
            // Fallback: show all relevant based on domain
            if (stdContainer.children.length === 0) {
                const domainStds = {
                    bridge_truss: ['AISC 360-22', 'AWS D1.1', 'AASHTO LRFD'],
                    pressure_vessel: ['ASME BPVC VIII-1', 'ASME B16.5', 'ASME B31.3'],
                    gear_assembly: ['AGMA 2001-D04', 'ISO 6336', 'ISO 281'],
                    building_frame: ['AISC 360-22', 'AISC 341-22', 'ASCE 7-22', 'IBC 2021'],
                };
                (domainStds[this.domain] || []).forEach(s => {
                    const tag = document.createElement('span');
                    tag.className = 'standard-tag';
                    tag.textContent = s;
                    stdContainer.appendChild(tag);
                });
            }
        }
    }

    renderComponents() {
        const grid = document.getElementById('componentsGrid');
        grid.innerHTML = '';
        const compIds = Object.keys(this.components);
        document.getElementById('compCount').textContent = `${compIds.length} total`;

        compIds.forEach((cid, i) => {
            const comp = this.components[cid];
            const ct = comp.component_type || 'default';
            const icon = COMP_ICONS[ct] || COMP_ICONS.default;
            const isInspected = this.inspectedComponents.includes(cid);
            const isFlagged = this.flaggedComponents.includes(cid);

            const card = document.createElement('div');
            card.className = `component-card${isInspected ? ' inspected' : ''}${isFlagged ? ' flagged' : ''}`;
            card.style.animationDelay = `${i * 0.03}s`;
            card.classList.add('animate-in');
            card.innerHTML = `
                <div class="comp-status">${isInspected ? '✅' : ''}${isFlagged ? '🚩' : ''}</div>
                <div class="comp-icon">${icon}</div>
                <div class="comp-name">${comp.name || cid}</div>
                <div class="comp-type">${ct}</div>
            `;
            card.addEventListener('click', () => {
                if (!this.episodeDone && !this.isDemoRunning) {
                    this.executeStep({ action_type: 'inspect', component_id: cid });
                }
            });
            grid.appendChild(card);
        });
    }

    showInspection(compId, component, context) {
        this.selectedComponent = compId;
        const panel = document.getElementById('inspectionPanel');
        panel.classList.remove('hidden');

        document.getElementById('inspCompName').textContent = component.name || compId;

        const grid = document.getElementById('paramsGrid');
        grid.innerHTML = '';

        Object.entries(component).forEach(([key, value]) => {
            if (key === 'component_type' || key === 'name') return;
            const item = document.createElement('div');
            item.className = 'param-item';
            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const displayVal = typeof value === 'number' ? (Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2)) : value;
            item.innerHTML = `
                <div class="param-key">${displayKey}</div>
                <div class="param-value">${displayVal}</div>
            `;
            grid.appendChild(item);
        });

        // Scroll to inspection panel
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    showAnalysis(results) {
        const panel = document.getElementById('analysisPanel');
        panel.classList.remove('hidden');

        const status = results.status || 'N/A';
        const statusEl = document.getElementById('analysisStatus');
        statusEl.textContent = status;
        statusEl.className = 'analysis-status ' + status.toLowerCase();

        const content = document.getElementById('analysisContent');
        content.innerHTML = '';

        // Safety factor gauge
        const sf = results.safety_factor;
        if (sf !== undefined) {
            const sfPercent = Math.min(100, (sf / 3) * 100);
            const sfClass = sf >= 1.5 ? 'pass' : sf >= 1.0 ? 'marginal' : 'fail';
            const gaugeHtml = `
                <div style="margin-bottom: 1rem;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:0.3rem;">
                        <span style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Safety Factor</span>
                        <span class="mono" style="font-size:0.85rem; font-weight:700; color:${sfClass === 'pass' ? 'var(--accent-emerald)' : sfClass === 'marginal' ? 'var(--accent-amber)' : 'var(--accent-red)'};">${sf.toFixed(3)}</span>
                    </div>
                    <div class="sf-gauge">
                        <div class="sf-gauge-fill ${sfClass}" style="width:${sfPercent}%"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.6rem; color:var(--text-muted);">
                        <span>0.0</span><span>Min: 1.5</span><span>3.0+</span>
                    </div>
                </div>
            `;
            content.innerHTML += gaugeHtml;
        }

        // Analysis parameters
        const paramsHtml = Object.entries(results)
            .filter(([k]) => !['status', 'safety_factor', 'analysis', 'formula', 'unit', 'error'].includes(k))
            .map(([key, value]) => {
                const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const displayVal = typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 3 }) : String(value);
                return `<div class="param-item"><div class="param-key">${displayKey}</div><div class="param-value">${displayVal}</div></div>`;
            }).join('');

        content.innerHTML += `<div class="params-grid">${paramsHtml}</div>`;

        if (results.formula) {
            content.innerHTML += `
                <div style="margin-top:0.75rem; padding:0.5rem 0.75rem; background:rgba(99,102,241,0.06); border-radius:var(--radius-sm); border:1px solid rgba(99,102,241,0.1);">
                    <span style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Formula</span>
                    <div class="mono" style="font-size:0.8rem; color:var(--accent-indigo); margin-top:0.2rem;">${results.formula}</div>
                </div>
            `;
        }

        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    updateMetrics(state) {
        if (!state) return;

        document.getElementById('stepsUsed').textContent = state.steps_taken || 0;
        document.getElementById('stepsLeft').textContent = state.max_steps ? (state.max_steps - (state.steps_taken || 0)) : '—';
        document.getElementById('flawsFound').textContent = `${state.flaws_correctly_found || 0}/${state.total_flaws_planted || 0}`;

        const reward = state.total_reward || 0;
        const rewardEl = document.getElementById('totalReward');
        rewardEl.textContent = reward.toFixed(1);
        rewardEl.className = 'step-stat-value ' + (reward >= 0 ? 'positive' : 'negative');

        // Update score
        const score = state.composite_score || 0;
        this.updateScoreCircle(score);

        // Live dimension updates from state fields
        if (state.detection_precision !== undefined) {
            this.setDimension('precision', state.detection_precision);
        }
        if (state.detection_recall !== undefined) {
            this.setDimension('recall', state.detection_recall);
        }
        if (state.severity_accuracy !== undefined) {
            this.setDimension('severity', state.severity_accuracy);
        }
        // Efficiency
        if (state.efficiency_score !== undefined && state.efficiency_score > 0) {
            this.setDimension('efficiency', state.efficiency_score);
        } else if (state.steps_taken > 0 && state.total_flaws_planted > 0) {
            const optimal = state.total_flaws_planted * 2;
            const eff = Math.min(100, (optimal / Math.max(state.steps_taken, 1)) * 100);
            this.setDimension('efficiency', eff);
        }
        // Reasoning quality
        if (state.reasoning_quality !== undefined && state.reasoning_quality > 0) {
            this.setDimension('reasoning', state.reasoning_quality);
        }
        // Ethical safety
        if (state.ethical_score !== undefined && state.ethical_score > 0 && state.ethical_score <= 1.0) {
            this.setDimension('ethical', state.ethical_score * 100);
        } else if (state.total_flaws_planted > 0) {
            const missed = state.total_flaws_planted - (state.flaws_correctly_found || 0);
            const ethical = (1.0 - missed / state.total_flaws_planted) * 100;
            this.setDimension('ethical', Math.max(0, ethical));
        }

        // Update episode summary dimensions if available
        if (state.episode_summary) {
            this.updateDimensions(state.episode_summary);
        }
    }

    setDimension(shortName, value) {
        const el = document.getElementById(`dim_${shortName}`);
        const bar = document.getElementById(`dimBar_${shortName}`);
        if (el) el.textContent = `${Math.round(value)}%`;
        if (bar) bar.style.width = `${Math.min(100, value)}%`;
    }

    updateScoreCircle(score) {
        const ring = document.getElementById('scoreRing');
        const circumference = 2 * Math.PI * 65; // 408.4
        const offset = circumference - (score / 100) * circumference;
        ring.style.strokeDashoffset = offset;

        const num = document.getElementById('scoreNumber');
        num.textContent = Math.round(score);
    }

    updateDimensions(summary) {
        if (!summary || !summary.dimensions) return;

        const dims = summary.dimensions;

        const mapping = {
            detection_precision: { score: 'dim_precision', bar: 'dimBar_precision' },
            detection_recall: { score: 'dim_recall', bar: 'dimBar_recall' },
            severity_accuracy: { score: 'dim_severity', bar: 'dimBar_severity' },
            efficiency: { score: 'dim_efficiency', bar: 'dimBar_efficiency' },
            reasoning_quality: { score: 'dim_reasoning', bar: 'dimBar_reasoning' },
            ethical_safety: { score: 'dim_ethical', bar: 'dimBar_ethical' },
        };

        Object.entries(dims).forEach(([key, info]) => {
            const m = mapping[key];
            if (m) {
                const el = document.getElementById(m.score);
                const bar = document.getElementById(m.bar);
                if (el) el.textContent = `${info.score}%`;
                if (bar) bar.style.width = `${info.score}%`;
            }
        });
    }

    resetDimensions() {
        ['precision', 'recall', 'severity', 'efficiency', 'reasoning', 'ethical'].forEach(d => {
            const el = document.getElementById(`dim_${d}`);
            const bar = document.getElementById(`dimBar_${d}`);
            if (el) el.textContent = '0%';
            if (bar) bar.style.width = '0%';
        });
        this.updateScoreCircle(0);
    }

    showEpisodeComplete(state) {
        const banner = document.getElementById('episodeBanner');
        banner.classList.remove('hidden');

        const score = state.composite_score || 0;
        const scoreEl = document.getElementById('finalScore');
        scoreEl.className = 'final-score ' + (score >= 80 ? 'excellent' : score >= 60 ? 'good' : score >= 40 ? 'average' : 'poor');

        // Animated score counter
        let currentScore = 0;
        const targetScore = Math.round(score);
        const increment = Math.max(1, Math.floor(targetScore / 30));
        const counter = setInterval(() => {
            currentScore = Math.min(currentScore + increment, targetScore);
            scoreEl.textContent = currentScore;
            if (currentScore >= targetScore) {
                clearInterval(counter);
                scoreEl.textContent = targetScore;
            }
        }, 30);

        const decision = state.final_decision || 'timeout';
        const flawsFound = state.flaws_correctly_found || 0;
        const totalFlaws = state.total_flaws_planted || 0;
        const fpCount = state.false_positives || 0;
        document.getElementById('finalDecision').textContent =
            `Decision: ${decision.toUpperCase()} | Flaws: ${flawsFound}/${totalFlaws} found | FP: ${fpCount} | Steps: ${state.steps_taken}/${state.max_steps}`;

        // Update dimensions from episode_summary
        if (state.episode_summary) {
            this.updateDimensions(state.episode_summary);
        }

        this.updateScoreCircle(score);

        // Scroll banner into view
        setTimeout(() => {
            banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 200);

        // Add final transcript entry
        const scoreEmoji = score >= 80 ? '🏆' : score >= 60 ? '✅' : score >= 40 ? '⚡' : '❌';
        this.addTranscript(
            score >= 60 ? 'correct' : score >= 40 ? 'warning' : 'incorrect',
            `${scoreEmoji} FINAL`,
            `Score: ${targetScore}/100 | ${decision.toUpperCase()} | ${flawsFound}/${totalFlaws} flaws`
        );

        // Disable buttons
        document.getElementById('runDemoBtn').disabled = false;
        document.getElementById('nextStepBtn').disabled = true;
        document.getElementById('autoPlayBtn').disabled = true;
    }

    // ── Modals ─────────────────────────────────────────────────────────

    openInspectModal() {
        const sel = document.getElementById('inspectComponent');
        sel.innerHTML = '';
        Object.keys(this.components).forEach(cid => {
            const opt = document.createElement('option');
            opt.value = cid;
            opt.textContent = `${this.components[cid].name || cid} (${this.components[cid].component_type || ''})`;
            sel.appendChild(opt);
        });
        document.getElementById('inspectModal').classList.remove('hidden');
    }

    submitInspect() {
        const cid = document.getElementById('inspectComponent').value;
        document.getElementById('inspectModal').classList.add('hidden');
        this.executeStep({ action_type: 'inspect', component_id: cid });
    }

    openFlagModal() {
        if (this.episodeDone) return;
        const sel = document.getElementById('flagComponent');
        sel.innerHTML = '';
        Object.keys(this.components).forEach(cid => {
            const opt = document.createElement('option');
            opt.value = cid;
            opt.textContent = this.components[cid].name || cid;
            if (cid === this.selectedComponent) opt.selected = true;
            sel.appendChild(opt);
        });
        document.getElementById('flagModal').classList.remove('hidden');
    }

    closeFlagModal() {
        document.getElementById('flagModal').classList.add('hidden');
    }

    async submitFlag() {
        const data = {
            action_type: 'flag_issue',
            component_id: document.getElementById('flagComponent').value,
            issue_type: document.getElementById('flagIssueType').value,
            severity: document.getElementById('flagSeverity').value,
            standard_reference: document.getElementById('flagStandard').value,
            justification: document.getElementById('flagJustification').value,
        };
        this.closeFlagModal();
        await this.executeStep(data);
    }

    openAnalysisModal() {
        const sel = document.getElementById('analysisComponent');
        sel.innerHTML = '';
        Object.keys(this.components).forEach(cid => {
            const opt = document.createElement('option');
            opt.value = cid;
            opt.textContent = this.components[cid].name || cid;
            if (cid === this.selectedComponent) opt.selected = true;
            sel.appendChild(opt);
        });
        document.getElementById('analysisModal').classList.remove('hidden');
    }

    closeAnalysisModal() {
        document.getElementById('analysisModal').classList.add('hidden');
    }

    async submitAnalysis() {
        const data = {
            action_type: 'request_analysis',
            component_id: document.getElementById('analysisComponent').value,
            analysis_type: document.getElementById('analysisType').value,
        };
        this.closeAnalysisModal();
        await this.executeStep(data);
    }

    // ── Helpers ─────────────────────────────────────────────────────────

    showFeedback(text) {
        const bar = document.getElementById('feedbackBar');
        if (!text) {
            bar.classList.add('hidden');
            return;
        }
        bar.classList.remove('hidden');
        bar.textContent = text;
    }

    setStatus(text, type = 'active') {
        document.getElementById('statusText').textContent = text;
        const dot = document.getElementById('statusDot');
        dot.className = 'status-dot';
        if (type === 'inactive') dot.classList.add('inactive');
        if (type === 'running') dot.classList.add('running');
    }

    enableActions(enabled) {
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.disabled = !enabled;
        });
    }

    clearTranscript() {
        document.getElementById('transcriptFeed').innerHTML = '';
        this.transcriptItems = [];
    }

    addTranscript(type, step, text) {
        const feed = document.getElementById('transcriptFeed');
        const item = document.createElement('div');
        item.className = `transcript-item ${type}`;
        item.innerHTML = `
            <div class="transcript-step">${step}</div>
            <div class="transcript-text">${text}</div>
        `;
        feed.appendChild(item);
        feed.scrollTop = feed.scrollHeight;
        this.transcriptItems.push({ type, step, text });
    }
}

// ── Initialize ──────────────────────────────────────────────────────────

const app = new DesignReviewApp();
