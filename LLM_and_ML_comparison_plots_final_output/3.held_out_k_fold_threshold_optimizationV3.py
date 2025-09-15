#!/usr/bin/python3.5

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import glob

def process_tsv_and_plot(file_path, output_file_path, plot_output_path, legend_output_path, graph_name,
                         auc_fontsize=22, legend_fontsize=24, title_fontsize=28,
                         label_fontsize=26, tick_fontsize=22, point_size=400):

    data = pd.read_csv(file_path, sep='\t')

    # Required columns
    required_cols = ['threshold', 'recall', 'specificity', 'precision']
    if not all(col in data.columns for col in required_cols):
        raise ValueError("The input file must contain 'threshold', 'recall', 'specificity', and 'precision' columns.")

    data['FalsePositiveRate'] = 1 - data['specificity']
    final_data = data[['threshold', 'recall', 'specificity', 'FalsePositiveRate', 'precision']].copy()
    final_data = final_data.round(3)
    final_data = final_data.sort_values(by='FalsePositiveRate', ascending=True).reset_index(drop=True)

    # Best thresholds
    distances = np.sqrt(final_data['FalsePositiveRate']**2 + (1 - final_data['recall'])**2)
    best_index = distances.idxmin()
    best_threshold = final_data.iloc[best_index]['threshold']
    best_fpr = final_data.iloc[best_index]['FalsePositiveRate']
    best_recall = final_data.iloc[best_index]['recall']

    final_data['F1'] = 2 * (final_data['precision'] * final_data['recall']) / (final_data['precision'] + final_data['recall'])
    best_f1_index = final_data['F1'].idxmax()
    best_f1_threshold = final_data.iloc[best_f1_index]['threshold']
    best_f1_recall = final_data.iloc[best_f1_index]['recall']
    best_f1_precision = final_data.iloc[best_f1_index]['precision']

    print("Best Threshold (ROC):", best_threshold)
    print("Best Threshold (F1):", best_f1_threshold)

    final_data.to_csv(output_file_path, sep='\t', index=False, float_format="%.3f")

    auc = np.trapz(final_data['recall'], final_data['FalsePositiveRate'])
    auc2 = np.trapz(final_data['precision'], final_data['recall'])

    print("ROC AUC:", round(auc,3))
    print("PR AUC:", round(auc2,3))



#terrestrial metrics
# --- CUSTOM POINTS SECTION ---
    custom_roc_points = [
        #first nr is False Positive Rate and 2nd is Recall
        #(0, 0.06, "Rule-based system", 'orange'),
        (0.09, 0.92, "llama3.3:70b-instruct-q8_0-prompt5-4yes", 'purple'),
        (0.12, 0.88, "qwen3:30b-a3b-q8_0-prompt4", 'teal'),
        (0.18, 0.88, "qwen2.5:72b-instruct-q8_0-prompt5-4yes", 'orange'),
        (0.2, 0.88, "qwen2.5:72b-instruct-q8_0-prompt5", 'green'),
        (0.29, 0.88, "mistral-small:22b-instruct-2409-q8_0-prompt5", 'brown')
        
        
    ]

    custom_pr_points = [
        #first nr is Recall
        #(0.06, 0.5, "Rule-based system", 'orange'),
        (0.92, 0.27, "llama3.3:70b-instruct-q8_0-prompt5-4yes", 'purple'),
        (0.88, 0.34, "qwen3:30b-a3b-q8_0-prompt4", 'teal'),
        (0.88, 0.26, "qwen2.5:72b-instruct-q8_0-prompt5-4yes", 'orange'),
        (0.88, 0.24, "qwen2.5:72b-instruct-q8_0-prompt5", 'green'),
        (0.88, 0.18, "mistral-small:22b-instruct-2409-q8_0-prompt5", 'brown')
        
        
    ]
    
    

    # --- Create figure with two subplots ---
    fig, axes = plt.subplots(1, 2, figsize=(28, 10), constrained_layout=False, dpi=500)

    # ROC Plot
    sns.lineplot(x='FalsePositiveRate', y='recall', data=final_data, color='red', estimator=None, ax=axes[0])
    for fpr, rec, label, color in custom_roc_points:
        axes[0].scatter(fpr, rec, color=color, marker='X', s=point_size)
    axes[0].scatter(best_fpr, best_recall, color='green', s=point_size, label="Best ROC threshold")
    axes[0].plot([0,1],[0,1], linestyle='--', color='gray', lw=2)
    axes[0].text(0.6, 0.5, "AUC = " + str(round(auc,3)), fontsize=auc_fontsize, color='red')
    axes[0].set_xlabel('False Positive Rate', fontsize=label_fontsize)
    axes[0].set_ylabel('True Positive Rate', fontsize=label_fontsize)
    axes[0].tick_params(axis='x', labelsize=tick_fontsize)
    axes[0].tick_params(axis='y', labelsize=tick_fontsize)
    axes[0].grid(True)

    # PR Plot
    sns.lineplot(x='recall', y='precision', data=final_data, color='red', estimator=None, ax=axes[1])
    for rec, prec, label, color in custom_pr_points:
        axes[1].scatter(rec, prec, color=color, marker='X', s=point_size)
    axes[1].scatter(best_f1_recall, best_f1_precision, color='mediumblue', s=point_size, label="Best F1 threshold")
    axes[1].text(0.2, 0.15, "AUC = " + str(round(auc2,3)), fontsize=auc_fontsize, color='red')
    axes[1].set_xlabel('Recall', fontsize=label_fontsize)
    axes[1].set_ylabel('Precision', fontsize=label_fontsize)
    axes[1].tick_params(axis='x', labelsize=tick_fontsize)
    axes[1].tick_params(axis='y', labelsize=tick_fontsize)
    axes[1].grid(True)

    # Save main figure without legend
    plt.savefig(plot_output_path, format='png', dpi=500, bbox_inches='tight')
    plt.close(fig)

    # --- Create separate legend figure ---
    custom_handles = []
    custom_labels = []
    other_handles = []
    other_labels = []

    # Column 1: Custom points
    for label, color in [(pt[2], pt[3]) for pt in custom_roc_points + custom_pr_points]:
        if label not in custom_labels:
            custom_handles.append(plt.Line2D([], [], color=color, marker='X', linestyle='None', markersize=20))
            custom_labels.append(label)

    # Column 2: Best thresholds and reference lines
    other_handles.append(plt.Line2D([], [], color='green', marker='o', linestyle='None', markersize=20))
    other_labels.append("Best ROC threshold - LR")

    other_handles.append(plt.Line2D([], [], color='mediumblue', marker='o', linestyle='None', markersize=20))
    other_labels.append("Best PR threshold - LR")

    other_handles.append(plt.Line2D([], [], color='red', lw=2))
    other_labels.append("Logistic regression")

    other_handles.append(plt.Line2D([], [], color='gray', lw=2, linestyle='--'))
    other_labels.append("Random chance")

    # Combine handles and labels
    handles = custom_handles + other_handles
    labels = custom_labels + other_labels

    legend_fig = plt.figure(figsize=(8, max(len(custom_handles), len(other_handles))*0.5), dpi=500)
    legend_ax = legend_fig.add_subplot(111)
    legend_ax.axis('off')

    legend_ax.legend(
        handles, labels,
        loc='center',
        frameon=False,
        fontsize=legend_fontsize,
        ncol=2,
        columnspacing=2
    )

    legend_fig.tight_layout()
    legend_fig.savefig(legend_output_path, dpi=500, bbox_inches='tight')
    plt.close(legend_fig)


# === Usage ===
input_folder = "/_full_path_in_your_server_to_/inputs_for_curves"
outputs_folder = os.path.join(input_folder, "outputs")
plots_folder = os.path.join(input_folder, "plots")

os.makedirs(outputs_folder, exist_ok=True)
os.makedirs(plots_folder, exist_ok=True)

tsv_files = glob.glob(os.path.join(input_folder, "*.tsv"))

for file_path in tsv_files:
    graph_name = 'Combined held-out dataset'
    name_combo = os.path.splitext(os.path.basename(file_path))[0]
    output_file_path = os.path.join(outputs_folder, name_combo + "_output.tsv")
    plot_output_path = os.path.join(plots_folder, "ROC_PR_curve-" + name_combo + ".png")
    legend_output_path = os.path.join(plots_folder, "ROC_PR_legend-" + name_combo + ".png")
    process_tsv_and_plot(file_path, output_file_path, plot_output_path, legend_output_path, graph_name)

print("Processing complete. Plots saved in 'plots/' and legend saved separately.")





"""

#aquatic metrics
    # --- CUSTOM POINTS SECTION ---
    custom_roc_points = [
        (0.06, 0.96, "qwen2.5:72b-instruct-q8_0-prompt4-4yes", 'orange'),
        (0.07, 0.96, "qwen2.5:72b-instruct-q8_0-prompt4", 'green'),
        (0.08, 0.96, "phi4:14b-q8_0-prompt5", 'teal'),
        (0.09, 0.96, "phi4:14b-q8_0-prompt4", 'brown'),
        (0.14, 1, "qwen2.5:72b-instruct-q8_0-prompt5", 'purple')
    ]

    custom_pr_points = [
        (0.96, 0.42, "qwen2.5:72b-instruct-q8_0-prompt4-4yes", 'orange'),
        (0.96, 0.36, "qwen2.5:72b-instruct-q8_0-prompt4", 'green'),
        (0.96, 0.33, "phi4:14b-q8_0-prompt5", 'teal'),
        (0.96, 0.3, "phi4:14b-q8_0-prompt4", 'brown'),
        (1, 0.23, "qwen2.5:72b-instruct-q8_0-prompt5", 'purple')
    ]





#terrestrial metrics
# --- CUSTOM POINTS SECTION ---
    custom_roc_points = [
        #first nr is False Positive Rate and 2nd is Recall
        #(0, 0.06, "Rule-based system", 'orange'),
        (0.09, 0.92, "llama3.3:70b-instruct-q8_0-prompt5-4yes", 'purple'),
        (0.12, 0.88, "qwen3:30b-a3b-q8_0-prompt4", 'teal'),
        (0.18, 0.88, "qwen2.5:72b-instruct-q8_0-prompt5-4yes", 'orange'),
        (0.2, 0.88, "qwen2.5:72b-instruct-q8_0-prompt5", 'green'),
        (0.29, 0.88, "mistral-small:22b-instruct-2409-q8_0-prompt5", 'brown')
        
        
    ]

    custom_pr_points = [
        #first nr is Recall
        #(0.06, 0.5, "Rule-based system", 'orange'),
        (0.92, 0.27, "llama3.3:70b-instruct-q8_0-prompt5-4yes", 'purple'),
        (0.88, 0.34, "qwen3:30b-a3b-q8_0-prompt4", 'teal'),
        (0.88, 0.26, "qwen2.5:72b-instruct-q8_0-prompt5-4yes", 'orange'),
        (0.88, 0.24, "qwen2.5:72b-instruct-q8_0-prompt5", 'green'),
        (0.88, 0.18, "mistral-small:22b-instruct-2409-q8_0-prompt5", 'brown')
        
        
    ]




#combined metrics
# --- CUSTOM POINTS SECTION ---
    custom_roc_points = [
        #first nr is False Positive Rate and 2nd is Recall
        #(0, 0.07, "Rule-based system", 'orange'),
        
        (0.08, 0.93, "qwen2.5:72b-instruct-q8_0-prompt4", 'green'),
        (0.09, 0.93, "qwen3:30b-a3b-q8_0-prompt4", 'orange'),
        (0.1, 0.93, "phi4:14b-q8_0-prompt4", 'teal'),
        (0.16, 0.93, "qwen2.5:72b-instruct-q8_0-prompt5", 'brown'),
        (0.18, 0.95, "mistral-nemo:12b-instruct-2407-q8_0-prompt4", 'purple')
        
        
    ]

    custom_pr_points = [
        #first nr is Recall
        #(0.07, 0.60, "Rule-based system", 'orange'),
        (0.93, 0.36, "qwen2.5:72b-instruct-q8_0-prompt4", 'green'),
        (0.93, 0.35, "qwen3:30b-a3b-q8_0-prompt4", 'orange'),
        (0.93, 0.31, "phi4:14b-q8_0-prompt4", 'teal'),
        (0.93, 0.23, "qwen2.5:72b-instruct-q8_0-prompt5", 'brown'),
        (0.95, 0.21, "mistral-nemo:12b-instruct-2407-q8_0-prompt4", 'purple')
        
        
    ]





"""