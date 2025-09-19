// Basic Jest tests for dashboard.js
const { JSDOM } = require('jsdom');

describe('updateClock', () => {
    let clockElem, dateElem;
    beforeEach(() => {
        const dom = new JSDOM('<div id="clock"></div><div id="date"></div>');
        global.document = dom.window.document;
        global.window = dom.window;
    });
    it('updates clock and date elements', () => {
        require('./dashboard.js');
        // Simulate one tick
        global.updateClock();
        expect(document.getElementById('clock').textContent).toMatch(/\d{2}:\d{2}/);
        expect(document.getElementById('date').textContent).toMatch(/\w{3}, \w{3} \d{1,2}, \d{4}/);
    });
});

describe('setupNewsTickerFromTemplate', () => {
    beforeEach(() => {
        const dom = new JSDOM('<div id="news-title"></div><div id="news-summary"></div>');
        global.document = dom.window.document;
        global.window = dom.window;
        global.window.newsEvents = [{title: 'Headline', summary: 'Summary'}];
    });
    it('shows first news item', () => {
        require('./dashboard.js');
        global.setupNewsTickerFromTemplate();
        expect(document.getElementById('news-title').textContent).toBe('Headline');
        expect(document.getElementById('news-summary').textContent).toBe('Summary');
    });
});
