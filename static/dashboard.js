// Live clock
function updateClock() {
    const now = new Date();
    let h = now.getHours().toString().padStart(2, '0');
    let m = now.getMinutes().toString().padStart(2, '0');
    const clockElem = document.getElementById('clock');
    if (clockElem) clockElem.textContent = h + ':' + m;
}
setInterval(updateClock, 1000);

// News ticker using news_events passed from Flask
function setupNewsTickerFromTemplate() {
    const titleElem = document.getElementById('news-title');
    const summaryElem = document.getElementById('news-summary');
    if (!titleElem || !summaryElem) return;
    // news_events is passed as a JS array in the template
    if (!window.newsEvents || !window.newsEvents.length) {
        titleElem.textContent = 'No news available';
        summaryElem.textContent = '';
        return;
    }
    let newsIndex = 0;
    function showNewsItem(idx) {
        const item = window.newsEvents[idx];
        titleElem.textContent = item.title;
        summaryElem.textContent = item.summary || '';
    }
    showNewsItem(0);
    setInterval(function() {
        newsIndex = (newsIndex + 1) % window.newsEvents.length;
        showNewsItem(newsIndex);
    }, 19000);
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupNewsTickerFromTemplate);
} else {
    setupNewsTickerFromTemplate();
}
