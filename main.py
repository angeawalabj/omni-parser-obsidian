"""
Omni-Parser Pro - The Industrial Orchestrator
---------------------------------------------
Pipeline: Audit -> Transform -> Sanitize -> Enrich -> Optimize
Version: 1.0.0 (Production Ready)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Import des modules spécialisés
from scripts.auditor import SourceAuditor
from scripts.transformer import ContentTransformer
from scripts.sanitizer import ContentSanitizer
from scripts.metadata_injector import MetadataInjector
from scripts.asset_deduplicator import AssetDeduplicator

# ============================================================
# CONFIGURATION
# ============================================================

SOURCE_PATH = Path("./data/samples")
VAULT_PATH = Path("./data/output_vault")
ATTACHMENTS_PATH = VAULT_PATH / "attachments"
LOG_FILE = Path("migration_log.txt")

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("OmniParser.Main")

# ============================================================
# ORCHESTRATEUR
# ============================================================

class MigrationOrchestrator:
    """Orchestrates the full Omni-Parser Pro pipeline"""
    def __init__(self):
        self.auditor = SourceAuditor()
        self.transformer = ContentTransformer()
        self.sanitizer = ContentSanitizer()
        self.injector = MetadataInjector()
        self.optimizer = AssetDeduplicator()

    def run(self):
        start_time = datetime.now()
        logger.info("Starting Full Migration Pipeline...")

        # --- ÉTAPE 1: AUDIT ---
        try:
            logger.info("STEP 1: Pre-flight Audit...")
            report = self.auditor.audit_directory(SOURCE_PATH)
            print(self.auditor.generate_text_report(report))

            if not report.is_valid:
                logger.error("Audit failed. Migration aborted for data safety.")
                return
        except Exception as e:
            logger.exception(f"Audit stage failed: {e}")
            return

        # --- ÉTAPE 2: TRANSFORMATION ---
        VAULT_PATH.mkdir(parents=True, exist_ok=True)
        ATTACHMENTS_PATH.mkdir(parents=True, exist_ok=True)

        processed_files = []
        for file_audit in report.file_audits:
            input_file = file_audit.filepath
            output_file = VAULT_PATH / f"{input_file.stem}.md"
            try:
                result = self.transformer.transform_file(
                    input_file, 
                    output_file, 
                    ATTACHMENTS_PATH
                )
                if result.success:
                    processed_files.append(output_file)
                    logger.info(f"✓ Transformed: {input_file.name}")
                else:
                    logger.warning(f"✗ Failed: {input_file.name} | Error: {result.error}")
            except Exception as e:
                logger.exception(f"Exception while transforming {input_file.name}: {e}")

        # --- ÉTAPE 3: SANITIZATION & METADATA ---
        logger.info("STEP 3: Cleaning & Intelligence Injection...")
        for md_file in processed_files:
            try:
                self.sanitizer.sanitize_file(md_file)
                self.injector.inject_metadata(md_file)
            except Exception as e:
                logger.exception(f"Failed to sanitize or inject metadata for {md_file.name}: {e}")

        logger.info(f"Normalized {len(processed_files)} notes.")

        # --- ÉTAPE 4: DÉDOUBLONNAGE ---
        logger.info("STEP 4: Asset Optimization (Deduplication)...")
        try:
            dedup_result = self.optimizer.deduplicate_directory(ATTACHMENTS_PATH, VAULT_PATH)
        except Exception as e:
            logger.exception(f"Asset deduplication failed: {e}")
            dedup_result = type('DedupResult', (object,), {'bytes_saved': 0, 'duplicates_removed': 0})()

        # --- ÉTAPE 5: RÉSUMÉ ---
        end_time = datetime.now()
        duration = end_time - start_time

        logger.info("=== MIGRATION COMPLETE ===")
        print(f"""
{'='*50}
MIGRATION SUMMARY
{'='*50}
Duration:           {duration.total_seconds():.2f} seconds
Notes Migrated:     {len(processed_files)}
Space Saved:        {dedup_result.bytes_saved / 1024 / 1024:.2f} MB
Duplicates Removed: {dedup_result.duplicates_removed}
Vault Location:     {VAULT_PATH.absolute()}
{'='*50}
        """)


if __name__ == "__main__":
    orchestrator = MigrationOrchestrator()
    orchestrator.run()
