import shutil
import subprocess
import sys
import logging
import csv
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QMessageBox, QHBoxLayout, QApplication

from albumexplore.database import get_session
from albumexplore.database.models import Tag, album_tags

# Import script modules directly to run them in-process
# We need to add 'scripts' to sys.path if not there, or assume structure
# Since 'scripts' is at root, we might need to adjust path or use subprocess
# user said "Python analysis scripts automatically run", subprocess is often cleaner for "scripts"

dev_logger = logging.getLogger('albumexplore.dev_tools')

class TagDevLoopDialog(QDialog):
    def __init__(self, parent=None, summary_text=""):
        super().__init__(parent)
        self.setWindowTitle("Tag Normalization Dev Loop Output")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setPlainText(summary_text)
        layout.addWidget(self.editor)
        
        # Buttons: Copy Text and Close
        btn_row = QHBoxLayout()
        copy_btn = QPushButton("Copy Text")
        copy_btn.clicked.connect(self._copy_text)
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _copy_text(self):
        try:
            text = self.editor.toPlainText()
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "Copied", "Dialog text copied to clipboard.")
        except Exception as e:
            QMessageBox.warning(self, "Copy Failed", f"Failed to copy text: {e}")

class TagDevLoop:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.export_dir = self.project_root / "data" / "exports"
        self.tag_analysis_dir = self.project_root / "scripts" / "tag_analysis"
        self.csv_name = "atomic_tags_export2.csv"
        self.csv_path = self.export_dir / self.csv_name
        # Track tag rules file mtime to detect external changes
        self.tag_rules_path = self.project_root / "src" / "albumexplore" / "config" / "tag_rules.json"
        try:
            self._tag_rules_mtime = self.tag_rules_path.stat().st_mtime
        except Exception:
            self._tag_rules_mtime = None
        
        # Ensure directories exist
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.tag_analysis_dir.mkdir(parents=True, exist_ok=True)

    def run_loop(self, parent_widget=None):
        try:
            # 1. Wipe export directory (or just the target files to be safe)
            self._wipe_exports()
            
            # 2. Export tags from DB
            self._export_tags_to_csv()
            
            # 3. Run analysis scripts
            analysis_output = self._run_analysis_scripts()
            
            # 4. Generate LLM Prompt
            final_output = self._generate_llm_prompt(analysis_output)
            
            # 5. Show Result
            if parent_widget:
                dialog = TagDevLoopDialog(parent_widget, final_output)
                dialog.exec()
            else:
                print(final_output)
                
        except Exception as e:
            dev_logger.error(f"Dev loop failed: {e}", exc_info=True)
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"Dev loop failed:\n{e}")

    def _wipe_exports(self):
        dev_logger.info(f"Wiping files in {self.export_dir}...")
        # Only delete relevant files to avoid wiping user data accidentally
        for file in self.export_dir.glob("*.csv"):
            try:
                file.unlink()
            except Exception as e:
                dev_logger.warning(f"Could not delete {file}: {e}")
        for file in self.export_dir.glob("*.json"):
            try: 
                file.unlink()
            except Exception as e:
                dev_logger.warning(f"Could not delete {file}: {e}")
    
    def _export_tags_to_csv(self):
        dev_logger.info("Exporting tags from database...")
        session = get_session()
        try:
            # Query tags and counts
            # Assuming models.Tag and models.AlbumTag are set up for this join/count logic
            # Use raw SQL for speed and simplicity if models define relationships differently
            # But let's try ORM first if possible, or straight SQL
            
            # SQL equivalent: 
            # SELECT t.name, count(at.album_id) as cnt 
            # FROM tags t 
            # JOIN album_tags at ON t.id = at.tag_id 
            # GROUP BY t.name 
            # ORDER BY cnt DESC
            
            from sqlalchemy import func
            query = (session.query(Tag.name, func.count(album_tags.c.album_id).label('count'))
                     .join(album_tags, Tag.id == album_tags.c.tag_id)
                     .group_by(Tag.name)
                     .order_by(func.count(album_tags.c.album_id).desc()))
            
            results = query.all()
            
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Tag', 'Count'])
                for tag_name, count in results:
                    writer.writerow([tag_name, count])
                    
            dev_logger.info(f"Exported {len(results)} tags to {self.csv_path}")
            
        finally:
            session.close()

    def _run_analysis_scripts(self):
        output_buffer = ["--- script execution log ---"]
        
        # Script 1: auto_singleton_mapper.py
        script1 = self.tag_analysis_dir / "auto_singleton_mapper.py"
        suggestions_json = self.export_dir / "singleton_suggestions.json"
        
        # Prepare environment with src in pythonpath
        env = os.environ.copy()
        src_dir = self.project_root / 'src'
        env['PYTHONPATH'] = str(src_dir) + os.pathsep + env.get('PYTHONPATH', '')
        
        cmd1 = [sys.executable, str(script1), str(self.csv_path), str(suggestions_json)]
        output_buffer.append(f"Running: {' '.join(cmd1)}")
        try:
            res1 = subprocess.run(cmd1, capture_output=True, text=True, cwd=self.project_root, env=env)
            output_buffer.append(res1.stdout)
            if res1.stderr:
                output_buffer.append(f"STDERR:\n{res1.stderr}")
        except Exception as e:
            output_buffer.append(f"Failed to run script 1: {e}")

        # Script 1.5: check_cooccurrence.py
        script1_5 = self.tag_analysis_dir / "check_cooccurrence.py"
        cmd1_5 = [sys.executable, str(script1_5)]
        output_buffer.append(f"Running: {' '.join(cmd1_5)}")
        try:
            res1_5 = subprocess.run(cmd1_5, capture_output=True, text=True, cwd=self.project_root, env=env)
            output_buffer.append(res1_5.stdout)
            if res1_5.stderr:
                output_buffer.append(f"STDERR:\n{res1_5.stderr}")
        except Exception as e:
            output_buffer.append(f"Failed to run script 1.5: {e}")

        # Script 1.6: merge_suggestions.py
        script1_6 = self.tag_analysis_dir / "merge_suggestions.py"
        cmd1_6 = [sys.executable, str(script1_6)]
        output_buffer.append(f"Running: {' '.join(cmd1_6)}")
        try:
            res1_6 = subprocess.run(cmd1_6, capture_output=True, text=True, cwd=self.project_root, env=env)
            output_buffer.append(res1_6.stdout)
            if res1_6.stderr:
                output_buffer.append(f"STDERR:\n{res1_6.stderr}")
        except Exception as e:
            output_buffer.append(f"Failed to run script 1.6: {e}")
            
        merged_json = self.export_dir / 'merged_suggestions.json'

        # Script 2: score_suggestions.py
        script2 = self.tag_analysis_dir / "score_suggestions.py"
        cmd2 = [sys.executable, str(script2), str(merged_json)]
        output_buffer.append(f"Running: {' '.join(cmd2)}")
        try:
            res2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=self.project_root, env=env)
            output_buffer.append(res2.stdout)
            if res2.stderr:
                output_buffer.append(f"STDERR:\n{res2.stderr}")
        except Exception as e:
            output_buffer.append(f"Failed to run script 2: {e}")

        # Script 3: generate_application_script.py (this replaces direct review)
        script3 = self.tag_analysis_dir / "generate_application_script.py"
        scored_json = self.export_dir / 'merged_suggestions_scored.json'
        target_json = scored_json if scored_json.exists() else merged_json
        
        # We need a predictable location for the script so we can find it later
        adhoc_dir = self.project_root / 'scripts' / 'adhoc'
        adhoc_dir.mkdir(parents=True, exist_ok=True)
        
        cmd3 = [sys.executable, str(script3), '--suggestions', str(target_json), '--output-dir', str(adhoc_dir)]
        output_buffer.append(f"Running: {' '.join(cmd3)}")
        try:
            res3 = subprocess.run(cmd3, capture_output=True, text=True, cwd=self.project_root, env=env)
            output_buffer.append(res3.stdout)
            if res3.stderr:
                output_buffer.append(f"STDERR:\n{res3.stderr}")
        except Exception as e:
            output_buffer.append(f"Failed to run script 3: {e}")

        # Script 4: validate_normalization.py
        script4 = self.tag_analysis_dir / "validate_normalization.py"
        validation_json = self.export_dir / "normalization_validation.json"
        
        cmd4 = [sys.executable, str(script4), str(self.csv_path), str(validation_json)]
        output_buffer.append(f"Running: {' '.join(cmd4)}")
        try:
            res4 = subprocess.run(cmd4, capture_output=True, text=True, cwd=self.project_root, env=env)
            output_buffer.append(res4.stdout)
            if res4.stderr:
                output_buffer.append(f"STDERR:\n{res4.stderr}")
        except Exception as e:
            output_buffer.append(f"Failed to run script 4: {e}")
        # After running analysis scripts, check for tag_rules.json changes and reload normalizer if needed
        try:
            self._maybe_refresh_normalizer()
            output_buffer.append("[DevLoop] Normalizer refresh attempted if rules changed.")
        except Exception as e:
            output_buffer.append(f"[DevLoop] Normalizer refresh failed: {e}")

        return "\n".join(output_buffer)

    def _maybe_refresh_normalizer(self):
        """If `tag_rules.json` changed, reload normalizer modules and try to refresh in-memory instances."""
        import importlib, sys

        try:
            new_mtime = None
            try:
                new_mtime = self.tag_rules_path.stat().st_mtime
            except Exception:
                new_mtime = None

            if new_mtime and self._tag_rules_mtime and new_mtime == self._tag_rules_mtime:
                # No change
                return

            # Update stored mtime
            self._tag_rules_mtime = new_mtime

            # Modules to reload
            module_names = [
                'albumexplore.tags.config.tag_rules_config',
                'albumexplore.tags.normalizer.tag_normalizer',
                'albumexplore.tags.normalizer.enhanced_normalizer',
                'albumexplore.tags.normalizer'
            ]

            reloaded = []
            for mname in module_names:
                if mname in sys.modules:
                    try:
                        importlib.reload(sys.modules[mname])
                        reloaded.append(mname)
                    except Exception:
                        # Try importing then reloading
                        try:
                            mod = importlib.import_module(mname)
                            importlib.reload(mod)
                            reloaded.append(mname)
                        except Exception:
                            pass

            # Attempt to find any in-memory normalizer singletons and call their reload methods
            # Common places: modules may expose a `normalizer` or `tag_normalizer` variable
            for mod in list(sys.modules.values()):
                if not mod:
                    continue
                for attr_name in ('normalizer', 'tag_normalizer', 'tagNormalizer'):
                    try:
                        obj = getattr(mod, attr_name, None)
                        if obj and hasattr(obj, 'reload_config'):
                            try:
                                obj.reload_config()
                            except Exception:
                                pass
                        if obj and hasattr(obj, 'reload_atomic_config'):
                            try:
                                obj.reload_atomic_config()
                            except Exception:
                                pass
                        if obj and hasattr(obj, 'clear_cache'):
                            try:
                                obj.clear_cache()
                            except Exception:
                                pass
                    except Exception:
                        continue

            # Also attempt to reload module-level TagNormalizer class caches if any
            # Informational logging
            dev_logger.info(f"Reloaded modules: {reloaded}")

            # If running inside a Qt app, show a brief messagebox to the user
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(None, "Normalizer Reloaded", "Tag normalizer rules reloaded (if changed).")
            except Exception:
                pass

        except Exception as e:
            dev_logger.exception("Failed during normalizer refresh: %s", e)

    def _generate_llm_prompt(self, analysis_log):
        # Look for the generated script in stdout
        generated_script_path = None
        for line in analysis_log.splitlines():
            if "Generated application script:" in line:
                generated_script_path = line.split("Generated application script:")[-1].strip()
        
        # Validation output
        validation_json_path = self.export_dir / "normalization_validation.json"
        validation_content = ""
        if validation_json_path.exists():
            validation_content = validation_json_path.read_text(encoding='utf-8')
            
        script_snippet = ""
        if generated_script_path:
             try:
                 # Read first 50 lines of generated script
                 with open(generated_script_path, 'r', encoding='utf-8') as f:
                     lines = f.readlines()
                     script_snippet = "".join(lines) # Read all for context if not too huge
             except Exception as e:
                 script_snippet = f"Could not read script: {e}"

        timestamp = datetime.now().isoformat()
        
        prompt = f"""# Tag Normalization Task - {timestamp}

Here is the latest analysis from the dev loop. 
A Python script has been generated with suggested tag mappings.

## Context
- **Generated Script**: `{generated_script_path or "Unknown"}`
- **Analysis Log**:
```
{analysis_log}
```

## Generated Application Script (Draft)
The script below contains the suggested mappings.
```python
{script_snippet}
```

## Validation Report
The file `data/exports/normalization_validation.json` contains:
```json
{validation_content}
```

## Task
Please review the generated script.
1. Analyze the mappings in `SUGGESTED_MAPPINGS`.
2. Identify any incorrect or dangerous normalizations (e.g. incorrect fuzzy matches, year swaps, antonyms).
3. **Execute the script** (or a modified version of it) to apply the mappings to `src/albumexplore/config/tag_rules.json`.
"""
        return prompt
