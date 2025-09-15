Script execution order : 

1. held_out_k_fold_threshold_optimization.py (creates models parameters)
2. evaluate_models.py (loads models and averages performance)
3. held_out_k_fold_threshold_optimizationV3.py (plots ROC and PR curves)



Script 1 – held_out_k_fold_threshold_optimization.py

-Trains 5 logistic regression models using k-fold cross-validation with 1 repetition.

-Each fold produces a separate model with its own parameters, which are saved for later evaluation.

-This script essentially creates the trained model parameters, but does not evaluate them yet.



Script 2 – evaluate_models.py

-Loads the 5 pre-trained models created by the first script.

-Evaluates each model on a held-out validation dataset across a range of probability thresholds.

-Computes accuracy, precision, recall, specificity, F1, and confusion matrix values for each threshold.

-Saves metrics per individual model and also computes averaged metrics across all models for each threshold.



Script 3 – held_out_k_fold_threshold_optimizationV3.py

-Uses the averaged metrics from evaluate_models.py.

-Plots ROC curves and Precision-Recall curves across thresholds.

-Optionally overlays individual model points (from LLM or per-fold metrics) for comparison with the ML threshold performance.