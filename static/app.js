'use strict';
async function send(form, endpoint, payload) {
  const status = form.querySelector('.form-status');
  const buttons = form.querySelectorAll('button');
  buttons.forEach(b => b.disabled = true);
  status.textContent = 'Saving…';
  try {
    const response = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': form.elements.csrf.value}, body: JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'The request could not be completed.');
    if (result.status === 'invalid' || result.status === 'failed' || result.status === 'blocked') {
      status.textContent = `${result.status}: ${result.error || (result.gaps || []).join(', ')}. Inspect the recorded attempt after refreshing.`;
    } else {
      status.textContent = 'Saved. Refreshing your workspace…';
      window.location.reload();
    }
  } catch (error) {
    status.textContent = error.message || 'Connection failed. Your unsaved text is still here; retry when connected.';
    status.tabIndex = -1;
    status.focus();
  } finally { buttons.forEach(b => b.disabled = false); }
}
for (const form of document.querySelectorAll('.json-form')) {
  form.addEventListener('submit', event => {
    event.preventDefault();
    try {
      const payload = JSON.parse(form.elements.payload.value);
      const endpoint = form.dataset.dynamicStep ? `/api/admin/runs/${form.dataset.dynamicStep}/steps/${form.elements.step.value}` : form.action;
      send(form, endpoint, payload);
    } catch (_) {
      const status = form.querySelector('.form-status');
      status.textContent = 'Enter valid JSON. Nothing has been saved.';
      status.tabIndex = -1; status.focus();
    }
  });
}
for (const form of document.querySelectorAll('.stage-form')) {
  form.addEventListener('submit', event => {
    event.preventDefault();
    const draft = {reflection: form.elements.reflection.value};
    for (const field of form.querySelectorAll('[data-draft-field]')) draft[field.dataset.draftField] = field.value;
    send(form, `/api/students/${form.dataset.student}/stages/${form.dataset.stage}`, {action: event.submitter?.value || 'save', revision: Number(form.dataset.revision), draft});
  });
}
