import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import classification_report, roc_auc_score, silhouette_score, confusion_matrix
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
import seaborn as sns

def run_sklearn_analysis():
    print("Loading data...")
    import os
    base_path = r"c:\Users\lenovo\Documents\CDAC project\Version_Control_For_Databases"
    input_path = os.path.join(base_path, "data", "silver", "user_features.csv")
    
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Error: {input_path} not found. Please run feature_engineering_spark.py first.")
        return

    print(f"Data loaded: {df.shape}")
    
    # Handle missing values (if any)
    df = df.fillna(0)
    
    # ==========================================
    # 1. Customer Segmentation (K-Means)
    # ==========================================
    print("\n--- Customer Segmentation (K-Means) ---")
    
    # Features for segmentation
    seg_features = ["frequency", "monetary", "tenure_days", "days_since_last_active"]
    X_seg = df[seg_features]
    
    # Scale features
    scaler = StandardScaler()
    X_seg_scaled = scaler.fit_transform(X_seg)
    
    # K-Means
    k = 4
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(X_seg_scaled)
    
    # Evaluate
    sil_score = silhouette_score(X_seg_scaled, df['cluster'], sample_size=5000) # Sample for speed if large
    print(f"Silhouette Score: {sil_score:.4f}")
    
    # Cluster Profiles
    print("\nCluster Profiles (Means):")
    print(df.groupby('cluster')[seg_features + ['is_churned']].mean())
    
    # ==========================================
    # 2. Churn Prediction (Random Forest)
    # ==========================================
    print("\n--- Churn Prediction (Random Forest) ---")
    
    # Features for prediction (exclude target and leakage)
    pred_features = ["frequency", "monetary", "tenure_days"]
    target = "is_churned"
    
    X = df[pred_features]
    y = df[target]
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")
    
    # Models and Parameters
    models_params = {
        'LogisticRegression': {
            'model': LogisticRegression(random_state=42, max_iter=1000),
            'params': {
                'classifier__C': [0.01, 0.1, 1, 10],
                'classifier__penalty': ['l2']
            }
        },
        'RandomForestClassifier': {
            'model': RandomForestClassifier(random_state=42),
            'params': {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__max_depth': [None, 10, 20],
                'classifier__min_samples_split': [2, 5, 10]
            }
        },
        'GradientBoostingClassifier': {
            'model': GradientBoostingClassifier(random_state=42),
            'params': {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__learning_rate': [0.01, 0.1, 0.2],
                'classifier__max_depth': [3, 5, 10]
            }
        }
    }

    best_overall_model = None
    best_overall_score = -1
    best_overall_name = ""

    for name, mp in models_params.items():
        print(f"\nTraining {name}...")
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', mp['model'])
        ])
        
        clf = RandomizedSearchCV(pipeline, mp['params'], n_iter=10, cv=3, scoring='roc_auc', random_state=42, n_jobs=-1)
        clf.fit(X_train, y_train)
        
        print(f"Best params: {clf.best_params_}")
        print(f"Best ROC-AUC: {clf.best_score_:.4f}")
        
        if clf.best_score_ > best_overall_score:
            best_overall_score = clf.best_score_
            best_overall_model = clf.best_estimator_
            best_overall_name = name

    print(f"\nBest Overall Model: {best_overall_name}")
    
    # Evaluate Best Model
    y_pred = best_overall_model.predict(X_test)
    
    # Save Results to Gold
    print("\n--- Saving Results to Gold ---")
    output_dir = os.path.join(base_path, "data", "gold")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "customer_segmentation.csv")
    
    # We want to save the original DF with the new 'cluster' col and 'churn_prediction'
    # We already added 'cluster' earlier.
    # Let's add predictions for the whole dataset (or just test? normally the whole current snapshot)
    
    # Predict for all
    all_X = df[pred_features]
    all_X_scaled = best_overall_model.named_steps['scaler'].transform(all_X) # Pipeline handles this if we use predict directly?
    # Actually best_overall_model IS the pipeline or the RandomizedSearchCV which wraps the pipeline.
    # If it is the RandomizedSearchCV, best_estimator_ is the pipeline.
    
    df['churn_prediction'] = best_overall_model.predict(all_X)
    df['churn_probability'] = best_overall_model.predict_proba(all_X)[:, 1]
    
    df.to_csv(output_path, index=False)
    print(f"Saved segmented customer data with predictions to {output_path}")

    y_prob = best_overall_model.predict_proba(X_test)[:, 1]
    
    print("\nClassification Report (Best Model):")
    print(classification_report(y_test, y_pred))
    
    auc = roc_auc_score(y_test, y_prob)
    print(f"Test ROC-AUC Score: {auc:.4f}")
    
    # Feature Importance (if tree-based)
    if best_overall_name in ['RandomForestClassifier', 'GradientBoostingClassifier']:
        feature_importances = best_overall_model.named_steps['classifier'].feature_importances_
        importances = pd.Series(feature_importances, index=pred_features).sort_values(ascending=False)
        print("\nFeature Importances:")
        print(importances)

if __name__ == "__main__":
    run_sklearn_analysis()
