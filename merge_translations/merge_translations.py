import polib
from pathlib import Path
from typing import Dict, Tuple

def load_po_file(file_path: Path) -> Dict[Tuple[str, str], Dict]:
    translations = {}
    if not file_path.exists():
        return translations
    
    po = polib.pofile(str(file_path))
    for entry in po:
        key = (entry.msgid, entry.msgctxt if hasattr(entry, 'msgctxt') else None)
        translations[key] = {
            'msgstr': entry.msgstr,
            'comment': entry.comment,
            'tcomment': entry.tcomment,
            'occurrences': entry.occurrences
        }
    return translations

def save_ai_translations(file_path: Path, translations: Dict[Tuple[str, str], Dict]):
    po = polib.POFile()
    
    for (msgid, msgctxt), trans_data in translations.items():
        entry = polib.POEntry(
            msgid=msgid,
            msgstr=trans_data['msgstr'],
            msgctxt=msgctxt,
            comment=trans_data['comment'],
            tcomment=trans_data['tcomment'],
            occurrences=trans_data['occurrences']
        )
        po.append(entry)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(file_path))

def process_translations(manual_root: Path, auto_root: Path):
    manual_root = manual_root.resolve()
    auto_root = auto_root.resolve()

    for po_path in manual_root.rglob('*.po'):
        rel_path = po_path.relative_to(manual_root)
        auto_path = auto_root / rel_path

        if not auto_path.exists():
            continue
            
        manual_trans = load_po_file(po_path)
        auto_trans = load_po_file(auto_path)
        
        ai_translations = {}
        for key, value in auto_trans.items():
            manual_data = manual_trans.get(key)
            is_manual_translated = manual_data is not None and manual_data['msgstr'] != ""

            if not is_manual_translated and value['msgstr']:
                ai_translations[key] = value

        ai_path = po_path.parent / f"{po_path.stem}.ai.po"
        save_ai_translations(ai_path, ai_translations)
        print(f"Created {ai_path} with {len(ai_translations)} unique translations")

def main():
    current_dir = Path.cwd()

    manual_root = current_dir / "master"
    auto_root = current_dir / "polyglot"
    
    process_translations(manual_root, auto_root)

if __name__ == "__main__":
    main() 