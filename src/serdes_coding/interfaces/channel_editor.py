"""Editable victim/NEXT/FEXT references, independent of source mapping."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
from ..io.conversion.channels import COLUMNS, replace_channels
from ..io.conversion.mapping_rules import is_enabled


class ChannelEditor(ttk.LabelFrame):
    def __init__(self,parent,project_root,on_change):
        super().__init__(parent,text='Reference channels',padding=4)
        self.project_root=project_root
        self.on_change=on_change
        self.kind=tk.StringVar(value='victim')
        defaults={'S4P Path':'','Port Order':'1,2,3,4','Use':'True'}
        self.values={k:tk.StringVar(value=v) for k,v in defaults.items()}
        self.tree=ttk.Treeview(self,columns=('kind',*COLUMNS),show='headings',height=3)
        for name in ('kind',*COLUMNS):
            self.tree.heading(name,text=name)
            self.tree.column(name,width=350 if name=='S4P Path' else 95)
        self.tree.pack(fill='x');self.tree.bind('<<TreeviewSelect>>',self.select)
        form=ttk.Frame(self);form.pack(fill='x')
        ttk.Combobox(form,textvariable=self.kind,values=('victim','fext','next'),width=7,state='readonly').pack(side='left')
        for key,value in self.values.items():ttk.Entry(form,textvariable=value,width=34 if key=='S4P Path' else 10).pack(side='left',padx=2)
        for label,command in [('S4P',self.browse),('Add',self.add),('Update',self.update_row),('Remove',self.remove)]:
            ttk.Button(form,text=label,command=command).pack(side='left')

    def select(self,*_):
        items=self.tree.selection()
        if items:
            values=self.tree.item(items[0],'values');self.kind.set(values[0])
            for key,value in zip(COLUMNS,values[1:]):self.values[key].set(value)

    def browse(self):
        path=filedialog.askopenfilename(initialdir=self.project_root/'reference_data/COM_channel_data',filetypes=[('Touchstone S4P','*.s4p')])
        if path:self.values['S4P Path'].set(path)

    def row(self):return (self.kind.get(),*(v.get() for v in self.values.values()))

    def add(self):self.tree.insert('','end',values=self.row());self.on_change()

    def update_row(self):
        for iid in self.tree.selection():self.tree.item(iid,values=self.row())
        self.on_change()

    def remove(self):self.tree.delete(*self.tree.selection());self.on_change()

    def load(self,draft):
        self.tree.delete(*self.tree.get_children())
        rows={}
        for field in draft.fields:
            if field.sheet=='channels':rows.setdefault(field.row,{'kind':field.group})[field.parameter.rsplit('.',1)[1]]=field.value
        for row in rows.values():
            if row.get('S4P Path') and hasattr(draft,'source_path'):
                from ..io.com_excel_common import _resolve_channel_path
                row['S4P Path']=_resolve_channel_path(draft.source_path,str(row['S4P Path']))
            self.tree.insert('','end',values=(row['kind'],*(row.get(k,'') for k in COLUMNS)))

    def apply(self,draft):
        channels=[]
        for iid in self.tree.get_children():
            row=self.tree.item(iid,'values');values=dict(zip(COLUMNS,row[1:]))
            if values['S4P Path']:
                path=Path(values['S4P Path']).expanduser().resolve()
                if not path.is_relative_to((self.project_root/'reference_data/COM_channel_data').resolve()):
                    raise ValueError('Channel files must remain under reference_data/COM_channel_data')
                values['S4P Path']=str(path)
            values['Use']=is_enabled(values['Use'])
            channels.append((row[0],values))
        replace_channels(draft,channels)
