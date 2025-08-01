#!/usr/bin/env python3
"""
Simple script to drop currency columns from SQLite database.

This script directly modifies the database schema to remove all *_currency columns
since the system now only uses RUB currency.
"""

import sqlite3
import os
from pathlib import Path
from loguru import logger


def drop_currency_columns():
    """Drop all currency columns from read models tables."""
    
    # Get database path
    db_path = Path(__file__).parent.parent.parent / "local.db"
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"Connected to database: {db_path}")
        
        # List of currency columns to drop
        currency_columns = [
            # read_deals table
            ('read_deals', 'total_revenue_currency'),
            ('read_deals', 'total_margin_currency'),
            ('read_deals', 'total_cost_currency'),
            ('read_deals', 'kickback_amount_currency'),
            
            # read_positions table
            ('read_positions', 'purchase_price_currency'),
            ('read_positions', 'sale_price_currency'),
            ('read_positions', 'revenue_currency'),
            ('read_positions', 'margin_currency'),
            ('read_positions', 'cost_currency'),
        ]
        
        # Drop each column
        for table, column in currency_columns:
            try:
                # Check if column exists
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in cursor.fetchall()]
                
                if column in columns:
                    # SQLite doesn't support DROP COLUMN directly, so we need to recreate table
                    logger.info(f"Dropping column {table}.{column}")
                    
                    # Get current table schema
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
                    create_sql = cursor.fetchone()[0]
                    
                    # Remove the column from CREATE TABLE statement
                    # This is a simplified approach - in production you'd want more robust parsing
                    lines = create_sql.split('\n')
                    new_lines = []
                    skip_next = False
                    
                    for line in lines:
                        if f'"{column}"' in line or f"'{column}'" in line:
                            skip_next = True
                            continue
                        if skip_next and line.strip().endswith(','):
                            skip_next = False
                            continue
                        if skip_next:
                            skip_next = False
                            continue
                        new_lines.append(line)
                    
                    new_create_sql = '\n'.join(new_lines)
                    
                    # Create new table without the column
                    temp_table = f"{table}_temp"
                    new_create_sql = new_create_sql.replace(f'CREATE TABLE "{table}"', f'CREATE TABLE "{temp_table}"')
                    
                    cursor.execute(new_create_sql)
                    
                    # Copy data (excluding the dropped column)
                    cursor.execute(f"PRAGMA table_info({table})")
                    all_columns = [col[1] for col in cursor.fetchall() if col[1] != column]
                    columns_str = ', '.join(f'"{col}"' for col in all_columns)
                    
                    cursor.execute(f"INSERT INTO {temp_table} ({columns_str}) SELECT {columns_str} FROM {table}")
                    
                    # Drop old table and rename new one
                    cursor.execute(f"DROP TABLE {table}")
                    cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table}")
                    
                    logger.info(f"✅ Successfully dropped column {table}.{column}")
                else:
                    logger.info(f"Column {table}.{column} does not exist, skipping")
                    
            except Exception as e:
                logger.error(f"Failed to drop column {table}.{column}: {e}")
                continue
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info("✅ Currency columns dropped successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to drop currency columns: {e}")
        return False


if __name__ == "__main__":
    logger.info("🚀 Starting currency columns removal...")
    success = drop_currency_columns()
    
    if success:
        logger.info("🎉 Currency columns removal completed successfully!")
    else:
        logger.error("💥 Currency columns removal failed!")
        exit(1) 