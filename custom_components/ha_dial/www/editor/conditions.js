const types = {state:'Entity state', numeric_state:'Numeric state', time:'Time', template:'Template', and:'All conditions', or:'Any condition', not:'None of these'};
const icons = {state:'mdi:state-machine',numeric_state:'mdi:numeric',time:'mdi:calendar-clock',template:'mdi:code-braces',and:'mdi:ampersand',or:'mdi:gate-or',not:'mdi:not-equal-variant'};
const weekdays = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map((label,index)=>({label,value:['mon','tue','wed','thu','fri','sat','sun'][index]}));

export function conditionsEditor(hass, initial, changed) {
  const host = document.createElement('div'); host.className = 'condition-editor';
  let conditions = structuredClone(initial || []);
  let revision = 0, subscriptions = [];
  const dispose = () => { revision++; subscriptions.forEach(unsubscribe => unsubscribe()); subscriptions = []; };
  host.destroy = dispose;
  const results = new Map(), badges = new Map(); let overall;
  const result = item => {
    if (item.enabled === false) return true;
    if (!['and','or','not'].includes(item.condition)) return results.get(item);
    const values = (item.conditions || item.options?.conditions || []).map(result);
    if (!values.length) return undefined;
    if (item.condition === 'and' && values.includes(false)) return false;
    if (item.condition !== 'and' && values.includes(true)) return item.condition === 'or';
    if (values.includes(undefined)) return undefined;
    return item.condition !== 'or';
  };
  const display = (node, value, overall = false) => {
    node.textContent = value === undefined ? 'Waiting for a valid condition' : value ? (overall ? 'Currently visible' : 'Passes') : (overall ? 'Currently hidden' : 'Does not pass');
    node.dataset.result = value === undefined ? 'pending' : value ? 'pass' : 'fail';
  };
  const update = () => {
    for (const [item,badge] of badges) display(badge,result(item));
    const values = conditions.map(result);
    display(overall, values.some(value => value === false) ? false : values.some(value => value === undefined) ? undefined : true, true);
  };
  const watch = () => {
    dispose(); results.clear(); const current = revision;
    const subscribe = async item => {
      if (['and','or','not'].includes(item.condition)) { for (const child of item.conditions || item.options?.conditions || []) subscribe(child); return; }
      if (item.enabled === false || !hass.callWS || !hass.connection?.subscribeMessage) return;
      try {
        const template = await hass.callWS({type:'ha_dial/condition_template',condition:item});
        if (current !== revision) return;
        const unsubscribe = await hass.connection.subscribeMessage(message => {
          if (current !== revision) return;
          results.set(item, message.result === true || ['true','on','yes','1'].includes(String(message.result).toLowerCase())); update();
        }, {type:'render_template',template});
        if (current !== revision) unsubscribe(); else subscriptions.push(unsubscribe);
      } catch (_) { if (current === revision) update(); }
    };
    conditions.forEach(subscribe); update();
  };
  const button = (label, action) => { const el = document.createElement('button'); el.type='button'; el.textContent=label; el.addEventListener('click',action); return el; };
  const render = () => {
    host.replaceChildren();
    const hint = document.createElement('p'); hint.className='condition-hint';
    hint.textContent = conditions.length ? 'Shown when all conditions pass.' : 'Always shown. Add a condition to control visibility.'; host.append(hint);
    overall = document.createElement('p'); overall.className='condition-result'; overall.setAttribute('role','status'); host.append(overall); badges.clear();
    const list = (items, container) => {
      items.forEach((item, index) => {
        const row = document.createElement('details'); row.className='condition-row'; row.open = item === host.newItem;
        const summary = document.createElement('summary');
        const config = item.options || item;
        const description = item.condition === 'time' ? [config.after && `after ${config.after}`,config.before && `before ${config.before}`,config.weekday?.join?.(', ')].filter(Boolean).join(' · ') : config.entity_id || config.value_template || '';
        const icon = document.createElement('ha-icon'); icon.setAttribute('icon',icons[item.condition] || 'mdi:help-circle-outline');
        const summaryText = document.createElement('span'); summaryText.textContent = `${types[item.condition] || item.condition}${description ? ' · ' + description : ''}`; const badge=document.createElement('span'); badge.className='condition-badge'; badges.set(item,badge); summary.append(icon,summaryText,badge); row.append(summary);
        if (['and','or','not'].includes(item.condition)) {
          const nested = item.conditions || item.options?.conditions || [];
          if (!item.conditions && !item.options?.conditions) item.conditions = nested;
          list(nested,row); addMenu(nested,row);
        } else {
          const form = document.createElement('ha-form'); form.hass=hass; form.data=config;
          form.schema = item.condition === 'state' ? [{name:'entity_id',selector:{entity:{}}},{name:'attribute',selector:{attribute:{}},context:{filter_entity:'entity_id'}},{name:'state',selector:{state:{multiple:true}},context:{filter_entity:'entity_id',filter_attribute:'attribute'}}] :
            item.condition === 'numeric_state' ? [{name:'entity_id',selector:{entity:{}}},{name:'above',selector:{number:{mode:'box'}}},{name:'below',selector:{number:{mode:'box'}}}] :
            item.condition === 'time' ? [{name:'after',selector:{time:{}}},{name:'before',selector:{time:{}}},{name:'weekday',selector:{select:{multiple:true,options:weekdays}}}] :
            [{name:'value_template',selector:{template:{}}}];
          form.computeLabel = field => ({entity_id:'Entity',state:'State',above:'Above',below:'Below',after:'After',before:'Before',weekday:'Days of the week',value_template:'Template'})[field.name];
          if (item.condition === 'time') form.computeHelper = () => 'Fixed times use the Home Assistant time zone.';
          form.addEventListener('value-changed', event => { event.stopPropagation(); const values = event.detail.value; if (item.options) item.options={...item.options,...values}; else Object.assign(item,values); form.data=item.options || item; const updated = item.options || item; const detail = item.condition === 'time' ? [updated.after && `after ${updated.after}`,updated.before && `before ${updated.before}`,updated.weekday?.join?.(', ')].filter(Boolean).join(' · ') : updated.entity_id || updated.value_template || ''; summaryText.textContent = `${types[item.condition] || item.condition}${detail ? ' · ' + detail : ''}`; changed(conditions); watch(); });
          row.append(form);
        }
        const remove = button('Remove',() => { items.splice(index,1); host.newItem=undefined; changed(conditions); render(); }); remove.className='chip danger'; row.append(remove); container.append(row);
      });
    };
    const addMenu = (items, container) => {
      const menu = document.createElement('details'); menu.className='condition-add';
      const summary = document.createElement('summary'); summary.textContent='+ Add condition'; summary.className='chip accent'; menu.append(summary);
      const choices = document.createElement('div'); choices.className='condition-menu';
      for (const [type, label] of Object.entries(types)) { const option = button(label,() => { const item={condition:type,...(['and','or','not'].includes(type)?{conditions:[]}:{})}; items.push(item); host.newItem=item; changed(conditions); render(); }); const icon=document.createElement('ha-icon'); icon.setAttribute('icon',icons[type]); option.prepend(icon); choices.append(option); }
      menu.append(choices); container.append(menu);
    };
    list(conditions,host); addMenu(conditions,host); watch();
  };
  render(); return host;
}
