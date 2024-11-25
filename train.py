import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from tensorflow.keras.utils import to_categorical
import pickle

# Step 1: Load the CSV Data
print("Loading data from CSV file...")
df = pd.read_csv('gesture_data_calibrated_scaled.csv')

# Step 2: Encode Gesture Labels
print("Encoding gesture labels...")
label_encoder = LabelEncoder()
df['label'] = label_encoder.fit_transform(df['gesture'])

# Save the label encoder for future use
with open('label_encoder.pkl', 'wb') as f:
    pickle.dump(label_encoder, f)

# Step 3: Define Features and Labels
print("Defining features and labels...")
features = ['acc_x_g', 'acc_y_g', 'acc_z_g', 'gyro_x_dps', 'gyro_y_dps', 'gyro_z_dps']
X = df[features].values
y = df['label'].values

# Step 4: Segment Data into Windows
print("Segmenting data into windows...")
window_size = 20  # Number of samples per window
step_size = 10    # Overlap between windows

X_windows = []
y_windows = []

for i in range(0, len(X) - window_size + 1, step_size):
    X_window = X[i:i+window_size]
    y_window = y[i:i+window_size]
    # Use the most frequent label in the window as the label
    y_label = np.bincount(y_window).argmax()
    X_windows.append(X_window)
    y_windows.append(y_label)

X_windows = np.array(X_windows)
y_windows = np.array(y_windows)

# Step 5: Normalize the Data
print("Normalizing data...")
num_samples, window_length, num_features = X_windows.shape
X_reshaped = X_windows.reshape(-1, num_features)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_reshaped)

# Save the scaler for use during real-time detection
with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# Reshape back to original shape
X_scaled = X_scaled.reshape(num_samples, window_length, num_features)

# Step 6: One-Hot Encode Labels
print("One-hot encoding labels...")
num_classes = len(np.unique(y_windows))
y_categorical = to_categorical(y_windows, num_classes=num_classes)

# Step 7: Split Data into Training and Testing Sets
print("Splitting data into training and testing sets...")
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_categorical, test_size=0.2, stratify=y_windows, random_state=42)

# Step 8: Define the Model
print("Defining the model...")
model = Sequential()
model.add(Conv1D(64, kernel_size=3, activation='relu',
                 input_shape=(window_size, num_features)))
model.add(MaxPooling1D(pool_size=2))
model.add(Conv1D(128, kernel_size=3, activation='relu'))
model.add(MaxPooling1D(pool_size=2))
model.add(Flatten())
model.add(Dense(128, activation='relu'))
model.add(Dense(num_classes, activation='softmax'))

# Step 9: Compile the Model
print("Compiling the model...")
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Step 10: Train the Model
print("Training the model...")
history = model.fit(X_train, y_train, epochs=20, batch_size=32,
                    validation_data=(X_test, y_test))

# Step 11: Evaluate the Model
print("Evaluating the model...")
loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {accuracy * 100:.2f}%")

# Step 12: Save the Trained Model
print("Saving the trained model...")
model.save('gesture_recognition_model.h5')

# Step 13: Convert the Model to TensorFlow Lite
print("Converting the model to TensorFlow Lite format...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
# Optional: Enable optimization
# converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

# Save the TensorFlow Lite model
with open('gesture_recognition_model.tflite', 'wb') as f:
    f.write(tflite_model)

print("Model training and conversion complete.")

