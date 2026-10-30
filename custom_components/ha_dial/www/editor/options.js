import { CONTROL_STYLES, NAV_STYLES } from './catalogue.js';
import { renderScene } from '../scene.js';

const number = (min, max, step = 1) => ({ number: { min, max, step, mode: 'box' } });
const select = (options) => ({ select: { options, mode: 'dropdown' } });
const labels = { title:'Page title', label:'Control label', icon:'Icon', style:'Atlas style', theme:'Theme', conditions:'Show when all conditions pass', confirm:'Confirm actions', css:'Advanced style', 'outer-border':'Outer border', 'border-width':'Border width', 'font-size':'Title size', 'icon-size':'Icon size', 'orbit-radius':'Orbit radius', raster:'Crisp / Smooth', accent:'Accent colour', background:'Background colour', text:'Text colour' };
const defaults = {'outer-border':true,'border-width':2,'font-size':11,'icon-size':18,'orbit-radius':84,raster:'smooth'};
const appearanceKeys = [...Object.keys(defaults), 'accent','background','text','surface','secondary','quiet','grid'];

function declarations(source) {
  const result = {};
  for (const declaration of (source || '').split(';')) {
    if (!declaration.trim()) continue;
    const at = declaration.indexOf(':');
    if (at < 0) throw new Error('Use property: value; in Advanced style.');
    const name = declaration.slice(0, at).trim(), raw = declaration.slice(at + 1).trim();
    if (!appearanceKeys.includes(name)) throw new Error(`Unsupported style property: ${name}`);
    result[name] = name === 'outer-border' ? ['true','on'].includes(raw) ? true : ['false','off'].includes(raw) ? false : raw : ['border-width','font-size','icon-size','orbit-radius'].includes(name) ? Number(raw.replace(/px$/, '')) : raw;
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

export function openOptions(editor, pageId, entityId) {
  editor.querySelector('.edit-options-dialog')?.remove();
  const page = editor.config.pages.find((candidate) => candidate.id === pageId);
  const entities = editor.entities(pageId);
  const original = entityId ? entities.find((item) => (typeof item === 'string' ? item : item.entity_id) === entityId) : page;
  const item = typeof original === 'string' ? {entity_id:original} : {...original};
  const domain = entityId?.split('.')[0];
  const dialog = document.createElement('dialog'); dialog.className = 'options-dialog edit-options-dialog';
  dialog.setAttribute('aria-label', entityId ? `Edit ${domain} control` : 'Edit page');
  const heading = document.createElement('h3'); heading.textContent = entityId ? `Edit ${domain} control` : 'Page appearance';
  const hint = document.createElement('p'); hint.textContent = 'Conditions are evaluated in Home Assistant. Visibility is not access control.';
  const error = document.createElement('p'); error.setAttribute('role','alert');
  const form = document.createElement('ha-form');
  const appearanceForm = document.createElement('ha-form');
  const conditionForm = document.createElement('ha-form');
  let options;
  try { options = {...defaults, ...page.appearance, ...declarations(page.css), ...item.appearance, ...declarations(item.css)}; }
  catch (reason) { error.textContent = reason.message; options = {...defaults,...item.appearance}; }
  let draft = {...item,...options,confirm:item.confirm ?? ['lock','alarm_control_panel','scene','button','input_button'].includes(domain), conditions:item.conditions || []};
  for (const field of [form, appearanceForm, conditionForm]) { field.hass = editor._hass; field.data = draft; }
  form.schema = [
    {name: entityId ? 'label' : 'title', selector:{text:{}}},
    {name:'icon',selector:{icon:{}}},
    ...(!editor.panelMode ? [{name:'style',selector:select(domain ? CONTROL_STYLES[domain] : NAV_STYLES)}, {name:'theme',selector:select(['ember','verdant','cobalt','rose','acid','alloy'])}] : []),
    ...(domain && !['sensor','binary_sensor','weather','calendar'].includes(domain) ? [{name:'confirm',selector:{boolean:{}}}] : []),
  ];
  appearanceForm.schema = [
    {name:'raster',selector:select(['smooth','crisp'])},
    {name:'outer-border',selector:{boolean:{}}},
    {name:'border-width',selector:number(1,4)},
    {name:'font-size',selector:number(6,16)},
    {name:'icon-size',selector:number(12,28)},
    ...(!domain ? [{name:'orbit-radius',selector:number(70,90)}] : []),
    ...['accent','background','text'].map((name)=>({name,selector:{text:{}}})),
  ];
  conditionForm.schema = [{name:'conditions',selector:{condition:{}}}];
  for (const field of [form, appearanceForm, conditionForm]) {
    field.computeLabel = (item) => labels[item.name] || item.name;
    field.computeHelper = (item) => ({icon:'Material Design Icons (bundled for offline rendering).',accent:'Optional #RRGGBB override.',background:'Optional #RRGGBB override.',text:'Optional #RRGGBB override.',confirm:'Locks and alarms always require confirmation; PIN-protected actions remain unavailable.'})[item.name];
  }
  const advanced = document.createElement('details'), summary = document.createElement('summary'); summary.textContent = 'Advanced style';
  const css = document.createElement('textarea'); css.rows = 8; css.setAttribute('aria-label','Advanced style declarations');
  let syncAppearance = () => {};
  const writeCss = () => { css.value = appearanceKeys.filter((key)=>draft[key] !== undefined && draft[key] !== '').map((key)=>`${key}: ${draft[key]};`).join('\n'); };
  css.value = item.css || ''; if (!css.value) writeCss();
  for (const field of [form, appearanceForm, conditionForm]) field.addEventListener('value-changed', (event)=>{event.stopPropagation();for (const item of field.schema) draft[item.name] = event.detail.value[item.name];writeCss();});
  css.addEventListener('change', ()=>{try {draft={...draft,...declarations(css.value)};appearanceForm.data=draft;syncAppearance();error.textContent='';}catch(reason){error.textContent=reason.message;}});
  advanced.append(summary, css);
  const save = document.createElement('button'); save.type='button'; save.textContent='Apply';
  save.addEventListener('click', ()=>{
    try {
      validateConditions(draft.conditions || []);
      const styling = {...Object.fromEntries(appearanceKeys.filter((key)=>draft[key] !== undefined && draft[key] !== '').map((key)=>[key,draft[key]])), ...declarations(css.value)};
      for (const [key, low, high] of [['border-width',1,4],['font-size',6,16],['icon-size',12,28],['orbit-radius',70,90]]) if (!(Number.isFinite(styling[key]) && styling[key]>=low && styling[key]<=high)) throw new Error(`${key} must be between ${low} and ${high}.`);
      if (typeof styling['outer-border'] !== 'boolean' || !['crisp','smooth'].includes(styling.raster)) throw new Error('Check outer-border and raster values.');
      for (const name of ['accent','background','text','surface','secondary','quiet','grid']) if (styling[name] && !/^#[a-f\d]{6}$/i.test(styling[name])) throw new Error(`${name} needs a #RRGGBB colour.`);
      const updated = {...item,appearance:styling,conditions:draft.conditions || []};
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
  const cancel = document.createElement('button'); cancel.type='button'; cancel.textContent='Cancel'; cancel.addEventListener('click',()=>{dialog.close();dialog.remove();});
  const head = document.createElement('header'); head.className = 'options-head'; head.append(heading);
  const appearance = document.createElement('details'), appearanceTitle = document.createElement('summary'); appearanceTitle.textContent = 'Detailed appearance'; appearance.append(appearanceTitle,appearanceForm,advanced);
  const visibility = document.createElement('details'), visibilityTitle = document.createElement('summary'); visibilityTitle.textContent = 'Visibility conditions'; visibility.append(visibilityTitle,hint,conditionForm);
  const body = document.createElement('div'); body.className = 'options-body'; body.append(error,form,appearance,visibility);
  if (editor.panelMode) {
    body.replaceChildren(error);
    const gallery = document.createElement('div'); gallery.className = 'options-galleries';
    const tabs = document.createElement('div'); tabs.className = 'dialog-tabs'; tabs.setAttribute('role','tablist'); tabs.setAttribute('aria-label','Appearance settings');
    const panels = [gallery, document.createElement('div'), document.createElement('div')];
    const controls = document.createElement('div'); controls.className='appearance-controls';
    const updates = [];
    const title = document.createElement('h4'); title.textContent='Display'; controls.append(title);
    for (const [key,low,high] of [['border-width',1,4],['font-size',6,16],['icon-size',12,28],...(!domain?[['orbit-radius',70,90]]:[])]) {
      const row=document.createElement('label'); row.className='slider-row';
      const name=document.createElement('span'); name.textContent=labels[key];
      const input=document.createElement('input'); input.type='range'; input.min=low; input.max=high; input.step=1; input.setAttribute('aria-label',labels[key]);
      const value=document.createElement('output');
      const sync=()=>{input.value=draft[key] ?? defaults[key]; value.textContent=input.value;}; updates.push(sync); sync();
      input.addEventListener('input',()=>{draft[key]=Number(input.value);value.textContent=input.value;writeCss();});
      row.append(name,input,value); controls.append(row);
    }
    const border=document.createElement('label'); border.className='switch-row'; const borderName=document.createElement('span'); borderName.textContent='Outer border';
    const toggle=document.createElement('input'); toggle.type='checkbox'; toggle.setAttribute('aria-label','Outer border');
    const syncBorder=()=>{toggle.checked=draft['outer-border'] !== false;}; updates.push(syncBorder); syncBorder();
    toggle.addEventListener('change',()=>{draft['outer-border']=toggle.checked;writeCss();}); border.append(borderName,toggle); controls.append(border);
    const raster=document.createElement('div'); raster.className='raster-row'; const rasterLabel=document.createElement('span'); rasterLabel.textContent='Rendering'; raster.append(rasterLabel);
    const segments=document.createElement('div'); segments.className='dialog-tabs'; segments.setAttribute('role','group'); segments.setAttribute('aria-label','Rendering');
    const modes=['smooth','crisp'].map(mode=>{const button=document.createElement('button');button.type='button';button.textContent=mode;button.addEventListener('click',()=>{draft.raster=mode;syncRaster();writeCss();});segments.append(button);return button;});
    const syncRaster=()=>modes.forEach((button,index)=>button.setAttribute('aria-pressed',String((draft.raster || 'smooth') === ['smooth','crisp'][index]))); updates.push(syncRaster); syncRaster(); raster.append(segments); controls.append(raster);
    const coloursTitle=document.createElement('h4'); coloursTitle.textContent='Colour overrides'; controls.append(coloursTitle);
    const colours=document.createElement('div'); colours.className='colour-grid';
    for (const [key,fallback] of [['accent','#ff8b2d'],['background','#060707'],['text','#fff7eb']]) {
      const row=document.createElement('div');row.className='colour-choice';const label=document.createElement('label');label.textContent=labels[key];
      const input=document.createElement('input');input.type='color';input.setAttribute('aria-label',labels[key]);
      const reset=document.createElement('button');reset.type='button';reset.className='chip';reset.textContent='Use theme';
      const sync=()=>{input.value=draft[key] || fallback;reset.disabled=!draft[key];};updates.push(sync);sync();
      input.addEventListener('input',()=>{draft[key]=input.value;sync();writeCss();});reset.addEventListener('click',()=>{delete draft[key];sync();writeCss();});
      label.append(input);row.append(label,reset);colours.append(row);
    }
    controls.append(colours);syncAppearance=()=>updates.forEach(update=>update());
    panels[1].append(form,controls); panels[2].append(css);
    const names = ['Styles & themes','Options','Advanced'];
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
    let request = 0;
    const updateGallery = async () => {
      const sequence = ++request;
      const current = entityId ? {...page,entities:entities.map(entry => (typeof entry === 'string' ? entry : entry.entity_id) === entityId ? {...item, ...draft} : entry),lights:[]} : {...page,...draft};
      try {
        const children = editor.config.pages.filter(candidate => candidate.parent === pageId).map(({title,icon})=>({title,icon}));
        const data = await editor._hass.callWS({type:'ha_dial/gallery',page:current,children,...(entityId ? {entity:entityId} : {}),theme:editor.config.theme || 'ember'});
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
            choice.append(canvas,label); choices.append(choice); renderScene(canvas,scene);
            choice.addEventListener('click',()=>{draft[field]=value; updateGallery();});
          }
          gallery.append(section);
        }
      } catch (reason) { if (sequence === request) error.textContent = `Could not load previews: ${reason.message || reason}`; }
    };
    updateGallery();
  }
  const foot = document.createElement('footer'); foot.className = 'options-foot'; foot.append(cancel,save);
  dialog.append(head,body,foot);
  dialog.addEventListener('close',()=>dialog.remove());
  editor.append(dialog); dialog.showModal();
  form.querySelector('input')?.focus();
}
