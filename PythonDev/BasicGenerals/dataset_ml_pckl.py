    # ============================================================
# PIPELINE DE MACHINE LEARNING SUPERVISADO
# Clasificación binaria con Random Forest Classifier
# Dataset: Iris
# Clases seleccionadas:
#   0 -> setosa
#   1 -> versicolor
# ============================================================

# =========================
# 1. ENTRADA DE DATOS
# =========================

import pickle
import pandas as pd

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


# Cargar dataset Iris desde Scikit-Learn
iris = load_iris()

# Convertir el dataset en un DataFrame para facilitar su análisis
df_iris = pd.DataFrame(
    iris.data,
    columns=iris.feature_names
)

# Agregar la variable objetivo numérica
df_iris["target"] = iris.target

# Agregar el nombre de la especie
df_iris["species"] = df_iris["target"].map({
    0: "setosa",
    1: "versicolor",
    2: "virginica"
})

print("Dataset original:")
print(df_iris.head())

print("\nClases originales del dataset:")
print(df_iris["species"].value_counts())


# ------------------------------------------------------------
# Filtrar solamente 2 clases:
#   setosa     -> target 0
#   versicolor -> target 1
# ------------------------------------------------------------

df_binary = df_iris[df_iris["target"].isin([0, 1])].copy()

print("\nDataset filtrado para clasificación binaria:")
print(df_binary["species"].value_counts())


# Variables predictoras
X = df_binary[iris.feature_names]

# Variable objetivo
y = df_binary["target"]


# Separar datos en entrenamiento y prueba
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y
)


# =========================
# 2. MODELO DE MACHINE LEARNING
# =========================

# Crear modelo Random Forest Classifier
modelo_rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=5,
    random_state=42
)

# Entrenar modelo
modelo_rf.fit(X_train, y_train)

# Generar predicciones con datos de prueba
y_pred = modelo_rf.predict(X_test)

# Evaluar desempeño del modelo
accuracy = accuracy_score(y_test, y_pred)

print("\n==============================")
print("RESULTADOS DEL MODELO")
print("==============================")

print(f"\nAccuracy: {accuracy:.4f}")

print("\nMatriz de confusión:")
print(confusion_matrix(y_test, y_pred))

print("\nReporte de clasificación:")
print(classification_report(
    y_test,
    y_pred,
    target_names=["setosa", "versicolor"]
))


# ------------------------------------------------------------
# Importancia de variables
# ------------------------------------------------------------

feature_importance = pd.DataFrame({
    "feature": iris.feature_names,
    "importance": modelo_rf.feature_importances_
}).sort_values(by="importance", ascending=False)

print("\nImportancia de variables:")
print(feature_importance)


# ------------------------------------------------------------
# Ejemplo de predicción individual
# ------------------------------------------------------------

# Formato de entrada:
# [sepal length, sepal width, petal length, petal width]

nueva_flor = pd.DataFrame(
    [[5.1, 3.5, 1.4, 0.2]],
    columns=iris.feature_names
)

prediccion = modelo_rf.predict(nueva_flor)[0]

clases = {
    0: "setosa",
    1: "versicolor"
}

print("\nPredicción para una nueva flor:")
print(nueva_flor)
print(f"Clase predicha: {clases[prediccion]}")


# =========================
# 3. GUARDAR MODELO CON PICKLE
# =========================

# Se recomienda guardar no solamente el modelo,
# sino también metadata útil para el post-procesamiento.

artefacto_modelo = {
    "model": modelo_rf,
    "features": iris.feature_names,
    "target_classes": {
        0: "setosa",
        1: "versicolor"
    },
    "model_type": "RandomForestClassifier",
    "problem_type": "Binary Classification",
    "dataset": "Iris"
}

# Aquí guardas el nombre del archivo Pickle
pickle_filename = "iris_random_forest_binary_classifier.pkl"

# Guardar modelo entrenado
with open(pickle_filename, "wb") as file:
    pickle.dump(artefacto_modelo, file)

print("\n==============================")
print("MODELO GUARDADO")
print("==============================")
print(f"Archivo Pickle generado: {pickle_filename}")

# -------------------------------------------------------------------------------------------------------------------

# Ahora el código para guardar el Pickle, osea importarlo en otro código de python, así:

import pickle
import pandas as pd

with open("iris_random_forest_binary_classifier.pkl", "rb") as file:
    artefacto = pickle.load(file)

modelo = artefacto["model"]
features = artefacto["features"]
target_classes = artefacto["target_classes"]

nuevo_dato = pd.DataFrame(
    [[5.8, 2.7, 4.1, 1.0]],
    columns=features
)

prediccion = modelo.predict(nuevo_dato)[0]

print("Clase predicha:", target_classes[prediccion])