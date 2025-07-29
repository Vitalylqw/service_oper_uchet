#!/usr/bin/env python3
"""
Diagnostic script for Health Service issues.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from presentation.api.services.real_health_service import RealHealthService


async def debug_health_service():
    """Debug health service issues."""
    
    logger.info("🔍 Starting Health Service diagnostics...")
    
    try:
        # Initialize services
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        health_service = RealHealthService(db_manager)
        
        # Test 1: Database status
        logger.info("📊 Testing database status...")
        db_status = await health_service.get_database_status()
        logger.info(f"Database status: {db_status.get('status')}")
        logger.info(f"Database details: {db_status.get('details')}")
        
        # Test 2: File system check
        logger.info("📁 Testing file system...")
        fs_status = await health_service._check_file_system()
        logger.info(f"File system status: {fs_status.get('status')}")
        logger.info(f"File system details: {fs_status.get('details')}")
        
        # Test 3: Memory check
        logger.info("🧠 Testing memory usage...")
        memory_status = await health_service._check_memory_usage()
        logger.info(f"Memory status: {memory_status.get('status')}")
        logger.info(f"Memory details: {memory_status.get('details')}")
        
        # Test 4: Overall status
        logger.info("🌐 Testing overall service status...")
        overall_status = await health_service.get_service_status()
        logger.info(f"Overall status: {overall_status.get('overall_status')}")
        
        # Detailed analysis
        logger.info("\n📋 DETAILED ANALYSIS:")
        logger.info("=" * 50)
        
        components = overall_status.get('components', {})
        for component_name, component_status in components.items():
            status = component_status.get('status', 'unknown')
            details = component_status.get('details', 'No details')
            logger.info(f"{component_name.upper()}: {status}")
            logger.info(f"  Details: {details}")
            
        # Identify the problem
        logger.info("\n🔍 PROBLEM IDENTIFICATION:")
        logger.info("=" * 50)
        
        unhealthy_components = []
        for component_name, component_status in components.items():
            if component_status.get('status') != 'healthy':
                unhealthy_components.append(component_name)
        
        if unhealthy_components:
            logger.error(f"❌ Unhealthy components: {', '.join(unhealthy_components)}")
            for component in unhealthy_components:
                logger.error(f"  - {component}: {components[component].get('details')}")
        else:
            logger.success("✅ All components are healthy!")
            
        return len(unhealthy_components) == 0
        
    except Exception as e:
        logger.error(f"💥 Health service diagnostic failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main function."""
    success = await debug_health_service()
    
    if success:
        logger.success("🎉 Health service diagnostics completed successfully!")
        return 0
    else:
        logger.error("💥 Health service has issues that need to be fixed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)