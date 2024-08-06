# Python
import os
import json
import yaml
from yaml.loader import SafeLoader
import re
import argparse
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel
import polib
from litellm import completion


class TranslationEntry(BaseModel):
    original: str
    translation: str = ""


LANGUAGE_MAP = {
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "es": "Spanish",
    "be": "Belarusian",
    "bg": "Bulgarian",
    "cs": "Czech",
    "zh-cn": "Chinese_Simplified",
    "pt": "Portuguese"
}


def custom_yaml_loader():
    """Create a custom YAML loader that can handle problematic quotations."""

    class QuotedLoader(SafeLoader):
        pass

    def construct_quoted_string(loader, node):
        return node.value.strip("'")

        QuotedLoader.add_constructor('tag:yaml.org,2002:str', construct_quoted_string)

    return QuotedLoader


def clean_translation(translation: str) -> str:
    """Clean up the translation by removing YAML artifacts and extra whitespace."""
    # Remove any leading/trailing quotes
    translation = translation.strip("'")
    # Remove any YAML-like structure
    translation = re.sub(r'^- original:.*?\n\s*translation:\s*', '', translation, flags=re.MULTILINE)
    # Remove extra whitespace
    translation = ' '.join(translation.split())
    return translation


def clean_yaml_content(content):
    """Clean up YAML content by escaping problematic characters."""
    # Replace unescaped single quotes with escaped ones, but only if they're not already escaped
    content = re.sub(r"(?<!\)')", r"'", content)
    # Replace unescaped double quotes with escaped ones, but only if they're not already escaped
    content = re.sub(r'(?<!\)")', r'"', content)
    return content


def parse_yaml_safely(yaml_content: str) -> List[Dict[str, str]]:
    """Parse YAML content and extract only the translations."""
    try:
        # Try to parse as YAML first
        data = yaml.safe_load(yaml_content)
        if isinstance(data, list):
            return [{'original': item['original'], 'translation': clean_translation(item['translation'])} for item in
                    data]
    except yaml.YAMLError:
        pass

    # If YAML parsing fails, use regex to extract translations
    entries = []
    pattern = r"- original: '?(.*?)'?\s+translation: '?(.*?)'?(?:\n|$)"
    matches = re.findall(pattern, yaml_content, re.DOTALL)
    for original, translation in matches:
        entries.append({
            'original': original.strip(),
            'translation': clean_translation(translation)
        })

    return entries


def create_summary(entries: List[polib.POEntry], source_lang: str, model: str) -> str:
    all_texts = "\n".join(entry.msgid for entry in entries if entry.msgid)
    prompt = (
        f"You are analyzing messages for a Web GIS software written in {source_lang}.\n"
        "Create a concise summary that reflects the technical topics described in these strings.\n"
        "Focus on the main themes, key functionalities, and any specific GIS-related concepts mentioned.\n"
        "This summary will be used to provide context for translation.\n\n"
        "Here are the messages:\n\n"
        f"{all_texts}\n\n"
        "Provide a concise summary:\n"
    )

    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.1
    )

    return response.choices[0].message.content.strip()


def load_translation_dictionary(source_lang: str, target_lang: str) -> Dict[str, str]:
    dict_file = f"dict_{source_lang.lower()}_{target_lang.lower()}.json"
    if os.path.exists(dict_file):
        with open(dict_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_translated_examples(po: polib.POFile, limit: int = 20) -> List[Dict[str, str]]:
    examples = [
        {"original": entry.msgid, "translation": entry.msgstr}
        for entry in po if entry.msgstr and entry.msgstr != entry.msgid
    ]
    return examples[:limit]


def translate_batch(entries: List[TranslationEntry], source_lang: str, target_lang: str, context: str, model: str,
                    translation_dict: Dict[str, str], examples: List[Dict[str, str]], log_dir: str) -> List[
    TranslationEntry]:
    yaml_entries = yaml.dump([entry.dict() for entry in entries])
    dict_yaml = yaml.dump(translation_dict)
    examples_yaml = yaml.dump(examples)

    prompt = (
        f"You are translating messages for a Web GIS software from {source_lang} to {target_lang}.\n"
        "Ensure that the translation is in perfect {target_lang}.\n"
        "The messages may contain Python string formatting (e.g., %d, %s, {{}}, {{0}}). "
        "These formatting strings must be preserved exactly as they appear in the original text.\n"
        "Translate only the text around the formatting strings, maintaining the original meaning and tone.\n"
        "Use appropriate technical terms commonly used in the IT context of the target language. "
        "Often, English words are directly used in technical contexts when there is no better term available.\n\n"
        "For example:\n"
        "- 'flag': This is usually understood as an option or setting and can be used directly in the translation.\n"
        "- 'upgrade': This is a technical term that can be used as is in the translation.\n"
        "- 'server': Commonly used in IT and can be used directly.\n"
        "- 'database': Often used as is in many languages.\n"
        "- 'API': Stands for Application Programming Interface and is widely recognized.\n"
        "- 'debug': Used in the context of troubleshooting and can be used directly.\n"
        "- 'cache': Refers to temporary storage and is often used as is.\n"
        "- 'module': A component or part of a system, commonly used directly.\n"
        "- 'script': Refers to a set of commands and is often used as is.\n"
        "- 'interface': Refers to a point of interaction and is commonly used directly.\n"
        "- 'layer': Refers in a GIS context a map that can be displayed and edited and is commonly used directly.\n"
        "- 'geospatial': Refers to data that has a geographic or spatial aspect.\n"
        "- 'coordinate system': A system used to define the position of points in space.\n"
        "- 'projection': A method of transforming the curved surface of the Earth onto a flat plane.\n"
        "- 'datum': A reference system for measuring locations on the Earth.\n"
        "- 'geocoding': The process of converting addresses into geographic coordinates.\n"
        "- 'reverse geocoding': The process of converting geographic coordinates into addresses.\n"
        "- 'raster': A data structure that represents a generally rectangular grid of pixels or points of color.\n"
        "- 'vector': A data structure that represents geographical features using points, lines, and polygons.\n"
        "- 'shapefile': A popular geospatial vector data format for geographic information system software.\n"
        "- 'georeferencing': The process of establishing a relationship between a spatial reference system and the coordinate system of a digital map or raster image.\n"
        "- 'web map': An interactive map displayed in a web browser.\n"
        "- 'map service': A service that provides map data over the internet.\n"
        "- 'feature service': A service that provides access to geographic features and their attributes.\n"
        "- 'tile service': A service that provides map data in the form of pre-rendered image tiles.\n"
        "- 'WMS (Web Map Service)': A standard protocol for serving georeferenced map images over the internet.\n"
        "- 'WFS (Web Feature Service)': A standard protocol for serving geographic features over the internet.\n"
        "- 'REST API': A set of rules and conventions for building and interacting with web services.\n"
        "- 'geoprocessing': The use of computational methods to analyze and manipulate geospatial data.\n"
        "- 'spatial analysis': The process of analyzing geospatial data to identify patterns, trends, and relationships.\n"
        "- 'heatmap': A graphical representation of data where the individual values contained in a matrix are represented as colors.\n"
        "- 'algorithm': A set of instructions or procedures used to solve a problem or accomplish a task.\n"
        "- 'API key': A unique identifier used to authenticate a user, developer, or calling program to an API.\n"
        "- 'cloud computing': The delivery of different services through the internet, including data storage, servers, databases, networking, and software.\n"
        "- 'data visualization': The graphical representation of information and data.\n"
        "- 'machine learning': A subset of artificial intelligence that involves training algorithms to make predictions or decisions based on data.\n"
        "- 'metadata': Data that describes and gives information about other data.\n"
        "- 'plugin': A software component that adds a specific feature to an existing computer program.\n"
        "- 'SDK (Software Development Kit)': A set of software development tools that allows the creation of applications for a certain software package, software framework, hardware platform, computer system, video game console, operating system, or similar development platform.\n"
        "- 'UI (User Interface)': The space where interactions between humans and machines occur.\n"
        "- 'UX (User Experience)': The overall experience of a person using a product such as a website or a computer application, especially in terms of how easy or pleasing it is to use.\n\n"
        "Ensure that you translate technical topics correctly.\n\n"
        f"Context for translation:\n{context}\n\n"
        f"Use the following translation dictionary for specific terms:\n{dict_yaml}\n\n"
        f"Here are some examples of previously translated messages:\n{examples_yaml}\n\n"
        "Here are the messages to translate, provided in YAML format:\n\n"
        f"{yaml_entries}\n\n"
        "Translate each entry and provide the result in the same YAML format, filling in the 'translation' field for each entry.\n"
        "Enclose your YAML output within <yaml_content> tags. Ensure correct YAML output.\n"
    )

    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096
    )

    yaml_content = response.choices[0].message.content.split("<yaml_content>")[1].split("</yaml_content>")[0].strip()

    log_file = os.path.join(log_dir, f"translation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
    log_content = {
        "request": {"model": model, "prompt": prompt},
        "response": yaml_content
    }

    with open(log_file, 'w', encoding="utf-8") as f:
        yaml.safe_dump(log_content, f, default_flow_style=False, sort_keys=False, width=80, indent=2,
                       allow_unicode=True)

    try:
        translated_entries = parse_yaml_safely(yaml_content)
        return [TranslationEntry(original=entry['original'], translation=entry['translation']) for entry in
                translated_entries]
    except Exception as e:
        print(f"Error parsing YAML content: {e}")
        print("Falling back to original entries without translation")
        return entries


def translate_po_file(input_file: str, output_file: str, source_lang: str, target_lang: str, model: str,
                      batch_size: int, log_dir: str):
    po = polib.pofile(input_file)

    entries_to_translate = [TranslationEntry(original=entry.msgid) for entry in po if
                            not entry.msgstr or entry.msgstr == entry.msgid]

    if len(entries_to_translate) < 5:
        context = ""
    else:
        context = create_summary(po, source_lang, model)
        print(f"Context summary created")

    translation_dict = load_translation_dictionary(source_lang, target_lang)
    print(f"Loaded {len(translation_dict)} translation dictionary entries")

    examples = get_translated_examples(po)
    print(f"Found {len(examples)} examples of previously translated messages")

    for i in range(0, len(entries_to_translate), batch_size):
        batch = entries_to_translate[i:i + batch_size]
        try:
            translated_batch = translate_batch(batch, source_lang, target_lang, context, model, translation_dict,
                                               examples, log_dir)
            for original_entry, translated_entry in zip(batch, translated_batch):
                print(f"Original: {original_entry.original}")
                print(f"Translation: {translated_entry.translation}\n")

                for po_entry in po:
                    if po_entry.msgid == original_entry.original:
                        po_entry.msgstr = translated_entry.translation
                        break

        except Exception as e:
            print(f"Error translating batch: {e}")

    po.save(output_file)


def create_backup_file(input_file: str) -> str:
    base_name = os.path.splitext(input_file)[0]

    for i in range(1, 1000):
        backup_file = f"{base_name}.{i:03d}.bak"
        if not os.path.exists(backup_file):
            return backup_file

    raise RuntimeError("Unable to create a unique backup filename")


def translate_directory(directory: str, source_lang: str, model: str, batch_size: int, log_dir: str):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".po"):
                lang_code = file.split('.')[0]
                target_lang = LANGUAGE_MAP.get(lang_code)
                if target_lang:
                    input_file = os.path.join(root, file)
                    output_file = input_file  # Output file should have the same name as the original
                    backup_file = create_backup_file(input_file)
                    os.rename(input_file, backup_file)
                    translate_po_file(backup_file, output_file, source_lang, target_lang, model, batch_size, log_dir)

                    # Check if any translations were made
                    if os.path.getsize(backup_file) != os.path.getsize(output_file):
                        print(f"Translated {input_file}")
                    else:
                        print(f"No translations needed for {input_file}")
                        os.remove(output_file)  # Remove the unnecessary output file
                        os.rename(backup_file, input_file)  # Restore the original file


def main():
    """
     python scripts/po_translater.py ../nextgisweb_i18n/nextgisweb_ngwcluster/ngwcluster/ --recursive --log-dir logs --model gpt-4o --batch-size 1

     python scripts/po_translater.py de.po --source English --target German --log-dir logs --model gpt-4o

    :return:
    """
    parser = argparse.ArgumentParser(description="Translate .po files using specified LLM.")
    parser.add_argument("input_path", help="Path to the input .po file or directory")
    parser.add_argument("--source", default="English", help="Source language (default: English)")
    parser.add_argument("--target", help="Target language for translation (required for single file mode)")
    parser.add_argument("--model", default="gpt-4o",
                        help="LLM model to use for translation. Options: gpt-4o, gpt-4o-mini, anthropic/claude-3-5-sonnet-20240620")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of entries to translate in each batch")
    parser.add_argument("--log-dir", default="translation_logs", help="Directory to store translation logs")
    parser.add_argument("--recursive", action="store_true", help="Translate all .po files in a directory recursively")

    args = parser.parse_args()

    print(f"Using model: {args.model}")
    print(f"Batch size: {args.batch_size}")
    print(f"Log directory: {args.log_dir}")

    os.makedirs(args.log_dir, exist_ok=True)

    if args.recursive:
        print(f"Translating all .po files in directory {args.input_path} recursively")
        translate_directory(args.input_path, args.source, args.model, args.batch_size, args.log_dir)
    else:
        if not args.target:
            print("Target language is required for single file mode")
            return
        print(f"Translating {args.input_path} from {args.source} to {args.target}")
        print(f"Output will be saved to {args.input_path}")
        translate_po_file(args.input_path, args.input_path, args.source, args.target, args.model, args.batch_size,
                          args.log_dir)

    print("Translation completed successfully!")


if __name__ == "__main__":
    main()
