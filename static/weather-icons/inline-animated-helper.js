// Inline animated SVG helper
// Finds <img class="weather-svg"> elements, fetches their SVG files,
// and replaces the <img> with the inline <svg> so animations and internal
// classes can be styled or manipulated.
(function(){
  async function inlineImages(root=document) {
    const imgs = Array.from((root || document).querySelectorAll('img.weather-svg'));
    for (const img of imgs) {
      if (img.dataset.inlined) continue;
      const src = img.getAttribute('src');
      if (!src) continue;
      try {
        const resp = await fetch(src, {cache: 'no-store'});
        if (!resp.ok) continue;
        const txt = await resp.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(txt, 'image/svg+xml');
        const svg = doc.querySelector('svg');
        if (!svg) continue;
        // Transfer useful attributes from img -> svg
        if (img.id) svg.id = img.id;
        const imgClass = Array.from(img.classList).filter(c=>c!=='weather-svg').join(' ');
        svg.setAttribute('class', (svg.getAttribute('class') || '') + ' weather-icon-svg ' + imgClass);
        if (img.getAttribute('width')) svg.setAttribute('width', img.getAttribute('width'));
        if (img.getAttribute('height')) svg.setAttribute('height', img.getAttribute('height'));
        if (img.alt) svg.setAttribute('aria-label', img.alt);
        svg.dataset.source = src;
        svg.dataset.inlined = '1';
        // Preserve data-* attributes
        for (const attr of Array.from(img.attributes)) {
          if (attr.name.startsWith('data-')) svg.setAttribute(attr.name, attr.value);
        }
        img.replaceWith(svg);
      } catch (e) {
        console.warn('inline-animated-helper: failed to inline', src, e);
      }
    }
  }

  // Observe fragment insertions so dynamically refreshed sections get inlined
  const mo = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.addedNodes && m.addedNodes.length) {
        for (const node of m.addedNodes) {
          if (node.nodeType === 1) inlineImages(node);
        }
      }
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      inlineImages(document).catch(()=>{});
      mo.observe(document.body, {childList:true, subtree:true});
    });
  } else {
    inlineImages(document).catch(()=>{});
    mo.observe(document.body, {childList:true, subtree:true});
  }
})();
