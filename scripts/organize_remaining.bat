@echo off
echo Organizing remaining scripts...

echo Moving database scripts...
move create_*.py database\
move simple_db_init.py database\

echo Moving service scripts...
move run_sync_once.py services\
move build_read_models.py services\
move fix_read_model_builder.py services\

echo Moving utility scripts...
move check_*.py services\
move final_check.py services\
move simple_*.py services\

echo Moving report...
move DEAL_ENDPOINT_FIX_REPORT.md ..\docs\

echo Organization completed! 