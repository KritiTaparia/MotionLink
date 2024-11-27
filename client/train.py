import pickle
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.utils import to_categorical

# Step 1: Load the Dataset
with open('gesture_dataset.pkl', 'rb') as f:
    dataset = pickle.load(f)

# Step 2: Prepare Data and Labels
X = []
y = []
for sample in dataset:
    data = sample['data']
    gesture = sample['gesture']
    data_array = np.array(data).reshape(100, 6)
    X.append(data_array)
    y.append(gesture)

X = np.array(X)  # Shape: (num_samples, 100, 6)
y = np.array(y)

# Step 3: Encode Labels
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Save the label encoder
with open('label_encoder.pkl', 'wb') as f:
    pickle.dump(label_encoder, f)

# Step 4: One-Hot Encode Labels
num_classes = len(np.unique(y_encoded))
y_categorical = to_categorical(y_encoded, num_classes=num_classes)

# Step 5: Normalize the Data
num_samples, seq_length, num_features = X.shape
X_reshaped = X.reshape(-1, num_features)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_reshaped)

# Save the scaler
with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

X_scaled = X_scaled.reshape(num_samples, seq_length, num_features)

# Step 6: Split Data into Training and Testing Sets
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_categorical, test_size=0.2, stratify=y_encoded, random_state=42)

# Step 7: Define the Model
model = Sequential()
model.add(LSTM(64, return_sequences=True, input_shape=(seq_length, num_features)))
model.add(LSTM(64))
model.add(Dense(64, activation='relu'))
model.add(Dense(num_classes, activation='softmax'))

# Step 8: Compile the Model
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Step 9: Train the Model
history = model.fit(X_train, y_train, epochs=30, batch_size=16,
                    validation_data=(X_test, y_test))

# Step 10: Evaluate the Model
loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {accuracy * 100:.2f}%")

# Step 11: Save the Trained Model
model.save('gesture_recognition_model.h5')

# Step 12: Convert the Model to TensorFlow Lite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.experimental_enable_resource_variables = True
converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS,  # Enable TensorFlow Lite ops.
    tf.lite.OpsSet.SELECT_TF_OPS     # Enable TensorFlow ops.
]
converter._experimental_lower_tensor_list_ops = False
tflite_model = converter.convert()
with open('gesture_recognition_model.tflite', 'wb') as f:
    f.write(tflite_model)

print("Model training and conversion complete.")

