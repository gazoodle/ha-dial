import { CONTROL_STYLES, CRISP_DEFAULTS, CRISP_HIDDEN, DEFAULTS, DEFAULT_STYLES, DOMAINS, FACE_SOURCES, NAV_STYLES, PICTURE_DEFAULTS, REQUIRES, SETTINGS, STYLE_SETTINGS } from './catalogue.js';
import { renderScene } from '../scene.js';

const number = (min, max, step = 1) => ({ number: { min, max, step, mode: 'box' } });
const select = (options) => ({ select: { options, mode: 'dropdown' } });
const labels = { title:'Page title', label:'Control label', icon:'Icon', style:'Atlas style', theme:'Theme', conditions:'Show when all conditions pass', confirm:'Confirm actions', css:'Advanced style', 'outer-border':'Outer border', 'border-width':'Border width', 'font-size':'Title size', 'icon-size':'Icon size', 'orbit-radius':'Orbit radius', 'highlight-radius':'Highlight radius', raster:'Crisp / Smooth', accent:'Accent colour', background:'Background colour', text:'Text colour', 'snake-line':'Snake line colour', 'snake-travelled':'Snake travelled colour' };
for (const [key, setting] of Object.entries(SETTINGS)) labels[key] = setting.label;
const defaultsFor = (raster) => ({...DEFAULTS, ...(raster === 'crisp' ? CRISP_DEFAULTS : {})});
const ranges = Object.entries(SETTINGS).filter(([,setting]) => setting.kind === 'number').map(([key,setting]) => [key,setting.low,setting.high]);
const appearanceKeys = [...Object.keys(SETTINGS), 'accent','background','text','surface','secondary','quiet','grid','snake-line','snake-travelled'];
const rebuildsSettings = (key) => key === 'raster' || Object.values(REQUIRES).some(([driver]) => driver === key);
const toggle = (raw) => ['true','on'].includes(raw) ? true : ['false','off'].includes(raw) ? false : raw;
// What a dialog shows: only settings this style reads, so every control has a visible effect.
const settingsFor = (style, raster) => (STYLE_SETTINGS[style] || STYLE_SETTINGS['NAV-ORBIT']).filter((key) => !(raster === 'crisp' && CRISP_HIDDEN.includes(key)));

function declarations(source) {
  const result = {};
  for (const declaration of (source || '').split(';')) {
    if (!declaration.trim()) continue;
    const at = declaration.indexOf(':');
    if (at < 0) throw new Error('Use property: value; in Advanced style.');
    const name = declaration.slice(0, at).trim(), raw = declaration.slice(at + 1).trim();
    if (!appearanceKeys.includes(name)) throw new Error(`Unsupported style property: ${name}`);
    result[name] = SETTINGS[name]?.kind === 'toggle' ? toggle(raw) : SETTINGS[name]?.kind === 'number' ? Number(raw.replace(/px$/, '')) : raw;
  }
  return result;
}

function validateConditions(conditions) {
  if (!Array.isArray(conditions)) throw new Error('Conditions must be a list.');
  for (const item of conditions) {
    if (item.enabled === false) continue;
    if (['and','or','not'].includes(item.condition)) {
      const children = item.conditions || item.options?.conditions;
      if (!Array.isArray(children) || !children.length) throw new Error('Logical conditions need at least one condition.');
      validateConditions(children);
    } else {
      if (!['state','numeric_state','template','time'].includes(item.condition)) throw new Error('Use state, numeric state, time, template or AND/OR/NOT visibility conditions.');
      if ('for' in (item.options || item)) throw new Error('Use an HA helper/template sensor for duration conditions.');
    }
  }
}

export function confirmDialog(host, {title, message, choices, confirm, action}) {
  const dialog = document.createElement('dialog'); dialog.className = 'options-dialog confirm-dialog'; dialog.setAttribute('aria-label',title);
  const head = document.createElement('header'); head.className='options-head'; const heading=document.createElement('h3'); heading.textContent=title; head.append(heading);
  const body=document.createElement('div'); body.className='options-body'; const description=document.createElement('p'); description.textContent=message; body.append(description);
  let selected=choices?.[0]?.value;
  if (choices) {
    const group=document.createElement('fieldset'); group.className='confirm-choices'; const legend=document.createElement('legend'); legend.textContent='What should happen to the subpages?'; group.append(legend);
    for (const choice of choices) { const label=document.createElement('label'); label.className='confirm-choice'; const radio=document.createElement('input'); radio.type='radio'; radio.name='page-removal'; radio.value=choice.value; radio.checked=choice.value===selected; radio.addEventListener('change',()=>{selected=choice.value;}); const text=document.createElement('span'); const name=document.createElement('strong'); name.textContent=choice.label; const detail=document.createElement('small'); detail.textContent=choice.detail; text.append(name,detail); label.append(radio,text); group.append(label); } body.append(group);
  }
  const foot=document.createElement('footer'); foot.className='options-foot'; const cancel=document.createElement('button'); cancel.type='button'; cancel.textContent='Cancel'; cancel.addEventListener('click',()=>dialog.close()); const submit=document.createElement('button'); submit.type='button'; submit.className='destructive'; submit.textContent=confirm; submit.addEventListener('click',()=>{dialog.close(); action(selected);}); foot.append(cancel,submit);
  dialog.addEventListener('close',()=>dialog.remove()); dialog.append(head,body,foot); host.append(dialog); dialog.showModal();
}

// `generated` is set for an Explorer: `key` names one of its generated pages, otherwise it's the Explorer itself.
export function openOptions(editor, pageId, entityId, generated) {
  editor.querySelector('.edit-options-dialog')?.remove();
  const page = editor.config.pages.find((candidate) => candidate.id === pageId);
  const entities = editor.entities(pageId);
  const overrideKey = generated?.key;
  const original = entityId ? entities.find((item) => (typeof item === 'string' ? item : item.entity_id) === entityId) : overrideKey ? {title:generated.label,style:generated.style,...page.explorer.pages?.[overrideKey]} : page;
  const item = typeof original === 'string' ? {entity_id:original} : {...original};
  const domain = entityId?.split('.')[0];
  const dialog = document.createElement('dialog'); dialog.className = 'options-dialog edit-options-dialog';
  dialog.setAttribute('aria-label', entityId ? `Edit ${domain} control` : 'Edit page');
  const heading = document.createElement('h3'); heading.textContent = entityId ? `Edit ${domain} control` : overrideKey ? `${generated.label} appearance` : 'Page appearance';
  const hint = document.createElement('p'); hint.textContent = 'Conditions are evaluated in Home Assistant. Visibility is not access control.';
  const error = document.createElement('p'); error.setAttribute('role','alert');
  const form = document.createElement('ha-form');
  const appearanceForm = document.createElement('ha-form');
  const conditionForm = document.createElement('ha-form');
  let options;
  try { options = {...page.appearance, ...declarations(page.css), ...item.appearance, ...declarations(item.css)}; }
  catch (reason) { error.textContent = reason.message; options = {...item.appearance}; }
  let draft = {...item,...options,clock_timezone:item.clock?.timezone || '',clock_world_zones:(item.clock?.world_zones || ['UTC','Europe/London','America/New_York','Asia/Tokyo']).join(', '),clock_moon_entity:item.clock?.moon_entity || '',clock_reserve_entity:item.clock?.reserve_entity || '',clock_weather_entity:item.clock?.weather_entity || '',clock_history_hours:item.clock?.history_hours ?? 24,clock_image_entity:item.clock?.image_entity || '',clock_action_0:item.clock?.action_entities?.[0] || '',clock_action_1:item.clock?.action_entities?.[1] || '',clock_refresh_entity:item.clock?.refresh_entity || '',clock_detection_entity:item.clock?.detection_entity || '',...Object.fromEntries((item.clock?.metrics || []).flatMap((metric,index)=>[[`metric_${index}_entity`,metric.entity_id],[`metric_${index}_label`,metric.label || ''],[`metric_${index}_minimum`,metric.minimum],[`metric_${index}_maximum`,metric.maximum]])),confirm:item.confirm ?? ['lock','alarm_control_panel','scene','button','input_button'].includes(domain), conditions:item.conditions || []};
  const metricSettings = (metric) => { const metrics = Array.from({length:6},(_,index)=>index).filter(index=>draft[`metric_${index}_entity`]).map(metric); return metrics.length ? {metrics} : {}; };
  const clockSettings = () => ({...(draft.clock_timezone ? {timezone:draft.clock_timezone.trim()} : {}),...(domain ? {} : {world_zones:draft.clock_world_zones.split(',').map(zone=>zone.trim()).filter(Boolean)}),...(draft.clock_action_0 || draft.clock_action_1 ? {action_entities:[draft.clock_action_0,draft.clock_action_1].filter(Boolean)} : {}),...(draft.clock_moon_entity ? {moon_entity:draft.clock_moon_entity} : {}),...(draft.clock_reserve_entity ? {reserve_entity:draft.clock_reserve_entity} : {}),...(draft.clock_weather_entity ? {weather_entity:draft.clock_weather_entity} : {}),...(draft.clock_image_entity ? {image_entity:draft.clock_image_entity} : {}),...(draft.clock_refresh_entity ? {refresh_entity:draft.clock_refresh_entity} : {}),...(draft.clock_detection_entity ? {detection_entity:draft.clock_detection_entity} : {}),...(Number.isInteger(draft.clock_history_hours) && draft.clock_history_hours !== 24 ? {history_hours:draft.clock_history_hours} : {}),...metricSettings(index=>({entity_id:draft[`metric_${index}_entity`],...(draft[`metric_${index}_label`] ? {label:draft[`metric_${index}_label`]} : {}),...(Number.isFinite(draft[`metric_${index}_minimum`]) ? {minimum:draft[`metric_${index}_minimum`]} : {}),...(Number.isFinite(draft[`metric_${index}_maximum`]) ? {maximum:draft[`metric_${index}_maximum`]} : {})}))});
  for (const field of [form, appearanceForm, conditionForm]) { field.hass = editor._hass; field.data = draft; }
  const sourceSelectors = {timezone:['clock_timezone',{text:{}}],world_zones:['clock_world_zones',{text:{}}],moon_entity:['clock_moon_entity',{entity:{domain:'sensor'}}],reserve_entity:['clock_reserve_entity',{entity:{domain:'sensor'}}],weather_entity:['clock_weather_entity',{entity:{domain:'weather'}}],history_hours:['clock_history_hours',number(1,168)],image_entity:['clock_image_entity',{entity:{domain:['camera','image']}}],refresh_entity:['clock_refresh_entity',{entity:{}}],detection_entity:['clock_detection_entity',{entity:{}}]};
  const sourceFields = () => {
    const sources = FACE_SOURCES[draft.style || item.style || (domain ? DEFAULT_STYLES[domain] : '')];
    if (!sources) return [];
    const actionSelector = {entity:{domain:DOMAINS.filter((name)=>!['camera','image'].includes(name))}};
    return [
      ...sources.fields.filter((field)=>field !== 'action_entities').map((field)=>({name:sourceSelectors[field][0],selector:sourceSelectors[field][1]})),
      ...(sources.fields.includes('action_entities') ? [{name:'clock_action_0',selector:actionSelector},{name:'clock_action_1',selector:actionSelector}] : []),
      ...Array.from({length:sources.metrics},(_,index)=>[{name:`metric_${index}_entity`,selector:{entity:{}}},{name:`metric_${index}_label`,selector:{text:{}}},{name:`metric_${index}_minimum`,selector:number(-100000,100000,0.1)},{name:`metric_${index}_maximum`,selector:number(-100000,100000,0.1)}]).flat(),
    ];
  };
  const pageFields = () => [
    ...(overrideKey ? [] : [{name: entityId ? 'label' : 'title', selector:{text:{}}}]),
    {name:'icon',selector:{icon:{}}},
    ...sourceFields(),
    ...(!editor.panelMode ? [{name:'style',selector:select(domain ? CONTROL_STYLES[domain] : NAV_STYLES)}, {name:'theme',selector:select(['ember','verdant','cobalt','rose','acid','alloy'])}] : []),
    ...(domain && !['sensor','binary_sensor','weather','calendar','camera','image'].includes(domain) ? [{name:'confirm',selector:{boolean:{}}}] : []),
  ];
  form.schema = pageFields();
  const currentStyle = () => draft.style || item.style || (domain ? DEFAULT_STYLES[domain] : 'NAV-ORBIT');
  appearanceForm.schema = [
    ...settingsFor(currentStyle(), draft.raster).map((name) => ({name,selector:SETTINGS[name].kind === 'number' ? number(SETTINGS[name].low,SETTINGS[name].high) : SETTINGS[name].kind === 'toggle' ? {boolean:{}} : select(SETTINGS[name].choices)})),
    ...['accent','background','text'].map((name)=>({name,selector:{text:{}}})),
  ];
  conditionForm.schema = [{name:'conditions',selector:{condition:{}}}];
  for (const field of [form, appearanceForm, conditionForm]) {
    field.computeLabel = (item) => {
      const metric = item.name.match(/^metric_(\d)_(\w+)$/);
      if (metric) return `Metric ${Number(metric[1]) + 1} ${{entity:'sensor',label:'label',minimum:'minimum',maximum:'maximum or goal'}[metric[2]]}`;
      return ({clock_timezone:'Clock time zone (blank uses HA)',clock_world_zones:'World time zones (comma separated IANA names)',clock_moon_entity:'Moon phase sensor (Moonphase face)',clock_reserve_entity:'Power reserve sensor (Worldtimer, %)',clock_weather_entity:'Weather',clock_history_hours:'History to plot (hours)',clock_image_entity:'Picture (camera or image entity)',clock_refresh_entity:'New picture when this changes (optional)',clock_detection_entity:'Detection sensor (optional)',clock_action_0:'First action button (optional)',clock_action_1:'Second action button (optional)'})[item.name] || labels[item.name] || item.name;
    };
    field.computeHelper = (item) => ({icon:'Material Design Icons (bundled for offline rendering).',accent:'Optional #RRGGBB override.',background:'Optional #RRGGBB override.',text:'Optional #RRGGBB override.',confirm:'Locks and alarms always require confirmation; PIN-protected actions remain unavailable.'})[item.name];
  }
  const advanced = document.createElement('details'), summary = document.createElement('summary'); summary.textContent = 'Advanced style';
  const css = document.createElement('textarea'); css.rows = 8; css.setAttribute('aria-label','Advanced style declarations');
  let syncAppearance = () => {}, schedulePreview = () => {};
  const writeCss = () => { css.value = appearanceKeys.filter((key)=>draft[key] !== undefined && draft[key] !== '').map((key)=>`${key}: ${draft[key]};`).join('\n'); schedulePreview(); };
  css.value = item.css || ''; if (!css.value) writeCss();
  for (const field of [form, appearanceForm, conditionForm]) field.addEventListener('value-changed', (event)=>{event.stopPropagation();Object.assign(draft,event.detail.value);if (field===form && !editor.panelMode) form.schema=pageFields();writeCss();});
  css.addEventListener('change', ()=>{try {draft={...draft,...declarations(css.value)};appearanceForm.data=draft;syncAppearance();error.textContent='';}catch(reason){error.textContent=reason.message;}});
  advanced.append(summary, css);
  const save = document.createElement('button'); save.type='button'; save.textContent='Apply';
  save.addEventListener('click', ()=>{
    try {
      validateConditions(draft.conditions || []);
      const styling = {...Object.fromEntries(appearanceKeys.filter((key)=>draft[key] !== undefined && draft[key] !== '').map((key)=>[key,draft[key]])), ...declarations(css.value)};
      for (const [key, low, high] of ranges) if (styling[key] !== undefined && !(Number.isFinite(styling[key]) && styling[key]>=low && styling[key]<=high)) throw new Error(`${key} must be between ${low} and ${high}.`);
      for (const [key,setting] of Object.entries(SETTINGS)) {
        if (setting.kind === 'toggle' && styling[key] !== undefined && typeof styling[key] !== 'boolean') throw new Error(`${setting.label} must be on or off.`);
        if (setting.kind === 'choice' && styling[key] !== undefined && !setting.choices.includes(styling[key])) throw new Error(`${setting.label} must be one of ${setting.choices.join(', ')}.`);
      }
      for (const name of ['accent','background','text','surface','secondary','quiet','grid']) if (styling[name] && !/^#[a-f\d]{6}$/i.test(styling[name])) throw new Error(`${name} needs a #RRGGBB colour.`);
      if (overrideKey) {
        const override = {...page.explorer.pages?.[overrideKey],...(Object.keys(styling).length ? {appearance:styling} : {})};
        for (const name of ['icon','theme']) if (draft[name]) override[name]=draft[name];
        // Pinned only if chosen: otherwise a Random page would stop following Shuffle just by being opened.
        if (draft.style && draft.style!==generated.style) override.style=draft.style;
        storeOverride(override);
        return;
      }
      const updated = {...item,appearance:styling,conditions:draft.conditions || []};
      if (!domain || ['camera','image'].includes(domain)) updated.clock = clockSettings();
      delete updated.css;
      for (const name of [entityId?'label':'title','icon','style','theme','confirm']) {
        if (draft[name] !== undefined && draft[name] !== '') updated[name]=draft[name]; else delete updated[name];
      }
      if (entityId) {
        updated.label_override=Boolean(updated.label);
        editor.setEntities(pageId, entities.map((entity)=>(typeof entity==='string'?entity:entity.entity_id)===entityId?updated:entity));
      } else {
        editor.changed({...editor.config,pages:editor.config.pages.map((candidate)=>candidate.id===pageId?updated:candidate)});
        editor.renderTree();
      }
      dialog.close(); dialog.remove();
    } catch(reason) { error.textContent=reason.message; }
  });
  const storeOverride = (override) => {
    const {[overrideKey]:_previous, ...others} = page.explorer.pages || {};
    const explorer = {...page.explorer,pages:{...others,...(override ? {[overrideKey]:override} : {})}};
    editor.changed({...editor.config,pages:editor.config.pages.map((candidate)=>candidate.id===pageId?{...candidate,explorer}:candidate)});
    editor.renderTree();
    dialog.close(); dialog.remove();
  };
  const cancel = document.createElement('button'); cancel.type='button'; cancel.textContent='Cancel'; cancel.addEventListener('click',()=>{dialog.close();dialog.remove();});
  const head = document.createElement('header'); head.className = 'options-head'; head.append(heading);
  const appearance = document.createElement('details'), appearanceTitle = document.createElement('summary'); appearanceTitle.textContent = 'Detailed appearance'; appearance.append(appearanceTitle,appearanceForm,advanced);
  const visibility = document.createElement('details'), visibilityTitle = document.createElement('summary'); visibilityTitle.textContent = 'Visibility conditions'; visibility.append(visibilityTitle,hint,conditionForm);
  let body = document.createElement('div'); body.className = 'options-body'; body.append(error,form,appearance,visibility);
  if (editor.panelMode) {
    body.replaceChildren(error);
    const gallery = document.createElement('div'); gallery.className = 'options-galleries';
    const tabs = document.createElement('div'); tabs.className = 'dialog-tabs'; tabs.setAttribute('role','tablist'); tabs.setAttribute('aria-label','Appearance settings');
    const panels = [gallery, document.createElement('div')];
    const controls = document.createElement('div'); controls.className='appearance-controls';
    const updates = [], colourUpdates = [];
    // One group at a time keeps the dialog still and usable at phone width.
    const groupTabs=document.createElement('div'); groupTabs.className='dialog-tabs setting-groups'; groupTabs.setAttribute('role','group'); groupTabs.setAttribute('aria-label','Setting group');
    const groupBody=document.createElement('div'); groupBody.className='setting-group';
    controls.append(groupTabs,groupBody);
    let group;
    const settingRow=(key)=>{
      const setting=SETTINGS[key], fallback=()=>key==='picture-mode' ? PICTURE_DEFAULTS[currentStyle()] : defaultsFor(draft.raster)[key];
      const changed=()=>draft[key]!==undefined && draft[key]!==fallback();
      const reset=document.createElement('button'); reset.type='button'; reset.className='chip'; reset.textContent='Reset';
      const syncReset=()=>{reset.hidden=!changed();};
      let row,sync;
      if (setting.kind==='number') {
        row=document.createElement('label'); row.className='slider-row';
        const name=document.createElement('span'); name.textContent=setting.label;
        const input=document.createElement('input'); input.type='range'; input.min=setting.low; input.max=setting.high; input.step=1; input.setAttribute('aria-label',setting.label);
        const value=document.createElement('output');
        sync=()=>{input.value=draft[key] ?? fallback(); value.textContent=input.value;};
        input.addEventListener('input',()=>{draft[key]=Number(input.value);value.textContent=input.value;syncReset();writeCss();});
        row.append(name,input,value);
      } else if (setting.kind==='toggle') {
        row=document.createElement('label'); row.className='switch-row';
        const name=document.createElement('span'); name.textContent=setting.label;
        const input=document.createElement('input'); input.type='checkbox'; input.setAttribute('aria-label',setting.label);
        sync=()=>{input.checked=draft[key] ?? fallback();};
        input.addEventListener('change',()=>{draft[key]=input.checked;syncReset();writeCss();});
        row.append(name,input);
      } else {
        row=document.createElement('div'); row.className='raster-row';
        const name=document.createElement('span'); name.textContent=setting.label;
        const segments=document.createElement('div'); segments.className='dialog-tabs'; segments.setAttribute('role','group'); segments.setAttribute('aria-label',setting.label);
        const buttons=setting.choices.map(choice=>{const button=document.createElement('button');button.type='button';button.textContent=choice;button.addEventListener('click',()=>{draft[key]=choice;syncReset();sync();writeCss();if(rebuildsSettings(key))buildSettings();});segments.append(button);return button;});
        sync=()=>buttons.forEach((button,index)=>button.setAttribute('aria-pressed',String((draft[key] ?? fallback())===setting.choices[index])));
        row.append(name,segments);
      }
      reset.addEventListener('click',()=>{delete draft[key];sync();syncReset();writeCss();if(rebuildsSettings(key))buildSettings();});
      updates.push(sync,syncReset); sync(); syncReset(); row.append(reset);
      return row;
    };
    const buildSettings=()=>{
      updates.length=0;
      const applies=(key)=>!REQUIRES[key] || (draft[REQUIRES[key][0]] ?? defaultsFor(draft.raster)[REQUIRES[key][0]])===REQUIRES[key][1];
      const keys=settingsFor(currentStyle(),draft.raster).filter(applies);
      const groups=[...new Set(keys.map(key=>SETTINGS[key].group))];
      if (!groups.includes(group)) group=groups[0];
      groupTabs.replaceChildren(...groups.map(name=>{const button=document.createElement('button');button.type='button';button.textContent=name;button.setAttribute('aria-pressed',String(name===group));button.addEventListener('click',()=>{group=name;buildSettings();});return button;}));
      groupBody.replaceChildren(...keys.filter(key=>SETTINGS[key].group===group).map(settingRow));
      updates.push(...colourUpdates);
      colourUpdates.forEach(update=>update());
    };
    const coloursTitle=document.createElement('h4'); coloursTitle.textContent='Colour overrides'; controls.append(coloursTitle);
    const colours=document.createElement('div'); colours.className='colour-grid';
    for (const [key,fallback] of [['accent','#ff8b2d'],['background','#060707'],['text','#fff7eb'],['surface','#252525'],['secondary','#cccccc'],['quiet','#777777'],['grid','#444444'],['snake-line','#777777'],['snake-travelled','#ff8b2d']]) {
      const row=document.createElement('div');row.className='colour-choice';const label=document.createElement('label');label.textContent=labels[key] || `${key[0].toUpperCase()}${key.slice(1)} colour`;
      const input=document.createElement('input');input.type='color';input.setAttribute('aria-label',label.textContent);
      const reset=document.createElement('button');reset.type='button';reset.className='chip';reset.textContent='Use theme';
      const sync=()=>{input.value=draft[key] || fallback;reset.disabled=!draft[key];row.style.display=key.startsWith('snake-') && currentStyle()!=='NAV-SNAKE' ? 'none' : '';};colourUpdates.push(sync);sync();
      input.addEventListener('input',()=>{draft[key]=input.value;sync();writeCss();});reset.addEventListener('click',()=>{delete draft[key];sync();writeCss();});
      label.append(input);row.append(label,reset);colours.append(row);
    }
    controls.append(colours);syncAppearance=()=>updates.forEach(update=>update());
    buildSettings();
    panels[1].append(form,controls);
    const names = ['Styles & themes','Options'];
    const buttons = names.map((name,index) => {
      const tab = document.createElement('button'); tab.type='button'; tab.textContent=name; tab.setAttribute('role','tab');
      tab.id=`dial-tab-${index}`; tab.setAttribute('aria-controls',`dial-panel-${index}`);
      panels[index].id=`dial-panel-${index}`; panels[index].setAttribute('role','tabpanel'); panels[index].setAttribute('aria-labelledby',tab.id);
      const activate = () => buttons.forEach((button,i)=>{button.setAttribute('aria-selected',String(i===index)); button.tabIndex=i===index?0:-1; panels[i].hidden=i!==index;});
      tab.addEventListener('click',activate);
      tab.addEventListener('keydown',event=>{if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return; event.preventDefault(); const next=event.key==='Home'?0:event.key==='End'?buttons.length-1:(index+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length; buttons[next].click(); buttons[next].focus();});
      tabs.append(tab); return tab;
    });
    body.append(tabs,...panels); buttons[0].click();
    const preview=document.createElement('aside'); preview.className='appearance-preview';
    const previewTitle=document.createElement('h4'); previewTitle.textContent='Live preview';
    const canvas=document.createElement('canvas'); canvas.width=canvas.height=240; canvas.setAttribute('aria-label','Live Dial appearance preview'); canvas.setAttribute('role','img');
    const status=document.createElement('p'); status.textContent='Loading preview…'; status.setAttribute('role','status');
    preview.append(previewTitle,canvas,status);
    const layout=document.createElement('div'); layout.className='appearance-layout'; layout.append(body,preview); body=layout;
    const currentPage = () => {
      const updated = {...item,...draft,...(!domain || ['camera','image'].includes(domain) ? {clock:clockSettings()} : {}),appearance:Object.fromEntries(appearanceKeys.filter(key=>draft[key] !== undefined && draft[key] !== '').map(key=>[key,draft[key]]))}; delete updated.css;
      return entityId ? {...page,entities:entities.map(entry => (typeof entry === 'string' ? entry : entry.entity_id) === entityId ? updated : entry),lights:[]} : updated;
    };
    const children = generated?.children || editor.config.pages.filter(candidate => candidate.parent === pageId).map(({title,icon})=>({title,icon}));
    // An Explorer's pages use navigation styles only, and only ones that can show them all.
    const styleScope = generated ? {nav_only:true,...(generated.count > 8 ? {long:true} : {})} : !entityId && children.length + entities.length > 8 ? {long:true} : {};
    let previewSequence=0, timer;
    schedulePreview = () => {
      const sequence=++previewSequence; clearTimeout(timer); status.textContent='Updating preview…';
      timer=setTimeout(async()=>{
        try {
          const result=await editor._hass.callWS({type:'ha_dial/gallery',page:currentPage(),children,...(entityId ? {entity:entityId} : {}),theme:editor.config.theme || 'ember',preview_only:true});
          if (sequence !== previewSequence || !dialog.isConnected) return;
          renderScene(canvas,result.scene,result.frames); status.textContent='Preview only — changes are not applied yet.';
        } catch (reason) { if (sequence === previewSequence && dialog.isConnected) status.textContent=`Preview unavailable: ${reason.message || reason}`; }
      },80);
    };
    dialog.addEventListener('close',()=>{previewSequence++; clearTimeout(timer);});
    let request = 0;
    const updateGallery = async () => {
      const sequence = ++request;
      const current = currentPage();
      try {
        const data = await editor._hass.callWS({type:'ha_dial/gallery',page:current,children,...(entityId ? {entity:entityId} : {}),...styleScope,theme:editor.config.theme || 'ember'});
        if (sequence !== request || !dialog.isConnected) return;
        gallery.replaceChildren();
        for (const [key, headingText] of [['styles','Atlas style'],['themes','Theme']]) {
          const section = document.createElement('section'), title = document.createElement('h4'), choices = document.createElement('div');
          title.textContent=headingText; choices.className='gallery-grid'; section.append(title,choices);
          const field = key === 'styles' ? 'style' : 'theme';
          for (const [value, scene] of Object.entries(data[key])) {
            const choice=document.createElement('button'); choice.type='button'; choice.className='gallery-choice';
            choice.setAttribute('aria-pressed',String((draft[field] || data[field]) === value));
            const canvas=document.createElement('canvas'); canvas.width=canvas.height=240; canvas.setAttribute('aria-hidden','true');
            const label=document.createElement('span'); label.textContent=value.replace(/^NAV-|^CTL-/,'').replaceAll('-',' ').toLowerCase();
            choice.append(canvas,label); choices.append(choice); renderScene(canvas,scene,data.frames);
            choice.addEventListener('click',()=>{draft[field]=value; if(field==='style'){form.schema=pageFields();buildSettings();} schedulePreview(); updateGallery();});
          }
          gallery.append(section);
        }
      } catch (reason) { if (sequence === request) error.textContent = `Could not load previews: ${reason.message || reason}`; }
    };
    updateGallery(); schedulePreview();
  }
  const foot = document.createElement('footer'); foot.className = 'options-foot'; foot.append(cancel,save);
  if (overrideKey && page.explorer.pages?.[overrideKey]) {
    const clear = document.createElement('button'); clear.type='button'; clear.textContent='Use Explorer defaults'; clear.addEventListener('click',()=>storeOverride(null));
    foot.prepend(clear);
  }
  dialog.append(head,body,foot);
  dialog.addEventListener('close',()=>dialog.remove());
  editor.append(dialog); dialog.showModal();
  form.querySelector('input')?.focus();
}
