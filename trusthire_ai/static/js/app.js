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

  const photoInput = document.querySelector('#job-photo');
  const photoPreview = document.querySelector('#job-photo-preview');
  const readPhotoButton = document.querySelector('#read-job-photo');
  const photoStatus = document.querySelector('#photo-status');
  let photoPreviewUrl;
  const allowedPhotoTypes = new Set(['image/png', 'image/jpeg', 'image/webp']);

  photoInput?.addEventListener('change', () => {
    const photo = photoInput.files?.[0];
    if (!photo) return;

    if (!allowedPhotoTypes.has(photo.type) || photo.size > 4 * 1024 * 1024) {
      photoInput.value = '';
      readPhotoButton.disabled = true;
      photoPreview.hidden = true;
      photoStatus.textContent = 'Choose a PNG, JPG or WebP image smaller than 4 MB.';
      if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl);
      return;
    }

    if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl);
    photoPreviewUrl = URL.createObjectURL(photo);
    photoPreview.src = photoPreviewUrl;
    photoPreview.hidden = false;
    readPhotoButton.disabled = false;
    photoStatus.textContent = 'Photo selected. Read the text, review it, then analyze the job.';
  });

  readPhotoButton?.addEventListener('click', async () => {
    const photo = photoInput?.files?.[0];
    if (!photo || !jobText) return;
    if (!window.Tesseract) {
      photoStatus.textContent = 'Photo text reading did not load. Check your internet connection and try again.';
      return;
    }

    let worker;
    readPhotoButton.disabled = true;
    photoInput.disabled = true;
    photoStatus.textContent = 'Loading English and Gujarati text recognition…';
    try {
      worker = await window.Tesseract.createWorker('eng+guj', 1, {
        logger: (progress) => {
          if (progress.status === 'recognizing text') {
            photoStatus.textContent = `Reading photo… ${Math.round((progress.progress || 0) * 100)}%`;
          }
        },
      });
      const { data } = await worker.recognize(photo);
      const recognizedText = data.text.trim();
      if (!recognizedText) {
        photoStatus.textContent = 'No text was found. Try a clearer, well-lit screenshot.';
        return;
      }

      const existingText = jobText.value.trim();
      const combinedText = existingText ? `${existingText}\n\n${recognizedText}` : recognizedText;
      jobText.value = combinedText.slice(0, 20_000);
      jobText.dispatchEvent(new Event('input', { bubbles: true }));
      photoStatus.textContent = combinedText.length > 20_000
        ? 'Text was added up to the 20,000-character limit. Review it before analysis.'
        : 'Text added. Review the extracted text for OCR mistakes before analysis.';
      jobText.focus();
    } catch (error) {
      console.error('Could not read text from the selected job photo.', error);
      photoStatus.textContent = 'Could not read this photo. Try a clearer image or paste the job text instead.';
    } finally {
      if (worker) {
        try {
          await worker.terminate();
        } catch (error) {
          console.error('Could not stop the photo text reader.', error);
        }
      }
      photoInput.disabled = false;
      readPhotoButton.disabled = false;
    }
  });

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
