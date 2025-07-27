"""
Real Health Service for FastAPI endpoints.

Provides real system health monitoring including database connectivity,
system metrics, and service status checks.
"""

from __future__ import annotations

import time
from datetime import datetime

import psutil
from loguru import logger

from infrastructure.database.connection import DatabaseManager


class RealHealthService:
    """
    Real health service for system monitoring.

    Provides actual health checks including database connectivity,
    system metrics, and comprehensive service status monitoring.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize real health service with database manager."""
        self.db_manager = db_manager
        self._startup_time = datetime.utcnow()
        logger.debug("RealHealthService initialized")

    async def get_database_status(self) -> dict:
        """
        Check real database connection status.

        Returns:
            dict: Database status with connection details
        """
        try:
            logger.debug("Checking database connectivity...")
            start_time = time.time()

            # Test database connection
            connection_ok = await self.db_manager.test_connection()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if connection_ok:
                status = {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "database_type": self.db_manager.config.db_type,
                    "last_check": datetime.utcnow().isoformat(),
                    "details": "Database connection successful"
                }
                logger.debug(f"Database health check passed in {response_time:.2f}ms")
            else:
                status = {
                    "status": "unhealthy",
                    "response_time_ms": round(response_time, 2),
                    "database_type": self.db_manager.config.db_type,
                    "last_check": datetime.utcnow().isoformat(),
                    "details": "Database connection failed"
                }
                logger.warning(f"Database health check failed after {response_time:.2f}ms")

            return status

        except Exception as e:
            logger.error(f"Database health check error: {e}")
            return {
                "status": "error",
                "response_time_ms": None,
                "database_type": self.db_manager.config.db_type,
                "last_check": datetime.utcnow().isoformat(),
                "details": f"Health check error: {str(e)}"
            }

    async def get_system_metrics(self) -> dict:
        """
        Get real system metrics.

        Returns:
            dict: System performance metrics
        """
        try:
            logger.debug("Collecting system metrics...")

            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_total_gb = memory.total / (1024**3)
            memory_available_gb = memory.available / (1024**3)

            # Disk metrics (for the root directory)
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_total_gb = disk.total / (1024**3)
            disk_free_gb = disk.free / (1024**3)

            # Process metrics
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024**2)
            process_cpu_percent = process.cpu_percent()

            # Application uptime
            uptime_seconds = (datetime.utcnow() - self._startup_time).total_seconds()

            metrics = {
                # System-wide metrics
                "cpu_percent": round(cpu_percent, 1),
                "cpu_count": cpu_count,
                "memory_percent": round(memory_percent, 1),
                "memory_total_gb": round(memory_total_gb, 2),
                "memory_available_gb": round(memory_available_gb, 2),
                "disk_percent": round(disk_percent, 1),
                "disk_total_gb": round(disk_total_gb, 2),
                "disk_free_gb": round(disk_free_gb, 2),

                # Process-specific metrics
                "process_memory_mb": round(process_memory_mb, 1),
                "process_cpu_percent": round(process_cpu_percent, 1),

                # Application metrics
                "uptime_seconds": round(uptime_seconds, 1),
                "uptime_formatted": self._format_uptime(uptime_seconds),

                # Database connection metrics (simplified for now)
                "database_connections": 1 if await self._check_db_connection_quick() else 0,
                "active_sessions": 0,  # TODO: Implement session tracking

                # Request metrics (would be tracked by middleware in production)
                "requests_total": 0,  # TODO: Implement request counting
                "requests_duration_seconds": 0.0,  # TODO: Implement timing

                # Collection timestamp
                "collected_at": datetime.utcnow().isoformat(),
            }

            logger.debug("System metrics collected successfully")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {
                "error": f"Failed to collect metrics: {str(e)}",
                "collected_at": datetime.utcnow().isoformat(),
            }

    async def get_service_status(self) -> dict:
        """
        Get comprehensive service status.

        Returns:
            dict: Status of all system components
        """
        try:
            logger.debug("Checking service status...")

            # Check database
            db_status = await self.get_database_status()

            # Check file system access
            fs_status = await self._check_file_system()

            # Check memory usage
            memory_status = await self._check_memory_usage()

            # Overall health determination
            all_healthy = (
                db_status.get("status") == "healthy" and
                fs_status.get("status") == "healthy" and
                memory_status.get("status") == "healthy"
            )

            service_status = {
                "overall_status": "healthy" if all_healthy else "unhealthy",
                "components": {
                    "api": {
                        "status": "healthy",
                        "details": "API server running normally"
                    },
                    "database": db_status,
                    "file_system": fs_status,
                    "memory": memory_status,
                },
                "last_check": datetime.utcnow().isoformat(),
                "uptime": self._format_uptime((datetime.utcnow() - self._startup_time).total_seconds()),
            }

            logger.debug(f"Service status check completed: {service_status['overall_status']}")
            return service_status

        except Exception as e:
            logger.error(f"Service status check failed: {e}")
            return {
                "overall_status": "error",
                "components": {
                    "api": {"status": "error", "details": f"Status check failed: {str(e)}"}
                },
                "last_check": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    async def _check_db_connection_quick(self) -> bool:
        """Quick database connection check."""
        try:
            return await self.db_manager.test_connection()
        except Exception:
            return False

    async def _check_file_system(self) -> dict:
        """Check file system access and permissions."""
        try:
            import tempfile
            from pathlib import Path

            # Check if we can write to temp directory
            with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                temp_file.write(b"health_check")
                temp_file.flush()

            # Check data directory exists and is writable
            data_dir = Path("data")
            if not data_dir.exists():
                data_dir.mkdir(parents=True, exist_ok=True)

            # Test write access to data directory
            test_file = data_dir / "health_check.tmp"
            test_file.write_text("test")
            test_file.unlink()

            return {
                "status": "healthy",
                "details": "File system access normal",
                "data_directory": str(data_dir.absolute()),
                "writable": True,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "details": f"File system check failed: {str(e)}",
                "writable": False,
            }

    async def _check_memory_usage(self) -> dict:
        """Check memory usage and alert if too high."""
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()

            # Thresholds for warnings
            MEMORY_WARNING_THRESHOLD = 80  # 80%
            MEMORY_CRITICAL_THRESHOLD = 90  # 90%

            if memory.percent >= MEMORY_CRITICAL_THRESHOLD:
                status = "critical"
                details = f"Memory usage critical: {memory.percent:.1f}%"
            elif memory.percent >= MEMORY_WARNING_THRESHOLD:
                status = "warning"
                details = f"Memory usage high: {memory.percent:.1f}%"
            else:
                status = "healthy"
                details = f"Memory usage normal: {memory.percent:.1f}%"

            return {
                "status": status,
                "details": details,
                "system_memory_percent": round(memory.percent, 1),
                "process_memory_mb": round(process.memory_info().rss / (1024**2), 1),
                "available_gb": round(memory.available / (1024**3), 2),
            }

        except Exception as e:
            return {
                "status": "error",
                "details": f"Memory check failed: {str(e)}",
            }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
