# Order of execution

 0. syz-manager.log
 1. extract_logs_into_json.py
 2. separate_time_profile_entries.py
 3. unify_triage_lines.py
 4. process_triage_metrics.py
 4. plot_coverage_across_time.py
----
 0. syz-manager.log
 1. plot_exec_evolution.py