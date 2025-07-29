#!/usr/bin/env python3
"""
Full Integration Workflow Demo.

Demonstrates how the enhanced Excel validation integrates into the complete
system workflow from file upload to database synchronization.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from application.data_validator import DataValidator
from application.data_validator.config import DEFAULT_EXCEL_CONFIG, STRICT_EXCEL_CONFIG, ExcelValidationConfig, SheetConfig, BusinessRulesConfig, PeriodValidationConfig
from application.excel_parser import ExcelParserService
from application.change_detector import ChangeDetectorService
from application.sync_orchestrator import SyncOrchestratorService
from application.sync_orchestrator.models import SyncConfiguration
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.database.event_store import EventStoreImplementation
from infrastructure.database.repositories import (
    DealRepositoryImplementation,
    SyncSessionRepositoryImplementation,
)
from infrastructure.workers.read_model_builder import ReadModelBuilder
from domain.models import SyncSession


def create_adapted_config():
    """Create configuration adapted to real file format."""
    
    # Custom business rules for this file format
    business_rules = BusinessRulesConfig(
        require_client_data=True,
        require_invoice_data=False,  # This format doesn't have invoice data
        require_financial_data=True,
        require_product_data=True,
        validate_financial_consistency=True,
        min_deals_per_sheet=1
    )
    
    # Period validation
    period_validation = PeriodValidationConfig(
        require_period_in_sheet_name=True,
        strict_period_validation=False,
        allow_future_periods=True  # Allow future periods for planning
    )
    
    # Configuration for monthly data sheets
    monthly_sheet_config = SheetConfig(
        name=r"^(Январь|Февраль|Март|Апрель|Май|Июнь|Июль|Август|Сентябрь|Октябрь|Ноябрь|Декабрь)\s+\d{4}$",
        is_required=False,
        is_processed=True,
        expected_headers=[
            "Клиент", "Номенклатурах", "Кол/Отгр?", "Цена вх/накл", "цена исх/Оплач?"
        ],
        required_headers=["Клиент", "Номенклатурах"],
        optional_headers=[
            "Кол/Отгр?", "Цена вх/накл", "цена исх/Оплач?"
        ],
        header_row_patterns=["Клиент", "Номенклатурах"],
        min_rows=1,
        min_columns=3,
        allow_empty=False,
        allow_extra_headers=True,
        strict_header_match=False,
        business_rules=business_rules,
        period_validation=period_validation
    )
    
    # Configuration for settings sheet
    settings_sheet_config = SheetConfig(
        name="^Настройки$",
        is_required=False,
        is_processed=False,  # Don't process settings sheet
        expected_headers=[],
        required_headers=[],
        allow_empty=True,
        allow_extra_headers=True,
        business_rules=BusinessRulesConfig(
            require_client_data=False,
            require_invoice_data=False,
            require_financial_data=False,
            require_product_data=False,
            validate_financial_consistency=False
        ),
        period_validation=PeriodValidationConfig(
            require_period_in_sheet_name=False
        )
    )
    
    # Create adapted configuration
    adapted_config = ExcelValidationConfig(
        sheets={
            "monthly": monthly_sheet_config,
            "settings": settings_sheet_config
        },
        business_rules=business_rules,
        period_validation=period_validation,
        strict_mode=False,
        allow_unknown_sheets=True,
        skip_empty_sheets=True,
        max_errors_per_sheet=10,
        max_warnings_per_sheet=20
    )
    
    return adapted_config


class FullIntegrationWorkflow:
    """Demonstrates complete integration workflow with enhanced validation."""
    
    def __init__(self):
        """Initialize workflow components."""
        self.db_config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.db_config)
        
        # Initialize services with adapted configuration
        self.adapted_config = create_adapted_config()
        self.data_validator = DataValidator(self.adapted_config)
        self.excel_parser = ExcelParserService()
        
    async def demonstrate_full_workflow(self, file_path: str):
        """Demonstrate complete workflow with enhanced validation."""
        print("🚀 FULL INTEGRATION WORKFLOW DEMONSTRATION")
        print("=" * 70)
        print(f"📁 Processing file: {file_path}")
        print()
        
        # Step 1: Enhanced Excel Validation
        print("🔍 STEP 1: Enhanced Excel Validation")
        print("-" * 40)
        
        validation_result = self.data_validator.validate_excel_file_detailed(file_path)
        
        print(f"✅ Validation Status: {validation_result.status}")
        print(f"📊 File Summary: {validation_result.validation_summary}")
        print(f"📋 Total Sheets: {validation_result.total_sheets}")
        print(f"✅ Valid Sheets: {validation_result.valid_sheets}")
        print(f"❌ Invalid Sheets: {validation_result.invalid_sheets}")
        print(f"⏭️ Skipped Sheets: {validation_result.skipped_sheets}")
        
        # Show detailed validation results
        print("\n📋 Detailed Validation Results:")
        for i, sheet in enumerate(validation_result.sheets):
            print(f"\n   Sheet {i+1}: '{sheet.name}'")
            print(f"      Status: {sheet.status}")
            print(f"      Is Valid: {sheet.is_valid}")
            print(f"      Is Processed: {sheet.is_processed}")
            print(f"      Has Data: {sheet.has_data}")
            print(f"      Total Rows: {sheet.total_rows}")
            print(f"      Total Columns: {sheet.total_columns}")
            
            # Period validation results
            if sheet.period_validation:
                print(f"      Period: {sheet.period_validation.extracted_month} {sheet.period_validation.extracted_year}")
                print(f"      Period Valid: {sheet.period_is_valid}")
            
            # Business rules validation
            if sheet.business_rules_validation:
                print(f"      Business Rules:")
                print(f"        - Client Data: {sheet.business_rules_validation.has_client_data}")
                print(f"        - Financial Data: {sheet.business_rules_validation.has_financial_data}")
                print(f"        - Product Data: {sheet.business_rules_validation.has_product_data}")
                print(f"        - Rules Violations: {len(sheet.business_rules_validation.rules_violations)}")
        
        # Decision point: Continue or stop based on validation
        if not validation_result.is_valid:
            print("\n⚠️ WARNING: File validation failed!")
            print("❌ Cannot proceed with synchronization.")
            print("📋 Issues to fix:")
            for error in validation_result.validation_errors[:5]:
                print(f"   - {error}")
            return False
        
        print("\n✅ Validation passed! Proceeding with synchronization...")
        
        # Step 2: Database Integration
        print("\n💾 STEP 2: Database Integration")
        print("-" * 40)
        
        async with self.db_manager.get_async_session() as session:
            # Initialize database services
            deal_repo = DealRepositoryImplementation(session)
            sync_session_repo = SyncSessionRepositoryImplementation(session)
            event_store = EventStoreImplementation(session)
            change_detector = ChangeDetectorService(deal_repo)
            read_model_builder = ReadModelBuilder(session, event_store)
            
            # Create orchestrator
            orchestrator = SyncOrchestratorService(
                excel_parser=self.excel_parser,
                change_detector=change_detector,
                event_store=event_store,
                sync_session_repository=sync_session_repo,
                read_model_builder=read_model_builder,
            )
            
            # Step 3: Excel Parsing with Validation Context
            print("\n📋 STEP 3: Excel Parsing (with validation context)")
            print("-" * 40)
            
            # Create sync session
            sync_session = SyncSession(sync_type="incremental")
            sync_session.source_file_path = file_path
            sync_session.started_at = datetime.now()
            
            # Parse file with validation context
            parse_result = await self.excel_parser.parse_file(file_path, sync_session)
            
            print(f"✅ Parsing completed:")
            print(f"   - Total Deals: {parse_result.total_deals}")
            print(f"   - Total Items: {parse_result.total_items}")
            print(f"   - File Hash: {parse_result.file_hash[:16]}...")
            print(f"   - File Size: {parse_result.file_size / 1024:.1f} KB")
            
            if parse_result.has_errors:
                print(f"   ⚠️ Parsing Errors: {len(parse_result.stats.errors)}")
                for error in parse_result.stats.errors[:3]:
                    print(f"      - {error}")
            
            # Step 4: Change Detection
            print("\n🔍 STEP 4: Change Detection")
            print("-" * 40)
            
            change_result = await change_detector.detect_changes(
                parse_result.deals, 
                incremental_period_months=12
            )
            
            print(f"✅ Change detection completed:")
            print(f"   - Insertions: {change_result.insertion_count}")
            print(f"   - Updates: {change_result.update_count}")
            print(f"   - Deletions: {change_result.deletion_count}")
            print(f"   - Total Changes: {change_result.total_changes}")
            
            # Step 5: Full Orchestration
            print("\n🎯 STEP 5: Full Orchestration")
            print("-" * 40)
            
            # Create sync configuration
            sync_config = SyncConfiguration(
                sync_type="incremental",
                incremental_period_months=12,
                max_retry_attempts=1,
                continue_on_errors=True,
                rollback_on_failure=False,
                create_events=True,
                update_read_models=True,
            )
            
            # Execute full sync
            sync_result = await orchestrator.execute_sync(file_path, sync_config)
            
            print(f"✅ Full synchronization completed:")
            print(f"   - Success: {sync_result.summary.success}")
            print(f"   - Duration: {sync_result.summary.duration_seconds:.2f}s")
            print(f"   - Total Deals Processed: {sync_result.summary.total_deals_processed}")
            print(f"   - Total Items Processed: {sync_result.summary.total_items_processed}")
            print(f"   - Events Created: {len(sync_result.events_created) if sync_result.events_created else 0}")
            
            # Step 6: Validation Integration Benefits
            print("\n🎉 STEP 6: Validation Integration Benefits")
            print("-" * 40)
            
            print("✅ Enhanced validation provides:")
            print("   📊 Period validation from sheet names")
            print("   🏢 Business rules validation")
            print("   📁 File path and accessibility checks")
            print("   💰 Financial data consistency validation")
            print("   📈 Monitoring integration capabilities")
            print("   🔧 Configurable validation rules")
            
            # Show how validation data is used
            print("\n📋 Validation data integration:")
            print(f"   - File monitoring: {validation_result.monitoring_info.is_monitored if validation_result.monitoring_info else 'Not configured'}")
            
            # Get valid period sheets
            valid_period_sheets = [s.name for s in validation_result.sheets if s.period_is_valid and s.is_processed]
            print(f"   - Valid period sheets: {valid_period_sheets}")
            
            # Get business rules compliance
            compliant_sheets = [s.name for s in validation_result.sheets if s.is_valid and s.is_processed]
            print(f"   - Business rules compliant sheets: {compliant_sheets}")
            
            await session.commit()
            print("\n✅ Database transaction committed successfully!")
            
        return True
    
    async def demonstrate_validation_configurations(self, file_path: str):
        """Demonstrate different validation configurations."""
        print("\n🔧 VALIDATION CONFIGURATIONS DEMONSTRATION")
        print("=" * 70)
        
        # Default configuration
        print("\n📋 Default Configuration:")
        default_validator = DataValidator(DEFAULT_EXCEL_CONFIG)
        default_result = default_validator.validate_excel_file_detailed(file_path)
        print(f"   Status: {default_result.status}")
        print(f"   Success Rate: {default_result.success_rate:.1f}%")
        
        # Strict configuration
        print("\n📋 Strict Configuration:")
        strict_validator = DataValidator(STRICT_EXCEL_CONFIG)
        strict_result = strict_validator.validate_excel_file_detailed(file_path)
        print(f"   Status: {strict_result.status}")
        print(f"   Success Rate: {strict_result.success_rate:.1f}%")
        
        # Adapted configuration (our custom one)
        print("\n📋 Adapted Configuration (for real file format):")
        adapted_validator = DataValidator(self.adapted_config)
        adapted_result = adapted_validator.validate_excel_file_detailed(file_path)
        print(f"   Status: {adapted_result.status}")
        print(f"   Success Rate: {adapted_result.success_rate:.1f}%")
        
        print("\n📊 Configuration Comparison:")
        print(f"   Default: {default_result.status} ({default_result.success_rate:.1f}%)")
        print(f"   Strict: {strict_result.status} ({strict_result.success_rate:.1f}%)")
        print(f"   Adapted: {adapted_result.status} ({adapted_result.success_rate:.1f}%)")
        print("\n💡 The adapted configuration is specifically designed for this file format!")
    
    async def demonstrate_monitoring_integration(self, file_path: str):
        """Demonstrate monitoring integration capabilities."""
        print("\n📊 MONITORING INTEGRATION DEMONSTRATION")
        print("=" * 70)
        
        validator = DataValidator(self.adapted_config)
        excel_file = validator.validate_excel_file_detailed(file_path)
        
        # Set up monitoring
        excel_file.set_monitoring_info(is_monitored=True, monitoring_status="active")
        
        print("✅ Monitoring configured:")
        print(f"   - Is Monitored: {excel_file.monitoring_info.is_monitored}")
        print(f"   - Status: {excel_file.monitoring_info.monitoring_status}")
        print(f"   - Started: {excel_file.monitoring_info.monitoring_started}")
        
        # Simulate file change detection
        excel_file.update_monitoring_status("changed", change_detected=True)
        
        print("\n📈 Monitoring events:")
        print(f"   - Change Detected: {excel_file.change_detected}")
        print(f"   - Change Count: {excel_file.monitoring_info.change_count}")
        print(f"   - Last Modified: {excel_file.last_modified}")
        
        print("\n🔔 Monitoring integration benefits:")
        print("   - Automatic file change detection")
        print("   - Real-time validation status updates")
        print("   - Integration with notification systems")
        print("   - Historical change tracking")
        
        # Show period-based monitoring
        print("\n📅 Period-based monitoring:")
        for sheet in excel_file.sheets:
            if sheet.period_validation and sheet.period_is_valid:
                print(f"   - {sheet.name}: {sheet.period_validation.extracted_month} {sheet.period_validation.extracted_year}")


async def main():
    """Main demonstration function."""
    print("🚀 Enhanced Excel Validation - Full Integration Demo")
    print("=" * 70)
    
    # File path
    file_path = "data/real_data_for_testing/Data_source_excel.xlsx"
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        workflow = FullIntegrationWorkflow()
        
        # Demonstrate full workflow
        success = await workflow.demonstrate_full_workflow(file_path)
        
        if success:
            # Demonstrate different configurations
            await workflow.demonstrate_validation_configurations(file_path)
            
            # Demonstrate monitoring integration
            await workflow.demonstrate_monitoring_integration(file_path)
            
            print("\n🎉 All demonstrations completed successfully!")
            print("\n📋 SUMMARY:")
            print("✅ Enhanced validation is fully integrated into the system workflow")
            print("✅ Validation provides early error detection and prevention")
            print("✅ Configurable validation rules adapt to different file formats")
            print("✅ Monitoring integration enables proactive file management")
            print("✅ Business rules validation ensures data quality")
            print("✅ Period validation supports temporal data organization")
            print("✅ Adapted configurations handle real-world file formats")
            
        else:
            print("\n❌ Workflow demonstration failed due to validation issues")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)