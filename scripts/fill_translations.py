"""Merge a Python dict of translations into a gettext catalog and compile it.

Normal translation work happens directly in the .po files (any PO editor, e.g. Poedit).
This helper exists for bulk updates:

    python scripts/fill_translations.py <template.pot> <catalog.po> <module_with_KM_dict.py>

Messages without a translation are kept empty, so gettext falls back to English for them.
"""
import importlib.util
import sys
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po


def main(pot_path: str, po_path: str, dict_module: str):
    spec = importlib.util.spec_from_file_location("translations", dict_module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    translations: dict = module.KM

    with open(pot_path, "rb") as f:
        template = read_po(f)
    po = Path(po_path)
    if po.exists():
        with po.open("rb") as f:
            catalog = read_po(f, locale="km")
        catalog.update(template)
    else:
        catalog = template
        catalog.locale = "km"

    missing = []
    for message in catalog:
        if not message.id:
            continue
        if message.id in translations:
            message.string = translations[message.id]
        elif not message.string:
            missing.append(message.id)
    catalog.fuzzy = False
    for message in catalog:
        message.flags.discard("fuzzy")

    po.parent.mkdir(parents=True, exist_ok=True)
    with po.open("wb") as f:
        write_po(f, catalog, width=0, omit_header=False, sort_output=True)
    with po.with_suffix(".mo").open("wb") as f:
        write_mo(f, catalog)
    print(f"{po}: {len([m for m in catalog if m.id])} messages, {len(missing)} untranslated")
    for message_id in missing:
        print("  untranslated:", message_id)


if __name__ == "__main__":
    main(*sys.argv[1:4])
