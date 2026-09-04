# DataSciBench

Secondary benchmark for DataScientistOS.

Official repository:

https://github.com/THUDM/DataSciBench

Target week-one subset:

- 20 tasks

Important:

- task data is separate from evaluator-side ground truth
- ground truth must not be exposed to the runtime agent
- task IDs are selected in `selected_tasks.json`, copied verbatim from directory names
  under `external/datascibench/data/`; each selected task's prompt is self-contained
  and requires no separate data download
