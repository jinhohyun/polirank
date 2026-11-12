/**
 * PoliRank MVP - 프론트엔드 인터랙션 & 데이터 연동 스크립트 (6대 정량 지표 & 3D 플립 & 재미요소)
 */

// Global State
const PAGE_SIZE = 36;
let currentLang = localStorage.getItem('polirank_lang') || 'ko';
let allMembers = [];
let filteredMembers = [];

function toggleLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('polirank_lang', lang);
    const select = document.getElementById('lang-select');
    if (select) select.value = lang;
    filterAndRenderMembers();
}

document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('lang-select');
    if (select) select.value = currentLang;
});
let displayedCount = PAGE_SIZE;
let renderedCount = 0;
let showAllMode = false;
let currentSort = 'total';
let currentParty = 'all';
let searchQuery = '';
let currentMember = null;
let radarChartInstance = null;
let isModalPhotoView = false;
const CHEER_STORAGE_KEY = 'polirank_cheered_members';
let cheeredSet = new Set();
const cheerInFlight = new Set();
let officeSession = { authenticated: false, username: null, role: null, member_id: null, office_name: null };

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// DOM Elements
const membersGrid = document.getElementById('members-grid');
const filterResultCount = document.getElementById('filter-result-count');
const displayShowingCount = document.getElementById('display-showing-count');
const loadMoreContainer = document.getElementById('load-more-container');
const btnLoadMore = document.getElementById('btn-load-more');
const btnLoadMoreText = document.getElementById('btn-load-more-text');
const btnShowAllText = document.getElementById('btn-show-all-text');
const currentRankLabel = document.getElementById('current-rank-label');
const searchInput = document.getElementById('member-search');
const detailModal = document.getElementById('detail-modal');
const toastContainer = document.getElementById('toast-container');

// Sort Labels (v3.1 Core 6 Axes + Fun 4 Modes)
const FUN_SORT_KEYS = new Set(['fandom', 'controversy', 'hidden_gem', 'cheer']);

const SORT_LABELS = {
    total: '종합 랭킹 기준 정렬 중 (입법품질 30% · 표결 20% · 발의 15% · 협치 15% · 직무 12% · 소통 8%)',
    passed: '🎯 입법 성과·품질 순 정렬 중 (가결/대안반영 실적 70% + 입법 타율 30%)',
    voting: '🗳️ 본회의 표결·참여 순 정렬 중 (전자표결 참여율 + 찬·반 적극 의사표시)',
    legislation: '📜 입법 발의·협업 순 정렬 중 (대표발의 총건수 + 동료 법안 공동발의 참여수)',
    bipartisan: '🤝 초당적 협치·연대 순 정렬 중 (타 정당 공동발의 비율 + 평균 설득 인원)',
    committee: '⚖️ 위원회 직무·성실 순 정렬 중 (겸임 상임위·특위 참여 + 직책 + 성실도)',
    policy: '🎙️ 정책 소통·다양성 순 정렬 중 (발의 분야 다양성 + 상임위 발언 + 정책 활동)',
    fandom: '🎭 [재미·화제성] ❤️ 인기·팬덤 지수 순 (응원·긍정댓글·30일 뉴스 화제성 — 종합점수 미반영)',
    controversy: '🎭 [재미·화제성] 🔥 논란·핫이슈 온도 순 (쟁점뉴스·찬반표결·분발댓글 — 종합점수 미반영)',
    hidden_gem: '🎭 [재미·화제성] 💎 흙속의 진주 순 (고득점 의정실력 대비 낮은 뉴스 노출 — 종합점수 미반영)',
    cheer: '🎭 [재미·화제성] 💖 시민 실시간 응원순 (종합점수 미반영)'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadLocalCheers();
    loadSummaryStats();
    loadMyCheers();
    loadOfficeSession();
    loadMembers();
    setupEventListeners();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('polirank_theme');
    if (savedTheme === 'light') {
        document.documentElement.classList.remove('dark');
    } else {
        document.documentElement.classList.add('dark');
    }

    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('polirank_theme', isDark ? 'dark' : 'light');
            if (radarChartInstance && currentMember) {
                renderRadarChart(currentMember);
            }
        });
    }
}

// Fetch Header Live Summary Stats & Party Seat Counts
async function loadSummaryStats() {
    try {
        const res = await fetch('/api/stats/summary');
        const data = await res.json();
        if (data) {
            const cheerElem = document.getElementById('header-cheer-count');
            if (cheerElem) cheerElem.textContent = `${data.total_cheers.toLocaleString()}회`;
            const memElem = document.getElementById('header-member-count');
            if (memElem) memElem.textContent = `${data.total_members}명`;
            const updElem = document.getElementById('header-last-updated');
            if (updElem && data.last_updated_at) {
                updElem.textContent = data.last_updated_at;
            }
            if (data.party_counts) {
                updatePartyCounts(data.party_counts);
            }
        }
    } catch (err) {
        console.error('Failed to load summary stats', err);
    }
}

// Update Party Filter Chip Seat Counts
function updatePartyCounts(partyCounts) {
    const chips = document.querySelectorAll('#party-filters .party-chip');
    chips.forEach(chip => {
        const partyKey = chip.dataset.party;
        const countSpan = chip.querySelector('.party-count');
        if (countSpan && partyCounts.hasOwnProperty(partyKey)) {
            countSpan.textContent = `(${partyCounts[partyKey]})`;
        } else if (countSpan && partyKey === '무소속/기타') {
            const etcCnt = partyCounts['무소속/기타'] ?? partyCounts['무소속'] ?? 0;
            countSpan.textContent = `(${etcCnt})`;
        }
    });
}

// Fetch Members List
async function loadMembers() {
    try {
        displayedCount = PAGE_SIZE;
        showAllMode = false;
        const url = `/api/members?sort_by=${currentSort}&party=${encodeURIComponent(currentParty)}`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.status === 'success') {
            allMembers = data.members;
            applyFiltersAndRender();
        }
    } catch (err) {
        console.error('Failed to load members', err);
        showToast('의원 데이터를 불러오는 중 오류가 발생했습니다.', 'error');
    }
}

// Update Sort Tab Active UI & Fun Banner
function updateSortTabStyles(activeSort) {
    const sortTabs = document.querySelectorAll('.sort-tab');
    sortTabs.forEach(t => {
        t.classList.remove(
            'active',
            'bg-sky-600',
            'bg-fuchsia-600',
            'text-white',
            'shadow-md',
            'shadow-sky-600/30',
            'shadow-fuchsia-600/30'
        );
        if (t.dataset.group === 'fun') {
            t.classList.add('bg-white/90', 'dark:bg-slate-900/70');
        } else {
            t.classList.add('bg-white', 'dark:bg-slate-800', 'text-slate-600', 'dark:text-slate-300');
        }
        if (t.dataset.sort === activeSort) {
            t.classList.add('active', 'text-white', 'shadow-md');
            if (t.dataset.group === 'fun') {
                t.classList.remove('bg-white/90', 'dark:bg-slate-900/70');
                t.classList.add('bg-fuchsia-600', 'shadow-fuchsia-600/30');
            } else {
                t.classList.remove('bg-white', 'dark:bg-slate-800', 'text-slate-600', 'dark:text-slate-300');
                t.classList.add('bg-sky-600', 'shadow-sky-600/30');
            }
        }
    });

    const funBanner = document.getElementById('fun-mode-banner');
    if (funBanner) {
        if (FUN_SORT_KEYS.has(activeSort)) {
            funBanner.classList.remove('hidden');
        } else {
            funBanner.classList.add('hidden');
        }
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Sort Tabs
    const sortTabs = document.querySelectorAll('.sort-tab');
    sortTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            currentSort = tab.dataset.sort;
            updateSortTabStyles(currentSort);
            if (currentRankLabel) {
                currentRankLabel.textContent = SORT_LABELS[currentSort] || '';
            }
            loadMembers();
        });
    });

    // Party Filter Chips
    const partyChips = document.querySelectorAll('.party-chip');
    partyChips.forEach(chip => {
        chip.addEventListener('click', () => {
            partyChips.forEach(c => {
                c.classList.remove('active', 'bg-slate-900', 'text-white', 'dark:bg-white', 'dark:text-slate-900');
                c.classList.add('bg-slate-100', 'dark:bg-slate-800', 'text-slate-600', 'dark:text-slate-300');
            });
            chip.classList.add('active', 'bg-slate-900', 'text-white', 'dark:bg-white', 'dark:text-slate-900');
            chip.classList.remove('bg-slate-100', 'dark:bg-slate-800', 'text-slate-600', 'dark:text-slate-300');

            currentParty = chip.dataset.party;
            loadMembers();
        });
    });

    // Real-time Search Input (Member Name, District, Committee, Quote)
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            applyFiltersAndRender();
        });
    }

    // Modal ESC Key Close
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (detailModal && !detailModal.classList.contains('hidden')) {
                closeModal();
            }
            const methModal = document.getElementById('methodology-modal');
            if (methModal && !methModal.classList.contains('hidden')) {
                closeMethodologyModal();
            }
            const loginModal = document.getElementById('office-login-modal');
            if (loginModal && !loginModal.classList.contains('hidden')) {
                closeOfficeLoginModal();
            }
            const adminModal = document.getElementById('admin-issue-modal');
            if (adminModal && !adminModal.classList.contains('hidden')) {
                closeAdminIssueModal();
            }
            const devSupportModal = document.getElementById('dev-support-modal');
            if (devSupportModal && !devSupportModal.classList.contains('hidden')) {
                closeDevSupportModal();
            }
            const feedbackModal = document.getElementById('feedback-modal');
            if (feedbackModal && !feedbackModal.classList.contains('hidden')) {
                closeFeedbackModal();
            }
        }
    });
}

// Reset Filters to Default
function resetFilters() {
    currentSort = 'total';
    currentParty = 'all';
    searchQuery = '';
    if (searchInput) searchInput.value = '';
    updateSortTabStyles('total');
    if (currentRankLabel) {
        currentRankLabel.textContent = SORT_LABELS.total;
    }

    const partyChips = document.querySelectorAll('.party-chip');
    partyChips.forEach(c => {
        if (c.dataset.party === 'all') {
            c.classList.add('active', 'bg-slate-900', 'text-white', 'dark:bg-white', 'dark:text-slate-900');
            c.classList.remove('bg-slate-100', 'dark:bg-slate-800');
        } else {
            c.classList.remove('active', 'bg-slate-900', 'text-white', 'dark:bg-white', 'dark:text-slate-900');
            c.classList.add('bg-slate-100', 'dark:bg-slate-800');
        }
    });

    loadMembers();
}

// Filter and Render Cards
function applyFiltersAndRender() {
    if (!searchQuery) {
        filteredMembers = [...allMembers];
    } else {
        filteredMembers = allMembers.filter(m => {
            const kwMatch = Array.isArray(m.keywords) && m.keywords.some(k => k.toLowerCase().includes(searchQuery));
            return (
                m.name.toLowerCase().includes(searchQuery) ||
                (m.district && m.district.toLowerCase().includes(searchQuery)) ||
                (m.committee && m.committee.toLowerCase().includes(searchQuery)) ||
                (m.party && m.party.toLowerCase().includes(searchQuery)) ||
                (m.quote && m.quote.toLowerCase().includes(searchQuery)) ||
                kwMatch
            );
        });
    }

    if (filterResultCount) {
        filterResultCount.textContent = filteredMembers.length;
    }

    // 검색어가 있을 때는 매칭된 전체 결과 즉시 표시, 평상시에는 36명 단위 제어
    computeTiedRanks(filteredMembers);
    const limit = searchQuery || showAllMode
        ? filteredMembers.length
        : Math.min(displayedCount, filteredMembers.length);
    renderMemberCards(filteredMembers, limit);
}

// Helper: Get metric value for sorting & tied ranking
function getMemberStatValue(member, sortKey) {
    if (sortKey === 'passed') return member.passed_score || 0;
    if (sortKey === 'voting') return member.voting_score || 0;
    if (sortKey === 'legislation') return member.legislation_score || 0;
    if (sortKey === 'bipartisan') return member.bipartisan_score || 0;
    if (sortKey === 'committee' || sortKey === 'attendance') return member.committee_score ?? member.attendance_score ?? 0;
    if (sortKey === 'speech') return member.speech_count || 0;
    if (sortKey === 'policy') return member.policy_score || 0;
    if (sortKey === 'fandom') return member.fandom_score || 0;
    if (sortKey === 'controversy') return member.controversy_score || 0;
    if (sortKey === 'hidden_gem') return member.hidden_gem_score || 0;
    if (sortKey === 'cheer') return member.cheer_count || 0;
    return member.total_score || 0;
}

// Standard Competition Ranking (Tied Ranking: 공동순위 사전 계산)
function computeTiedRanks(members) {
    const scoreCounts = {};
    members.forEach(m => {
        const val = getMemberStatValue(m, currentSort);
        scoreCounts[val] = (scoreCounts[val] || 0) + 1;
    });

    let currentRank = 1;
    members.forEach((member, index) => {
        const curScore = getMemberStatValue(member, currentSort);
        if (index > 0) {
            const prevScore = getMemberStatValue(members[index - 1], currentSort);
            if (prevScore !== curScore) {
                currentRank = index + 1;
            }
        } else {
            currentRank = 1;
        }
        const isTied = scoreCounts[curScore] > 1;
        member.current_display_rank = currentRank;
        member.current_display_rank_text = isTied ? `공동 ${currentRank}위` : `${currentRank}위`;
        member.is_tied = isTied;
    });
}

// Render Member Card Elements (Initial Slice)
function renderMemberCards(members, limit) {
    if (!membersGrid) return;
    membersGrid.innerHTML = '';
    renderedCount = 0;

    if (members.length === 0) {
        membersGrid.innerHTML = `
            <div class="col-span-full py-16 text-center space-y-3">
                <i class="fa-solid fa-user-slash text-4xl text-slate-300 dark:text-slate-600"></i>
                <p class="text-sm font-semibold text-slate-500">조건에 맞는 국회의원이 없습니다.</p>
                <button onclick="resetFilters()" class="text-xs text-sky-600 dark:text-sky-400 font-bold underline">검색 초기화</button>
            </div>
        `;
        updateLoadMoreControls();
        return;
    }

    appendMemberCards(members, 0, limit);
    updateLoadMoreControls();
}

// Append a range of member cards efficiently
function appendMemberCards(members, startIdx, endIdx) {
    const fragment = document.createDocumentFragment();
    const safeEnd = Math.min(endIdx, members.length);
    for (let i = startIdx; i < safeEnd; i++) {
        const member = members[i];
        const card = createMemberCardElement(
            member,
            member.current_display_rank,
            member.current_display_rank_text,
            member.is_tied
        );
        fragment.appendChild(card);
    }
    membersGrid.appendChild(fragment);
    renderedCount = safeEnd;
}

// Update Pagination / Load More Controls
function updateLoadMoreControls() {
    if (displayShowingCount) {
        displayShowingCount.textContent = renderedCount;
    }
    if (!loadMoreContainer) return;

    const total = filteredMembers.length;
    const remaining = total - renderedCount;
    if (remaining <= 0 || searchQuery) {
        loadMoreContainer.classList.add('hidden');
        return;
    }

    loadMoreContainer.classList.remove('hidden');
    if (btnLoadMoreText) {
        const nextBatch = Math.min(PAGE_SIZE, remaining);
        btnLoadMoreText.textContent = `👇 다음 의원 더 보기 (+${nextBatch}명)`;
    }
    if (btnShowAllText) {
        btnShowAllText.textContent = `전체 ${total}명 한 번에 보기`;
    }
}

// Load Next Batch (+36)
function loadMoreMembers() {
    const nextLimit = Math.min(displayedCount + PAGE_SIZE, filteredMembers.length);
    appendMemberCards(filteredMembers, renderedCount, nextLimit);
    displayedCount = nextLimit;
    updateLoadMoreControls();
}

// Show All Remaining Members
function showAllMembers() {
    showAllMode = true;
    appendMemberCards(filteredMembers, renderedCount, filteredMembers.length);
    displayedCount = filteredMembers.length;
    updateLoadMoreControls();
}

// 3D Flip Card for Avatar Toggle
function toggleCardFlip(event, memberId) {
    event.stopPropagation();
    const flipBox = document.getElementById(`flipper-${memberId}`);
    if (flipBox) {
        flipBox.classList.toggle('is-flipped');
    }
}

// Create Single Member Card DOM
function createMemberCardElement(member, displayRank, rankText, isTied) {
    const card = document.createElement('div');
    card.className = 'member-card glass-card rounded-3xl p-5 flex flex-col justify-between relative overflow-hidden group cursor-pointer border border-slate-200/80 dark:border-slate-800 hover:border-sky-500/50 transition-all';
    card.onclick = (e) => {
        if (e.target.closest('button') || e.target.closest('a') || e.target.closest('.flip-trigger')) return;
        openModal(member.id);
    };

    // Rank Medal Badge Logic (공동 1~3위 모두 메달 스타일 적용)
    let rankBadgeClass = 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
    let rankIcon = '';
    if (displayRank === 1) {
        rankBadgeClass = 'rank-1-badge text-slate-900 font-black animate-pulse';
        rankIcon = '<i class="fa-solid fa-crown mr-1"></i>';
    } else if (displayRank === 2) {
        rankBadgeClass = 'rank-2-badge text-slate-900 font-black';
        rankIcon = '<i class="fa-solid fa-medal mr-1"></i>';
    } else if (displayRank === 3) {
        rankBadgeClass = 'rank-3-badge text-white font-black';
        rankIcon = '<i class="fa-solid fa-award mr-1"></i>';
    } else if (displayRank <= 10) {
        rankBadgeClass = 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/30 font-bold';
    }

    // Tier Color
    let tierColor = 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
    if (member.tier === 'S+') tierColor = 'bg-gradient-to-r from-amber-400 to-yellow-500 text-slate-950 font-black';
    else if (member.tier === 'S') tierColor = 'bg-purple-600 text-white font-bold';
    else if (member.tier === 'A') tierColor = 'bg-sky-600 text-white font-bold';

    // Primary score based on current sort (Core vs Fun isolation)
    let primaryStatLabel = '종합 PoliScore';
    let primaryStatVal = member.total_score;
    let unit = '점';
    let primaryColorClass = 'text-sky-600 dark:text-sky-400';
    let highlightBoxClass = 'bg-slate-50 dark:bg-slate-800/60 border-slate-200/60 dark:border-slate-700/60';
    let subNoteHtml = `<span class="text-[10px] text-slate-400 block">종합 PoliScore</span><span class="text-sm font-bold text-slate-700 dark:text-slate-300">${member.total_score}점</span>`;

    const commScore = member.committee_score ?? member.attendance_score ?? 0;
    const bipScore = member.bipartisan_score ?? 0;
    const fandomScore = member.fandom_score ?? 0;
    const contScore = member.controversy_score ?? 0;
    const gemScore = member.hidden_gem_score ?? 0;
    const news30d = member.news_30d_count ?? 0;
    const contNews = member.controversy_news_count ?? 0;

    let topFunBadgeHtml = `<span class="px-2 py-0.5 rounded-md text-[10px] bg-rose-500/10 text-rose-500 font-bold border border-rose-500/20">📰 뉴스 ${news30d}건</span>`;

    if (currentSort === 'passed') {
        primaryStatLabel = '🎯 입법 성과·품질';
        primaryStatVal = member.passed_score;
    } else if (currentSort === 'voting') {
        primaryStatLabel = '🗳️ 본회의 표결·참여';
        primaryStatVal = member.voting_score;
    } else if (currentSort === 'legislation') {
        primaryStatLabel = '📜 입법 발의·협업';
        primaryStatVal = member.legislation_score;
    } else if (currentSort === 'bipartisan') {
        primaryStatLabel = '🤝 초당적 협치·연대';
        primaryStatVal = bipScore;
    } else if (currentSort === 'committee' || currentSort === 'attendance') {
        primaryStatLabel = '⚖️ 위원회 직무·성실';
        primaryStatVal = commScore;
    } else if (currentSort === 'policy') {
        primaryStatLabel = '🎙️ 정책 소통·다양성';
        primaryStatVal = member.policy_score;
    } else if (currentSort === 'fandom') {
        primaryStatLabel = '❤️ 인기·팬덤 지수';
        primaryStatVal = fandomScore;
        primaryColorClass = 'text-rose-500 dark:text-rose-400';
        highlightBoxClass = 'bg-rose-500/10 border-rose-500/30';
        topFunBadgeHtml = `<span class="px-2 py-0.5 rounded-md text-[10px] bg-rose-500/15 text-rose-500 font-bold border border-rose-500/30">❤️ 팬덤 ${fandomScore}</span>`;
        subNoteHtml = `<span class="text-[10px] text-rose-400 block">뉴스 ${news30d}건 · 응원 ${member.cheer_count}</span><span class="text-xs font-bold text-slate-600 dark:text-slate-300">의정 ${member.total_score}점(별도)</span>`;
    } else if (currentSort === 'controversy') {
        primaryStatLabel = '🔥 논란·핫이슈 온도';
        primaryStatVal = contScore;
        unit = '°C';
        primaryColorClass = contScore >= 70 ? 'text-red-500' : 'text-amber-500';
        highlightBoxClass = 'bg-amber-500/10 border-amber-500/30';
        topFunBadgeHtml = `<span class="px-2 py-0.5 rounded-md text-[10px] bg-amber-500/15 text-amber-500 font-bold border border-amber-500/30">🔥 ${contScore}°C</span>`;
        subNoteHtml = `<span class="text-[10px] text-amber-500 block">쟁점기사 ${contNews}/${news30d}건</span><span class="text-xs font-bold text-slate-600 dark:text-slate-300">의정 ${member.total_score}점(별도)</span>`;
    } else if (currentSort === 'hidden_gem') {
        primaryStatLabel = '💎 흙속의 진주 지수';
        primaryStatVal = gemScore;
        primaryColorClass = 'text-cyan-600 dark:text-cyan-400';
        highlightBoxClass = 'bg-cyan-500/10 border-cyan-500/30';
        topFunBadgeHtml = `<span class="px-2 py-0.5 rounded-md text-[10px] bg-cyan-500/15 text-cyan-500 font-bold border border-cyan-500/30">💎 진주 ${gemScore}</span>`;
        subNoteHtml = `<span class="text-[10px] text-cyan-500 block">의정 ${member.total_score}점 · 뉴스 ${news30d}건</span><span class="text-xs font-bold text-slate-600 dark:text-slate-300">저노출 숨은고수</span>`;
    } else if (currentSort === 'cheer') {
        primaryStatLabel = '💖 시민 실시간 응원';
        primaryStatVal = member.cheer_count;
        unit = '개';
        primaryColorClass = 'text-pink-500';
        highlightBoxClass = 'bg-pink-500/10 border-pink-500/30';
        subNoteHtml = `<span class="text-[10px] text-pink-400 block">종합점수 미반영</span><span class="text-xs font-bold text-slate-600 dark:text-slate-300">의정 ${member.total_score}점</span>`;
    }

    // Keywords Tags HTML
    const keywords = member.keywords || ['#국회의원', '#입법활동'];
    const keywordsHtml = keywords.map(kw => `<span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-[10px] font-medium">${kw}</span>`).join(' ');

    // Quote short
    const quote = member.quote || '국민을 위한 의정 활동에 전념하겠습니다.';

    card.innerHTML = `
        <!-- Top Row: Rank & Tier & Media Mentions -->
        <div class="flex items-center justify-between mb-2">
            <span class="px-2.5 py-1 rounded-full text-xs ${rankBadgeClass} flex items-center shadow-xs">
                ${rankIcon}
                <span class="font-bold tracking-tight">${rankText}</span>
            </span>
            <div class="flex items-center space-x-1.5">
                <span class="px-2 py-0.5 rounded-md text-[10px] ${tierColor}">${member.tier} TIER</span>
                ${topFunBadgeHtml}
            </div>
        </div>

        <!-- 3D Flip Box Avatar Area (Caricature <-> Real Photo) -->
        <div class="flex flex-col items-center text-center my-1 relative">
            <div id="flipper-${member.id}" class="flip-box flip-trigger w-24 h-24 sm:w-28 sm:h-28 mx-auto cursor-pointer" onclick="toggleCardFlip(event, '${member.id}')" title="클릭 시 캐리커쳐 ↔ 실사진 3D 회전 전환">
                <div class="flip-box-inner">
                    <!-- Front: Cartoon SVG -->
                    <div class="flip-box-front flex items-center justify-center p-0.5">
                        <img src="${member.avatar_url}" alt="${member.name} 의원 캐리커쳐" loading="lazy" decoding="async" class="w-full h-full object-contain filter drop-shadow-md">
                        <span class="absolute bottom-1 right-1 text-[9px] px-1.5 py-0.5 rounded-full bg-slate-900/70 text-white font-medium backdrop-blur-xs">🎨 만화</span>
                    </div>
                    <!-- Back: Official Real Photo -->
                    <div class="flip-box-back flex items-center justify-center border-2 border-sky-500/80 rounded-2xl bg-slate-900 shadow-md">
                        <img src="${member.official_photo_url || member.photo_url}" alt="${member.name} 의원 실제 사진" loading="lazy" decoding="async" onerror="this.onerror=null; this.src='${member.avatar_url}';" class="w-full h-full object-cover rounded-2xl">
                        <span class="absolute bottom-1 right-1 text-[9px] px-1.5 py-0.5 rounded-full bg-sky-600/90 text-white font-medium backdrop-blur-xs">📷 실사진</span>
                    </div>
                </div>
            </div>
            
            <!-- Member Identity -->
            <div class="mt-2 space-y-0.5">
                <div class="flex flex-wrap items-center justify-center gap-1">
                    <h3 class="text-lg font-black text-slate-900 dark:text-white tracking-tight group-hover:text-sky-500 transition-colors">${member.name}</h3>
                    <span class="text-xs text-slate-400">${member.hanja_name || ''}</span>
                    <span class="text-[11px] font-semibold text-slate-400">(${member.terms}선)</span>
                    ${Number(member.is_verified_office) === 1
                        ? `<span class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-bold verified-office-pill" title="공식 의원실 직접 인증"><i class="fa-solid fa-circle-check text-sky-500"></i>공식 인증</span>`
                        : ''}
                </div>
                <div class="flex items-center justify-center space-x-1.5 flex-wrap gap-y-0.5">
                    <span class="inline-block px-2 py-0.5 rounded text-[10px] font-bold text-white shadow-xs" style="background-color: ${member.party_color}">
                        ${member.party}
                    </span>
                    <span class="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[130px]">${member.district}</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-semibold border border-indigo-500/20" title="보좌진 총원"><i class="fa-solid fa-users text-[9px] mr-0.5"></i>${(member.staff_info && member.staff_info.total_count) || member.staff_total_count || 0}명</span>
                </div>
            </div>
        </div>

        <!-- Quote Bubble (Famous Signature Quote) -->
        <div class="my-2 p-2 rounded-xl quote-bubble text-[11px] text-slate-600 dark:text-slate-300 italic line-clamp-2">
            <i class="fa-solid fa-quote-left text-slate-400 mr-1 text-[9px]"></i>${quote}<i class="fa-solid fa-quote-right text-slate-400 ml-1 text-[9px]"></i>
        </div>

        <!-- Keyword Hashtags -->
        <div class="flex flex-wrap items-center justify-center gap-1 my-1.5">
            ${keywordsHtml}
        </div>

        <!-- Score Highlight Box -->
        <div class="my-2 p-3 rounded-2xl border ${highlightBoxClass} flex items-center justify-between">
            <div>
                <span class="text-[10px] uppercase font-bold text-slate-400 block">${primaryStatLabel}</span>
                <span class="text-xl sm:text-2xl font-black ${primaryColorClass}">${primaryStatVal}<span class="text-xs font-semibold text-slate-400 ml-0.5">${unit}</span></span>
            </div>
            <div class="text-right">
                ${subNoteHtml}
            </div>
        </div>

        <!-- 6-Attribute Micro Progress Bars (v3.0 6 Core Axes) -->
        <div class="space-y-1 text-[10px] mb-3">
            <div class="flex items-center justify-between">
                <span class="text-slate-500">🎯 입법품질 (${member.passed_score})</span>
                <div class="w-20 h-1 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                    <div class="h-full bg-emerald-500 rounded-full" style="width: ${member.passed_score}%"></div>
                </div>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-500">🗳️ 표결참여 (${member.voting_rate}%)</span>
                <div class="w-20 h-1 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                    <div class="h-full bg-teal-500 rounded-full" style="width: ${member.voting_score}%"></div>
                </div>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-500">📜 입법발의 (${member.legislation_score})</span>
                <div class="w-20 h-1 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                    <div class="h-full bg-sky-500 rounded-full" style="width: ${member.legislation_score}%"></div>
                </div>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-500">🤝 초당협치 (${bipScore})</span>
                <div class="w-20 h-1 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                    <div class="h-full bg-indigo-500 rounded-full" style="width: ${bipScore}%"></div>
                </div>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-500">⚖️ 위원직무 (${commScore})</span>
                <div class="w-20 h-1 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                    <div class="h-full bg-amber-500 rounded-full" style="width: ${commScore}%"></div>
                </div>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-500">🎙️ 정책소통 (${member.policy_score})</span>
                <div class="w-20 h-1 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                    <div class="h-full bg-purple-500 rounded-full" style="width: ${member.policy_score}%"></div>
                </div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="pt-2 border-t border-slate-200/60 dark:border-slate-800 flex items-center justify-between gap-1.5">
            ${renderCardCheerButton(member.id, member.cheer_count)}
            <button onclick="copyAccountDirect(event, '${member.donation_account}')" title="공식 후원계좌 1초 복사" class="py-1.5 px-2.5 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-all">
                <i class="fa-solid fa-hand-holding-dollar text-amber-500"></i>
            </button>
            <button onclick="openModal('${member.id}')" class="py-1.5 px-3 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 text-white transition-all shadow-xs flex items-center space-x-1">
                <span>분석</span>
                <i class="fa-solid fa-chevron-right text-[10px]"></i>
            </button>
        </div>
    `;

    return card;
}

// LocalStorage + Server /api/my-cheers Sync Helpers (v3.2 1-Person 1-Cheer)
function loadLocalCheers() {
    try {
        const raw = localStorage.getItem(CHEER_STORAGE_KEY);
        if (!raw) return;
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) {
            arr.forEach(id => {
                if (typeof id === 'string' && id) cheeredSet.add(id);
            });
        }
    } catch (err) {
        console.warn('Failed to parse local cheers', err);
    }
}

function saveLocalCheers() {
    try {
        localStorage.setItem(CHEER_STORAGE_KEY, JSON.stringify([...cheeredSet]));
    } catch (err) {
        console.warn('Failed to save local cheers', err);
    }
}

async function loadMyCheers() {
    try {
        const res = await fetch('/api/my-cheers', { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data.cheered_member_ids)) {
            data.cheered_member_ids.forEach(id => {
                if (typeof id === 'string' && id) cheeredSet.add(id);
            });
            saveLocalCheers();
            updateCheerButtonsUI();
        }
    } catch (err) {
        console.warn('Failed to sync server cheers', err);
    }
}

function getCardCheerButtonConfig(memberId, count) {
    const isCheered = cheeredSet.has(memberId);
    const className = isCheered
        ? 'cheer-btn flex-1 py-1.5 px-2 rounded-xl text-xs font-bold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60 transition-all flex items-center justify-center space-x-1 relative'
        : 'cheer-btn flex-1 py-1.5 px-2 rounded-xl text-xs font-bold bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-900/60 border border-rose-200 dark:border-rose-900/40 transition-all flex items-center justify-center space-x-1 relative';
    const innerHTML = isCheered
        ? `<span>💖</span><span>응원완료</span><span class="cheer-label-${memberId}">${count}</span>`
        : `<i class="fa-solid fa-heart text-[11px]"></i><span class="cheer-label-${memberId}">${count}</span>`;
    return { isCheered, className, innerHTML };
}

function renderCardCheerButton(memberId, count) {
    const cfg = getCardCheerButtonConfig(memberId, count);
    return `<button data-cheer-btn="${memberId}" aria-pressed="${cfg.isCheered}" onclick="handleCheer(event, '${memberId}')" class="${cfg.className}">${cfg.innerHTML}</button>`;
}

function syncMemberCheerCount(memberId, serverCount, fandomScore = null) {
    const numericCount = Number(serverCount ?? 0);
    const matched = allMembers.find(m => m.id === memberId);
    if (matched) {
        matched.cheer_count = numericCount;
        if (fandomScore !== null && fandomScore !== undefined) {
            matched.fandom_score = fandomScore;
        }
    }
    const matchedFiltered = filteredMembers.find(m => m.id === memberId);
    if (matchedFiltered) {
        matchedFiltered.cheer_count = numericCount;
        if (fandomScore !== null && fandomScore !== undefined) {
            matchedFiltered.fandom_score = fandomScore;
        }
    }
    if (currentMember && currentMember.id === memberId) {
        currentMember.cheer_count = numericCount;
        if (fandomScore !== null && fandomScore !== undefined) {
            currentMember.fandom_score = fandomScore;
        }
    }
    document.querySelectorAll(`.cheer-label-${memberId}`).forEach(el => {
        el.textContent = numericCount;
    });
    const modalCheerCount = document.getElementById('modal-cheer-count');
    if (modalCheerCount && currentMember && currentMember.id === memberId) {
        modalCheerCount.textContent = numericCount;
    }
}

function updateCheerButtonsUI(targetMemberId = null) {
    const selector = targetMemberId ? `[data-cheer-btn="${targetMemberId}"]` : '[data-cheer-btn]';
    document.querySelectorAll(selector).forEach(btn => {
        const mid = btn.getAttribute('data-cheer-btn');
        if (!mid) return;
        const labelEl = btn.querySelector(`.cheer-label-${mid}`);
        const matched = allMembers.find(m => m.id === mid);
        const count = labelEl ? labelEl.textContent : (matched ? matched.cheer_count : 0);
        const cfg = getCardCheerButtonConfig(mid, count);
        btn.className = cfg.className;
        btn.setAttribute('aria-pressed', String(cfg.isCheered));
        btn.innerHTML = cfg.innerHTML;
    });

    const modalBtn = document.getElementById('modal-cheer-btn');
    if (modalBtn && currentMember && (!targetMemberId || currentMember.id === targetMemberId)) {
        const isCheered = cheeredSet.has(currentMember.id);
        const modalCount = document.getElementById('modal-cheer-count')?.textContent ?? currentMember.cheer_count ?? 0;
        modalBtn.className = isCheered
            ? 'px-4 py-2 rounded-xl text-xs font-bold bg-emerald-500/15 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-300 border border-emerald-400/50 transition-all flex items-center space-x-1.5 relative'
            : 'px-4 py-2 rounded-xl text-xs font-bold bg-rose-500 hover:bg-rose-600 text-white transition-all transform active:scale-95 shadow-md shadow-rose-500/25 flex items-center space-x-1.5 relative';
        modalBtn.setAttribute('aria-pressed', String(isCheered));
        modalBtn.innerHTML = isCheered
            ? `<span>💖</span><span id="modal-cheer-label">응원완료</span><span id="modal-cheer-count" class="font-bold">${modalCount}</span>`
            : `<i class="fa-solid fa-heart"></i><span id="modal-cheer-label">응원하기</span><span id="modal-cheer-count" class="font-bold">${modalCount}</span>`;
    }
}

// 1-Click Live Cheer Handler (Server-Verified 1-Person 1-Cheer, No Unverified Optimistic +1)
async function handleCheer(e, memberId) {
    e.stopPropagation();

    if (cheeredSet.has(memberId)) {
        showToast('이미 이 의원을 응원하셨습니다! (중복 응원 방지: 의원당 1회)', 'info');
        return;
    }
    if (cheerInFlight.has(memberId)) {
        return;
    }

    cheerInFlight.add(memberId);
    try {
        const res = await fetch(`/api/members/${memberId}/cheer`, {
            method: 'POST',
            credentials: 'same-origin'
        });
        const data = await res.json();

        if (res.status === 409 || data.status === 'already_cheered') {
            cheeredSet.add(memberId);
            saveLocalCheers();
            if (data.cheer_count !== undefined) {
                syncMemberCheerCount(memberId, data.cheer_count);
            }
            updateCheerButtonsUI(memberId);
            showToast('이미 이 의원을 응원하셨습니다! (중복 응원 방지: 의원당 1회)', 'info');
            return;
        }

        if (res.ok && data.status === 'success') {
            spawnFloatingHeart(e.clientX, e.clientY);
            cheeredSet.add(memberId);
            saveLocalCheers();
            syncMemberCheerCount(memberId, data.cheer_count, data.fandom_score);
            updateCheerButtonsUI(memberId);
            loadSummaryStats();
            showToast(`${data.name} 의원에게 응원을 보냈습니다! 💖`, 'success');
            return;
        }

        showToast(data.message || '응원 처리 중 오류가 발생했습니다.', 'error');
    } catch (err) {
        console.error('Cheer failed', err);
        showToast('네트워크 오류로 응원을 반영하지 못했습니다.', 'error');
    } finally {
        cheerInFlight.delete(memberId);
    }
}

// Floating Heart Particle Effect
function spawnFloatingHeart(x, y) {
    const heart = document.createElement('div');
    heart.className = 'floating-heart fa-solid fa-heart';
    heart.style.left = `${x - 10}px`;
    heart.style.top = `${y - 15}px`;
    document.body.appendChild(heart);

    setTimeout(() => {
        heart.remove();
    }, 850);
}

// Direct Copy Donation Account
function copyAccountDirect(e, accountString) {
    e.stopPropagation();
    navigator.clipboard.writeText(accountString).then(() => {
        showToast(`📋 후원계좌가 복사되었습니다!\n${accountString}`, 'success');
    }).catch(() => {
        showToast('클립보드 복사에 실패했습니다.', 'error');
    });
}

function copyDonationAccount() {
    if (!currentMember || !currentMember.donation_account) return;
    navigator.clipboard.writeText(currentMember.donation_account).then(() => {
        showToast(`📋 [${currentMember.name} 의원 후원회] 계좌번호가 복사되었습니다!\n연간 10만원까지 전액 세액공제됩니다.`, 'success');
    }).catch(() => {
        showToast('클립보드 복사에 실패했습니다.', 'error');
    });
}

function cheerCurrentModalMember(e) {
    if (!currentMember) return;
    handleCheer(e, currentMember.id);
}

// Open Deep-Dive Modal
async function openModal(memberId) {
    try {
        const res = await fetch(`/api/members/${memberId}`);
        const member = await res.json();
        if (!member) return;

        currentMember = member;
        isModalPhotoView = false;

        const matchedMember = allMembers.find(m => m.id === member.id);
        const modalRankText = (matchedMember && matchedMember.current_display_rank_text) ? matchedMember.current_display_rank_text : `${member.total_rank || 1}위`;
        document.getElementById('modal-rank-badge').textContent = modalRankText;
        document.getElementById('modal-member-name').textContent = member.name;
        document.getElementById('modal-hanja-name').textContent = member.hanja_name || '';
        document.getElementById('modal-age').textContent = member.age ? `${member.age}세` : '';
        document.getElementById('modal-district').textContent = member.district;
        const roleLabel = member.committee_role_label || (member.committee_role === 'chair' ? '위원장' : member.committee_role === 'secretary' ? '간사' : '위원');
        document.getElementById('modal-committee').textContent = `${member.committee} (${roleLabel})`;
        document.getElementById('modal-total-score').textContent = member.total_score;
        document.getElementById('modal-tier-badge').textContent = `${member.tier} TIER`;
        document.getElementById('modal-terms-badge').textContent = `${member.terms}선`;
        
        // Fun elements
        document.getElementById('modal-quote').textContent = member.quote || '국민을 위한 의정 활동에 전념하겠습니다.';
        document.getElementById('modal-media-mentions').textContent = `🔥 언론 언급 ${(member.media_mentions || 1200).toLocaleString()}회`;
        
        const keywordsElem = document.getElementById('modal-keywords');
        if (keywordsElem && member.keywords) {
            keywordsElem.innerHTML = member.keywords.map(kw => `<span class="px-2 py-0.5 rounded-md bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold">${kw}</span>`).join(' ');
        }

        const funBadgesElem = document.getElementById('modal-fun-badges');
        if (funBadgesElem) {
            funBadgesElem.innerHTML = `
                <span class="px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-500 border border-rose-500/25 text-[11px] font-bold" title="종합점수 미반영">❤️ 팬덤 ${member.fandom_score ?? 0}</span>
                <span class="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-500 border border-amber-500/25 text-[11px] font-bold" title="종합점수 미반영">🔥 핫이슈 ${member.controversy_score ?? 0}°C</span>
                <span class="px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/25 text-[11px] font-bold" title="종합점수 미반영">💎 숨은고수 ${member.hidden_gem_score ?? 0}</span>
            `;
        }

        const partyBadge = document.getElementById('modal-party-badge');
        partyBadge.textContent = member.party;
        partyBadge.style.backgroundColor = member.party_color;

        renderModalAvatar();

        // 6-Stat Bars (v3.0 6 Axes)
        const commScore = member.committee_score ?? member.attendance_score ?? 0;
        const bipScore = member.bipartisan_score ?? 0;

        document.getElementById('stat-pass-val').textContent = `${member.passed_score}점`;
        document.getElementById('stat-pass-bar').style.width = `${member.passed_score}%`;

        document.getElementById('stat-vot-val').textContent = `${member.voting_rate}% (${member.voting_score}점)`;
        document.getElementById('stat-vot-bar').style.width = `${member.voting_score}%`;

        document.getElementById('stat-leg-val').textContent = `${member.legislation_score}점`;
        document.getElementById('stat-leg-bar').style.width = `${member.legislation_score}%`;

        document.getElementById('stat-bip-val').textContent = `${bipScore}점`;
        document.getElementById('stat-bip-bar').style.width = `${bipScore}%`;

        document.getElementById('stat-comm-val').textContent = `${commScore}점`;
        document.getElementById('stat-comm-bar').style.width = `${commScore}%`;

        document.getElementById('stat-pol-val').textContent = `${member.policy_score}점`;
        document.getElementById('stat-pol-bar').style.width = `${member.policy_score}%`;

        renderModalFactSheet14(member);
        renderModalNews(member);
        renderModalStaffInfo(member);

        document.getElementById('modal-donation-account').textContent = member.donation_account || '선관위 정치후원금센터 참조';
        document.getElementById('modal-cheer-count').textContent = member.cheer_count;
        updateCheerButtonsUI(member.id);

        const verifiedBadge = document.getElementById('modal-verified-badge');
        if (verifiedBadge) {
            if (Number(member.is_verified_office) === 1) {
                verifiedBadge.classList.remove('hidden');
            } else {
                verifiedBadge.classList.add('hidden');
            }
        }
        renderModalOfficeNotice(member);

        renderModalBills(member.recent_bills || []);
        renderRadarChart(member);
        loadModalComments(member.id);

        detailModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    } catch (err) {
        console.error('Failed to open modal', err);
        showToast('의원 정보를 불러오는 데 실패했습니다.', 'error');
    }
}

// Toggle Staff List Panel in Modal
function toggleStaffList() {
    const panel = document.getElementById('modal-staff-panel');
    const chevron = document.getElementById('staff-chevron');
    if (!panel) return;
    
    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        if (chevron) chevron.style.transform = 'rotate(180deg)';
    } else {
        panel.classList.add('hidden');
        if (chevron) chevron.style.transform = 'rotate(0deg)';
    }
}

// Render Staff Info in Modal
function renderModalStaffInfo(member) {
    const staffInfo = member.staff_info || {
        total_count: member.staff_total_count || 0,
        advisors_4th: member.staff_advisors_4th || [],
        secretaries_5th: member.staff_secretaries_5th || [],
        assistants_6to9th: member.staff_assistants_6to9th || []
    };

    const totCount = staffInfo.total_count || 0;
    const advisors = staffInfo.advisors_4th || [];
    const secretaries = staffInfo.secretaries_5th || [];
    const assistants = staffInfo.assistants_6to9th || [];

    const textElem = document.getElementById('modal-staff-count-text');
    if (textElem) textElem.textContent = `보좌진 ${totCount}명`;

    const totalTag = document.getElementById('modal-staff-total-tag');
    if (totalTag) totalTag.textContent = `총 ${totCount}명`;

    const advCount = document.getElementById('modal-staff-4th-count');
    if (advCount) advCount.textContent = `(${advisors.length}명)`;
    const advListElem = document.getElementById('modal-staff-4th-list');
    if (advListElem) {
        advListElem.innerHTML = advisors.length > 0
            ? advisors.map(name => `<span class="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/60 text-xs font-semibold">${name}</span>`).join(' ')
            : '<span class="text-slate-400 text-xs italic">등록 정보 없음</span>';
    }

    const secCount = document.getElementById('modal-staff-5th-count');
    if (secCount) secCount.textContent = `(${secretaries.length}명)`;
    const secListElem = document.getElementById('modal-staff-5th-list');
    if (secListElem) {
        secListElem.innerHTML = secretaries.length > 0
            ? secretaries.map(name => `<span class="px-2 py-0.5 rounded bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800/60 text-xs font-semibold">${name}</span>`).join(' ')
            : '<span class="text-slate-400 text-xs italic">등록 정보 없음</span>';
    }

    const astCount = document.getElementById('modal-staff-6to9th-count');
    if (astCount) astCount.textContent = `(${assistants.length}명)`;
    const astListElem = document.getElementById('modal-staff-6to9th-list');
    if (astListElem) {
        astListElem.innerHTML = assistants.length > 0
            ? assistants.map(name => `<span class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700/60 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600/60 text-xs font-medium">${name}</span>`).join(' ')
            : '<span class="text-slate-400 text-xs italic">등록 정보 없음</span>';
    }

    const panel = document.getElementById('modal-staff-panel');
    const chevron = document.getElementById('staff-chevron');
    if (panel) panel.classList.add('hidden');
    if (chevron) chevron.style.transform = 'rotate(0deg)';
}

// Close Modal
function closeModal() {
    detailModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
    currentMember = null;
    if (radarChartInstance) {
        radarChartInstance.destroy();
        radarChartInstance = null;
    }
}

// Toggle Modal Avatar (Cartoon vs Real Photo)
function toggleModalAvatarType() {
    isModalPhotoView = !isModalPhotoView;
    const btn = document.getElementById('modal-avatar-toggle-btn');
    if (btn) {
        btn.innerHTML = isModalPhotoView 
            ? '<i class="fa-solid fa-palette mr-1"></i>캐리커쳐 전환' 
            : '<i class="fa-solid fa-camera mr-1"></i>실사진 전환';
    }
    renderModalAvatar();
}

function renderModalAvatar() {
    const container = document.getElementById('modal-avatar-container');
    if (!container || !currentMember) return;

    if (isModalPhotoView && (currentMember.official_photo_url || currentMember.photo_url)) {
        container.innerHTML = `<img src="${currentMember.official_photo_url || currentMember.photo_url}" alt="${currentMember.name}" onerror="this.onerror=null; this.src='${currentMember.avatar_url}?size=160';" class="w-full h-full object-cover">`;
    } else {
        container.innerHTML = `<img src="${currentMember.avatar_url}?size=160" alt="${currentMember.name} 캐리커쳐" class="w-full h-full object-contain filter drop-shadow-md">`;
    }
}

// Render Recent Bills in Modal
function renderModalBills(bills) {
    const list = document.getElementById('modal-bills-list');
    if (!list) return;

    if (!bills || bills.length === 0) {
        list.innerHTML = `<p class="text-xs text-slate-400 py-2">최근 등록된 대표발의 법안 정보가 없습니다.</p>`;
        return;
    }

    list.innerHTML = bills.map(b => {
        let statusColor = 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
        if (b.status && b.status.includes('가결')) {
            statusColor = 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 font-bold';
        } else if (b.status && b.status.includes('대안반영')) {
            statusColor = 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/30 font-semibold';
        } else if (b.status && (b.status.includes('회부') || b.status.includes('심사'))) {
            statusColor = 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/30';
        }

        const linkHtml = b.detail_link
            ? `<a href="${b.detail_link}" target="_blank" rel="noopener noreferrer" class="text-[10px] text-sky-500 hover:underline font-semibold whitespace-nowrap"><i class="fa-solid fa-arrow-up-right-from-square mr-0.5"></i>의안상세</a>`
            : '';

        return `
            <div class="p-3 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 space-y-1">
                <div class="flex items-center justify-between gap-2">
                    <span class="text-xs font-bold text-slate-800 dark:text-slate-100 flex-1 truncate">${b.bill_name}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full ${statusColor} whitespace-nowrap">${b.status || '심사중'}</span>
                </div>
                <div class="flex items-center justify-between text-[11px] text-slate-400">
                    <div class="flex items-center space-x-3">
                        <span><i class="fa-regular fa-calendar mr-1"></i>${b.proposed_date || '2026-11'}</span>
                        <span><i class="fa-solid fa-landmark mr-1"></i>${b.committee || '상임위'}</span>
                    </div>
                    ${linkHtml}
                </div>
                ${b.summary ? `<p class="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 pt-0.5">${b.summary}</p>` : ''}
            </div>
        `;
    }).join('');
}

// Toggle 14-Metric Fact Sheet Accordion
function toggleFactSheet() {
    const body = document.getElementById('modal-fact-sheet-body');
    const chevron = document.getElementById('fact-sheet-chevron');
    if (!body) return;
    const isHidden = body.classList.toggle('hidden');
    if (chevron) {
        chevron.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    }
}

// Render 14 Detailed Public Fact Metrics in Modal
function renderModalFactSheet14(member) {
    const grid = document.getElementById('modal-fact-sheet-grid');
    const commTags = document.getElementById('modal-committees-tags');
    if (!grid) return;

    const fs = member.fact_sheet_14 || {};
    const ws = member.weekly_stats || {};
    const vb = fs.vote_breakdown || ws.vote_breakdown || {};

    const passedOrig = fs.passed_original ?? ws.passed_original ?? 0;
    const passedAmend = fs.passed_amended ?? ws.passed_amended ?? 0;
    const altInc = fs.alt_incorporated ?? ws.alt_incorporated ?? ws.subcommittee_passed ?? 0;
    const billsProp = fs.bills_proposed ?? ws.bills_proposed ?? 0;
    const eff = fs.passage_efficiency ?? ws.passage_efficiency ?? 0;
    const bipRate = fs.bipartisan_rate ?? ws.bipartisan_rate ?? 0;
    const bipShare = fs.bipartisan_cosponsor_share ?? ws.bipartisan_cosponsor_share ?? 0;
    const avgCosp = fs.avg_cosponsors ?? ws.avg_cosponsors ?? 0;
    const cospPart = fs.cosponsor_participations ?? ws.cosponsor_participations ?? 0;
    const polDiv = fs.policy_diversity ?? ws.policy_diversity ?? 0;
    const vRate = fs.voting_rate ?? member.voting_rate ?? 0;
    const vPart = fs.votes_participated ?? ws.votes_participated ?? 0;
    const vElig = fs.votes_eligible ?? ws.votes_eligible ?? 0;
    const actVote = fs.active_vote_ratio ?? ws.active_vote_ratio ?? vRate;
    const yesCnt = vb['찬성'] || 0;
    const noCnt = vb['반대'] || 0;
    const absCnt = vb['기권'] || 0;
    const outCnt = vb['불참'] || 0;
    const commCnt = fs.committee_count ?? ws.committee_count ?? 1;
    const hasSpec = fs.has_special_duty ?? ws.has_special_duty ?? false;
    const roleLabel = fs.committee_role_label || member.committee_role_label || '위원';
    const spkCnt = fs.speech_count ?? member.speech_count ?? 0;
    const interpCnt = fs.interpellation_count ?? ws.interpellation_count ?? 0;
    const mentions = fs.media_mentions ?? member.media_mentions ?? 0;

    const items = [
        { icon: '📜', label: '1. 대표발의 총 건수', val: `${billsProp}건`, sub: '22대 누적 실측' },
        { icon: '🏛️', label: '2. 원안가결', val: `${passedOrig}건`, sub: '최고 가결 등급(×3.0)' },
        { icon: '✏️', label: '3. 수정가결', val: `${passedAmend}건`, sub: '본회의 통과(×2.5)' },
        { icon: '🔀', label: '4. 대안반영폐기', val: `${altInc}건`, sub: '위원회 대안 반영(×1.0)' },
        { icon: '🎯', label: '5. 입법 타율·효율', val: `${eff}%`, sub: '최소 5건 보정 가결효율' },
        { icon: '🤝', label: '6. 타 정당 협치율', val: `${bipRate}%`, sub: `타당의원 비중 ${bipShare}%` },
        { icon: '👥', label: '7. 평균 공동발의', val: `${avgCosp}명`, sub: '법안당 설득 인원' },
        { icon: '🔗', label: '8. 동료법안 공동참여', val: `${cospPart}회`, sub: '3,378+건 풀 기준' },
        { icon: '🌐', label: '9. 입법 분야 다양성', val: `${polDiv}개 분야`, sub: '발의 소관 상임위 수' },
        { icon: '🗳️', label: '10. 본회의 표결률', val: `${vRate}%`, sub: `${vPart}/${vElig}건 참여` },
        { icon: '✅', label: '11. 찬·반 적극표결', val: `${actVote}%`, sub: `찬${yesCnt}·반${noCnt}·기${absCnt}·불${outCnt}` },
        { icon: '⚖️', label: '12. 겸임 위원회 수', val: `${commCnt}개`, sub: hasSpec ? '핵심 특위·겸임 참여' : '본 상임위 전담' },
        { icon: '🎙️', label: '13. 직책 · 상임위발언', val: `${roleLabel} · ${spkCnt}회`, sub: '의정 활동 발언 지표' },
        { icon: '💡', label: '14. 정책질의 · 언론', val: `${mentions.toLocaleString()}회`, sub: `대정부질의/세미나 ${interpCnt}건` },
    ];

    grid.innerHTML = items.map(it => `
        <div class="p-2.5 rounded-xl bg-white dark:bg-slate-900/70 border border-slate-200/80 dark:border-slate-700/80 space-y-0.5">
            <div class="text-[10px] text-slate-400 font-semibold truncate">${it.icon} ${it.label}</div>
            <div class="text-xs sm:text-sm font-black text-slate-800 dark:text-slate-100">${it.val}</div>
            <div class="text-[10px] text-slate-400 truncate">${it.sub}</div>
        </div>
    `).join('');

    if (commTags) {
        const commsList = fs.committees_list || ws.committees_list || [member.committee];
        const specSet = new Set(fs.special_duties || ws.special_duties || []);
        commTags.innerHTML = `<span class="text-slate-400 font-semibold mr-1">소속 위원회:</span>` + commsList.map(c => {
            const isSpec = specSet.has(c);
            return `<span class="px-2 py-0.5 rounded-md ${isSpec ? 'bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30 font-bold' : 'bg-slate-200/80 dark:bg-slate-700/80 text-slate-600 dark:text-slate-300'}">${c}${isSpec ? ' ★' : ''}</span>`;
        }).join('');
    }
}

// Render Recent 30d News Headlines in Modal
function renderModalNews(member) {
    const list = document.getElementById('modal-news-list');
    const meta = document.getElementById('modal-news-meta');
    if (!list) return;

    const newsCnt = member.news_30d_count ?? 0;
    const contCnt = member.controversy_news_count ?? 0;
    if (meta) {
        meta.textContent = `최근 30일 ${newsCnt}건 (쟁점 키워드 ${contCnt}건)`;
    }

    const items = member.recent_news_items || [];
    const titles = member.recent_news_titles || [];
    if (items.length === 0 && titles.length === 0) {
        list.innerHTML = `<p class="text-xs text-slate-400 py-2">최근 30일 이내 수집된 뉴스 헤드라인이 없습니다.</p>`;
        return;
    }

    const normalized = items.length > 0
        ? items.slice(0, 2)
        : titles.slice(0, 2).map(t => ({ title: t, link: '', pub_date: '' }));

    list.innerHTML = normalized.map(n => {
        const title = typeof n === 'string' ? n : (n.title || '');
        const link = typeof n === 'object' ? (n.link || '') : '';
        const linkBtn = link
            ? `<a href="${link}" target="_blank" rel="noopener noreferrer" class="text-[10px] text-rose-500 hover:underline font-semibold whitespace-nowrap ml-2"><i class="fa-solid fa-arrow-up-right-from-square mr-0.5"></i>기사보기</a>`
            : '';
        return `
            <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-700/80 flex items-center justify-between gap-2">
                <span class="text-xs font-medium text-slate-700 dark:text-slate-200 flex-1 line-clamp-1">${title}</span>
                ${linkBtn}
            </div>
        `;
    }).join('');
}

// Open & Close Methodology Modal (Fallback if called)
function openMethodologyModal() {
    const m = document.getElementById('methodology-modal');
    if (m) {
        m.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeMethodologyModal() {
    const m = document.getElementById('methodology-modal');
    if (m) {
        m.classList.add('hidden');
        if (!detailModal || detailModal.classList.contains('hidden')) {
            document.body.style.overflow = 'auto';
        }
    }
}

// Render 6-Axis Hexagon Radar Chart with Chart.js
function renderRadarChart(member) {
    const canvas = document.getElementById('modalRadarChart');
    if (!canvas) return;

    if (radarChartInstance) {
        radarChartInstance.destroy();
    }

    const isDark = document.documentElement.classList.contains('dark');
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)';
    const pointLabelColor = isDark ? '#CBD5E1' : '#475569';

    const ctx = canvas.getContext('2d');
    radarChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['입법품질(30%)', '본회의표결(20%)', '입법발의(15%)', '초당적협치(15%)', '위원회직무(12%)', '정책소통(8%)'],
            datasets: [{
                label: `${member.name} 의원 6대 핵심 축`,
                data: [
                    member.passed_score,
                    member.voting_score,
                    member.legislation_score,
                    member.bipartisan_score ?? 0,
                    member.committee_score ?? member.attendance_score ?? 0,
                    member.policy_score
                ],
                backgroundColor: `${member.party_color}33`,
                borderColor: member.party_color,
                borderWidth: 2.5,
                pointBackgroundColor: member.party_color,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: member.party_color,
                pointRadius: 4.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: gridColor },
                    grid: { color: gridColor },
                    pointLabels: {
                        color: pointLabelColor,
                        font: { size: 10.5, weight: 'bold' }
                    },
                    suggestedMin: 0,
                    suggestedMax: 100,
                    ticks: {
                        display: false,
                        stepSize: 20
                    }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Load Comments Feed in Modal (v3.3 Hierarchical Replies & Official Office Answers)
async function loadModalComments(memberId) {
    const feed = document.getElementById('modal-comments-feed');
    const countBadge = document.getElementById('modal-comment-count-badge');
    if (!feed) return;

    const isOwnOffice = Boolean(
        officeSession.authenticated &&
        officeSession.role === 'office' &&
        officeSession.member_id === memberId
    );

    try {
        const res = await fetch(`/api/members/${memberId}/comments`, { credentials: 'same-origin' });
        const data = await res.json();
        const comments = data.comments || [];

        if (countBadge) countBadge.textContent = `${data.count ?? comments.length}건`;

        if (comments.length === 0) {
            feed.innerHTML = `<p class="text-xs text-slate-400 py-4 text-center">첫 번째 시민 의견을 남겨주세요!</p>`;
            return;
        }

        feed.innerHTML = comments.map(c => {
            let stanceBadge = '';
            if (c.stance === 'cheer') {
                stanceBadge = '<span class="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-500 border border-rose-500/30 font-semibold">💖 응원</span>';
            } else if (c.stance === 'proposal') {
                stanceBadge = '<span class="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-500 border border-purple-500/30 font-semibold">💡 제언</span>';
            } else {
                stanceBadge = '<span class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/30 font-semibold">🧐 분발</span>';
            }

            const repliesHtml = (c.replies || []).map(r => {
                if (Number(r.is_official_reply) === 1) {
                    const badgeLabel = escapeHtml(r.official_badge_name || `${currentMember?.name || ''} 의원실 공식`);
                    return `
                        <div class="ml-5 sm:ml-6 mt-2 pl-3 pr-2.5 py-2.5 border-l-2 border-sky-500 bg-sky-500/5 dark:bg-sky-500/10 rounded-r-xl space-y-1">
                            <div class="flex items-center justify-between gap-2">
                                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold verified-office-pill">
                                    <span>🏛️</span>
                                    <span>${badgeLabel} 답변</span>
                                    <i class="fa-solid fa-circle-check text-sky-500"></i>
                                </span>
                                <span class="text-[10px] text-slate-400">${escapeHtml(r.created_at || '방금')}</span>
                            </div>
                            <p class="text-xs text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-line">${escapeHtml(r.content)}</p>
                        </div>
                    `;
                }
                return `
                    <div class="ml-5 sm:ml-6 mt-2 pl-3 pr-2.5 py-2 border-l-2 border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 rounded-r-xl space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="text-[11px] font-bold text-slate-700 dark:text-slate-300">${escapeHtml(r.author)}</span>
                            <span class="text-[10px] text-slate-400">${escapeHtml(r.created_at || '최근')}</span>
                        </div>
                        <p class="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">${escapeHtml(r.content)}</p>
                    </div>
                `;
            }).join('');

            const replyActionHtml = isOwnOffice ? `
                <div class="pt-1 flex justify-end">
                    <button type="button" onclick="toggleOfficialReplyForm(${c.id})" class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-sky-500/10 hover:bg-sky-500/20 text-sky-600 dark:text-sky-400 border border-sky-400/30 transition-colors">
                        <span>🏛️ 공식 대댓글 달기</span>
                    </button>
                </div>
                <form id="official-reply-form-${c.id}" onsubmit="submitOfficialReply(event, ${c.id})" class="hidden mt-2 pt-2 border-t border-sky-400/20 space-y-2">
                    <textarea id="official-reply-input-${c.id}" rows="2" maxlength="600" required placeholder="${escapeHtml(currentMember?.name || '')} 의원실 공식 답변을 작성해주세요..."
                              class="w-full text-xs px-3 py-2 rounded-xl bg-sky-50/70 dark:bg-slate-900 border border-sky-300 dark:border-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 dark:text-slate-100"></textarea>
                    <div class="flex justify-end space-x-1.5">
                        <button type="button" onclick="toggleOfficialReplyForm(${c.id})" class="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">취소</button>
                        <button type="submit" class="px-3 py-1 rounded-lg text-[11px] font-bold bg-sky-600 hover:bg-sky-500 text-white">공식 답변 등록</button>
                    </div>
                </form>
            ` : '';

            return `
                <div class="p-3 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200/80 dark:border-slate-700/80 space-y-1.5">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2">
                            <span class="text-xs font-bold text-slate-800 dark:text-slate-200">${escapeHtml(c.author)}</span>
                            ${stanceBadge}
                        </div>
                        <span class="text-[10px] text-slate-400">${escapeHtml(c.created_at || '최근')}</span>
                    </div>
                    <p class="text-xs text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">${escapeHtml(c.content)}</p>
                    ${replyActionHtml}
                    ${repliesHtml}
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to load comments', err);
    }
}

// Submit New Citizen Comment
async function submitComment(e) {
    e.preventDefault();
    if (!currentMember) return;

    const authorInput = document.getElementById('comment-author');
    const contentInput = document.getElementById('comment-content');
    const stanceRadio = document.querySelector('input[name="stance"]:checked');

    const author = authorInput.value.trim() || '익명 유권자';
    const content = contentInput.value.trim();
    const stance = stanceRadio ? stanceRadio.value : 'cheer';

    if (!content) {
        showToast('의견 내용을 입력해주세요.', 'error');
        return;
    }

    try {
        const res = await fetch(`/api/members/${currentMember.id}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ author, content, stance })
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            contentInput.value = '';
            showToast('의견이 성공적으로 등록되었습니다!', 'success');
            loadModalComments(currentMember.id);
            loadSummaryStats();
        } else {
            showToast(data.detail || data.message || '댓글 등록에 실패했습니다.', 'error');
        }
    } catch (err) {
        console.error('Failed to submit comment', err);
        showToast('댓글 등록 중 오류가 발생했습니다.', 'error');
    }
}

// Official Office Session, Notice, Replies & Admin B2B Functions (v3.3)
async function loadOfficeSession() {
    try {
        const res = await fetch('/api/office/me', { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        officeSession = data && data.authenticated
            ? data
            : { authenticated: false, username: null, role: null, member_id: null, office_name: null };
        renderOfficeAuthHeader();
    } catch (err) {
        console.warn('Failed to load office session', err);
    }
}

function renderOfficeAuthHeader() {
    const container = document.getElementById('office-auth-controls');
    if (!container) return;

    if (!officeSession.authenticated) {
        container.innerHTML = `
            <button onclick="openOfficeLoginModal()" class="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-sky-50 dark:hover:bg-sky-950/50 hover:text-sky-600 dark:hover:text-sky-400 transition-all border border-slate-200 dark:border-slate-700">
                <span>🏛️</span>
                <span class="hidden sm:inline">의원실 로그인</span>
                <span class="sm:hidden">로그인</span>
            </button>
        `;
        return;
    }

    if (officeSession.role === 'admin') {
        container.innerHTML = `
            <button onclick="openAdminIssueModal()" class="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-amber-500/15 hover:bg-amber-500/25 text-amber-600 dark:text-amber-300 border border-amber-400/40 transition-all">
                <span>⚙️</span>
                <span class="hidden sm:inline">의원실 계정 발급</span>
                <span class="sm:hidden">계정관리</span>
            </button>
            <button onclick="logoutOfficeSession()" class="px-2.5 py-2 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-rose-500 hover:text-white border border-slate-200 dark:border-slate-700 transition-colors">
                로그아웃
            </button>
        `;
        return;
    }

    container.innerHTML = `
        <button onclick="openMemberFromOfficeSession()" class="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-bold verified-office-pill hover:opacity-90 transition-all">
            <i class="fa-solid fa-circle-check text-sky-500"></i>
            <span>${escapeHtml(officeSession.office_name || '공식 의원실')}</span>
        </button>
        <button onclick="logoutOfficeSession()" class="px-2.5 py-2 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-rose-500 hover:text-white border border-slate-200 dark:border-slate-700 transition-colors">
            로그아웃
        </button>
    `;
}

function openMemberFromOfficeSession() {
    if (officeSession.authenticated && officeSession.member_id) {
        openModal(officeSession.member_id);
    }
}

function openOfficeLoginModal() {
    const modal = document.getElementById('office-login-modal');
    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('office-login-username')?.focus();
    }
}

function closeOfficeLoginModal() {
    document.getElementById('office-login-modal')?.classList.add('hidden');
}

async function submitOfficeLogin(e) {
    e.preventDefault();
    const username = document.getElementById('office-login-username')?.value.trim() || '';
    const password = document.getElementById('office-login-password')?.value || '';

    try {
        const res = await fetch('/api/office/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.detail || '로그인에 실패했습니다.', 'error');
            return;
        }

        officeSession = data;
        document.getElementById('office-login-form')?.reset();
        closeOfficeLoginModal();
        renderOfficeAuthHeader();
        showToast(`${data.office_name} 계정으로 로그인되었습니다!`, 'success');

        if (currentMember) {
            renderModalOfficeNotice(currentMember);
            loadModalComments(currentMember.id);
        } else if (data.role === 'admin') {
            openAdminIssueModal();
        } else if (data.role === 'office' && data.member_id) {
            openModal(data.member_id);
        }
    } catch (err) {
        console.error('Login error', err);
        showToast('로그인 중 네트워크 오류가 발생했습니다.', 'error');
    }
}

async function logoutOfficeSession() {
    try {
        await fetch('/api/office/logout', { method: 'POST', credentials: 'same-origin' });
    } catch (err) {
        console.warn('Logout warning', err);
    }
    officeSession = { authenticated: false, username: null, role: null, member_id: null, office_name: null };
    renderOfficeAuthHeader();
    closeAdminIssueModal();
    if (currentMember) {
        renderModalOfficeNotice(currentMember);
        loadModalComments(currentMember.id);
    }
    showToast('로그아웃되었습니다.', 'info');
}

function syncMemberVerificationInMemory(memberId, isVerified, officeNotice = undefined) {
    const applyPatch = (m) => {
        if (!m || m.id !== memberId) return;
        m.is_verified_office = isVerified ? 1 : 0;
        if (officeNotice !== undefined) m.office_notice = officeNotice;
    };
    allMembers.forEach(applyPatch);
    filteredMembers.forEach(applyPatch);
    if (currentMember && currentMember.id === memberId) {
        applyPatch(currentMember);
        const verifiedBadge = document.getElementById('modal-verified-badge');
        if (verifiedBadge) {
            verifiedBadge.classList.toggle('hidden', !isVerified);
        }
    }
    applyFiltersAndRender();
}

function renderModalOfficeNotice(member) {
    const section = document.getElementById('modal-office-notice-section');
    const titleEl = document.getElementById('modal-office-notice-title');
    const textEl = document.getElementById('modal-office-notice-text');
    const editorEl = document.getElementById('office-notice-editor');
    const inputEl = document.getElementById('office-notice-input');
    if (!section || !textEl) return;

    const isOwnOffice = Boolean(
        officeSession.authenticated &&
        officeSession.role === 'office' &&
        officeSession.member_id === member.id
    );
    const hasNotice = Boolean((member.office_notice || '').trim());

    if (!hasNotice && !isOwnOffice) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');
    if (titleEl) {
        titleEl.textContent = `${member.name} 의원실 공식 의정 브리핑`;
    }
    textEl.textContent = hasNotice
        ? member.office_notice
        : '아직 등록된 공식 의정 브리핑이 없습니다. 아래에서 유권자에게 전할 첫 브리핑을 작성해보세요.';

    if (editorEl) {
        editorEl.classList.toggle('hidden', !isOwnOffice);
    }
    if (inputEl && isOwnOffice) {
        inputEl.value = member.office_notice || '';
    }
}

async function saveOfficeNotice() {
    if (!currentMember) return;
    const noticeInput = document.getElementById('office-notice-input');
    const notice = noticeInput ? noticeInput.value.trim() : '';

    try {
        const res = await fetch('/api/office/notice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ notice, member_id: currentMember.id })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.detail || '공식 브리핑 저장에 실패했습니다.', 'error');
            return;
        }
        syncMemberVerificationInMemory(currentMember.id, true, data.office_notice);
        renderModalOfficeNotice(currentMember);
        showToast('공식 의정 브리핑이 저장 및 인증 반영되었습니다! 📌', 'success');
    } catch (err) {
        console.error('Save notice error', err);
        showToast('브리핑 저장 중 오류가 발생했습니다.', 'error');
    }
}

function toggleOfficialReplyForm(parentId) {
    const form = document.getElementById(`official-reply-form-${parentId}`);
    if (!form) return;
    const willOpen = form.classList.contains('hidden');
    form.classList.toggle('hidden', !willOpen);
    if (willOpen) {
        document.getElementById(`official-reply-input-${parentId}`)?.focus();
    }
}

async function submitOfficialReply(e, parentId) {
    e.preventDefault();
    if (!currentMember) return;
    const input = document.getElementById(`official-reply-input-${parentId}`);
    const content = input ? input.value.trim() : '';
    if (!content) {
        showToast('공식 답변 내용을 입력해주세요.', 'error');
        return;
    }

    try {
        const res = await fetch(`/api/members/${currentMember.id}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({
                content,
                parent_id: parentId,
                is_official_reply: true,
                stance: 'official'
            })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.detail || '공식 대댓글 등록에 실패했습니다.', 'error');
            return;
        }
        syncMemberVerificationInMemory(currentMember.id, true);
        showToast('의원실 공식 대댓글이 등록되었습니다! 🏛️', 'success');
        loadModalComments(currentMember.id);
        loadSummaryStats();
    } catch (err) {
        console.error('Official reply failed', err);
        showToast('공식 답변 등록 중 오류가 발생했습니다.', 'error');
    }
}

// Admin B2B Issuance, Feedbacks & Dev Support Console Helpers
async function openAdminIssueModal(initialTab = 'accounts') {
    const modal = document.getElementById('admin-issue-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    switchAdminTab(initialTab);
    if (allMembers.length === 0) {
        await loadMembers();
    }
    populateAdminMemberSelect();
    loadAdminOfficeAccounts();
    loadAdminFeedbacks();
    loadAdminDevSupportForm();
}

function switchAdminTab(tabKey) {
    const tabs = ['accounts', 'feedbacks', 'devsupport'];
    tabs.forEach(t => {
        const panel = document.getElementById(`admin-tab-${t}`);
        const btn = document.getElementById(`admin-tab-btn-${t}`);
        const isActive = t === tabKey;
        if (panel) panel.classList.toggle('hidden', !isActive);
        if (btn) {
            if (isActive) {
                btn.classList.add('bg-white', 'dark:bg-slate-900', 'text-sky-600', 'dark:text-sky-400', 'shadow-xs');
                btn.classList.remove('text-slate-600', 'dark:text-slate-300');
            } else {
                btn.classList.remove('bg-white', 'dark:bg-slate-900', 'text-sky-600', 'dark:text-sky-400', 'shadow-xs');
                btn.classList.add('text-slate-600', 'dark:text-slate-300');
            }
        }
    });
}

function closeAdminIssueModal() {
    document.getElementById('admin-issue-modal')?.classList.add('hidden');
}

function populateAdminMemberSelect(filterText = '') {
    const select = document.getElementById('admin-member-select');
    if (!select) return;
    const prevValue = select.value;
    const q = filterText.trim().toLowerCase();
    const list = allMembers
        .filter(m => !q || m.name.toLowerCase().includes(q) || m.party.toLowerCase().includes(q) || m.district.toLowerCase().includes(q))
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, 'ko'));

    select.innerHTML = `<option value="">의원을 선택하세요 (${list.length}명)...</option>` + list.map(m => {
        const badge = Number(m.is_verified_office) === 1 ? ' ✓인증' : '';
        return `<option value="${m.id}">${escapeHtml(m.name)} (${escapeHtml(m.party)} · ${escapeHtml(m.district)})${badge}</option>`;
    }).join('');
    if (prevValue && list.some(m => m.id === prevValue)) {
        select.value = prevValue;
    }
}

function filterAdminMemberSelect() {
    const q = document.getElementById('admin-member-search')?.value || '';
    populateAdminMemberSelect(q);
}

async function submitAdminIssueAccount(e) {
    e.preventDefault();
    const memberId = document.getElementById('admin-member-select')?.value || '';
    const username = document.getElementById('admin-issue-username')?.value.trim() || '';
    const password = document.getElementById('admin-issue-password')?.value || '';
    const verifyNow = Boolean(document.getElementById('admin-issue-verify')?.checked);

    if (!memberId) {
        showToast('대상 국회의원을 선택해주세요.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/admin/issue-office-account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ member_id: memberId, username, password, verify_now: verifyNow })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.detail || '계정 발급에 실패했습니다.', 'error');
            return;
        }
        const acc = data.account;
        syncMemberVerificationInMemory(acc.member_id, Number(acc.is_verified_office) === 1);
        populateAdminMemberSelect(document.getElementById('admin-member-search')?.value || '');
        loadAdminOfficeAccounts();
        document.getElementById('admin-issue-username').value = '';
        document.getElementById('admin-issue-password').value = '';
        showToast(`${acc.office_name} 계정(${acc.username}) 발급 완료!`, 'success');
    } catch (err) {
        console.error('Issue account error', err);
        showToast('계정 발급 요청 중 오류가 발생했습니다.', 'error');
    }
}

async function toggleSelectedMemberVerify() {
    const memberId = document.getElementById('admin-member-select')?.value || '';
    if (!memberId) {
        showToast('인증 배지를 전환할 의원을 먼저 선택해주세요.', 'error');
        return;
    }
    await toggleMemberVerifyById(memberId);
}

async function toggleMemberVerifyById(memberId) {
    try {
        const res = await fetch('/api/admin/toggle-verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ member_id: memberId })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.detail || '인증 상태 전환에 실패했습니다.', 'error');
            return;
        }
        syncMemberVerificationInMemory(memberId, Number(data.is_verified_office) === 1);
        populateAdminMemberSelect(document.getElementById('admin-member-search')?.value || '');
        loadAdminOfficeAccounts();
        showToast(`${data.name} 의원 공식 인증: ${data.is_verified_office ? '활성화(✓)' : '해제'}`, 'info');
    } catch (err) {
        console.error('Toggle verify error', err);
    }
}

async function loadAdminOfficeAccounts() {
    const listEl = document.getElementById('admin-accounts-list');
    if (!listEl) return;
    try {
        const res = await fetch('/api/admin/office-accounts', { credentials: 'same-origin' });
        if (!res.ok) {
            listEl.innerHTML = `<p class="text-[11px] text-rose-400">목록을 불러올 수 없습니다.</p>`;
            return;
        }
        const data = await res.json();
        const accounts = data.accounts || [];
        if (accounts.length === 0) {
            listEl.innerHTML = `<p class="text-[11px] text-slate-400">아직 발급된 의원실 계정이 없습니다.</p>`;
            return;
        }
        listEl.innerHTML = accounts.map(a => `
            <div class="flex items-center justify-between p-2 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-700/80 gap-2">
                <div class="min-w-0">
                    <div class="font-bold text-slate-800 dark:text-slate-100 truncate">
                        ${escapeHtml(a.office_name)} <span class="text-sky-500 font-mono">(${escapeHtml(a.username)})</span>
                        ${Number(a.is_verified_office) === 1 ? '<span class="ml-1 text-[10px] text-sky-500">✓인증</span>' : '<span class="ml-1 text-[10px] text-slate-400">미인증</span>'}
                    </div>
                    <div class="text-[10px] text-slate-400 truncate">${escapeHtml(a.member_party || '')} · 발급 ${escapeHtml(a.created_at || '')}</div>
                </div>
                <div class="flex items-center space-x-1 flex-shrink-0">
                    <button type="button" onclick="toggleMemberVerifyById('${a.member_id}')" class="px-2 py-1 rounded-lg text-[10px] font-semibold bg-slate-200 dark:bg-slate-700 hover:bg-sky-500 hover:text-white transition-colors">인증전환</button>
                    <button type="button" onclick="closeAdminIssueModal(); openModal('${a.member_id}')" class="px-2 py-1 rounded-lg text-[10px] font-semibold bg-sky-600 hover:bg-sky-500 text-white">페이지</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Failed to load office accounts', err);
    }
}

// v3.4: Developer Support Modal & Feedback System + Admin Consoles
let cachedDevBankInfo = '';

async function openDevSupportModal() {
    const modal = document.getElementById('dev-support-modal');
    if (!modal) return;
    modal.classList.remove('hidden');

    try {
        const res = await fetch('/api/dev-support');
        const data = await res.json();
        const msgEl = document.getElementById('dev-support-message');
        const bankBox = document.getElementById('dev-support-bank-box');
        const bankText = document.getElementById('dev-support-bank-text');
        const linksBox = document.getElementById('dev-support-links-box');
        const tossBtn = document.getElementById('dev-support-toss-btn');
        const kakaoBtn = document.getElementById('dev-support-kakao-btn');
        const emptyBox = document.getElementById('dev-support-empty-box');

        if (msgEl && data.dev_message) msgEl.textContent = data.dev_message;

        cachedDevBankInfo = (data.dev_bank_info || '').trim();
        if (bankBox && bankText) {
            if (cachedDevBankInfo) {
                bankText.textContent = cachedDevBankInfo;
                bankBox.classList.remove('hidden');
            } else {
                bankBox.classList.add('hidden');
            }
        }

        const safeUrl = (u) => {
            const s = (u || '').trim();
            return (s.startsWith('https://') || s.startsWith('http://')) ? s : '';
        };
        const tossUrl = safeUrl(data.dev_toss_link);
        const kakaoUrl = safeUrl(data.dev_kakaopay_link);

        if (tossBtn) {
            if (tossUrl) {
                tossBtn.href = tossUrl;
                tossBtn.classList.remove('hidden');
            } else {
                tossBtn.classList.add('hidden');
            }
        }
        if (kakaoBtn) {
            if (kakaoUrl) {
                kakaoBtn.href = kakaoUrl;
                kakaoBtn.classList.remove('hidden');
            } else {
                kakaoBtn.classList.add('hidden');
            }
        }
        if (linksBox) {
            linksBox.classList.toggle('hidden', !tossUrl && !kakaoUrl);
        }
        if (emptyBox) {
            emptyBox.classList.toggle('hidden', Boolean(cachedDevBankInfo || tossUrl || kakaoUrl));
        }
    } catch (err) {
        console.error('Failed to load dev support info', err);
    }
}

function closeDevSupportModal() {
    document.getElementById('dev-support-modal')?.classList.add('hidden');
}

function copyDevBankInfo() {
    if (!cachedDevBankInfo) return;
    navigator.clipboard.writeText(cachedDevBankInfo).then(() => {
        showToast(`☕ 후원 계좌가 복사되었습니다!\n${cachedDevBankInfo}`, 'success');
    }).catch(() => {
        showToast('클립보드 복사에 실패했습니다.', 'error');
    });
}

function openFeedbackModal() {
    const modal = document.getElementById('feedback-modal');
    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('feedback-content')?.focus();
    }
}

function closeFeedbackModal() {
    document.getElementById('feedback-modal')?.classList.add('hidden');
}

async function submitFeedbackForm(e) {
    e.preventDefault();
    const catRadio = document.querySelector('input[name="feedback_category"]:checked');
    const category = catRadio ? catRadio.value : '제안';
    const author = document.getElementById('feedback-author')?.value.trim() || '익명 사용자';
    const contact = document.getElementById('feedback-contact')?.value.trim() || '';
    const content = document.getElementById('feedback-content')?.value.trim() || '';

    if (!content) {
        showToast('내용을 입력해주세요.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, author, contact, content })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.detail || data.message || '의견 전송에 실패했습니다.', 'error');
            return;
        }
        document.getElementById('feedback-form')?.reset();
        closeFeedbackModal();
        showToast(data.message || '소중한 의견이 전달되었습니다!', 'success');
    } catch (err) {
        console.error('Feedback submit failed', err);
        showToast('네트워크 오류로 전송에 실패했습니다.', 'error');
    }
}

async function loadAdminFeedbacks() {
    const listEl = document.getElementById('admin-feedbacks-list');
    const countBadge = document.getElementById('admin-feedback-count');
    if (!listEl) return;
    try {
        const res = await fetch('/api/admin/feedbacks', { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        const items = data.feedbacks || [];
        const newCount = items.filter(f => f.status !== 'checked').length;
        if (countBadge) countBadge.textContent = newCount > 0 ? newCount : items.length;

        if (items.length === 0) {
            listEl.innerHTML = `<p class="text-[11px] text-slate-400 text-center py-4">아직 접수된 의견이 없습니다.</p>`;
            return;
        }

        listEl.innerHTML = items.map(f => {
            const isChecked = f.status === 'checked';
            return `
                <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-700/80 space-y-1.5">
                    <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center space-x-1.5 min-w-0">
                            <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-400/30">${escapeHtml(f.category)}</span>
                            <span class="font-bold text-slate-800 dark:text-slate-100 truncate">${escapeHtml(f.author)}</span>
                            ${f.contact ? `<span class="text-[10px] text-sky-500 truncate">(${escapeHtml(f.contact)})</span>` : ''}
                        </div>
                        <div class="flex items-center space-x-1.5 flex-shrink-0">
                            <span class="text-[10px] text-slate-400">${escapeHtml(f.created_at || '')}</span>
                            ${isChecked
                                ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-500">확인됨</span>`
                                : `<button type="button" onclick="markAdminFeedbackChecked(${f.id})" class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-600 hover:bg-sky-500 text-white">확인완료</button>`}
                        </div>
                    </div>
                    <p class="text-xs text-slate-700 dark:text-slate-200 whitespace-pre-line leading-relaxed">${escapeHtml(f.content)}</p>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to load admin feedbacks', err);
    }
}

async function markAdminFeedbackChecked(feedbackId) {
    try {
        const res = await fetch(`/api/admin/feedbacks/${feedbackId}/check`, {
            method: 'POST',
            credentials: 'same-origin'
        });
        if (res.ok) loadAdminFeedbacks();
    } catch (err) {
        console.error('Mark checked failed', err);
    }
}

async function loadAdminDevSupportForm() {
    try {
        const res = await fetch('/api/dev-support');
        if (!res.ok) return;
        const data = await res.json();
        const bankEl = document.getElementById('admin-dev-bank');
        const tossEl = document.getElementById('admin-dev-toss');
        const kakaoEl = document.getElementById('admin-dev-kakaopay');
        const msgEl = document.getElementById('admin-dev-message');
        if (bankEl) bankEl.value = data.dev_bank_info || '';
        if (tossEl) tossEl.value = data.dev_toss_link || '';
        if (kakaoEl) kakaoEl.value = data.dev_kakaopay_link || '';
        if (msgEl) msgEl.value = data.dev_message || '';
    } catch (err) {
        console.warn('Failed to load dev support form', err);
    }
}

async function submitAdminDevSupport(e) {
    e.preventDefault();
    const dev_bank_info = document.getElementById('admin-dev-bank')?.value.trim() || '';
    const dev_toss_link = document.getElementById('admin-dev-toss')?.value.trim() || '';
    const dev_kakaopay_link = document.getElementById('admin-dev-kakaopay')?.value.trim() || '';
    const dev_message = document.getElementById('admin-dev-message')?.value.trim() || '';

    try {
        const res = await fetch('/api/admin/dev-support', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ dev_bank_info, dev_toss_link, dev_kakaopay_link, dev_message })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.detail || '후원 설정 저장에 실패했습니다.', 'error');
            return;
        }
        showToast('개발자 후원 계좌/링크가 저장되어 즉시 반영되었습니다! ☕', 'success');
    } catch (err) {
        console.error('Save dev support failed', err);
        showToast('저장 중 오류가 발생했습니다.', 'error');
    }
}

// Toast Notification System
function showToast(message, type = 'info') {
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = 'toast-animate px-4 py-3 rounded-2xl shadow-xl border text-xs font-semibold flex items-center space-x-2 pointer-events-auto max-w-sm';

    if (type === 'success') {
        toast.classList.add('bg-emerald-600', 'text-white', 'border-emerald-500');
        toast.innerHTML = `<i class="fa-solid fa-circle-check text-sm"></i><span class="flex-1 whitespace-pre-line">${message}</span>`;
    } else if (type === 'error') {
        toast.classList.add('bg-rose-600', 'text-white', 'border-rose-500');
        toast.innerHTML = `<i class="fa-solid fa-circle-exclamation text-sm"></i><span class="flex-1 whitespace-pre-line">${message}</span>`;
    } else {
        toast.classList.add('bg-slate-900', 'text-white', 'dark:bg-slate-100', 'dark:text-slate-900', 'border-slate-700');
        toast.innerHTML = `<i class="fa-solid fa-bell text-sm"></i><span class="flex-1 whitespace-pre-line">${message}</span>`;
    }

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
