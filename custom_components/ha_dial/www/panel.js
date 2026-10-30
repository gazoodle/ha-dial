import { defaultConfig } from './editor.js';
if (!customElements.get('ha-dial-card')) await import(`./ha-dial-card.js${new URL(import.meta.url).search}`);

class HaDialPanel extends HTMLElement {
  connectedCallback() {
    if (this.initialised) return;
    this.initialised = true;
    this.loaded = false;
    this.innerHTML = `<style>
      ha-dial-panel{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family, sans-serif)}
      ha-dial-panel *{box-sizing:border-box} ha-dial-panel .bar{display:flex;align-items:center;gap:16px;padding:14px 24px;background:var(--app-header-background-color,var(--card-background-color));color:var(--app-header-text-color,var(--primary-text-color))}
      ha-dial-panel .bar h1{font-size:20px;margin:0;font-weight:600} ha-dial-panel .menu{border:0;background:none;color:inherit;font-size:24px;cursor:pointer}
      ha-dial-panel main{max-width:1280px;margin:auto;padding:28px 24px 64px} ha-dial-panel .intro h2{font-size:28px;margin:0 0 8px} ha-dial-panel p{color:var(--secondary-text-color);line-height:1.5}
      ha-dial-panel .toolbar{display:flex;align-items:end;gap:14px;flex-wrap:wrap;margin:24px 0} ha-dial-panel label{display:grid;gap:7px;font-weight:600;min-width:220px;flex:1;max-width:380px}
      ha-dial-panel select,ha-dial-panel button{font:inherit;border-radius:10px;padding:10px 14px;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);cursor:pointer}
      ha-dial-panel .save{background:var(--primary-color);color:var(--text-primary-color,#fff);border-color:transparent;font-weight:600} ha-dial-panel button:disabled{opacity:.5;cursor:default}
      ha-dial-panel .layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,400px);gap:20px;align-items:start} ha-dial-panel .box{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:16px;padding:22px;min-width:0}
      ha-dial-panel .box h3{margin:0;font-size:19px} ha-dial-panel .preview{position:sticky;top:20px} ha-dial-panel .preview p{font-size:14px} ha-dial-panel [role=alert]{color:var(--error-color);white-space:pre-wrap} ha-dial-panel .state{font-size:14px}
      ha-dial-panel ha-dial-card-editor .hint:first-of-type{display:none}
      @media(max-width:800px){ha-dial-panel main{padding:20px 16px 48px} ha-dial-panel .layout{grid-template-columns:1fr} ha-dial-panel .preview{position:static;grid-row:1} ha-dial-panel .bar{padding:12px 16px}}
    </style><header class="bar"><button class="menu" aria-label="Open sidebar">☰</button><h1>HA Dial</h1></header>
    <main><div class="intro"><h2>Make your Dial yours</h2><p>Choose a Dial, arrange its pages and controls, then try them in the preview.</p></div>
    <div class="toolbar"><label>Dial<select aria-label="Dial"></select></label><button class="save" disabled>Save and apply</button><span class="state" role="status"></span></div>
    <p class="error" role="alert" hidden></p><p class="empty" hidden>No Dials found. Add a Dial through the ESPHome integration, then return here.</p>
    <div class="layout" hidden><section class="box"><h3>Pages and controls</h3><p>Build the screens your Dial will show.</p><ha-dial-card-editor></ha-dial-card-editor></section>
    <section class="box preview"><h3>Try your Dial</h3><p>Changes here are a safe preview. They won’t operate your devices until applied.</p><ha-dial-card></ha-dial-card></section></div></main>`;
    this.querySelector('.menu').addEventListener('click', () => this.dispatchEvent(new CustomEvent('hass-toggle-menu', {bubbles:true, composed:true})));
    this.querySelector('select').addEventListener('change', (event) => this.selectDevice(event.target.value));
    this.querySelector('.save').addEventListener('click', () => this.save());
    this.beforeUnload = (event) => { if (this.dirty) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', this.beforeUnload);
    this.querySelector('ha-dial-card-editor').addEventListener('config-changed', (event) => {
      event.stopPropagation();
      this.draft = event.detail.config;
      this.dirty = JSON.stringify(this.definition()) !== this.saved;
      this.updateState();
      this.preview();
    });
    this.refresh();
  }

  disconnectedCallback() { window.removeEventListener('beforeunload', this.beforeUnload); this.initialised = false; }
  set hass(hass) {
    this._hass = hass;
    if (!this.initialised) return;
    this.querySelector('ha-dial-card-editor').hass = hass;
    this.querySelector('ha-dial-card').hass = hass;
    if (!this.loaded) this.refresh();
  }

  async refresh() {
    if (!this._hass || this.loading || this.loaded) return;
    this.loading = true;
    try {
      this.definitions = await this._hass.callWS({type:'ha_dial/definitions'});
      const suffix = '_ha_dial_show_view';
      const services = Object.keys(this._hass.services?.esphome || {}).filter(name => name.endsWith(suffix)).map(name => name.slice(0, -suffix.length));
      const devices = [...new Set([...services, ...Object.keys(this.definitions)])].filter(name => /^[a-z0-9_]{1,64}$/.test(name) && name !== 'preview' && !name.startsWith('preview_')).sort();
      const select = this.querySelector('select');
      select.replaceChildren();
      for (const device of devices) {
        const option = document.createElement('option'); option.value = device;
        option.textContent = device.replaceAll('_', ' ') + (services.includes(device) ? '' : ' (offline)'); select.append(option);
      }
      this.querySelector('.empty').hidden = devices.length > 0;
      this.querySelector('.layout').hidden = !devices.length;
      this.loaded = true;
      if (devices.length) this.selectDevice(devices[0], true);
    } catch (error) { this.showError(error); }
    finally { this.loading = false; }
  }

  selectDevice(device, force = false) {
    if (!force && this.dirty && !window.confirm('Discard unsaved changes to this Dial?')) {
      this.querySelector('select').value = this.device; return;
    }
    this.device = device;
    this.querySelector('select').value = device;
    this.draft = {...defaultConfig(), ...(this.definitions[device] || {}), device};
    this.saved = this.definitions[device] ? JSON.stringify(this.definition()) : '';
    this.dirty = !this.definitions[device];
    const editor = this.querySelector('ha-dial-card-editor');
    editor.panelMode = true; editor.setConfig(this.draft); editor.hass = this._hass;
    this.querySelector('.error').hidden = true;
    this.updateState(); this.preview();
  }

  definition() { return {template:this.draft.template || '', theme:this.draft.theme || 'ember', pages:this.draft.pages}; }
  preview() {
    const card = this.querySelector('ha-dial-card');
    card.setConfig({...this.draft, device:'preview'}); card.hass = this._hass;
  }
  updateState() {
    this.querySelector('.save').disabled = !this.device || !this.dirty || this.saving;
    this.querySelector('.state').textContent = this.saving ? 'Saving…' : this.dirty ? 'Unsaved changes' : 'Saved';
  }
  async save() {
    const device = this.device, definition = this.definition(), snapshot = JSON.stringify(definition);
    this.saving = true; this.querySelector('select').disabled = true; this.updateState();
    try {
      const result = await this._hass.callWS({type:'ha_dial/configure', device, definition});
      this.definitions[device] = definition;
      if (this.device === device) {
        this.saved = snapshot; this.dirty = JSON.stringify(this.definition()) !== snapshot;
        this.querySelector('.error').hidden = true;
        this.querySelector('.state').textContent = ({applied:'Applied to Dial', sent:'Sent to Dial', waiting:'Saved; waiting for Dial', failed:'Saved; deployment failed'})[result.deployment] || 'Saved';
      }
    } catch (error) { this.showError(error); }
    finally { this.saving = false; this.querySelector('select').disabled = false; this.querySelector('.save').disabled = !this.dirty; }
  }
  showError(error) { const node = this.querySelector('.error'); node.textContent = error.message || String(error); node.hidden = false; }
}

customElements.define('ha-dial-panel', HaDialPanel);
