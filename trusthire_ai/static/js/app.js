// Small, dependency-light interactions for the server-rendered website.
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.querySelector('.theme-toggle');
  themeToggle?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('trusthire-theme', next);
  });

  const menuToggle = document.querySelector('.menu-toggle');
  menuToggle?.addEventListener('click', () => {
    const nav = document.querySelector('.main-nav');
    const open = nav.classList.toggle('nav-open');
    menuToggle.setAttribute('aria-expanded', String(open));
  });

  const jobText = document.querySelector('#job-text');
  const counter = document.querySelector('#char-count');
  const updateCount = () => { if (jobText && counter) counter.textContent = jobText.value.length.toLocaleString(); };
  jobText?.addEventListener('input', updateCount);
  updateCount();
  document.querySelectorAll('[data-sample]').forEach((button) => {
    button.addEventListener('click', () => {
      const sampleGroup = window.trustHireSamples?.[button.dataset.sample];
      if (!sampleGroup?.length || !jobText) return;
      jobText.value = sampleGroup[Math.floor(Math.random() * sampleGroup.length)];
      jobText.dispatchEvent(new Event('input', { bubbles: true }));
      jobText.focus();
    });
  });

  const jobForm = document.querySelector('#job-form');
  jobForm?.addEventListener('submit', () => {
    const button = document.querySelector('#analyze-button');
    button?.classList.add('is-loading');
    button?.setAttribute('aria-busy', 'true');
    button?.querySelector('.button-label')?.replaceChildren(document.createTextNode('Analyzing job post…'));
  });

  document.querySelectorAll('.auth-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab').forEach((item) => item.classList.toggle('active', item === tab));
      const signup = tab.dataset.tab === 'signup';
      document.querySelector('#signup-form').hidden = !signup;
      document.querySelector('#login-form').hidden = signup;
    });
  });

  const search = document.querySelector('#history-search');
  const filter = document.querySelector('#history-filter');
  const filterRows = () => document.querySelectorAll('#history-table tbody tr[data-label]').forEach((row) => {
    const textMatch = row.dataset.search.includes((search?.value || '').toLowerCase());
    const labelMatch = !filter?.value || row.dataset.label === filter.value;
    row.hidden = !(textMatch && labelMatch);
  });
  search?.addEventListener('input', filterRows);
  filter?.addEventListener('change', filterRows);

  const original = document.querySelector('#original-job-post');
  const highlightData = document.querySelector('#highlight-data');
  if (original && highlightData) {
    const source = original.textContent;
    let segments = [{ text: source, marked: false }];
    const phrases = JSON.parse(highlightData.textContent);
    phrases.forEach((phrase) => {
      if (!phrase) return;
      const next = [];
      segments.forEach((segment) => {
        if (segment.marked) { next.push(segment); return; }
        const lower = segment.text.toLowerCase();
        const needle = phrase.toLowerCase();
        let cursor = 0;
        let position = lower.indexOf(needle, cursor);
        while (position !== -1) {
          if (position > cursor) next.push({ text: segment.text.slice(cursor, position), marked: false });
          next.push({ text: segment.text.slice(position, position + phrase.length), marked: true });
          cursor = position + phrase.length;
          position = lower.indexOf(needle, cursor);
        }

        const result = document.querySelector('#scan-result');
        if (result) result.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (cursor < segment.text.length) next.push({ text: segment.text.slice(cursor), marked: false });
      });
      segments = next;
    });
    original.replaceChildren(...segments.map((segment) => {
      const node = document.createTextNode(segment.text);
      if (!segment.marked) return node;
      const mark = document.createElement('mark');
      mark.className = 'suspicious-highlight';
      mark.append(node);
      return mark;
    }));
  }

  const charts = window.trustHireCharts;
  if (charts && window.Chart) {
    const trend = document.querySelector('#trend-chart');
    if (trend) new Chart(trend, {
      type: 'line',
      data: { labels: charts.labels, datasets: [{ label: 'Scans', data: charts.trend, borderColor: '#3784e8', backgroundColor: 'rgba(55,132,232,.12)', fill: true, tension: .35, pointRadius: 3 }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
    const breakdown = document.querySelector('#label-chart');
    if (breakdown) new Chart(breakdown, {
      type: 'doughnut',
      data: { labels: ['Fake', 'Suspicious', 'Genuine'], datasets: [{ data: charts.breakdown, backgroundColor: ['#e65d63', '#efad48', '#38a77b'], borderWidth: 0 }] },
      options: { responsive: true, cutout: '68%', plugins: { legend: { position: 'bottom' } } }
    });
  }
});
