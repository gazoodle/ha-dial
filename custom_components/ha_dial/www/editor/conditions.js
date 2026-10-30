const types = {state:'Entity state', numeric_state:'Numeric state', time:'Time', template:'Template', and:'All conditions', or:'Any condition', not:'None of these'};
const weekdays = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map((label,index)=>({label,value:['mon','tue','wed','thu','fri','sat','sun'][index]}));

export function conditionsEditor(hass, initial, changed) {
  const host = document.createElement('div'); host.className = 'condition-editor';
  let conditions = structuredClone(initial || []);
  const button = (label, action) => { const el = document.createElement('button'); el.type='button'; el.textContent=label; el.addEventListener('click',action); return el; };
  const render = () => {
    host.replaceChildren();
    const hint = document.createElement('p'); hint.className='condition-hint';
    hint.textContent = conditions.length ? 'Shown when all conditions pass.' : 'Always shown. Add a condition to control visibility.'; host.append(hint);
    const list = (items, container) => {
      items.forEach((item, index) => {
        const row = document.createElement('details'); row.className='condition-row'; row.open = item === host.newItem;
        const summary = document.createElement('summary');
        const config = item.options || item;
        const description = item.condition === 'time' ? [config.after && `after ${config.after}`,config.before && `before ${config.before}`,config.weekday?.join?.(', ')].filter(Boolean).join(' · ') : config.entity_id || config.value_template || '';
        summary.textContent = `${types[item.condition] || item.condition}${description ? ' · ' + description : ''}`; row.append(summary);
        if (['and','or','not'].includes(item.condition)) {
          const nested = item.conditions || item.options?.conditions || [];
          if (!item.conditions && !item.options?.conditions) item.conditions = nested;
          list(nested,row); addMenu(nested,row);
        } else {
          const form = document.createElement('ha-form'); form.hass=hass; form.data=config;
          form.schema = item.condition === 'state' ? [{name:'entity_id',selector:{entity:{}}},{name:'state',selector:{text:{}}}] :
            item.condition === 'numeric_state' ? [{name:'entity_id',selector:{entity:{}}},{name:'above',selector:{number:{mode:'box'}}},{name:'below',selector:{number:{mode:'box'}}}] :
            item.condition === 'time' ? [{name:'after',selector:{time:{}}},{name:'before',selector:{time:{}}},{name:'weekday',selector:{select:{multiple:true,options:weekdays}}}] :
            [{name:'value_template',selector:{template:{}}}];
          form.computeLabel = field => ({entity_id:'Entity',state:'State',above:'Above',below:'Below',after:'After',before:'Before',weekday:'Days of the week',value_template:'Template'})[field.name];
          if (item.condition === 'time') form.computeHelper = () => 'Fixed times use the Home Assistant time zone.';
          form.addEventListener('value-changed', event => { event.stopPropagation(); const values = event.detail.value; if (item.options) item.options={...item.options,...values}; else Object.assign(item,values); const updated = item.options || item; const detail = item.condition === 'time' ? [updated.after && `after ${updated.after}`,updated.before && `before ${updated.before}`,updated.weekday?.join?.(', ')].filter(Boolean).join(' · ') : updated.entity_id || updated.value_template || ''; summary.textContent = `${types[item.condition] || item.condition}${detail ? ' · ' + detail : ''}`; changed(conditions); });
          row.append(form);
        }
        const remove = button('Remove',() => { items.splice(index,1); host.newItem=undefined; changed(conditions); render(); }); remove.className='chip danger'; row.append(remove); container.append(row);
      });
    };
    const addMenu = (items, container) => {
      const menu = document.createElement('details'); menu.className='condition-add';
      const summary = document.createElement('summary'); summary.textContent='+ Add condition'; summary.className='chip accent'; menu.append(summary);
      const choices = document.createElement('div'); choices.className='condition-menu';
      for (const [type, label] of Object.entries(types)) choices.append(button(label,() => { const item={condition:type,...(['and','or','not'].includes(type)?{conditions:[]}:{})}; items.push(item); host.newItem=item; changed(conditions); render(); }));
      menu.append(choices); container.append(menu);
    };
    list(conditions,host); addMenu(conditions,host);
  };
  render(); return host;
}
