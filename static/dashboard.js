// Cruise Itinerary Temperatures
async function updateItineraryTemps() {
    try {
        const resp = await fetch('/cruise-temps', {cache: 'no-store'});
        if (!resp.ok) return;
        const temps = await resp.json();
        for (const [date, temp] of Object.entries(temps)) {
            const cell = document.getElementById('it-temp-' + date);
            if (cell) cell.textContent = temp;
        }
    } catch (e) { /* ignore */ }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateItineraryTemps);
} else {
    updateItineraryTemps();
}
// Cruise Countdown Timer
function setupCruiseCountdown() {
    // Set the cruise departure date/time (local time)
    // 28 May 2026 06:00 (24h format, Europe/London)
    const cruiseDeparture = new Date('2026-05-28T06:00:00+01:00');
    function updateCountdown() {
        const now = new Date();
        let diff = cruiseDeparture - now;
        if (diff < 0) diff = 0;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
        const mins = Math.floor((diff / (1000 * 60)) % 60);
        const secs = Math.floor((diff / 1000) % 60);
        const d = document.getElementById('cd-days');
        const h = document.getElementById('cd-hours');
        const m = document.getElementById('cd-mins');
        const s = document.getElementById('cd-secs');
        if (d) d.textContent = days;
        if (h) h.textContent = hours.toString().padStart(2, '0');
        if (m) m.textContent = mins.toString().padStart(2, '0');
        if (s) s.textContent = secs.toString().padStart(2, '0');
    }
    updateCountdown();
    setInterval(updateCountdown, 1000);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupCruiseCountdown);
} else {
    setupCruiseCountdown();
}
// Live clock
function updateClock() {
    const now = new Date();
    let h = now.getHours().toString().padStart(2, '0');
    let m = now.getMinutes().toString().padStart(2, '0');
    let dayOfWeek = now.toLocaleString('en-US', { weekday: 'long' });
    let month = now.toLocaleString('en-US', { month: 'long' });
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
        const timeElem = document.getElementById('news-time');
        if (timeElem) timeElem.textContent = formatHoursAgo(item.published);
    }
    function formatHoursAgo(published) {
        if (!published) return '';
        const pub = new Date(published);
        if (isNaN(pub.getTime())) return '';
        const diffMs = Date.now() - pub.getTime();
        const hours = Math.floor(diffMs / 3600000);
        if (hours <= 0) return 'Less than 1 Hour ago';
        if (hours === 1) return '1 Hour ago';
        return `${hours} Hours ago`;
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
