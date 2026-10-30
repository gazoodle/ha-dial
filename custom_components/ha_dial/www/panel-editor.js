import { openOptions } from './editor/options.js';
import { DOMAINS } from './editor/catalogue.js';
import { conditionsEditor } from './editor/conditions.js';

class HaDialPanelEditor extends customElements.get('ha-dial-card-editor') {
  render() {
    if (!this.config || !this._hass) return;
    if (!this.initialised) {
      this.initialised = true;
      this.innerHTML = `<div class="editor-workspace"><section class="editor-tree"><div class="section-title"><div><span class="eyebrow">YOUR DIAL</span><h3>Pages</h3></div><button class="chip add-page" type="button">+ Page</button></div><p class="editor-help">Choose a page or control to edit it. Drag the handle to rearrange.</p><div class="tree"></div></section><section class="inspector"><div class="inspector-content"></div></section></div><details class="advanced-details"><summary>Advanced · template &amp; theme</summary><ha-form class="settings"></ha-form><ha-form class="advanced"></ha-form></details><span class="sr-only" role="status"></span>`;
      this.querySelector('.add-page').addEventListener('click', () => this.addPage(this.selectedPage || this.config.pages[0]?.id));
      for (const name of ['settings','advanced']) this.querySelector('.' + name).addEventListener('value-changed', event => {
        event.stopPropagation(); this.changed({...this.config, ...event.detail.value});
      });
    }
    for (const form of [this.querySelector('.settings'),this.querySelector('.advanced')]) { form.hass = this._hass; form.data = this.config; }
    this.querySelector('.settings').schema = [{name:'theme',selector:{select:{options:['ember','verdant','cobalt','rose','acid','alloy']}}}];
    this.querySelector('.settings').computeLabel = () => 'Default theme';
    this.querySelector('.advanced').schema = [{name:'template',selector:{template:{}}}];
    this.querySelector('.advanced').computeLabel = () => 'Page template';
    if (this.treePages !== this.config.pages) this.renderTree();
    else for (const form of this.querySelectorAll('.inspector ha-form')) form.hass = this._hass;
  }

  addPage(parent) {
    if (!parent) return;
    const id = 'page_' + Array.from(crypto.getRandomValues(new Uint32Array(2))).join('_');
    this.expanded ||= new Set(); this.expanded.add(parent); this.selectedPage = id; this.selectedEntity = undefined;
    this.changed({...this.config,pages:[...this.config.pages,{id,title:'New page',parent,entities:[]}]});
    this.renderTree();
  }

  renderTree() {
    const pages = this.config.pages, tree = this.querySelector('.tree');
    this.selectedPage = pages.some(page => page.id === this.selectedPage) ? this.selectedPage : pages[0]?.id;
    this.expanded ||= new Set(pages.filter(page => !page.parent).map(page => page.id));
    const children = new Map();
    for (const page of pages) { if (!children.has(page.parent)) children.set(page.parent, []); children.get(page.parent).push(page); }
    tree.replaceChildren();
    const row = (page, depth) => {
      const line = document.createElement('div'); line.className = 'page-row'; line.style.paddingLeft = `${depth * 16}px`;
      line.dataset.kind = 'page'; line.dataset.id = page.id;
      const expand = document.createElement('button'); expand.type = 'button'; expand.className = 'expand';
      expand.textContent = this.expanded.has(page.id) ? '▾' : '▸'; expand.setAttribute('aria-label', `${this.expanded.has(page.id) ? 'Collapse' : 'Expand'} ${page.title}`);
      expand.addEventListener('click', () => { this.expanded.has(page.id) ? this.expanded.delete(page.id) : this.expanded.add(page.id); this.renderTree(); });
      const pick = document.createElement('button'); pick.type = 'button'; pick.className = 'pick'; pick.textContent = page.title || 'Untitled page';
      pick.setAttribute('aria-pressed', String(this.selectedPage === page.id && !this.selectedEntity));
      pick.addEventListener('click', () => { this.selectedPage = page.id; this.selectedEntity = undefined; this.renderTree(); });
      line.append(expand,pick); if (page.parent) line.append(this.handle({kind:'page',id:page.id},'Move ' + page.title)); tree.append(line);
      if (!this.expanded.has(page.id)) return;
      for (const item of this.entities(page.id)) {
        const id = typeof item === 'string' ? item : item.entity_id;
        const control = document.createElement('div'); control.className = 'control-row'; control.style.paddingLeft = `${(depth + 1) * 16 + 24}px`;
        control.dataset.kind = 'entity'; control.dataset.page = page.id; control.dataset.id = id;
        const button = document.createElement('button'); button.type = 'button'; button.className = 'pick';
        button.textContent = (typeof item === 'object' && item.label) || this._hass.states?.[id]?.attributes?.friendly_name || id;
        button.setAttribute('aria-pressed', String(this.selectedPage === page.id && this.selectedEntity === id));
        button.addEventListener('click', () => { this.selectedPage = page.id; this.selectedEntity = id; this.renderTree(); });
        control.append(button,this.handle({kind:'entity',page:page.id,id},'Move ' + button.textContent)); tree.append(control);
      }
      for (const child of children.get(page.id) || []) row(child,depth + 1);
    };
    for (const root of pages.filter(page => !page.parent || !pages.some(p => p.id === page.parent))) row(root,0);
    this.treePages = pages;
    this.renderInspector();
  }

  renderInspector() {
    const panel = this.querySelector('.inspector-content'); panel.replaceChildren();
    const page = this.config.pages.find(item => item.id === this.selectedPage); if (!page) return;
    const entity = this.selectedEntity;
    const head = document.createElement('div'); head.className = 'inspector-head';
    const eyebrow = document.createElement('span'); eyebrow.className = 'eyebrow'; eyebrow.textContent = entity ? 'CONTROL' : 'PAGE';
    const title = document.createElement('h3'); title.textContent = entity ? (this._hass.states?.[entity]?.attributes?.friendly_name || entity) : (page.title || 'Untitled page');
    const detail = document.createElement('p'); detail.className = 'editor-help'; detail.textContent = entity || (page.parent ? 'A page in your Dial' : 'Your Dial’s starting page');
    head.append(eyebrow,title,detail); panel.append(head);
    const button = (label, action, extra = '') => { const node = document.createElement('button'); node.type = 'button'; node.className = `chip ${extra}`; node.textContent = label; node.addEventListener('click',action); return node; };
    const actions = document.createElement('div'); actions.className = 'editor-actions';
    actions.append(button(entity ? 'Edit control' : 'Appearance', () => openOptions(this,page.id,entity), 'accent'));
    if (entity) actions.append(button('Remove control', () => { this.selectedEntity = undefined; this.setEntities(page.id,this.entities(page.id).filter(item => (typeof item === 'string' ? item : item.entity_id) !== entity)); }, 'danger'));
    else {
      actions.append(button('+ Subpage', () => this.addPage(page.id)));
      if (page.parent) actions.append(button('Remove page', () => { if (!window.confirm('Remove this page? Its subpages will move up one level.')) return; this.selectedPage = page.parent; this.changed({...this.config,pages:this.config.pages.filter(item => item.id !== page.id).map(item => item.parent === page.id ? {...item,parent:page.parent} : item)}); this.renderTree(); }, 'danger'));
    }
    panel.append(actions);
    if (!entity) {
      const label = document.createElement('p'); label.className = 'inspector-label'; label.textContent = 'ADD A CONTROL'; panel.append(label);
      const form = document.createElement('ha-form'); form.hass = this._hass; form.data = {};
      form.schema = [{name:'entity',selector:{entity:{filter:{domain:DOMAINS}}}}]; form.computeLabel = () => 'Choose an entity';
      form.addEventListener('value-changed', event => { event.stopPropagation(); const id = event.detail.value.entity; if (id && !this.entities(page.id).some(item => (typeof item === 'string' ? item : item.entity_id) === id)) { this.selectedEntity = id; this.expanded.add(page.id); this.setEntities(page.id,[...this.entities(page.id),id]); } });
      panel.append(form);
    }
    const entry = entity ? this.entities(page.id).find(item => (typeof item === 'string' ? item : item.entity_id) === entity) : page;
    const visibilityTitle = document.createElement('p'); visibilityTitle.className = 'inspector-label'; visibilityTitle.textContent = 'VISIBILITY'; panel.append(visibilityTitle);
    panel.append(conditionsEditor(this._hass, typeof entry === 'string' ? [] : entry.conditions, conditions => {
      const pages = this.config.pages.map(item => {
        if (item.id !== page.id) return item;
        if (!entity) return {...item,conditions};
        const entities = this.entities(page.id).map(value => (typeof value === 'string' ? value : value.entity_id) === entity ? {...(typeof value === 'string' ? {entity_id:value} : value),conditions} : value);
        const updated = {...item,entities}; delete updated.lights; return updated;
      });
      this.changed({...this.config,pages}); this.treePages = pages;
    }));
  }
}

customElements.define('ha-dial-panel-editor', HaDialPanelEditor);
