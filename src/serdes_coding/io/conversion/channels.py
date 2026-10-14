"""Channel rows are user inputs, not Ad Hoc mapping targets."""
from pathlib import Path
from .draft import MappingStatus, ProjectFieldDraft
from .mapping_rules import is_enabled

COLUMNS = {'S4P Path':3, 'Port Order':4, 'Use':5}


def channel_errors(fields):
    rows = {}
    for f in fields:
        if f.sheet=='channels':
            name,column=f.parameter.rsplit('.',1)
            rows.setdefault(name,{})[column]=f.value
    errors=[]
    victims=0
    for name,row in rows.items():
        if not is_enabled(row.get('Use',True)):continue
        victims += name.lower().startswith('victim[')
        path=Path(str(row.get('S4P Path') or ''))
        if not path.is_file() or path.suffix.lower()!='.s4p':
            errors.append(f'{name}: select an existing S4P file')
    if victims!=1:errors.append('Exactly one enabled victim channel is required')
    return errors


def replace_channels(draft, channels):
    """channels is a list of (kind, values); preserve settings provided by UI."""
    draft.fields[:]=[f for f in draft.fields if f.sheet!='channels']
    counts={'victim':-1, 'next':0, 'fext':0}
    for row,(kind,values) in enumerate(channels,start=4):
        kind=kind.lower()
        if kind not in {'victim','next','fext'}:raise ValueError('Invalid channel kind')
        counts[kind]+=1
        name=f'{kind}[{counts[kind]}]'
        for key,column in COLUMNS.items():
            value=values[key]
            draft.fields.append(ProjectFieldDraft('channels',row,column,kind,f'{name}.{key}','channel',value,None,'User-selected channel',value,MappingStatus.OVERRIDE))
    draft.changed.add(('channels','__rows__'))


def write_fields(workbook, fields):
    """Clear removed channel rows; explicitly assign None (cell(...,None) is a no-op)."""
    sheet=workbook['channels']
    for row in sheet.iter_rows(min_row=4):
        for cell in row:cell.value=None
    for f in fields:
        sheet=workbook[f.sheet]
        sheet.cell(f.row,f.value_column).value=f.value
        if f.sheet=='channels':
            kind,index=f.parameter.split(']',1)[0].split('[')
            sheet.cell(f.row,1).value=kind
            sheet.cell(f.row,2).value=int(index)
