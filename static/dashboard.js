// Live clock
function updateClock() {
    const now = new Date();
    let h = now.getHours().toString().padStart(2, '0');
    let m = now.getMinutes().toString().padStart(2, '0');
    let dayOfWeek = now.toLocaleString('en-US', { weekday: 'short' });
    let month = now.toLocaleString('en-US', { month: 'short' });
    let date = now.getDate();
    let year = now.getFullYear();
    let formattedDate = `${dayOfWeek}, ${month} ${date}, ${year}`;
    const clockElem = document.getElementById('clock');
    const dateElem = document.getElementById('date');
    if (clockElem) clockElem.textContent = h + ':' + m;
    if (dateElem) dateElem.textContent = formattedDate
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
    let tickerInterval = null;
    function showNewsItem(idx) {
        const item = window.newsEvents[idx];
        titleElem.textContent = item.title;
        summaryElem.textContent = item.summary || '';
    }
    function startTicker() {
        if (tickerInterval) clearInterval(tickerInterval);
        showNewsItem(0);
        tickerInterval = setInterval(function() {
            newsIndex = (newsIndex + 1) % window.newsEvents.length;
            showNewsItem(newsIndex);
        }, 19000);
    }
    startTicker();

    // Periodically refresh news from backend
    setInterval(async function() {
        try {
            const resp = await fetch('/news-fragment', {cache: 'no-store'});
            if (!resp.ok) return;
            const html = await resp.text();
            // Extract newsEvents from HTML fragment (assumes JSON in a script tag)
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            const scriptTag = tempDiv.querySelector('script');
            if (scriptTag) {
                const match = scriptTag.textContent.match(/window\.newsEvents\s*=\s*(\[.*\]);/s);
                if (match) {
                    window.newsEvents = JSON.parse(match[1]);
                    newsIndex = 0;
                    startTicker();
                }
            }
        } catch (e) { /* ignore */ }
    }, 5 * 60 * 1000); // Refresh every 5 minutes
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupNewsTickerFromTemplate);
} else {
    setupNewsTickerFromTemplate();
}
