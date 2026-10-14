"""Tk GUI for reviewing a labelled COM Ad Hoc to project-config mapping."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional

from ..io.adhoc import list_adhoc_formats
from ..io.conversion import (
    ConversionDraft,
    build_project_config_draft,
    case_config_path,
    validate_case_id,
    write_conversion_audit,
    write_project_config,
)
from ..io.conversion.existing_project import (
    ExistingProjectDraft,
    canonical_destination,
    load_existing_project,
    save_existing_project,
    validate_existing_project,
)
from .channel_editor import ChannelEditor
from ..io.conversion.mapping_rules import area_for, outcome, array


AUTO_FORMAT = "Auto-detect exact format"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_TEMPLATE_PATHS = {
    version: PROJECT_ROOT / "cases" / "_templates" / version / "config.xlsx"
    for version in ("93A", "178A")
}
COM_ADHOC_ROOT = PROJECT_ROOT / "reference_data" / "COM_adhoc_config"


class COMConfigConversionGui:
    def __init__(self, root: tk.Tk, source: Optional[str] = None):
        self.root = root
        self.root.title("COM Project Config: Create / Inspect / Edit")
        self.root.minsize(1200, 800)
        self.draft: Optional[ConversionDraft] = None
        self.existing_draft: Optional[ExistingProjectDraft] = None
        self.row_fields: dict[str, Any] = {}
        self.dirty = False
        self._active_version = '178A'
        self.source_note = tk.StringVar()
        self.output_preview = tk.StringVar()
        self.tx_profile = tk.StringVar()
        self.rx_profile = tk.StringVar()
        self.package_selection = tk.StringVar()

        self.workflow = tk.StringVar(value="新增 config")
        self._active_workflow = self.workflow.get()
        self.source_path = tk.StringVar(value=source or "")
        self.template_display = tk.StringVar(value="")
        self.version = tk.StringVar(value="178A")
        self.case_id = tk.StringVar(value="")
        self.format_id = tk.StringVar(value=AUTO_FORMAT)
        self.status_filter = tk.StringVar(value="全部")
        self.selected_value = tk.StringVar(value="")
        self.detected_text = tk.StringVar(value="No workbook loaded.")
        self.summary_text = tk.StringVar(value="")

        self._build()
        self.case_id.trace_add('write', self._case_changed)
        self.source_note.trace_add('write', self._case_changed)
        self.root.protocol('WM_DELETE_WINDOW', self._close)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.grid(sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(6, weight=1)

        self.path_label = ttk.Label(outer, text="Ad Hoc workbook (reference_data)")
        self.path_label.grid(row=1, column=0, sticky="w")
        ttk.Entry(outer, textvariable=self.source_path,state='readonly').grid(row=1, column=1, sticky="ew", padx=6)
        self.browse_button = ttk.Button(outer, text="Browse", command=self._browse_input)
        self.browse_button.grid(row=1, column=2)

        ttk.Label(outer, text="Case config / Case ID").grid(row=0, column=0, sticky="w")
        case = ttk.Frame(outer)
        case.grid(row=0,column=1,columnspan=2,sticky='ew')
        ttk.Entry(case,textvariable=self.case_id,width=28).pack(side='left')
        ttk.Label(case,text='Source note').pack(side='left',padx=6)
        ttk.Entry(case,textvariable=self.source_note,width=65).pack(side='left',fill='x',expand=True)

        self.template_label = ttk.Label(outer, text="Project template (automatic)")
        self.template_label.grid(row=2, column=0, sticky="w")
        ttk.Entry(outer, textvariable=self.template_display, state="readonly").grid(row=2, column=1, columnspan=2, sticky="ew", padx=6)

        controls = ttk.Frame(outer)
        controls.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        ttk.Label(controls, text="Workflow").pack(side="left")
        workflow_box = ttk.Combobox(
            controls, textvariable=self.workflow,
            values=("新增 config", "開啟既有 config"), state="readonly", width=15,
        )
        workflow_box.pack(side="left", padx=(4, 10))
        workflow_box.bind("<<ComboboxSelected>>", lambda _event: self._workflow_changed())
        ttk.Label(controls, text="Version").pack(side="left")
        self.version_box = ttk.Combobox(controls, textvariable=self.version, values=("93A", "178A"), state="readonly", width=8)
        self.version_box.pack(side="left", padx=(4, 12))
        self.version_box.bind("<<ComboboxSelected>>", lambda _event: self._version_changed())
        ttk.Label(controls, text="Parser format").pack(side="left")
        self.format_box = ttk.Combobox(
            controls, textvariable=self.format_id,
            values=(AUTO_FORMAT,) + list_adhoc_formats(), state="readonly", width=54,
        )
        self.format_box.pack(side="left", padx=4)
        self.load_button = ttk.Button(controls, text="Load Mapping", command=self._load_action)
        self.load_button.pack(side="left", padx=8)
        self.export_button = ttk.Button(controls, text="Export Project Config", command=self._export)
        self.export_button.pack(side="right")
        self.save_as_button = ttk.Button(controls, text="Save As", command=self._save_existing_as)
        self.save_as_button.pack(side="right", padx=6)

        reference=ttk.Frame(outer)
        reference.grid(row=4,column=0,columnspan=3,sticky='ew')
        ttk.Label(reference,textvariable=self.detected_text).pack(anchor='w')
        ttk.Label(reference,textvariable=self.output_preview).pack(anchor='w')
        package=ttk.Frame(reference);package.pack(fill='x')
        self.package_boxes=[]
        for label,var in [('TX profile',self.tx_profile),('RX profile',self.rx_profile),('Testcase',self.package_selection)]:
            ttk.Label(package,text=label).pack(side='left',padx=4)
            box=ttk.Combobox(package,textvariable=var,state='readonly',width=24)
            box.pack(side='left');box.bind('<<ComboboxSelected>>',self._package_changed)
            self.package_boxes.append(box)
        self.channel_editor=ChannelEditor(reference,PROJECT_ROOT,self._mark_dirty)
        self.channel_editor.pack(fill='x')
        filter_frame = ttk.Frame(outer)
        filter_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(4, 4))
        ttk.Label(filter_frame, text="欄位狀態").pack(side="left")
        status_values = ('全部','success','fail','empty')
        box = ttk.Combobox(filter_frame, textvariable=self.status_filter, values=status_values, state="readonly", width=16)
        box.pack(side="left", padx=4)
        box.bind("<<ComboboxSelected>>", lambda _event: self._refresh())
        ttk.Label(filter_frame, textvariable=self.summary_text).pack(side="right")

        self.tabs=ttk.Notebook(outer)
        self.tabs.grid(row=6,column=0,columnspan=3,sticky='nsew')
        self.trees={}
        columns=('parameter','source','source_value','source_unit','converted','value','unit','status','method','edited')
        for area,title in [('mapping','Ad Hoc → Project mapping'),('policy','Project policy'),('baseline','Single-run baseline')]:
            frame=ttk.Frame(self.tabs);self.tabs.add(frame,text=title)
            frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
            tree=ttk.Treeview(frame,columns=columns,show='headings',selectmode='browse')
            for name in columns:
                tree.heading(name,text=name)
                tree.column(name,width=220 if name in {'parameter','source'} else 110)
            tree.grid(row=0,column=0,sticky='nsew')
            y=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);y.grid(row=0,column=1,sticky='ns')
            x=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);x.grid(row=1,column=0,sticky='ew')
            tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
            tree.bind('<<TreeviewSelect>>',lambda e,t=tree:self._select_tree(t))
            for status,color in [('success','#e7f4e4'),('fail','#f8d7da'),('empty','#e8eef7')]:tree.tag_configure(status,background=color)
            self.trees[area]=tree
        self.tree=self.trees['mapping']

        editor = ttk.Frame(outer)
        editor.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        editor.columnconfigure(1, weight=1)
        ttk.Label(editor, text="Selected project value").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.selected_value).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(editor, text="Apply edit", command=self._apply_override).grid(row=0, column=3)

        self.details = tk.Text(outer, height=5, wrap="word", state="disabled")
        self.details.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self._version_changed()
        self._workflow_changed()

    def _workflow_changed(self) -> None:
        if self.workflow.get()!=self._active_workflow and not self._discard():
            self.workflow.set(self._active_workflow)
            return
        editing = self.workflow.get() == "開啟既有 config"
        if self.workflow.get() != self._active_workflow:
            self.source_path.set("")
            self.status_filter.set("全部")
        self._active_workflow = self.workflow.get()
        self.path_label.configure(text="Project config (cases/<case_id>/<version>)" if editing else "Ad Hoc workbook (reference_data)")
        self.template_label.configure(text="Detected config version" if editing else "Project template (automatic)")
        self.version_box.configure(state="disabled" if editing else "readonly")
        self.format_box.configure(state="disabled" if editing else "readonly")
        self.load_button.configure(text="Open Project Config" if editing else "Load Mapping")
        self.export_button.configure(text="Save Project Config" if editing else "Export Project Config")
        if editing:
            if not self.save_as_button.winfo_manager():
                self.save_as_button.pack(side="right", padx=6)
        else:
            self.save_as_button.pack_forget()
        self.draft = None
        self.existing_draft = None
        self.dirty=False
        self.channel_editor.tree.delete(*self.channel_editor.tree.get_children())
        self._refresh()
        if not editing:
            self._version_changed()
        else:
            self.detected_text.set("Choose an existing project config to open.")

    def _browse_input(self) -> None:
        if self.workflow.get() == "開啟既有 config":
            case_root = PROJECT_ROOT / "cases"
            options = {"filetypes": (("Project config", "config.xlsx"), ("Excel workbook", "*.xlsx"))}
            if case_root.is_dir():
                options["initialdir"] = str(case_root)
            value = filedialog.askopenfilename(**options)
            if value:
                self.source_path.set(value)
                self._open_existing()
            return
        self._browse_source()

    def _load_action(self) -> None:
        if self.workflow.get() == "開啟既有 config":
            self._open_existing()
        else:
            self._load()

    def _open_existing(self) -> None:
        try:
            if not self._discard():return
            draft = load_existing_project(self.source_path.get(), PROJECT_ROOT)
            self.existing_draft = draft
            self.draft = None
            self.case_id.set(draft.case_id)
            self.version.set(draft.target_version)
            self._active_version=draft.target_version
            self.channel_editor.load(draft)
            try:self.source_note.set(str(draft.get('fixed_config','source_note').value or ''))
            except KeyError:self.source_note.set('')
            for box in self.package_boxes:box.configure(state='disabled')
            self.dirty=False
            self.template_display.set(f"{draft.target_version} | {draft.source_path.relative_to(PROJECT_ROOT)}")
            self.status_filter.set("全部")
            audit_path = draft.source_path.with_suffix(".mapping.csv")
            audit_text = "mapping audit loaded" if audit_path.is_file() else "no mapping audit; source status is unrecorded"
            self._refresh()
            errors = validate_existing_project(draft, draft.source_path)
            validation_text = "runtime parser: valid" if not errors else f"runtime parser: {len(errors)} issue(s)"
            self.detected_text.set(
                f"Existing {draft.target_version} project config | {audit_text} | "
                f"{validation_text} | open warnings: {len(draft.open_warnings)}"
            )
            if errors or draft.open_warnings:
                messagebox.showwarning(
                    "Config opened with validation issues",
                    "\n".join((*draft.open_warnings, *errors)),
                )
        except Exception as error:
            if self.existing_draft is not None:
                self._refresh()
            messagebox.showerror("Open project config failed", f"{type(error).__name__}: {error}")

    def _version_changed(self) -> None:
        if self.version.get()!=self._active_version and not self._discard():
            self.version.set(self._active_version)
            return
        self._active_version=self.version.get()
        version = self.version.get()
        template = PROJECT_TEMPLATE_PATHS[version]
        self.template_display.set(str(template.relative_to(PROJECT_ROOT)))
        self.draft = None
        self.existing_draft = None
        self._refresh()
        self.load_button.configure(state="normal")
        self.export_button.configure(state="normal")
        self.detected_text.set("No workbook loaded.")
        self.dirty=False
        self._case_changed(mark=False)

    def _browse_source(self) -> None:
        if not self._discard():return
        source_dir = COM_ADHOC_ROOT
        options = {"filetypes": (("Excel workbook", "*.xlsx"), ("All files", "*.*"))}
        if source_dir.is_dir():
            options["initialdir"] = str(source_dir)
        value = filedialog.askopenfilename(**options)
        if value:
            self.source_path.set(value)
            self.tx_profile.set('');self.rx_profile.set('');self.package_selection.set('')
            self._load(confirm=False)

    def _browse_s4p(self) -> None:
        channel_dir = PROJECT_ROOT / "reference_data" / "COM_channel_data"
        options = {"filetypes": (("Touchstone S4P", "*.s4p"), ("All files", "*.*"))}
        if channel_dir.is_dir():
            options["initialdir"] = str(channel_dir)
        value = filedialog.askopenfilename(**options)
        if value:
            self.selected_value.set(value)

    def _load(self,confirm=True) -> None:
        try:
            if confirm and not self._discard():return
            selected_format = None if self.format_id.get() == AUTO_FORMAT else self.format_id.get()
            source_path = _validated_source_path(self.source_path.get())
            version = self.version.get()
            self.draft = build_project_config_draft(
                source_path, target_version=version,
                base_project_path=PROJECT_TEMPLATE_PATHS[version], format_id=selected_format,
                package_selection=int(self.package_selection.get()) if self.package_selection.get() else None,
                tx_profile=self.tx_profile.get() or None,rx_profile=self.rx_profile.get() or None,
            )
            self.existing_draft=None
            self._populate_packages()
            self.source_path.set(str(source_path))
            if self.case_id.get().strip():
                safe_case_id = validate_case_id(self.case_id.get().strip())
                self.case_id.set(safe_case_id)
                self.draft.set_override("fixed_config", "case_id", safe_case_id)
            descriptor = self.draft.source.descriptor
            self.detected_text.set(
                f"{descriptor.display_name} | {descriptor.format_id} | parser revision {descriptor.parser_revision} | "
                f"{self.draft.detection_status}/{self.draft.parser_selection} | "
                f"SHA-256 {self.draft.source.source_sha256[:16]}…"
            )
            self._refresh()
            self.dirty=False
            reference=[]
            for setting in self.draft.source.settings:
                if setting.key in {'Port Order','R_d'}:
                    reference.append(f'{setting.block or "source"} {setting.key}={setting.value}')
            self._show_details(('\n'.join(self.draft.source_issues) or 'Mapping loaded. Review fail / empty rows before export.')
                +'\nChannel interpretation reference (confirm for the selected S4P): '+ '; '.join(reference))
        except Exception as error:
            messagebox.showerror("Load mapping failed", f"{type(error).__name__}: {error}")

    def _refresh(self) -> None:
        for tree in self.trees.values():tree.delete(*tree.get_children())
        self.row_fields.clear()
        self.summary_text.set('')
        active = self.existing_draft or self.draft
        if active is None:
            return
        selected_status = self.status_filter.get()
        counts={'success':0,'fail':0,'empty':0}
        for field in active.fields:
            area=area_for(field,active.target_version)
            if area not in self.trees:continue
            display_status = self._display_status(field)
            if area=='mapping' and display_status in counts:counts[display_status]+=1
            if area=='mapping' and selected_status != "全部" and display_status != selected_status:
                continue
            tree=self.trees[area]
            item = tree.insert("", "end", values=(
                field.parameter, field.source_key or "", _display(field.source_value),_display(field.source_unit),
                _display(field.converted_value),_display(field.value),_display(field.unit),
                display_status if area=='mapping' else '',field.method,
                'yes' if field.status.value=='override' else '',
            ), tags=(display_status,))
            self.row_fields[(tree,item)] = field
        self.summary_text.set(" | ".join(f"{name}: {count}" for name, count in sorted(counts.items())))

    def _display_status(self, field: Any) -> str:
        if self.existing_draft is not None:
            if field.identity not in self.existing_draft.audit_rows or self.existing_draft.audit_rows[field.identity].get('original_status')=='existing_untracked':
                return "來源未記錄"
        active=self.existing_draft or self.draft
        return outcome(field,active.target_version,{f.identity:f.value for f in active.fields})

    def _select_tree(self,tree):
        self.tree=tree
        self._select()

    def _select(self, _event: Any = None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        field = self.row_fields[(self.tree,selection[0])]
        self.selected_value.set(_display(field.value))
        source_mapping = field.original_status or field.status
        if self.existing_draft is not None and field.identity not in self.existing_draft.audit_rows:
            mapping_detail = "來源／轉換稽核未記錄"
        else:
            mapping_detail = source_mapping.value
        detail = (
            f"Source: {field.source_cell or '-'}  key={field.source_key or '-'}  block={field.source_block or '-'}\n"
            f"Condition: {field.condition_cell or '-'}  key={field.condition_key or '-'}  value={_display(field.condition_value) or '-'}\n"
            f"Display status: {self._display_status(field)}; mapping detail: {mapping_detail}\n"
            f"Template value: {_display(field.base_value)}\n"
            f"Mapping: {field.note}\nDescription: {field.description or ''}"
        )
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", detail)
        self.details.configure(state="disabled")

    def _apply_override(self) -> None:
        selection = self.tree.selection()
        active = self.existing_draft or self.draft
        if not selection or active is None:
            return
        field = self.row_fields[(self.tree,selection[0])]
        try:
            value = _coerce_editor_value(self.selected_value.get(), field.value)
            active.set_override(field.sheet, field.parameter, value)
            self.dirty=True
            self._refresh()
        except Exception as error:
            messagebox.showerror("Invalid override", str(error))

    def _export(self) -> None:
        if self.existing_draft is not None:
            self._save_existing()
            return
        if self.draft is None:
            messagebox.showerror("Export failed", "Load a mapping first.")
            return
        try:
            case_id_text = self.case_id.get().strip()
            if not case_id_text:
                raise ValueError("Enter a case ID; it will also be the case-folder name.")
            case_id = validate_case_id(case_id_text)
            self.draft.set_override("fixed_config", "case_id", case_id)
            self.channel_editor.apply(self.draft)
            try:self.draft.set_override('fixed_config','source_note',self.source_note.get())
            except KeyError:pass
            self._refresh()
            destination = case_config_path(PROJECT_ROOT, case_id, self.draft.target_version)
        except (KeyError, ValueError) as error:
            messagebox.showerror("Export failed", str(error))
            return
        errors = self.draft.validation_errors()
        if errors:
            messagebox.showerror("Validation failed", "\n".join(f"• {error}" for error in errors))
            return
        if destination.exists() and not messagebox.askyesno(
            "Replace existing project config?",
            f"This case config already exists:\n{destination}\n\nReplace it?",
        ):
            return
        try:
            output = write_project_config(self.draft, destination)
            audit_json, audit_csv = write_conversion_audit(self.draft, output)
            self.dirty=False
            messagebox.showinfo("Export complete", f"{output}\n{audit_json}\n{audit_csv}")
        except Exception as error:
            messagebox.showerror("Export failed", f"{type(error).__name__}: {error}")

    def _save_existing_as(self) -> None:
        self._save_existing(save_as=True)

    def _save_existing(self, *, save_as: bool = False) -> None:
        draft = self.existing_draft
        if draft is None:
            messagebox.showerror("Save failed", "Open a project config first.")
            return
        try:
            case_id = validate_case_id(self.case_id.get().strip())
            if case_id != draft.case_id and not save_as:
                raise ValueError("Changing the case ID requires Save As so folder name and workbook stay aligned.")
            destination = canonical_destination(PROJECT_ROOT, case_id, draft.target_version) if save_as else draft.source_path
            self.channel_editor.apply(draft)
            try:draft.set_override('fixed_config','source_note',self.source_note.get())
            except KeyError:pass
            if destination.exists() and not messagebox.askyesno(
                "Replace existing project config?", f"This config already exists:\n{destination}\n\nReplace it?"
            ):
                return
            draft.set_override("fixed_config", "case_id", case_id)
            old_case_id=draft.case_id
            draft.case_id = case_id
            try:output = save_existing_project(draft, destination, PROJECT_ROOT)
            except Exception:
                draft.case_id=old_case_id
                raise
            self.source_path.set(str(output))
            self.case_id.set(case_id)
            self.detected_text.set(f"Saved {draft.target_version} project config | {output.relative_to(PROJECT_ROOT)}")
            self._refresh()
            self.dirty=False
            messagebox.showinfo("Save complete", str(output))
        except Exception as error:
            messagebox.showerror("Save failed", f"{type(error).__name__}: {error}")


    def _show_details(self,text):
        self.details.configure(state='normal');self.details.delete('1.0','end');self.details.insert('1.0',text);self.details.configure(state='disabled')

    def _mark_dirty(self):self.dirty=True

    def _case_changed(self,*_,mark=True):
        if mark and (self.draft or self.existing_draft):self.dirty=True
        try:self.output_preview.set(str(case_config_path(PROJECT_ROOT,self.case_id.get(),self.version.get())))
        except ValueError:self.output_preview.set('Output: cases/<case_id>/<version>/config.xlsx')

    def _discard(self):
        return not self.dirty or messagebox.askyesno('Unsaved edits','Discard unsaved edits and reload?')

    def _close(self):
        if self._discard():self.root.destroy()

    def _populate_packages(self):
        if not self.draft:return
        draft=self.draft
        for box in self.package_boxes:box.configure(state='readonly')
        for box in self.package_boxes[:2]:box.configure(values=draft.source.descriptor.signature_blocks)
        try:
            names=str(draft.source.require_one('PKG_NAME').value).split()
            self.tx_profile.set(draft.tx_profile or names[0]);self.rx_profile.set(draft.rx_profile or names[1])
            choices=tuple(str(int(v)) for v in array(draft.source.require_one('z_p select').value).ravel())
            self.package_boxes[2].configure(values=choices)
            self.package_selection.set(str(draft.package_selection) if draft.package_selection else choices[0] if len(choices)==1 else '')
        except (KeyError,ValueError,IndexError):pass

    def _package_changed(self,*_):
        if not self._discard():self._populate_packages();return
        self._load(confirm=False)


def _display(value: Any) -> str:
    return "" if value is None else str(value)


def _validated_source_path(value: str) -> Path:
    if not value.strip():
        raise ValueError("Choose an Ad Hoc workbook from the project reference_data/COM_adhoc_config folder.")
    path = Path(value).expanduser().resolve(strict=True)
    source_root = COM_ADHOC_ROOT.resolve(strict=True)
    try:
        path.relative_to(source_root)
    except ValueError as error:
        raise ValueError(
            f"Ad Hoc workbooks must be stored under the project folder {source_root}."
        ) from error
    if not path.is_file() or path.suffix.lower() != ".xlsx":
        raise ValueError("The selected source must be an .xlsx workbook file.")
    return path


def _coerce_editor_value(text: str, previous: Any) -> Any:
    stripped = text.strip()
    if stripped.lower() in {"none", "null", ""}:
        return None
    if isinstance(previous, bool):
        if stripped.lower() in {"true", "1", "yes"}:
            return True
        if stripped.lower() in {"false", "0", "no"}:
            return False
        raise ValueError("Boolean override must be true or false.")
    if isinstance(previous, int) and not isinstance(previous, bool):
        return int(stripped)
    if isinstance(previous, float):
        return float(stripped)
    return text


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Review COM Ad Hoc to project-config conversion")
    parser.add_argument("--source", default=None)
    args = parser.parse_args(argv)
    root = tk.Tk()
    missing_templates = [
        f"{version}: {path}" for version, path in PROJECT_TEMPLATE_PATHS.items()
        if not path.is_file()
    ]
    if missing_templates:
        messagebox.showerror(
            "Project template missing",
            "Required fixed project-config templates were not found:\n" + "\n".join(missing_templates),
        )
        root.destroy()
        return
    COMConfigConversionGui(root, source=args.source)
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:])


__all__ = ["COMConfigConversionGui", "main"]
