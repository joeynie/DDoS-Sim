/**
 * NetShield 防御监控中心
 * 前端控制逻辑
 */

// ===== 全局状态 =====
const state = {
    refreshInterval: 2000,
    refreshTimer: null,
    isConnected: false,
    charts: {},
    // 历史数据 - 存储增量值用于图表
    history: {
        tp: [],
        fp: [],
        tn: [],
        fn: [],
        labels: []
    },
    // 上一次的累计值，用于计算增量
    prevTotal: null,
    maxDataPoints: 30
};

// ===== API 请求封装 =====
const api = {
    baseUrl: '',

    async get(endpoint) {
        try {
            const res = await fetch(`${this.baseUrl}${endpoint}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        } catch (err) {
            console.error(`API GET ${endpoint} failed:`, err);
            throw err;
        }
    },

    async post(endpoint, data = {}) {
        try {
            const res = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        } catch (err) {
            console.error(`API POST ${endpoint} failed:`, err);
            throw err;
        }
    }
};

// ===== UI 工具函数 =====
function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function showToast(message, type = 'info') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function updateRing(elementId, value) {
    const ring = $(`#${elementId}`);
    if (!ring) return;
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (value * circumference);
    ring.style.strokeDashoffset = offset;
}

// ===== 导航切换 =====
function initNavigation() {
    const navItems = $$('.nav-item');
    const sections = $$('.content-section');
    const pageTitle = $('#page-title');
    
    const titles = {
        'overview': '系统总览',
        'rules': '规则配置',
        'traffic': '流量监控',
        'blacklist': '黑名单管理'
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const section = item.dataset.section;
            
            // 更新导航状态
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            // 切换内容区
            sections.forEach(s => s.classList.remove('active'));
            $(`#section-${section}`).classList.add('active');
            
            // 更新标题
            pageTitle.textContent = titles[section] || '系统总览';
            
            // 切换到流量监控时更新图表
            if (section === 'traffic') {
                updateTrafficCharts();
            }
        });
    });
}

// ===== 刷新控制 =====
function initRefreshControl() {
    const select = $('#refresh-interval');
    const btnRefresh = $('#btn-refresh');
    
    select.addEventListener('change', () => {
        state.refreshInterval = parseInt(select.value);
        startAutoRefresh();
    });
    
    btnRefresh.addEventListener('click', () => {
        fetchAndUpdateStats();
        showToast('数据已刷新', 'success');
    });
    
    startAutoRefresh();
}

function startAutoRefresh() {
    if (state.refreshTimer) {
        clearInterval(state.refreshTimer);
    }
    
    if (state.refreshInterval > 0) {
        state.refreshTimer = setInterval(fetchAndUpdateStats, state.refreshInterval);
    }
}

// ===== 数据获取与更新 =====
async function fetchAndUpdateStats() {
    try {
        const res = await api.get('/api/stats');
        if (res.success) {
            updateStats(res.stats);
            updateConnectionStatus(true);
        }
    } catch (err) {
        updateConnectionStatus(false);
    }
    
    // 同时获取最新参数，确保RL更新的参数也能显示
    try {
        const paramsRes = await api.get('/api/params');
        if (paramsRes.success) {
            updateParamInputs(paramsRes.params);
        }
    } catch (err) {
        console.warn('Failed to sync params:', err);
    }
}

function updateStats(stats) {
    const counters = stats.counters || {};
    const metrics = stats.metrics || {};
    
    // 获取当前累计值
    const tp = counters.tp_count || 0;
    const fp = counters.fp_count || 0;
    const tn = counters.tn_count || 0;
    const fn = counters.fn_count || 0;
    
    // 计算2秒内的增量
    let deltaTp = 0, deltaFp = 0, deltaTn = 0, deltaFn = 0;
    if (state.prevTotal) {
        deltaTp = Math.max(0, tp - state.prevTotal.tp);
        deltaFp = Math.max(0, fp - state.prevTotal.fp);
        deltaTn = Math.max(0, tn - state.prevTotal.tn);
        deltaFn = Math.max(0, fn - state.prevTotal.fn);
    }
    state.prevTotal = { tp, fp, tn, fn };
    
    // 更新统计卡片 - 显示实时增量 / 累计总量
    updateStatCard('tp', deltaTp, tp);
    updateStatCard('fp', deltaFp, fp);
    updateStatCard('tn', deltaTn, tn);
    updateStatCard('fn', deltaFn, fn);
    
    // 更新指标环
    const precision = metrics.precision || 0;
    const recall = metrics.recall || 0;
    const f1 = metrics.f1_score || 0;
    
    $('#metric-precision').textContent = (precision * 100).toFixed(1) + '%';
    $('#metric-recall').textContent = (recall * 100).toFixed(1) + '%';
    $('#metric-f1').textContent = (f1 * 100).toFixed(1) + '%';
    
    updateRing('ring-precision', precision);
    updateRing('ring-recall', recall);
    updateRing('ring-f1', f1);
    
    // 更新历史数据 - 使用增量值
    const now = new Date();
    const timeLabel = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    state.history.labels.push(timeLabel);
    state.history.tp.push(deltaTp);
    state.history.fp.push(deltaFp);
    state.history.tn.push(deltaTn);
    state.history.fn.push(deltaFn);
    
    // 保持最大数据点
    if (state.history.labels.length > state.maxDataPoints) {
        state.history.labels.shift();
        state.history.tp.shift();
        state.history.fp.shift();
        state.history.tn.shift();
        state.history.fn.shift();
    }
    
    // 更新图表
    updateOverviewChart();
    
    // 更新流量表格 - 显示增量和累计
    updateTableRow('tp', deltaTp, tp);
    updateTableRow('fp', deltaFp, fp);
    updateTableRow('tn', deltaTn, tn);
    updateTableRow('fn', deltaFn, fn);
}

// 更新统计卡片显示
function updateStatCard(type, delta, total) {
    const statEl = $(`#stat-${type}`);
    const trendEl = $(`#trend-${type}`);
    
    if (statEl) {
        // 主数字显示实时增量
        statEl.innerHTML = `${formatNumber(delta)}<span class="stat-total">/ ${formatNumber(total)}</span>`;
    }
    
    if (trendEl) {
        // 趋势显示每秒速率
        const rate = delta / (state.refreshInterval / 1000);
        trendEl.textContent = `${formatNumber(Math.round(rate))}/s`;
        trendEl.style.color = delta > 0 ? '#10b981' : '#64748b';
    }
}

// 更新表格行
function updateTableRow(type, delta, total) {
    const cell = $(`#table-${type}`);
    if (cell) {
        cell.innerHTML = `<span class="table-delta">${formatNumber(delta)}</span> <span class="table-total">/ ${formatNumber(total)}</span>`;
    }
}

function updateTrend(elementId, diff) {
    const el = $(`#${elementId}`);
    if (!el) return;
    
    if (diff > 0) {
        el.textContent = `+${formatNumber(diff)}`;
        el.style.color = '#10b981';
    } else if (diff < 0) {
        el.textContent = formatNumber(diff);
        el.style.color = '#ef4444';
    } else {
        el.textContent = '—';
        el.style.color = '#64748b';
    }
}

function updateConnectionStatus(connected) {
    state.isConnected = connected;
    const statusDot = $('.status-dot');
    const statusText = $('#connection-status');
    
    if (connected) {
        statusDot.classList.add('connected');
        statusText.textContent = '已连接';
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = '连接断开';
    }
}

// ===== 图表初始化 =====
function initCharts() {
    // 总览页面图表
    const overviewCtx = $('#overview-chart');
    if (overviewCtx) {
        state.charts.overview = new Chart(overviewCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'TP',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'FP',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'TN',
                        data: [],
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'FN',
                        data: [],
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(45, 58, 79, 0.5)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        grid: { color: 'rgba(45, 58, 79, 0.5)' },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    }

    // 流量监控 - 饼图
    const pieCtx = $('#traffic-pie-chart');
    if (pieCtx) {
        state.charts.pie = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['真阳性(TP)', '假阳性(FP)', '真阴性(TN)', '假阴性(FN)'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#10b981', '#f59e0b', '#06b6d4', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8' }
                    }
                },
                cutout: '60%'
            }
        });
    }

    // 流量监控 - 时序图
    const lineCtx = $('#traffic-line-chart');
    if (lineCtx) {
        state.charts.trafficLine = new Chart(lineCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '拦截',
                        data: [],
                        backgroundColor: 'rgba(239, 68, 68, 0.7)'
                    },
                    {
                        label: '放行',
                        data: [],
                        backgroundColor: 'rgba(16, 185, 129, 0.7)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#94a3b8' }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { color: 'rgba(45, 58, 79, 0.5)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        stacked: true,
                        grid: { color: 'rgba(45, 58, 79, 0.5)' },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    }
}

function updateOverviewChart() {
    if (!state.charts.overview) return;
    
    const chart = state.charts.overview;
    chart.data.labels = state.history.labels;
    chart.data.datasets[0].data = state.history.tp;
    chart.data.datasets[1].data = state.history.fp;
    chart.data.datasets[2].data = state.history.tn;
    chart.data.datasets[3].data = state.history.fn;
    chart.update('none');
}

function updateTrafficCharts() {
    const h = state.history;
    
    // 更新饼图
    if (state.charts.pie && h.tp.length > 0) {
        const lastIdx = h.tp.length - 1;
        state.charts.pie.data.datasets[0].data = [
            h.tp[lastIdx], h.fp[lastIdx], h.tn[lastIdx], h.fn[lastIdx]
        ];
        state.charts.pie.update();
    }
    
    // 更新堆叠柱状图
    if (state.charts.trafficLine) {
        const blocked = h.tp.map((tp, i) => tp + h.fp[i]);
        const passed = h.tn.map((tn, i) => tn + h.fn[i]);
        
        state.charts.trafficLine.data.labels = h.labels;
        state.charts.trafficLine.data.datasets[0].data = blocked;
        state.charts.trafficLine.data.datasets[1].data = passed;
        state.charts.trafficLine.update();
    }
}

// ===== 规则配置 =====
async function initRulesConfig() {
    // 获取初始参数
    try {
        const res = await api.get('/api/params');
        if (res.success) {
            updateParamInputs(res.params);
        }
    } catch (err) {
        console.error('Failed to load params:', err);
    }
    
    // 绑定滑块和输入框同步
    const params = ['global_limit', 'single_ip_limit', 'conn_limit', 'ban_threshold'];
    params.forEach(param => {
        const slider = $(`#param-${param}`);
        const input = $(`#input-${param}`);
        
        if (slider && input) {
            slider.addEventListener('input', () => {
                input.value = slider.value;
            });
            
            input.addEventListener('change', () => {
                let val = parseInt(input.value);
                val = Math.max(slider.min, Math.min(slider.max, val));
                input.value = val;
                slider.value = val;
            });
        }
    });
    
    // 应用规则按钮
    $('#btn-apply-rules')?.addEventListener('click', async () => {
        const params = {
            global_limit: parseInt($('#input-global_limit').value),
            single_ip_limit: parseInt($('#input-single_ip_limit').value),
            conn_limit: parseInt($('#input-conn_limit').value),
            ban_threshold: parseInt($('#input-ban_threshold').value)
        };
        
        try {
            const res = await api.post('/api/rl/action', { actions: params });
            if (res.success) {
                // 应用成功后，立即刷新参数显示
                if (res.new_state) {
                    updateParamInputs(res.new_state);
                }
                showToast('规则已成功应用', 'success');
            } else {
                showToast('规则应用失败: ' + res.message, 'error');
            }
        } catch (err) {
            showToast('请求失败', 'error');
        }
    });
    
    // 重置按钮
    $('#btn-reset-rules')?.addEventListener('click', async () => {
        try {
            const res = await api.post('/api/rl/reset');
            if (res.success) {
                updateParamInputs(res.params);
                showToast('已重置为默认参数', 'success');
            }
        } catch (err) {
            showToast('重置失败', 'error');
        }
    });
    
    // 预览规则
    $('#btn-preview-rules')?.addEventListener('click', async () => {
        try {
            const res = await api.get('/api/rules/generate');
            if (res.success) {
                $('#rules-code code').textContent = res.rules;
            }
        } catch (err) {
            showToast('获取规则预览失败', 'error');
        }
    });
}

function updateParamInputs(params) {
    Object.entries(params).forEach(([key, value]) => {
        if (key === 'PARAM_RANGES') return;
        
        const slider = $(`#param-${key}`);
        const input = $(`#input-${key}`);
        
        if (slider) slider.value = value;
        if (input) input.value = value;
    });
}

// ===== 黑名单管理 =====
function initBlacklist() {
    // 添加黑名单
    $('#btn-add-blacklist')?.addEventListener('click', async () => {
        const ip = $('#blacklist-ip').value.trim();
        const timeout = parseInt($('#blacklist-timeout').value) || 300;
        
        if (!ip) {
            showToast('请输入IP地址', 'warning');
            return;
        }
        
        try {
            const res = await api.post('/api/blacklist/add', { ip, timeout });
            if (res.success) {
                showToast(res.message, 'success');
                $('#blacklist-ip').value = '';
                fetchBlacklistStats();
            } else {
                showToast(res.message, 'error');
            }
        } catch (err) {
            showToast('添加失败', 'error');
        }
    });
    
    // 添加白名单
    $('#btn-add-whitelist')?.addEventListener('click', async () => {
        const ip = $('#whitelist-ip').value.trim();
        
        if (!ip) {
            showToast('请输入IP地址', 'warning');
            return;
        }
        
        try {
            const res = await api.post('/api/whitelist/add', { ip });
            if (res.success) {
                showToast(res.message, 'success');
                $('#whitelist-ip').value = '';
            } else {
                showToast(res.message, 'error');
            }
        } catch (err) {
            showToast('添加失败', 'error');
        }
    });
    
    fetchBlacklistStats();
}

async function fetchBlacklistStats() {
    try {
        const res = await api.get('/api/blacklist');
        if (res.success) {
            const count = res.blacklist?.count || 0;
            $('#blacklist-count').textContent = count;
        }
    } catch (err) {
        console.error('Failed to fetch blacklist stats:', err);
    }
}

// ===== 图表图例切换 =====
function initChartLegendToggle() {
    const legendItems = $$('.chart-legend .legend-item.clickable');
    
    legendItems.forEach(item => {
        item.addEventListener('click', () => {
            const datasetIndex = parseInt(item.dataset.dataset);
            const chart = state.charts.overview;
            
            if (!chart) return;
            
            // 切换数据集的可见性
            const meta = chart.getDatasetMeta(datasetIndex);
            meta.hidden = !meta.hidden;
            
            // 更新图例项的视觉状态
            item.classList.toggle('disabled');
            
            // 更新图表
            chart.update();
        });
    });
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initRefreshControl();
    initCharts();
    initChartLegendToggle();
    initRulesConfig();
    initBlacklist();
    
    // 首次加载数据
    fetchAndUpdateStats();
    
    console.log('NetShield 防御监控中心已启动');
});
