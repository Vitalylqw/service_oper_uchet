"""
File System configuration.

Contains settings for different file retrieval protocols and file monitoring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class FileSystemConfig(BaseSettings):
    """File system configuration settings."""

    # Protocol selection
    protocol: Literal["smb", "ftp", "sftp", "http", "local"] = Field(
        default="local", description="File retrieval protocol"
    )

    # Source configuration
    source_host: str = Field(default="", description="Remote host address")
    source_port: int = Field(default=0, description="Remote host port (0 = default)")
    source_path: str = Field(default="", description="Remote file path")
    source_filename: str = Field(default="data.xlsx", description="Expected filename pattern")

    # Authentication (for SMB/FTP/SFTP)
    username: str = Field(default="", description="Username for authentication")
    password: str = Field(default="", description="Password for authentication")
    domain: str = Field(default="", description="Domain for SMB authentication")

    # SSH/SFTP specific
    ssh_private_key_path: str = Field(default="", description="Path to SSH private key")
    ssh_known_hosts_path: str = Field(default="", description="Path to SSH known_hosts file")
    ssh_key_passphrase: str = Field(default="", description="SSH key passphrase")

    # HTTP specific
    http_auth_type: Literal["none", "basic", "bearer"] = Field(
        default="none", description="HTTP authentication type"
    )
    http_auth_token: str = Field(default="", description="HTTP auth token/bearer token")
    http_headers: dict[str, str] = Field(
        default_factory=dict, description="Additional HTTP headers"
    )
    http_verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    # Local file system
    local_source_directory: str = Field(
        default="data/input", description="Local source directory"
    )

    # Destination configuration
    local_destination_directory: str = Field(
        default="data/downloaded", description="Local destination directory for downloaded files"
    )
    create_destination_directory: bool = Field(
        default=True, description="Create destination directory if it doesn't exist"
    )

    # File monitoring and detection
    enable_file_monitoring: bool = Field(default=True, description="Enable file change monitoring")
    monitoring_interval_seconds: int = Field(default=300, description="File monitoring interval")
    file_change_detection_method: Literal["timestamp", "size", "hash", "both"] = Field(
        default="both", description="Method for detecting file changes"
    )

    # File validation
    validate_file_integrity: bool = Field(default=True, description="Validate downloaded file integrity")
    expected_file_extensions: list[str] = Field(
        default_factory=lambda: [".xlsx", ".xls"], description="Allowed file extensions"
    )
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")
    min_file_size_bytes: int = Field(default=1024, description="Minimum file size in bytes")

    # Backup and versioning
    enable_file_backup: bool = Field(default=True, description="Enable file backup with timestamps")
    backup_directory: str = Field(default="data/backup", description="Backup directory")
    backup_retention_days: int = Field(default=30, description="Backup retention period")
    backup_filename_format: str = Field(
        default="{name}_{timestamp}{ext}", description="Backup filename format"
    )

    # Connection timeouts and retries
    connection_timeout_seconds: int = Field(default=30, description="Connection timeout")
    read_timeout_seconds: int = Field(default=300, description="Read timeout for file transfer")
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=30, description="Delay between retry attempts")

    # Security settings
    allow_insecure_connections: bool = Field(default=False, description="Allow insecure connections")
    verify_host_keys: bool = Field(default=True, description="Verify host keys for SSH/SFTP")

    # Logging and monitoring
    log_file_operations: bool = Field(default=True, description="Log file operations")
    log_detailed_errors: bool = Field(default=True, description="Log detailed error information")
    collect_metrics: bool = Field(default=True, description="Collect file system metrics")

    model_config = ConfigDict(env_prefix="FILESYSTEM_", env_file=".env")

    @property
    def default_port(self) -> int:
        """Get default port for the selected protocol."""
        if self.source_port > 0:
            return self.source_port

        defaults = {
            "smb": 445,
            "ftp": 21,
            "sftp": 22,
            "http": 80,
            "https": 443,
            "local": 0,
        }
        return defaults.get(self.protocol, 0)

    @property
    def full_source_url(self) -> str:
        """Get full source URL based on protocol and configuration."""
        if self.protocol == "local":
            return str(Path(self.local_source_directory) / self.source_filename)

        if self.protocol == "smb":
            # SMB URL format: smb://domain;username:password@host:port/path/file
            auth_part = ""
            if self.username:
                auth_part = f"{self.domain};{self.username}" if self.domain else self.username
                if self.password:
                    auth_part += f":{self.password}"
                auth_part += "@"

            port_part = f":{self.default_port}" if self.default_port != 445 else ""
            return f"smb://{auth_part}{self.source_host}{port_part}/{self.source_path.lstrip('/')}/{self.source_filename}"

        elif self.protocol in ["ftp", "sftp"]:
            # FTP/SFTP URL format: ftp://username:password@host:port/path/file
            auth_part = ""
            if self.username:
                auth_part = self.username
                if self.password:
                    auth_part += f":{self.password}"
                auth_part += "@"

            port_part = f":{self.default_port}" if self.default_port not in [21, 22] else ""
            return f"{self.protocol}://{auth_part}{self.source_host}{port_part}/{self.source_path.lstrip('/')}/{self.source_filename}"

        elif self.protocol == "http":
            # HTTP URL format: http://host:port/path/file
            port_part = f":{self.default_port}" if self.default_port != 80 else ""
            return f"http://{self.source_host}{port_part}/{self.source_path.lstrip('/')}/{self.source_filename}"

        else:
            return f"{self.protocol}://{self.source_host}/{self.source_path}/{self.source_filename}"

    @property
    def destination_file_path(self) -> Path:
        """Get destination file path."""
        return Path(self.local_destination_directory) / self.source_filename

    @property
    def backup_file_path(self) -> Path:
        """Get backup file path with timestamp."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = Path(self.source_filename)
        name = file_path.stem
        ext = file_path.suffix

        backup_filename = self.backup_filename_format.format(
            name=name,
            timestamp=timestamp,
            ext=ext
        )

        return Path(self.backup_directory) / backup_filename

    def get_connection_params(self) -> dict[str, any]:
        """Get connection parameters for the selected protocol."""
        base_params = {
            "host": self.source_host,
            "port": self.default_port,
            "timeout": self.connection_timeout_seconds,
        }

        if self.protocol == "smb":
            return {
                **base_params,
                "username": self.username,
                "password": self.password,
                "domain": self.domain,
                "port": self.default_port or 445,
            }

        elif self.protocol in ["ftp", "sftp"]:
            params = {
                **base_params,
                "username": self.username,
                "password": self.password,
            }

            if self.protocol == "sftp":
                params.update({
                    "private_key_path": self.ssh_private_key_path,
                    "known_hosts_path": self.ssh_known_hosts_path,
                    "key_passphrase": self.ssh_key_passphrase,
                    "verify_host_key": self.verify_host_keys,
                })

            return params

        elif self.protocol == "http":
            return {
                **base_params,
                "auth_type": self.http_auth_type,
                "auth_token": self.http_auth_token,
                "headers": self.http_headers,
                "verify_ssl": self.http_verify_ssl,
            }

        return base_params

    def validate_configuration(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if self.protocol != "local" and not self.source_host:
            errors.append("source_host is required for remote protocols")

        if self.protocol in ["smb", "ftp", "sftp"] and not self.username:
            errors.append(f"username is required for {self.protocol} protocol")

        if self.protocol == "http" and self.http_auth_type == "bearer" and not self.http_auth_token:
            errors.append("http_auth_token is required when using bearer authentication")

        if self.protocol == "sftp" and self.ssh_private_key_path and not Path(self.ssh_private_key_path).exists():
            errors.append(f"SSH private key file not found: {self.ssh_private_key_path}")

        if self.max_file_size_mb <= 0:
            errors.append("max_file_size_mb must be greater than 0")

        if self.min_file_size_bytes < 0:
            errors.append("min_file_size_bytes must be non-negative")

        return errors
