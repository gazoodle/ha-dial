import { confirmDialog, openOptions } from './editor/options.js';
import { DOMAINS, PAGED_STYLES } from './editor/catalogue.js';
import { conditionsEditor } from './editor/conditions.js';

const LEFT_OUT = {hidden:'hidden in HA',disabled:'disabled',diagnostic:'diagnostic or configuration',unsupported:'not supported on the Dial',excluded:'excluded by you',not_exposed:'not exposed to Assist',security:'security items left out',out_of_scope:'outside this floor or area'};
const styleName = (style) => style.replace(/^NAV-/,'').toLowerCase();

class HaDialPanelEditor extends customElements.get('ha-dial-card-editor') {
  disconnectedCallback() { this.conditionEditor?.destroy(); }
  render() {
    if (!this.config || !this._hass) return;
    if (!this.initialised) {
      this.initialised = true;
      this.innerHTML = `<div class="editor-workspace"><section class="editor-tree"><div class="section-title"><div><span class="eyebrow">YOUR DIAL</span><h3>Pages</h3></div><button class="chip add-page" type="button">+ Page</button></div><p class="editor-help">Choose a page or control to edit it. Drag the handle to rearrange.</p><div class="tree"></div></section><section class="inspector"><div class="inspector-content"></div></section></div><div class="advanced-details"><button class="chip dial-settings" type="button">Dial settings</button></div><dialog class="dial-settings-dialog options-dialog" aria-label="Dial settings"><header class="options-head"><h3>Dial settings</h3></header><div class="options-body"><div class="dialog-tabs" role="tablist" aria-label="Dial settings"><button type="button" role="tab" aria-selected="true" data-settings-tab="theme">Theme</button><button type="button" role="tab" aria-selected="false" data-settings-tab="template">Advanced</button></div><div class="theme-settings" role="tabpanel"><ha-form class="settings"></ha-form></div><div class="template-settings" role="tabpanel" hidden><ha-form class="advanced"></ha-form></div></div><footer class="options-foot"><button type="button" class="settings-done">Done</button></footer></dialog><span class="sr-only" role="status"></span>`;
      this.querySelector('.add-page').addEventListener('click', () => { const selected = this.config.pages.find(page => page.id === this.selectedPage); this.addPage(selected?.explorer ? selected.parent : selected?.id || this.config.pages[0]?.id); });
      const settingsDialog = this.querySelector('.dial-settings-dialog');
      this.querySelector('.dial-settings').addEventListener('click', () => settingsDialog.showModal());
      this.querySelector('.settings-done').addEventListener('click', () => settingsDialog.close());
      for (const tab of this.querySelectorAll('[data-settings-tab]')) tab.addEventListener('click', () => {
        for (const sibling of this.querySelectorAll('[data-settings-tab]')) sibling.setAttribute('aria-selected',String(sibling === tab));
        this.querySelector('.theme-settings').hidden = tab.dataset.settingsTab !== 'theme';
        this.querySelector('.template-settings').hidden = tab.dataset.settingsTab !== 'template';
      });
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

  addPage(parent, fields = {title:'New page'}) {
    if (!parent) return;
    const id = 'page_' + Array.from(crypto.getRandomValues(new Uint32Array(2))).join('_');
    this.expanded ||= new Set(); this.expanded.add(parent); this.selectedPage = id; this.selectedEntity = undefined;
    this.changed({...this.config,pages:[...this.config.pages,{id,parent,entities:[],...fields}]});
    this.renderTree();
  }

  addExplorer(parent) { this.addPage(parent,{title:'Explorer',icon:'mdi:compass-outline',style:'NAV-LIST',explorer:{}}); }

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
      const pick = document.createElement('button'); pick.type = 'button'; pick.className = 'pick'; pick.textContent = (page.title || 'Untitled page') + (page.explorer ? ' · Explorer' : '');
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
    this.conditionEditor?.destroy();
    const panel = this.querySelector('.inspector-content'); panel.replaceChildren();
    const page = this.config.pages.find(item => item.id === this.selectedPage); if (!page) return;
    if (page.explorer) { this.renderExplorer(panel,page); return; }
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
      actions.append(button('+ Explorer', () => this.addExplorer(page.id)));
      if (page.parent) actions.append(button('Remove page', () => this.removePage(page), 'danger'));
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
    this.conditionEditor = conditionsEditor(this._hass, typeof entry === 'string' ? [] : entry.conditions, conditions => {
      const pages = this.config.pages.map(item => {
        if (item.id !== page.id) return item;
        if (!entity) return {...item,conditions};
        const entities = this.entities(page.id).map(value => (typeof value === 'string' ? value : value.entity_id) === entity ? {...(typeof value === 'string' ? {entity_id:value} : value),conditions} : value);
        const updated = {...item,entities}; delete updated.lights; return updated;
      });
      this.changed({...this.config,pages}); this.treePages = pages;
    }); panel.append(this.conditionEditor);
  }

  renderExplorer(panel, page) {
    const head = document.createElement('div'); head.className = 'inspector-head';
    const eyebrow = document.createElement('span'); eyebrow.className = 'eyebrow'; eyebrow.textContent = 'EXPLORER';
    const title = document.createElement('h3'); title.textContent = page.title || 'Explorer';
    const detail = document.createElement('p'); detail.className = 'editor-help'; detail.textContent = 'Takes one slot on its parent page and fills itself from your floors, areas and entities.';
    head.append(eyebrow,title,detail); panel.append(head);

    const options = () => this.config.pages.find(item => item.id === page.id).explorer;
    const store = (explorer) => { const pages = this.config.pages.map(item => item.id === page.id ? {...item,explorer} : item); this.changed({...this.config,pages}); this.treePages = pages; };
    const chip = (label, action, extra = '') => { const node = document.createElement('button'); node.type = 'button'; node.className = `chip ${extra}`; node.textContent = label; node.addEventListener('click',action); return node; };
    const actions = document.createElement('div'); actions.className = 'editor-actions';
    const generatedPage = () => ({label:page.title,count:this.explorerResult?.items?.length || 0,children:(this.explorerResult?.items || []).map(item => ({title:item.label}))});
    const shuffle = chip('Shuffle styles', () => { store({...options(),shuffle:(options().shuffle || 0) + 1}); refresh(); });
    actions.append(chip('Appearance', () => openOptions(this,page.id,undefined,generatedPage()), 'accent'),shuffle);
    if (page.parent) actions.append(chip('Remove page', () => this.removePage(page), 'danger'));
    panel.append(actions);

    const form = document.createElement('ha-form'); form.hass = this._hass;
    const labels = {scope:'Covers',floor_id:'Floor',area_id:'Area',random:'Random style on every page',long_style:'Style for pages over 8 items',assist_only:'Only entities exposed to Assist',include_security:'Include locks, alarms and doors',exclude:'Leave out these entities'};
    const helpers = {random:'Shows off every style. A page keeps its style until you shuffle.',long_style:'Any style works up to 8 items. Longer pages need one that scrolls or pages.',include_security:'They always ask for confirmation.',assist_only:'Reads your Assist settings and never changes them.'};
    form.computeLabel = (field) => labels[field.name]; form.computeHelper = (field) => helpers[field.name];
    const fill = () => {
      const current = options(), scope = current.area_id !== undefined ? 'area' : current.floor_id !== undefined ? 'floor' : 'home';
      form.data = {long_style:'NAV-LIST',include_security:true,random:false,assist_only:false,exclude:[],...current,scope};
      form.schema = [
        {name:'scope',selector:{select:{options:[{value:'home',label:'Whole home'},{value:'floor',label:'One floor'},{value:'area',label:'One area'}]}}},
        ...(scope === 'floor' ? [{name:'floor_id',selector:{floor:{}}}] : scope === 'area' ? [{name:'area_id',selector:{area:{}}}] : []),
        {name:'random',selector:{boolean:{}}},
        {name:'long_style',selector:{select:{options:PAGED_STYLES.map(value => ({value,label:styleName(value)}))}}},
        {name:'assist_only',selector:{boolean:{}}},{name:'include_security',selector:{boolean:{}}},
        {name:'exclude',selector:{entity:{multiple:true,filter:{domain:DOMAINS}}}},
      ];
      shuffle.hidden = !current.random;
    };
    form.addEventListener('value-changed', event => {
      event.stopPropagation();
      const {scope, ...values} = event.detail.value, explorer = {...options(),...values};
      if (scope !== 'floor') delete explorer.floor_id; else explorer.floor_id ??= '';
      if (scope !== 'area') delete explorer.area_id; else explorer.area_id ??= '';
      store(explorer); fill(); refresh();
    });
    panel.append(form);

    const summary = document.createElement('p'); summary.className = 'editor-help'; summary.setAttribute('role','status');
    const tree = document.createElement('div'); tree.className = 'explorer-pages tree';
    panel.append(summary,tree);
    const rows = (items, depth) => items.filter(item => item.children).flatMap(item => {
      const row = document.createElement('div'); row.className = 'page-row'; row.style.paddingLeft = `${depth * 16}px`;
      const open = document.createElement('button'); open.type = 'button'; open.className = 'pick'; open.textContent = `${item.label} (${item.children.length}) · ${styleName(item.style)}`;
      open.addEventListener('click', () => openOptions(this,page.id,undefined,{key:item.id,label:item.label,style:item.style,count:item.children.length,children:item.children.map(child => ({title:child.label}))}));
      row.append(open); return [row,...rows(item.children,depth + 1)];
    });
    let sequence = this.explorerSequence = (this.explorerSequence || 0) + 1;
    const refresh = async () => {
      sequence = this.explorerSequence = this.explorerSequence + 1;
      const asked = sequence;
      try {
        const result = await this._hass.callWS({type:'ha_dial/explorer',options:options(),style:page.style || 'NAV-LIST'});
        if (asked !== this.explorerSequence) return;
        this.explorerResult = result;
        const gone = Object.entries(result.omitted).map(([reason,count]) => `${count} ${LEFT_OUT[reason] || reason}`);
        summary.textContent = `${result.shown} shown.${gone.length ? ` Left out: ${gone.join(', ')}.` : ''}`;
        tree.replaceChildren(...rows(result.items,0));
      } catch (error) { if (asked === this.explorerSequence) { summary.textContent = `Couldn’t read your home: ${error.message || error}`; tree.replaceChildren(); } }
    };
    fill(); refresh();
  }

  removePage(page) {
    const descendants = new Set([page.id]);
    let size; do { size = descendants.size; for (const item of this.config.pages) if (descendants.has(item.parent)) descendants.add(item.id); } while (size !== descendants.size);
    const count = descendants.size - 1, noun = count === 1 ? 'subpage' : 'subpages';
    confirmDialog(this, {title:'Remove page', message:`Remove “${page.title || 'Untitled page'}” and its controls? This takes effect when you save and apply.`, confirm:'Remove page',
      choices: count ? [
        {value:'move',label:`Move subpages up (${count} total)`,detail:'Direct subpages move to the parent page; their own subpages stay with them.'},
        {value:'remove',label:`Remove ${count === 1 ? 'the' : 'all'} ${count} ${noun}`,detail:'Remove every nested subpage and its controls too.'},
      ] : undefined,
      action: choice => { this.selectedPage=page.parent; this.selectedEntity=undefined; const pages=this.config.pages.filter(item=>choice === 'remove' ? !descendants.has(item.id) : item.id !== page.id).map(item=>choice !== 'remove' && item.parent === page.id ? {...item,parent:page.parent} : item); this.changed({...this.config,pages}); this.renderTree(); }
    });
  }
}

customElements.define('ha-dial-panel-editor', HaDialPanelEditor);
