# Merge Translations

This script helps manage and merge translations from automatic translation services with manually maintained translations.

## Requirements

- Python 3.8 or higher
- polib library

## Installation

1. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install required packages:
```bash
pip install polib
```

## Purpose

The script serves to:
1. Combine AI-generated translations with existing manual translations
2. Preserve manually translated strings while filling in missing translations from AI
3. Generate separate .ai.po files containing only AI translations that don't conflict with manual ones

## How it works

The script processes translations by:

1. Loading two sets of .po files:
   - Manual translations from the `master/` directory - https://github.com/nextgis/nextgisweb_i18n/tree/master
   - Automatic translations from the `polyglot/` directory - https://github.com/nextgis/nextgisweb_i18n/tree/polyglot

2. For each language/component pair:
   - Loads both manual and automatic translation files
   - Compares translations between them
   - Creates a new .ai.po file containing only AI translations for strings that:
     - Don't exist in manual translations
     - Exist but aren't translated in manual translations (empty msgstr)

3. File structure:
```
project/
├── master/              # Manual translations
│   └── component/
│       ├── en.po       # Original manual translations
│       └── en.ai.po    # Generated AI-only translations
└── polyglot/           # AI-generated translations
    └── component/
        └── en.po
```

## Usage

```bash
python merge_translations.py
```

The script will:
1. Scan the master/ directory for .po files
2. Find corresponding files in polyglot/
3. Generate .ai.po files next to original manual translations
4. Print summary of unique translations added to each .ai.po file
