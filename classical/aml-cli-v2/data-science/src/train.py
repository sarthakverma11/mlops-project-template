
import argparse

from pathlib import Path
import os
import pickle

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

import mlflow
import mlflow.sklearn

TARGET_COL = "cost"

NUMERIC_COLS = [
    "distance",
    "dropoff_latitude",
    "dropoff_longitude",
    "passengers",
    "pickup_latitude",
    "pickup_longitude",
    "pickup_weekday",
    "pickup_month",
    "pickup_monthday",
    "pickup_hour",
    "pickup_minute",
    "pickup_second",
    "dropoff_weekday",
    "dropoff_month",
    "dropoff_monthday",
    "dropoff_hour",
    "dropoff_minute",
    "dropoff_second",
]

CAT_NOM_COLS = [
    "store_forward",
    "vendor",
]

CAT_ORD_COLS = [
]


def parse_args():

    parser = argparse.ArgumentParser("train")
    parser.add_argument("--prepared_data", type=str, help="Path to training data")
    parser.add_argument("--model_output", type=str, help="Path of output model")

    # classifier specific arguments
    parser.add_argument('--regressor__n_estimators', type=int, default=500,
                        help='Number of trees')
    parser.add_argument('--regressor__bootstrap', type=int, default=1,
                        help='Method of selecting samples for training each tree')   
    parser.add_argument('--regressor__max_depth', type=int, default=10,
                        help=' Maximum number of levels in tree')
    parser.add_argument('--regressor__max_features', type=str, default='auto',
                        help='Number of features to consider at every split')    
    parser.add_argument('--regressor__min_samples_leaf', type=int, default=4,
                        help='Minimum number of samples required at each leaf node')    
    parser.add_argument('--regressor__min_samples_split', type=int, default=5,
                        help='Minimum number of samples required to split a node')

    args = parser.parse_args()

    return args

def main():

    args = parse_args()
    
    lines = [
        f"Training data path: {args.prepared_data}",
        f"Model output path: {args.model_output}",
    ]

    for line in lines:
        print(line)

    print("mounted_path files: ")
    arr = os.listdir(args.prepared_data)
    print(arr)

    train_data = pd.read_csv((Path(args.prepared_data) / "train.csv"))

    # Split the data into input(X) and output(y)
    y_train = train_data[TARGET_COL]
    X_train = train_data[NUMERIC_COLS + CAT_NOM_COLS + CAT_ORD_COLS]

    # Train a Linear Regression Model with the train set

    # numerical features
    numeric_transformer = Pipeline(steps=[
        ('standardscaler', StandardScaler())])

    # ordinal features transformer
    ordinal_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(missing_values=np.nan, strategy="most_frequent")),
        ('minmaxscaler', MinMaxScaler())
    ])

    # nominal features transformer
    nominal_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(missing_values=np.nan, strategy="most_frequent")),
        ('onehot', OneHotEncoder(sparse=False))
    ])

    # imputer only for all other features
    imputer_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(missing_values=np.nan, strategy="most_frequent"))
    ])

    # preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('numeric', numeric_transformer, NUMERIC_COLS),
           #('ordinal', ordinal_transformer, CAT_ORD_COLS),
            ('nominal', nominal_transformer, CAT_NOM_COLS)], # other features are already binary
            remainder="drop")

    # append regressor to preprocessing pipeline.
    # now we have a full prediction pipeline.
    pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                          ('regressor', RandomForestRegressor(
                              n_estimators = args.regressor__n_estimators,
                              bootstrap = args.regressor__bootstrap,
                              max_depth = args.regressor__max_depth,
                              max_features = args.regressor__max_features,
                              min_samples_leaf = args.regressor__min_samples_leaf,
                              min_samples_split = args.regressor__min_samples_split,
                              random_state=0))])

    mlflow.log_param("model", "RandomForestRegressor")
    mlflow.log_param("n_estimators", args.regressor__n_estimators)
    mlflow.log_param("bootstrap", args.regressor__bootstrap)
    mlflow.log_param("max_depth", args.regressor__max_depth)
    mlflow.log_param("max_features", args.regressor__max_features)
    mlflow.log_param("min_samples_leaf", args.regressor__min_samples_leaf)
    mlflow.log_param("min_samples_split", args.regressor__min_samples_split)

    pipeline.fit(X_train, y_train)

    # Predict using the Regression Model
    yhat_train = pipeline.predict(X_train)

    # Evaluate Regression performance with the train set
    r2 = r2_score(y_train, yhat_train)
    mse = mean_squared_error(y_train, yhat_train)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_train, yhat_train)

    mlflow.log_metric("train r2", r2)
    mlflow.log_metric("train mse", mse)
    mlflow.log_metric("train rmse", rmse)
    mlflow.log_metric("train mae", mae)

    # Visualize results
    plt.scatter(y_train, yhat_train,  color='black')
    plt.plot(y_train, y_train, color='blue', linewidth=3)
    plt.xlabel("Real value")
    plt.ylabel("Predicted value")
    plt.savefig("regression_results.png")
    mlflow.log_artifact("regression_results.png")

    # Save the model
    pickle.dump(pipeline, open((Path(args.model_output) / "model.pkl"), "wb"))

if __name__ == "__main__":
    main()
    