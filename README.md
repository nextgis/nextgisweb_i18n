# Automated translation approach

We use a python script to automatically translate .po files that have missing 
translation strings. The script scans recursively all directories and translates
all *.po files using chatgpt 4o.

Perform several runs and check the generated .po files, since LLM's do not
work 100% correct.

To run the automated translation an .env file must be created with an OpenAI API key.

```bash
python po_translater.py . --recursive --batch-size 20 --log-dir .logs 
```