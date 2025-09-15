#!/usr/bin/python3.5
import pandas as pd
from sklearn.model_selection import KFold
from xgboost import XGBClassifier  # Import XGBoost Classifier
from sklearn.linear_model import LogisticRegression # Import logistic regression
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix, f1_score
import sys



#parameters:
# 1.Load your dataset
file_paths = ['/_full_path_in_your_server_to_/k_folds_combined_super_vector.csv'
              ,'/_full_path_in_your_server_to_/k_folds_shrinked_vector.csv'
              ,'/_full_path_in_your_server_to_/k_folds_embeddings.csv']
model_choice = ['logistic_regression','XGBoost'] # 1:logistic regression, 2:XGBoost
# Define the K-fold cross-validation


# Check if the correct number of arguments has been provided
if len(sys.argv) != 3:
    print("Usage: python script_name.py <k> <n_repeats>")
    sys.exit(1)

# Read and convert the command-line arguments
try:
    k = int(sys.argv[1])          # First argument as integer
    n_repeats = int(sys.argv[2])  # Second argument as integer
except ValueError:
    print("Both k and n_repeats must be integers.")
    sys.exit(1)

# Output the values to verify
print("Number of folds (k):", k)
print("Number of repeats (n_repeats):", n_repeats)
#k = 3  # Number of folds
#n_repeats is a multiple of k calculations e.g. for 3-fold validation a n_repeats of 1 means the training and 
# the evaluation is repeated 3 times.
#n_repeats = 10  # Number of times to repeat the K-fold cross-validation (adjust as needed)
#end of parameters


#for each of the file_paths a.k.a. datasets run the k_fold method with the parameters inserted from ARGV

for dataset in file_paths:
    for m_choice in model_choice:

        data = pd.read_csv(dataset)

        # Split features and labels (without dropping 'Study' yet)
        X = data.drop(columns=['cc','Study'])
        y = data['cc']  # Replace 'cc' with your target label column name

        # Define the XGBoost Classifier model according to the choice
        if m_choice=='logistic_regression':
            model = LogisticRegression(max_iter=1000)
        elif m_choice=='XGBoost':
            model = XGBClassifier(objective='binary:logistic', use_label_encoder=False, eval_metric='logloss')  # Replace LogisticRegression with XGBClassifier
        else:
            print("No choice 1 or 2 is selected")
            
            
            


        # Initialize lists to store the metrics for all repetitions
        accuracies = []
        precisions = []
        recalls = []
        specificities = []
        tp_values = []
        tn_values = []
        fp_values = []
        fn_values = []

        # Repeat the process n times
        for repeat in range(1, n_repeats + 1):
            print("Repeat {} of {}".format(repeat, n_repeats))
            
            # Define the K-fold cross-validation for each repeat
            kf = KFold(n_splits=k, shuffle=True, random_state=repeat)  # Random state ensures different splits in each repeat

            # Perform K-fold cross-validation
            for fold, (train_idx, test_idx) in enumerate(kf.split(X), start=1):

                
                # Split the data into training and test sets
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

                # Train the model
                model.fit(X_train, y_train)

                # Make predictions on the test set
                y_pred = model.predict(X_test)

            # Calculate accuracy, precision, recall
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, average='binary')
                recall = recall_score(y_test, y_pred, average='binary')
                #f1 = f1_score(y_test, y_pred)
                
                
                
                #f1 = 2*precision*recall/(precision+recall)
                
                # Calculate confusion matrix to get TP, TN, FP, FN
                tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
                
                #f1 = 2*tp / (2*tp + fp + fn)
                
                # Calculate specificity from confusion matrix
                specificity = float(tn) / (tn + fp) if (tn + fp) > 0 else 0

                # Append the metrics for averaging later
                accuracies.append(accuracy)
                precisions.append(precision)
                recalls.append(recall)
                specificities.append(specificity)
                tp_values.append(tp)
                tn_values.append(tn)
                fp_values.append(fp)
                fn_values.append(fn)
                
                
                """
                # Print metrics for this fold, including TP, TN, FP, FN
                print("  Fold {} Metrics:".format(fold))
                print("    Accuracy: {:.4f}".format(accuracy))
                print("    Precision: {:.4f}".format(precision))
                print("    Recall: {:.4f}".format(recall))
                print("    Specificity: {:.4f}".format(specificity))
                print("    True Positives (TP): {}".format(tp))
                print("    True Negatives (TN): {}".format(tn))
                print("    False Positives (FP): {}".format(fp))
                print("    False Negatives (FN): {}".format(fn))
                print("-" * 40)
                """
                
                
        # Calculate and print average metrics across all folds and repetitions
        avg_accuracy = sum(accuracies) / len(accuracies)
        avg_precision = sum(precisions) / len(precisions)
        avg_recall = sum(recalls) / len(recalls)
        avg_specificity = sum(specificities) / len(specificities)
        avg_tp = sum(tp_values) / len(tp_values)
        avg_tn = sum(tn_values) / len(tn_values)
        avg_fp = sum(fp_values) / len(fp_values)
        avg_fn = sum(fn_values) / len(fn_values)
        
        avg_f1 = f1 = 2*avg_tp / (2*avg_tp + avg_fp + avg_fn)

        #isolate dataset name
        dataset_name = dataset.split('/')[-1].replace('.csv', '')
        #print which dataset is used
        """
        print(" Dataset: {}".format(dataset_name))
        print("Fold nr: {}".format(k))
        print("Repeats: {}".format(n_repeats))
        print("Average metrics across all folds and repetitions:")
        print("  Average Accuracy: {:.4f}".format(avg_accuracy))
        print("  Average Precision: {:.4f}".format(avg_precision))
        print("  Average Recall: {:.4f}".format(avg_recall))
        print("  Average Specificity: {:.4f}".format(avg_specificity))
        print("  Average True Positives (TP): {:.4f}".format(avg_tp))
        print("  Average True Negatives (TN): {:.4f}".format(avg_tn))
        print("  Average False Positives (FP): {:.4f}".format(avg_fp))
        print("  Average False Negatives (FN): {:.4f}".format(avg_fn))
        """
        
        ## Now printing one-liner output to go to a file
        print("{:s}\t{:s}\t{}\t{}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}".format(
            str(m_choice), 
            str(dataset_name), 
            k,         
            n_repeats,  
            avg_accuracy, 
            avg_precision, 
            avg_recall, 
            avg_specificity, 
            avg_f1
        ))
        
        # Open the output file in write mode
        with open('/_full_path_in_your_server_to_/metrics_table.tsv', 'a') as f:
            f.write("{:s}\t{:s}\t{}\t{}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\n".format(
            str(m_choice), 
            str(dataset_name), 
            k,         
            n_repeats,  
            avg_accuracy, 
            avg_precision, 
            avg_recall, 
            avg_specificity, 
            avg_f1
        ))