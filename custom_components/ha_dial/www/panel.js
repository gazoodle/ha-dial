import { defaultConfig } from './editor.js';
import './panel-editor.js';
if (!customElements.get('ha-dial-card')) await import(`./ha-dial-card.js${new URL(import.meta.url).search}`);

class HaDialPanel extends HTMLElement {
  connectedCallback() {
    if (this.initialised) return;
    this.initialised = true;
    this.loaded = false;
    this.innerHTML = `<style>
      ha-dial-panel{--bg:#07170f;--surface:#0f2419;--surface-2:#143022;--border:#21402f;--text:#eef5ef;--muted:#9db3a4;--accent:#7bd1a0;--on-accent:#062117;--bad:#ff7a6b;--primary-text-color:var(--text);--secondary-text-color:var(--muted);--primary-color:var(--accent);--card-background-color:var(--surface);--secondary-background-color:var(--surface-2);--divider-color:var(--border);display:block;color:var(--text);background:var(--bg);min-height:100%;font:15px/1.45 Inter,system-ui,sans-serif}
      ha-dial-panel *{box-sizing:border-box} ha-dial-panel .bar{display:flex;align-items:center;gap:16px;padding:14px 24px;background:var(--app-header-background-color,var(--card-background-color));color:var(--app-header-text-color,var(--primary-text-color))}
      ha-dial-panel .bar h1{font-size:20px;margin:0;font-weight:600} ha-dial-panel .menu{border:0;background:none;color:inherit;font-size:24px;cursor:pointer}
      ha-dial-panel main{max-width:1280px;margin:auto;padding:28px 24px 64px} ha-dial-panel .intro h2{font-size:28px;margin:0 0 8px} ha-dial-panel p{color:var(--secondary-text-color);line-height:1.5}
      ha-dial-panel .toolbar{display:flex;align-items:end;gap:14px;flex-wrap:wrap;margin:24px 0} ha-dial-panel label{display:grid;gap:7px;font-weight:600;min-width:220px;flex:1;max-width:380px}
      ha-dial-panel button{font:inherit;border-radius:10px;padding:8px 14px;color:var(--text);background:var(--surface-2);border:1px solid var(--border);cursor:pointer}
      ha-dial-panel button:hover:not(:disabled),ha-dial-panel button:focus-visible{outline:none;box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 35%,transparent);filter:brightness(1.08)}
      ha-dial-panel .save{background:var(--accent);color:var(--on-accent);border-color:transparent;font-weight:600} ha-dial-panel button:disabled{opacity:.5;cursor:default}
      ha-dial-panel .layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,360px);gap:20px;align-items:start} ha-dial-panel .box{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:22px;min-width:0}
      ha-dial-panel .box h3{margin:0;font-size:19px} ha-dial-panel .preview{position:sticky;top:20px} ha-dial-panel .preview p{font-size:14px} ha-dial-panel [role=alert]{color:var(--bad);white-space:pre-wrap} ha-dial-panel .state{font-size:10px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;border-radius:12px;padding:3px 9px;background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent)}
      ha-dial-panel .bar{background:var(--surface);color:var(--text);border-bottom:1px solid var(--border)} ha-dial-panel p{color:var(--muted)}
      ha-dial-panel .devices{display:flex;flex-wrap:wrap;gap:8px} ha-dial-panel .chip{display:inline-flex;align-items:center;justify-content:center;gap:4px;padding:3px 10px;border:0;border-radius:12px;box-shadow:inset 0 0 0 1px var(--muted);background:var(--surface);color:var(--muted);font-size:10px;font-weight:500;letter-spacing:.04em;line-height:16px;text-transform:uppercase}
      ha-dial-panel .chip[aria-pressed=true],ha-dial-panel .chip.accent{box-shadow:none;background:var(--accent);color:var(--on-accent)} ha-dial-panel .chip.danger{color:var(--bad);box-shadow:inset 0 0 0 1px var(--bad)}
      ha-dial-panel .editor-workspace{display:grid;grid-template-columns:minmax(170px, .85fr) minmax(220px,1fr);gap:18px} ha-dial-panel .editor-tree{border-right:1px solid var(--border);padding-right:16px;min-width:0}
      ha-dial-panel .section-title{display:flex;justify-content:space-between;align-items:center;gap:8px} ha-dial-panel .eyebrow,ha-dial-panel .inspector-label{color:var(--accent);font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase} ha-dial-panel .editor-help{font-size:12px;line-height:1.4;margin:6px 0 12px}
      ha-dial-panel .page-row,ha-dial-panel .control-row{display:flex;align-items:center;min-width:0} ha-dial-panel .tree button{margin:0} ha-dial-panel .pick{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;text-align:left;border:0;background:none;padding:8px;color:var(--text);white-space:nowrap}
      ha-dial-panel .pick[aria-pressed=true]{background:color-mix(in srgb,var(--accent) 12%,transparent);box-shadow:inset 3px 0 0 var(--accent)} ha-dial-panel .expand,ha-dial-panel .grab{border:0;background:none;color:var(--muted);padding:5px;min-width:28px} ha-dial-panel .grab{cursor:grab;touch-action:none}
      ha-dial-panel .editor-actions{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0} ha-dial-panel .inspector-head h3{margin:4px 0} ha-dial-panel .inspector-label{margin:24px 0 8px} ha-dial-panel .advanced-details{margin-top:24px;border-top:1px solid var(--border);padding-top:14px} ha-dial-panel summary{cursor:pointer;color:var(--muted)}
      ha-dial-panel .sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)} ha-dial-panel .drop-before{box-shadow:0 -3px var(--accent)} ha-dial-panel .drop-after{box-shadow:0 3px var(--accent)} ha-dial-panel .drop-inside{outline:2px solid var(--accent)}
      ha-dial-panel .options-dialog{width:min(600px,calc(100vw - 24px));max-height:calc(100dvh - 40px);padding:0;border:1px solid var(--border);border-radius:18px;background:var(--surface);color:var(--text);overflow:hidden;box-shadow:0 24px 60px #0007} ha-dial-panel .options-dialog[open]{display:flex;flex-direction:column} ha-dial-panel .options-dialog::backdrop{background:#0009;backdrop-filter:blur(3px)}
      ha-dial-panel .options-head{padding:16px 18px 6px} ha-dial-panel .options-head h3{margin:0} ha-dial-panel .options-body{min-height:0;overflow:auto;padding:10px 18px 6px} ha-dial-panel .options-foot{flex:none;display:flex;justify-content:flex-end;gap:8px;padding:14px 18px 16px;border-top:1px solid var(--border)} ha-dial-panel .options-foot button:last-child{background:var(--accent);color:var(--on-accent)} ha-dial-panel textarea{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:10px;font:inherit}
      ha-dial-panel .options-dialog{width:min(840px,calc(100vw - 24px))} ha-dial-panel .options-galleries h4{margin:20px 0 10px;color:var(--text);font-size:14px} ha-dial-panel .gallery-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px} ha-dial-panel button.gallery-choice{display:grid;justify-items:center;gap:7px;min-width:0;padding:10px 6px;background:var(--bg);border:1px solid var(--border);border-radius:14px;color:var(--muted);font-size:11px;text-transform:capitalize;white-space:normal} ha-dial-panel .gallery-choice[aria-pressed=true]{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 8%,var(--bg));color:var(--text)} ha-dial-panel .gallery-choice canvas{width:min(100%,104px);aspect-ratio:1;border-radius:50%}
      ha-dial-panel .condition-hint{font-size:12px} ha-dial-panel .condition-row{border:1px solid var(--border);border-radius:10px;background:var(--bg);margin:8px 0;padding:10px} ha-dial-panel .condition-row summary{color:var(--text);font-size:13px;font-weight:600;overflow-wrap:anywhere} ha-dial-panel .condition-row ha-form{display:block;margin:12px 0} ha-dial-panel .condition-add{position:relative;margin:10px 0} ha-dial-panel .condition-add summary{list-style:none;width:max-content;cursor:pointer} ha-dial-panel .condition-menu{position:relative;z-index:2;display:grid;gap:4px;margin-top:6px;padding:6px;border:1px solid var(--border);border-radius:10px;background:var(--surface-2)} ha-dial-panel .condition-menu button{text-align:left;border:0;background:none;padding:7px 10px}
      @media(prefers-color-scheme:light){ha-dial-panel{--bg:#f4f6f1;--surface:#fff;--surface-2:#eef4ee;--border:#d9e3da;--text:#13241a;--muted:#5d7064;--accent:#1f7a4d;--on-accent:#fff;--bad:#c2412d}}
      @media(max-width:800px){ha-dial-panel main{padding:20px 16px 48px} ha-dial-panel .layout{grid-template-columns:1fr} ha-dial-panel .preview{position:static} ha-dial-panel .bar{padding:12px 16px}} @media(max-width:550px){ha-dial-panel .editor-workspace{grid-template-columns:1fr} ha-dial-panel .editor-tree{border-right:0;border-bottom:1px solid var(--border);padding:0 0 16px}}
    </style><header class="bar"><button class="menu" aria-label="Open sidebar">☰</button><h1>HA Dial</h1></header>
    <main><div class="intro"><h2>Make your Dial yours</h2><p>Choose a Dial, arrange its pages and controls, then try them in the preview.</p></div>
    <div class="toolbar"><label>Dial<span class="devices"></span><select aria-label="Dial" hidden></select></label><button class="save" disabled>Save and apply</button><span class="state" role="status"></span></div>
    <p class="error" role="alert" hidden></p><p class="empty" hidden>No Dials found. Add a Dial through the ESPHome integration, then return here.</p>
    <div class="layout" hidden><section class="box"><ha-dial-panel-editor></ha-dial-panel-editor></section>
    <section class="box preview"><h3>Try your Dial</h3><p>Changes here are a safe preview. They won’t operate your devices until applied.</p><ha-dial-card></ha-dial-card></section></div></main>`;
    this.querySelector('.menu').addEventListener('click', () => this.dispatchEvent(new CustomEvent('hass-toggle-menu', {bubbles:true, composed:true})));
    this.querySelector('select').addEventListener('change', (event) => this.selectDevice(event.target.value));
    this.querySelector('.save').addEventListener('click', () => this.save());
    this.beforeUnload = (event) => { if (this.dirty) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', this.beforeUnload);
    this.querySelector('ha-dial-panel-editor').addEventListener('config-changed', (event) => {
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
    this.querySelector('ha-dial-panel-editor').hass = hass;
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
      const buttons = this.querySelector('.devices'); buttons.replaceChildren();
      select.replaceChildren();
      for (const device of devices) {
        const option = document.createElement('option'); option.value = device;
        option.textContent = device.replaceAll('_', ' ') + (services.includes(device) ? '' : ' (offline)'); select.append(option);
        const button = document.createElement('button'); button.type = 'button'; button.className = 'chip'; button.dataset.device = device; button.textContent = option.textContent;
        button.addEventListener('click', () => this.selectDevice(device)); buttons.append(button);
      }
      this.querySelector('.empty').hidden = devices.length > 0;
      this.querySelector('.layout').hidden = !devices.length;
      this.loaded = true;
      if (devices.length) this.selectDevice(devices[0], true);
    } catch (error) { this.showError(error); }
    finally { this.loading = false; }
  }

  selectDevice(device, force = false) {
    if (!force && (this.saving || device === this.device)) return;
    if (!force && this.dirty && !window.confirm('Discard unsaved changes to this Dial?')) {
      this.querySelector('select').value = this.device; return;
    }
    this.device = device;
    this.querySelector('select').value = device;
    for (const button of this.querySelectorAll('.devices button')) button.setAttribute('aria-pressed', String(button.dataset.device === device));
    this.draft = {...defaultConfig(), ...(this.definitions[device] || {}), device};
    this.saved = this.definitions[device] ? JSON.stringify(this.definition()) : '';
    this.dirty = !this.definitions[device];
    const editor = this.querySelector('ha-dial-panel-editor');
    editor.selectedPage = editor.selectedEntity = editor.expanded = editor.treePages = undefined;
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
